"""Provider mocks only: this suite must never contact Resend or send an email."""
import json
import socket

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings
from app.services.paid_email import (
    DisabledEmailTransport, EmailDeliveryUnavailable, RESEND_ENDPOINT,
    ResendEmailTransport, send_verification_email,
)

CODE = "A" * 43
SECRET = "re_mock_not_a_real_key"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("Email tests forbid actual network connections")
    monkeypatch.setattr(socket.socket, "connect", fail)
    monkeypatch.setattr(socket.socket, "connect_ex", fail)


@pytest.fixture
def settings():
    return Settings(_env_file=None, paid_email_provider="resend",
                    paid_email_from="signin@example.invalid", paid_email_resend_api_key=SECRET)


def adapter(handler):
    return ResendEmailTransport(SECRET, transport=httpx.MockTransport(handler))


def test_disabled_default_opens_no_client(monkeypatch):
    settings = Settings(_env_file=None)
    assert settings.paid_email_provider == "disabled"
    assert settings.paid_email_from == "" and settings.paid_email_resend_api_key.get_secret_value() == ""
    monkeypatch.setattr(httpx, "Client", lambda *a, **k: pytest.fail("disabled transport opened HTTP client"))
    with pytest.raises(EmailDeliveryUnavailable, match="^Email delivery unavailable$"):
        send_verification_email(settings, "user@example.invalid", CODE)


def test_success_submits_fixed_endpoint_plain_text_and_redacted_idempotency(settings):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"id": "mock-message-id"})
    send_verification_email(settings, "user@example.invalid", CODE, transport=adapter(handler))
    assert len(calls) == 1
    req = calls[0]
    assert req.method == "POST" and str(req.url) == RESEND_ENDPOINT
    assert req.headers["authorization"] == f"Bearer {SECRET}"
    key = req.headers["idempotency-key"]
    assert key.startswith("paid-verification-") and len(key) < 256
    assert CODE not in key and "user@example.invalid" not in key
    body = json.loads(req.content)
    assert set(body) == {"from", "to", "subject", "text"}
    assert body["from"] == "signin@example.invalid" and body["to"] == ["user@example.invalid"]
    assert CODE in body["text"] and "15" in body["text"]
    assert "http" not in body["text"]
    assert req.extensions["timeout"] == {"connect": 10.0, "read": 10.0, "write": 10.0, "pool": 10.0}


def test_stable_key_for_same_message_and_distinct_for_new_challenge(settings):
    keys = []
    def handler(request):
        keys.append(request.headers["idempotency-key"])
        return httpx.Response(200, json={"id": "mock"})
    for code in (CODE, CODE, "B" * 43):
        send_verification_email(settings, "user@example.invalid", code, transport=adapter(handler))
    assert keys[0] == keys[1] and keys[1] != keys[2]


@pytest.mark.parametrize("status", [201, 202, 301, 302, 307, 308, 400, 401, 403, 409, 422, 429, 500, 503])
def test_http_failure_is_redacted_and_not_retried_or_redirected(settings, status, caplog):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(status, headers={"location": "https://untrusted.invalid/"},
                              text=f"provider echoed {CODE} and {SECRET}")
    with pytest.raises(EmailDeliveryUnavailable) as exc:
        send_verification_email(settings, "user@example.invalid", CODE, transport=adapter(handler))
    assert len(calls) == 1
    assert str(exc.value) == "Email delivery unavailable" and exc.value.__cause__ is None
    assert CODE not in caplog.text and SECRET not in caplog.text


@pytest.mark.parametrize("exception", [httpx.ReadTimeout, httpx.ConnectTimeout, httpx.WriteTimeout, httpx.ConnectError])
def test_network_error_never_retries_and_redacts_uncertain_outcome(settings, exception, caplog):
    calls = []
    def handler(request):
        calls.append(request)
        raise exception(f"sensitive {SECRET} {CODE}", request=request)
    with pytest.raises(EmailDeliveryUnavailable) as exc:
        send_verification_email(settings, "user@example.invalid", CODE, transport=adapter(handler))
    assert len(calls) == 1 and str(exc.value) == "Email delivery unavailable"
    assert SECRET not in caplog.text and CODE not in caplog.text


@pytest.mark.parametrize("payload", [{}, {"id": ""}, {"id": None}, [], {"id": 3}])
def test_malformed_success_does_not_claim_acceptance(settings, payload):
    with pytest.raises(EmailDeliveryUnavailable):
        send_verification_email(settings, "user@example.invalid", CODE,
                                transport=adapter(lambda request: httpx.Response(200, json=payload)))


def test_non_json_success_is_redacted(settings):
    with pytest.raises(EmailDeliveryUnavailable, match="^Email delivery unavailable$"):
        send_verification_email(settings, "user@example.invalid", CODE,
                                transport=adapter(lambda request: httpx.Response(200, text=CODE)))


@pytest.mark.parametrize("sender", ["", "Name <signin@example.invalid>", "a@example.invalid,b@example.invalid", "a\r\nBcc:x@example.invalid", "@example.invalid", "a@-example.invalid"])
def test_invalid_sender_fails_before_network(settings, sender):
    settings.paid_email_from = sender
    with pytest.raises(EmailDeliveryUnavailable):
        send_verification_email(settings, "user@example.invalid", CODE,
                                transport=adapter(lambda request: pytest.fail("sent with invalid sender")))


@pytest.mark.parametrize("recipient", ["", "not-email", "a@example.invalid,b@example.invalid", "a\r\nBcc:x@example.invalid"])
def test_invalid_recipient_fails_before_network(settings, recipient):
    with pytest.raises(EmailDeliveryUnavailable):
        send_verification_email(settings, recipient, CODE,
                                transport=adapter(lambda request: pytest.fail("sent with invalid recipient")))


@pytest.mark.parametrize("code", ["", "short", "A" * 42 + "\n", "<html>" * 8])
def test_only_generated_code_format_is_sent(settings, code):
    with pytest.raises(EmailDeliveryUnavailable):
        send_verification_email(settings, "user@example.invalid", code,
                                transport=adapter(lambda request: pytest.fail("sent invalid code")))


@pytest.mark.parametrize("key", ["", "wrong_format", "re_unsafe\r\nheader", "re_unsafe key"])
def test_missing_or_invalid_key_fails_closed(settings, key):
    settings.paid_email_resend_api_key = SecretStr(key)
    with pytest.raises(EmailDeliveryUnavailable):
        send_verification_email(settings, "user@example.invalid", CODE)


def test_settings_redact_key_and_unknown_provider_rejected(settings):
    assert SECRET not in repr(settings) and SECRET not in settings.model_dump_json()
    with pytest.raises(ValidationError):
        Settings(_env_file=None, paid_email_provider="unknown")


def test_disabled_transport_cannot_send(settings):
    with pytest.raises(EmailDeliveryUnavailable):
        send_verification_email(settings, "user@example.invalid", CODE, transport=DisabledEmailTransport())


def test_provider_neutral_transport_receives_message_and_safe_key(settings):
    calls = []
    class FakeTransport:
        def send(self, message, *, idempotency_key):
            calls.append((message, idempotency_key))
    send_verification_email(settings, "user@example.invalid", CODE, transport=FakeTransport())
    assert calls[0][0].recipient == "user@example.invalid" and CODE in calls[0][0].text
    assert CODE not in calls[0][1]

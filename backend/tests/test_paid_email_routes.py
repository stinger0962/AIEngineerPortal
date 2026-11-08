"""Actual account endpoints + Resend adapter, with HTTP entirely mocked."""
import json
import re

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from test_paid_accounts import product, count
from app.models.entities import Account
from app.models.paid_accounts import PaidChallenge
from app.services import paid_accounts as auth, paid_email


def configure(product, monkeypatch, handler):
    product.app.dependency_overrides.pop(auth.get_sender)
    product.settings.paid_email_provider = "resend"
    product.settings.paid_email_from = "signin@example.invalid"
    product.settings.paid_email_resend_api_key = SecretStr("re_mock_not_real")
    original = paid_email.ResendEmailTransport
    monkeypatch.setattr(paid_email, "ResendEmailTransport", lambda key: original(key, transport=httpx.MockTransport(handler)))


def test_endpoint_to_adapter_to_verification_with_no_code_response(product, monkeypatch):
    sent = []
    def handler(request):
        sent.append(request)
        return httpx.Response(200, json={"id": "mock-id"})
    configure(product, monkeypatch, handler)
    response = product.client.post("/api/v1/account/challenges", json={"email": "user@example.invalid"})
    assert response.status_code == 200 and len(sent) == 1
    assert set(response.json()) == {"challenge_id", "expires_in"}
    code = re.search(r"\n\n([A-Za-z0-9_-]{43})\n\n", json.loads(sent[0].content)["text"]).group(1)
    assert code not in response.text and code not in str(sent[0].url)
    assert product.client.post("/api/v1/account/verify", json={
        "challenge_id": response.json()["challenge_id"], "code": code}).status_code == 200
    assert product.client.get("/api/v1/account/session").json()["authenticated"] is True
    assert count(product, Account) == 1


@pytest.mark.parametrize("failure", ["rejected", "timeout", "redirect", "malformed"])
def test_provider_failures_consume_challenge_without_resend(product, monkeypatch, caplog, failure):
    calls = []
    def handler(request):
        calls.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("provider might have accepted re_mock_not_real", request=request)
        if failure == "redirect":
            return httpx.Response(307, headers={"location": "https://untrusted.invalid"})
        if failure == "malformed":
            return httpx.Response(200, text="provider-broken")
        return httpx.Response(500, text="provider echoed re_mock_not_real and private body")
    configure(product, monkeypatch, handler)
    response = product.client.post("/api/v1/account/challenges", json={"email": "user@example.invalid"})
    assert response.status_code == 503 and response.json() == {"detail": "Email delivery unavailable"}
    assert len(calls) == 1 and count(product, Account) == 0
    code = re.search(r"\n\n([A-Za-z0-9_-]{43})\n\n", json.loads(calls[0].content)["text"]).group(1)
    with Session(product.engine) as db:
        challenge = db.scalar(select(PaidChallenge))
        assert challenge.consumed
        challenge_id = challenge.id
    assert product.client.post("/api/v1/account/verify", json={"challenge_id": challenge_id, "code": code}).status_code == 400
    assert code not in caplog.text and "re_mock_not_real" not in caplog.text


def test_provider_disabled_even_with_stale_credentials(product, monkeypatch):
    product.app.dependency_overrides.pop(auth.get_sender)
    product.settings.paid_email_provider = "disabled"
    product.settings.paid_email_resend_api_key = SecretStr("re_mock_not_real")
    product.settings.paid_email_from = "signin@example.invalid"
    monkeypatch.setattr(paid_email, "ResendEmailTransport", lambda *a: pytest.fail("disabled provider constructed"))
    assert product.client.post("/api/v1/account/challenges", json={"email": "user@example.invalid"}).status_code == 503
    assert count(product, Account) == 0

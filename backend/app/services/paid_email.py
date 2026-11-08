"""Provider-neutral verification email delivery. Disabled unless explicitly configured.

No SDK retries, background jobs, credentials, or sender domains are provisioned here.
A provider accepting a message is not proof of mailbox delivery.
"""
from dataclasses import dataclass, field
import hashlib
import re
from typing import Protocol

import httpx

from app.core.config import Settings

RESEND_ENDPOINT = "https://api.resend.com/emails"
_CODE = re.compile(r"^[A-Za-z0-9_-]{43}$")


class EmailDeliveryUnavailable(RuntimeError):
    """Safe boundary exception: never include request/provider bodies or secrets."""

    def __init__(self):
        super().__init__("Email delivery unavailable")


@dataclass(frozen=True)
class VerificationEmail:
    sender: str
    recipient: str = field(repr=False)
    subject: str
    text: str = field(repr=False)


class EmailTransport(Protocol):
    def send(self, message: VerificationEmail, *, idempotency_key: str) -> None:
        """Submit once or raise EmailDeliveryUnavailable; never retry implicitly."""
        ...


class DisabledEmailTransport:
    def send(self, message: VerificationEmail, *, idempotency_key: str) -> None:
        raise EmailDeliveryUnavailable()


def valid_mailbox(value: str) -> bool:
    # A plain mailbox only. No display names, address lists, headers or control chars.
    if not value or len(value) > 255 or value.count("@") != 1:
        return False
    if any(c.isspace() or ord(c) < 32 or ord(c) == 127 or c in '<>,;\\"()' for c in value):
        return False
    local, domain = value.split("@")
    if not local or not domain or len(local) > 64:
        return False
    try:
        domain = domain.encode("idna").decode("ascii")
    except UnicodeError:
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", domain)
                and "." in domain and all(label and not label.startswith("-") and not label.endswith("-")
                                          and len(label) <= 63 for label in domain.split(".")))


class ResendEmailTransport:
    def __init__(self, api_key: str, *, transport: httpx.BaseTransport | None = None):
        # Configuration is never logged or included in an error's text/repr.
        if not api_key.startswith("re_") or any(ord(c) < 33 or ord(c) > 126 for c in api_key):
            raise EmailDeliveryUnavailable()
        self._api_key = api_key
        self._transport = transport  # Only tests inject an in-memory MockTransport.

    def send(self, message: VerificationEmail, *, idempotency_key: str) -> None:
        if not valid_mailbox(message.sender) or not valid_mailbox(message.recipient):
            raise EmailDeliveryUnavailable()
        try:
            # No retry configuration. Explicit redirect rejection prevents forwarding
            # the Authorization header, recipient or code to another endpoint.
            with httpx.Client(transport=self._transport, timeout=10.0,
                              follow_redirects=False, trust_env=False) as client:
                response = client.post(RESEND_ENDPOINT, headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Idempotency-Key": idempotency_key,
                }, json={"from": message.sender, "to": [message.recipient],
                         "subject": message.subject, "text": message.text},
                    follow_redirects=False)
            # Do not disclose provider response bodies (they may echo request data).
            if response.status_code != 200:
                raise EmailDeliveryUnavailable()
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("id"), str) or not payload["id"].strip():
                raise EmailDeliveryUnavailable()
        except Exception:
            # Includes timeouts after acceptance: outcome may be uncertain. The
            # calling challenge is invalidated and there is no automatic resend.
            raise EmailDeliveryUnavailable() from None


def send_verification_email(settings: Settings, recipient: str, code: str,
                            *, transport: EmailTransport | None = None) -> None:
    if transport is None:
        if settings.paid_email_provider == "disabled":
            raise EmailDeliveryUnavailable()
        if settings.paid_email_provider != "resend":
            raise EmailDeliveryUnavailable()
        transport = ResendEmailTransport(settings.paid_email_resend_api_key.get_secret_value())
    sender = settings.paid_email_from.strip()
    if not valid_mailbox(sender) or not valid_mailbox(recipient) or not _CODE.fullmatch(code):
        raise EmailDeliveryUnavailable()
    message = VerificationEmail(sender=sender, recipient=recipient,
        subject="登录验证码 / Your sign-in code",
        text=(f"你的登录验证码 / Your sign-in code:\n\n{code}\n\n"
              "验证码将在 15 分钟后过期，仅可使用一次。请只在你刚才申请登录的网站输入。\n"
              "This code expires in 15 minutes and can be used once. Enter it only on the website where you requested sign-in.\n"
              "如非本人操作，请忽略此邮件，不要转发验证码。\n"
              "If you did not request this, ignore this email. Do not share the code.\n"))
    # Stable for the same logical message, without placing the email/code in a URL
    # or header. A new user-requested challenge naturally gets a different key.
    key = "paid-verification-" + hashlib.sha256((recipient + "\0" + code).encode()).hexdigest()
    try:
        transport.send(message, idempotency_key=key)
    except Exception:
        raise EmailDeliveryUnavailable() from None

# Paid-product verification email boundary

This is nonproduction preparation. No provider account, API key, sender/domain verification, DNS record, live delivery or deployment is configured by this branch.

## Configuration and default behavior

`PAID_EMAIL_PROVIDER=disabled` is the default. `PAID_EMAIL_FROM` and `PAID_EMAIL_RESEND_API_KEY` default to empty values. Disabled transport fails closed even if stale sender/key values exist. `PAID_ACCOUNTS_ENABLED` independently defaults to false.

The optional implementation is selected with `PAID_EMAIL_PROVIDER=resend`, a plain verified sender mailbox in `PAID_EMAIL_FROM` (no display name/address list), and an authorized key in `PAID_EMAIL_RESEND_API_KEY`. The key uses Pydantic `SecretStr` and is excluded from the settings representation; do not put a real key in committed examples. No sender is selected here. Sender verification, account access, provider limits and any credentials need separate authorized configuration.

`app.services.paid_email.EmailTransport` is a provider-neutral, submit-once boundary. A future provider implements `send(message, idempotency_key=...)`; account routes and the frontend do not change. `get_sender` retains its existing injectable `(email, code)` function contract for isolated tests. No API/debug route exposes codes.

The Resend adapter submits plain-text verification messages to the fixed `https://api.resend.com/emails` endpoint, with a 10-second timeout per HTTP phase. It does not follow redirects, use environment proxy configuration, or configure retries. A stable hash of recipient and code supplies the per-message idempotency key; the raw code/address never goes into a URL or idempotency header. The code is necessarily present in the private email body. A provider's successful response means accepted for sending, not delivery to the recipient's mailbox.

## Failure and uncertain outcomes

Provider bodies, request contents, credentials and exception strings are not returned or logged by the adapter. Account routes return the existing generic `503 Email delivery unavailable` and mark that challenge consumed on delivery failure. This includes timeouts or malformed responses after the provider may have accepted the message. There is **no automatic resend**, failover or retry. A delivered code from a failed/uncertain attempt is intentionally unusable; the user can explicitly request a new challenge. New challenges produce new messages and remain subject to the existing IP/email limits.

Do not turn an uncertain provider response into a delivery-success claim. Actual delivery/bounce feedback and provider-dashboard reconciliation are future operational work. The adapter does not subscribe to provider webhooks or create persistent access.

## Tests and later real-mail validation

- `backend/tests/test_paid_email.py`: in-memory HTTP tests for request format, stable idempotency, disabled/missing configuration, invalid addresses/codes, redirect rejection, errors, timeouts, malformed responses, no retry and secret redaction.
- `backend/tests/test_paid_email_routes.py`: actual account endpoints through the adapter with `httpx.MockTransport`, then verification and session creation. Rejected/uncertain attempts invalidate codes. No external email is sent.
- Existing fresh-account tests retain their in-memory sender and ownership/security coverage.

Before activation, authorize the exact sender/domain and credential setup; verify the provider's account and domain, approved origin/cookie routing and nonproduction mailbox recipient; run a controlled real-email test and HTTPS browser-to-backend flow. Confirm failure/retry behavior, proxy policy, rate limits and retention. Provider-accepted mocks are not proof of deliverability, and this milestone does not enable real payments.

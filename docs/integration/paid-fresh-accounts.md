# Fresh verified accounts (nonproduction preparation)

Builds on the paid-product foundation (PR #20), not the migration/recovery PR #19. It adds one fresh mailbox-verified account shared by Ziwei, Qian and the credit ledger. Existing personal-portal accounts/data are never bound, matched or imported.

## Flow

`POST /api/v1/account/challenges` accepts `{email}` for both signup and return visits. `POST /verify` accepts `{challenge_id, code}`. A first successful verification creates a new account and welcome grant once; later verifications restore that account and revoke prior sessions. No account or profile is adopted from a device header or an old email field. Qian becomes account-owned but its pricing is not changed by this milestone.

`GET /session` returns `{authenticated, enabled, account_id}` (the account ID is nonsecret). Current logout clears stale cookies; logout-all revokes sessions for the authenticated account. Feature pages are gated before fetching private data, and the backend independently rejects unauthenticated requests. Disabled accounts fail closed on all private paid APIs; Stripe test webhooks still require their existing signature rather than a browser session.

All browser API calls require `X-Paid-Client: 1`, credentials included, and no device identity. Host-only, HttpOnly sessions never enter browser storage or URLs. HTTPS uses `__Host-paid_session`; isolated local HTTP tests use `paid_session_local` only with `PAID_SESSION_SECURE=false` and `APP_ENV=development/test`. Cookies are SameSite=Strict. Requests carrying an Origin must match configured CORS origins; supplied forwarding headers are not trusted for rate limiting.

## Nonproduction switches and email

`PAID_ACCOUNTS_ENABLED=false` by default. The frontend paid mode shows an unavailable notice until the backend is enabled. Even when enabled, email fails closed with 503 until an authorized transport is configured. `get_sender` remains injectable; the [optional provider-neutral/Resend adapter](paid-email-delivery.md) is disabled by default. Tests use in-memory fakes or mocked HTTP; there is no API/debug endpoint returning codes. No credentials or domain records are installed.

For isolated tests only, explicitly enable accounts and choose local cookie mode. A running preview still cannot log in until a reviewed sender is configured; use backend tests to exercise the fake outbox. Do not enable anonymous fallback or expose codes to make a demo work.

## Retention and launch requirements

Challenges expire after 15 minutes and are one-use. Sessions expire after 30 days; stored values are hashes. Rate limits count failed attempts, using per-IP/per-email/per-challenge hourly buckets. `purge_expired_auth_records` removes only expired auth material and is a maintenance primitive. A [dry-run-default maintenance CLI](paid-account-retention.md) is available; no scheduler is installed. Before public launch, review proxy trust and retention scheduling, choose and authorize a sender, validate real delivery and browser-to-backend HTTPS flows, and review final account/payment security. These tasks are not implied complete by mocked browser or fake-email tests.

## Verification

`backend/tests/test_paid_accounts.py` covers signup, replay/expiry, concurrent verification, credit grants, email/feature ownership, isolation, cookies/CSRF, revocation, disabled access and fake-sender failure. Existing portal regression tests remain required. `frontend/scripts/paid-account-test.cjs` covers cookie-only request contracts and failures; `paid-account-browser-test.cjs` covers gates, invalid codes, restarting a challenge, duplicate submissions, login/logout disabled states and cross-tab session changes with API responses mocked. Feature gates recheck on focus/pageshow, cross-tab signals and 401 responses; account changes remount private feature state.

## Browser-to-backend integration QA

`scripts/test-paid-browser-integration.sh` starts the real paid FastAPI app with a
fresh disposable SQLite database, a Next production build, and a same-origin
loopback proxy. Build the frontend first with `NEXT_PUBLIC_PRODUCT_MODE=paid`
and `NEXT_PUBLIC_API_BASE_URL=/api/v1`; install Playwright Chromium. Optional
`QA_PYTHON`, `QA_PLAYWRIGHT` and `QA_CHROMIUM` point at local test tooling.

Unlike the earlier browser checks, this suite does not mock API responses. It
covers desktop/mobile signup, invalid-code retry, mailbox-tab return, HttpOnly
cookies, private profile persistence, cross-account isolation, returning-account
identity, old-session revocation, CSRF rejection and logout-all. Only email
delivery is replaced: reserved `example.test` addresses and codes are captured in
an owner-only temporary directory, deleted with the disposable database on exit.
No code-retrieval HTTP endpoint exists. The fixture lives under `backend/tests`,
requires an explicit test-only guard, rejects backend outbound connections, and
is never imported by the production app. No actual emails or AI calls are made.

This fixture deliberately uses **local HTTP and the development cookie**, not
production TLS. Secure `__Host-` cookie attributes remain API-tested; actual
HTTPS/browser behavior and the launch reverse proxy must still be verified in an
authorized staging environment. CI uploads server logs, never the outbox or DB.

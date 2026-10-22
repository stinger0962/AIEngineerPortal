# Ziwei Stripe TEST integration acceptance — 2026-10-22

Integration starts from unchanged main `6c909b235fed2c81f1153a67d8f4bed36dab3fb5`.
Preserved commits:

- Backend: `dee0bd025485e80260d5fc04b455f0e2e978d1c3`
- Frontend: `3335735d4caf0c7007e7f306407bb0e3f6ddfee7`
- Independent QA: `fdd8f02b81ff80325921e5186e70a5cbba341aad`

## Integration corrections

Valid synthetic webhook fixtures now contain `mode=payment` and stored order/account
metadata, and the isolated test callback differs from the production host. The
credit-race barrier runs before lock acquisition instead of deadlocking inside a
correct lock-before-read implementation. Assertions still require one debit or
one grant, correct ownership, signature rejection, and test/live isolation.

New stream conversations are created in the generation transaction after credit
reservation. Rejected, failed, or disconnected first readings leave no orphan
conversation. Partial salvage remains possible for an existing conversation;
failed first readings roll back their new conversation and messages together.

The UI restores the complete pending oracle payload (including conversation ID)
with its persisted retry key. Submitted request A is separate from editable draft
B; recovery and explicit retry no longer overwrite B. Checkout keys bind to their
returned order IDs, so an old order return cannot clear a newer attempt. Payment
return state updates on Next search navigation and `pageshow` restoration.

## Verification

All API/provider effects were mocked. Initial database data was disposable SQLite;
the follow-up below also exercises real isolated PostgreSQL 16.15. Network sockets
were blocked during the full backend SQLite run. No real AI, Stripe,
production database, external migrations, deployment, or credentials were used.

Focused combined suite: **97 passed**:

```sh
/tmp/ziwei-qa-venv/bin/python -m pytest backend/tests/acceptance backend/tests/test_billing_stripe.py backend/tests/test_credits.py backend/tests/test_ziwei_oracle_routes.py backend/tests/test_ziwei_stream.py backend/tests/test_qian_routes.py -q --tb=short
```

Includes 41 independent acceptance cases: concurrent/duplicate webhooks, forced
overlapping reads, one-credit concurrent generation, account/order ownership,
payment validation, live isolation, retry contracts, failure rollback, generator
closure, and a real ASGI `http.disconnect` followed by same-key retry. ASGI testing
uses the application directly in-process; it is not a proxy/browser disconnect test.

Full backend suite: **373 passed, 6 failed**, exit 1. The six failures also reproduce
on the original main snapshot with the same SQLite JSONB adapter:

- `test_api.py::test_phase_four_python_lesson_has_real_depth`
- `test_api.py::test_seed_sync_is_idempotent_and_keeps_reference_content_populated`
- `test_api.py::test_phase_four_interview_question_has_answer_framework_depth`
- `test_ziwei_routes.py::test_create_profile`
- `test_ziwei_routes.py::test_get_update_delete_profile`
- `test_ziwei_routes.py::test_update_profile_ignores_explicit_nulls`

The first three assert stale seeded content/counts; the latter three omit the
existing required device identity. Baseline comparison: **22 passed, 6 failed**
across those two files. No unrelated baseline tests/application content were changed.
The network guard used a pytest autouse fixture blocking `socket.socket.connect`,
`connect_ex`, and `socket.create_connection`; JSONB compiled to JSON for SQLite.

Frontend commands (from `frontend/`):

```sh
node scripts/ziwei-billing-test.cjs
./node_modules/.bin/tsc --noEmit
NEXT_PUBLIC_ZIWEI_TEST_BILLING=false NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1 npm run build
```

Offline adapter/retry/component checks and TypeScript pass. The final production
build passes with billing disabled, exit 0; it logs a nonfatal dynamic-font fetch
warning during image generation. No deployment followed the build.

Actual Chromium browser checks, against a local Next dev server only:

```sh
NEXT_PUBLIC_ZIWEI_TEST_BILLING=true NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:3100/api/v1 npm run dev -- --hostname 127.0.0.1 --port 3100
QA_PLAYWRIGHT=/tmp/qa-browser/node_modules/playwright node scripts/ziwei-browser-test.cjs
```

All browser checks pass: navigation/payment return, pending-to-paid server
confirmation, synthetic persisted `pageshow`, draft B preservation after A fails,
reload of A's full conversation/payload/key, identical-key retry, and credit refresh
on success. No page exceptions. Every API request is intercepted; external origins
are blocked. The system Chromium `154.0.8037.57` was used after the Playwright browser
CDN returned HTTP 403 `Domain forbidden`; no download workaround or credentials
were used. This is mocked browser UI acceptance, **not** real Stripe end-to-end.
No external preview was deployed; the localhost dev server was stopped after testing.

## Transaction review and limits

- Conditional order status UPDATE and purchase ledger insertion commit atomically.
  Parallel signed deliveries cannot credit twice in the tested SQLite runs.
- Account UPDATE serializes balance decreases before SUM. Debit, BillingRequest,
  and successful reading commit together. Completed same-key replays return 409;
  failure/disconnect before commit rolls back and permits the same key.
- Checkout intent commits before contacting mocked Stripe; retries retain the
  provider key. Pending intent can survive final-persistence contention. Unresolved
  orders older than 23 hours require reconciliation rather than provider-key reuse.
- Locks remain held **through generation**. SQLite serializes all writers;
  PostgreSQL is intended to serialize per-account rows at normal READ COMMITTED.
  Busy/deadlock handling returns retryable 503. The 2-second default timeout bounds
  each lock wait, not generation time, total request time, or pool checkout.
- Slow upstream generation may still tie up a transaction/connection. Process-kill,
  network-proxy disconnect, crash-after-commit, alternative PostgreSQL isolation
  levels, and an actual PostgreSQL deadlock cycle were not exercised. Local
  PostgreSQL READ COMMITTED concurrency and lock-timeout checks now pass below.
- X-Device-Id remains the existing anonymous bearer identity, not login-based auth.

## Pending security and external acceptance

Parent explicitly deferred changes to legacy profile auto-adoption and callback
host validation because a separate security-fix action was denied by approval
review. Those implementations are unchanged by this integration; approval/review
remains pending. Isolated QA uses `ziwei_auto_adopt=false`. Passing these fixtures
does not establish safe legacy adoption or exhaustive callback-host validation.

Real Stripe TEST Checkout/webhook delivery and payment-method availability remain
pending. Local PostgreSQL concurrency/migration checks are now complete below. There is no live payment
verification. Qian charging was not introduced; the backend branch includes
read-history ownership tightening, preserved as supplied.

Deployment workflows remain unchanged: pushed `v*` tags trigger release/deployment,
and manual workflow dispatch can deploy. Feature-branch pushes do not trigger them.
No tags, main push/merge, PR, deployment, production changes, or persistent credential
creation are part of this integration task.


## Real PostgreSQL follow-up — 2026-10-22

Available local capability: Docker 28.4.0 and cached official `postgres:16-alpine`
image. No host postgres/initdb/psql binary or package installation was needed.
Started PostgreSQL **16.15**, isolated to `127.0.0.1:55432`, using an ephemeral tmpfs
data directory and a disposable `ziwei_qa` database. The test-only container uses
trust authentication for its disposable data; no external credentials were created
and no host authentication/security configuration changed. Container is removed
after testing. Existing images and other containers are untouched.

Reproduction (requires that cached image and the Python requirements):

```sh
docker run --detach --rm --pull=never --name ziwei-qa-postgres-20261022 \
  --publish 127.0.0.1:55432:5432 --tmpfs /var/lib/postgresql/data \
  -e POSTGRES_HOST_AUTH_METHOD=trust -e POSTGRES_USER=ziwei_qa \
  -e POSTGRES_DB=ziwei_qa postgres:16-alpine
# Wait until this returns accepting connections:
docker exec ziwei-qa-postgres-20261022 pg_isready -U ziwei_qa -d ziwei_qa
ZIWEI_QA_POSTGRES_URL=postgresql+psycopg://ziwei_qa@127.0.0.1:55432/ziwei_qa \
  /tmp/ziwei-qa-venv/bin/python -m pytest backend/tests/acceptance -q --tb=short
docker stop ziwei-qa-postgres-20261022
```

The fixture rejects any PostgreSQL target other than this exact local host,
port, and database. Each test uses a unique schema, dropped on teardown.
Python provider sockets remain blocked; psycopg/libpq connects to the explicitly
validated local database. Stripe and AI stay mocked throughout.

Results: **45 passed** on PostgreSQL, including all 41 original acceptance cases
and four dedicated PostgreSQL cases. SQLite cross-check: **41 passed, 4 skipped**;
only the four explicitly PostgreSQL-specific cases skip without its opt-in URL.

Evidence includes real concurrent webhook fulfillment (including forced overlapping
order reads), concurrent one-credit consumption/generation, rollback after failure
and ASGI disconnect, and same-key replay/retry semantics on PostgreSQL.
Dedicated PostgreSQL checks verify:

- Migration runs twice after fresh application bootstrap and after removing the
  new table to represent an existing baseline fixture schema. Existing account,
  order and ledger data survive, and the new idempotency table accepts/readbacks
  records. The migration is additive and assumes baseline `accounts` already exists.
- A locked/debited account does not block another account's successful debit at
  PostgreSQL READ COMMITTED isolation; rolling back the first restores its credit.
- Real contention returns HTTP 503 `billing_busy` / Retry-After 2 within the configured
  100 ms lock-timeout test budget (under 1.5 seconds including HTTP overhead), makes
  no AI call, rolls back, and permits the same-key successful retry after release.

No application fix was needed for these PostgreSQL cases. This verifies local
PostgreSQL 16.15 behavior, not production configuration, other isolation levels,
proxy failures, process crashes, or real deadlock cycles.

## Stripe configuration inventory and smallest next requirement

Read-only inspection of effective local settings (presence/mode only):

- `STRIPE_TEST_ENABLED`: false.
- `STRIPE_SECRET_KEY`: absent (neither test nor live key present).
- `STRIPE_WEBHOOK_SECRET`: absent.
- `STRIPE_TEST_BASE_URL`: absent.
- `ZIWEI_REQUIRE_CREDITS`: false.
- Stripe CLI executable: absent.

To perform genuine sandbox verification later, the smallest inputs are an authorized
Stripe TEST key, a TEST webhook signing secret, explicit isolated callback URL,
and explicit enabling of test billing. For example, use
`STRIPE_TEST_BASE_URL=http://127.0.0.1:3100` for the local UI, with a separate disposable
backend/database on localhost. Enable `NEXT_PUBLIC_ZIWEI_TEST_BILLING=true` in that
local UI build and `ZIWEI_REQUIRE_CREDITS=true` only for credit-enforcement checks.
AI must remain mocked; do not add provider credentials.

The safe webhook approach is an authorized Stripe CLI `listen` session forwarding
TEST events to `http://127.0.0.1:8000/api/v1/billing/webhook`; use that session's
signing secret only in the isolated backend. This requires installing the official
CLI and approved temporary Stripe authentication first. Do not forward to production
or register/configure an external endpoint as part of this task. No CLI installation,
Stripe connection, external request, credential creation, or enabling was performed.
The two separately denied security changes remain pending parent approval.

## Residual retry-draft correction

Independent frontend review reproduced recovered A remaining as an unsent draft
after an explicit retry succeeded. The success handler now clears that matching
draft only if the input edit version is unchanged. Distinct B or any edit made
during the retry is preserved. Chromium regression now additionally verifies that
successful retry clears recovered A from the textarea and session storage, reuses
A's original request key/body, and disables ordinary send on the empty draft.
The earlier browser assertion that B survives successful retry still passes.
All four browser checkpoint groups pass with mocked APIs and no page exceptions;
offline frontend tests and TypeScript also pass after this correction.

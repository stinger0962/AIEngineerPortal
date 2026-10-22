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

All API/provider effects were mocked, database data was disposable SQLite, and
network sockets were blocked during the full backend run. No real AI, Stripe,
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
  levels, and real PostgreSQL deadlock/locking behavior were not exercised.
- X-Device-Id remains the existing anonymous bearer identity, not login-based auth.

## Pending security and external acceptance

Parent explicitly deferred changes to legacy profile auto-adoption and callback
host validation because a separate security-fix action was denied by approval
review. Those implementations are unchanged by this integration; approval/review
remains pending. Isolated QA uses `ziwei_auto_adopt=false`. Passing these fixtures
does not establish safe legacy adoption or exhaustive callback-host validation.

Real Stripe TEST Checkout/webhook delivery, payment-method availability, and real
PostgreSQL concurrency/migration checks remain pending. There is no live payment
verification. Qian charging was not introduced; the backend branch includes
read-history ownership tightening, preserved as supplied.

Deployment workflows remain unchanged: pushed `v*` tags trigger release/deployment,
and manual workflow dispatch can deploy. Feature-branch pushes do not trigger them.
No tags, main push/merge, PR, deployment, production changes, or persistent credential
creation are part of this integration task.

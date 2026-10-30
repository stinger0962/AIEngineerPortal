# Ziwei Stripe TEST integration acceptance — 2026-10-22

## Infrastructure clarification — 2026-10-30

Permanent staging and a second server are **optional**, not a gate for the
completed payment acceptance or reviewed implementation. Codex + the temporary
Stripe CLI + the user's browser already proved Alipay test payment, genuine
signed webhook delivery and the exact 0-to-10 grant. That listener is stopped.

The manual test's localhost return URL could not reach the Codex UI from the
user's machine. This leaves actual hosted success/cancel return interaction
unverified, not payment fulfillment. Local mocked browser tests cover return,
cancel/resume and recovery behavior. If further real return-page coverage is
wanted, running UI/backend/CLI with the browser on a developer computer needs
no second server. An existing authorized preview or isolated same-host instance
is optional; no preview, tunnel, host change or production test setup was enabled.

The [readiness assessment](ziwei-deployment-readiness.md) now makes these options
and the actual approval boundaries explicit. No staging hostname, provider
purchase or persistent webhook is currently required to complete this scope.
This clarification changes documentation only, not guards or verified coverage.

## Independent review and readiness — 2026-10-30

A fresh read-only reviewer inspected the cumulative diff and reproduced one
substantive issue: cached Checkout URLs bypassed terminal-order and age checks.
The correction reports paid/failed state for client recovery before returning a
URL; unresolved intents older than 23 hours return explicit reconciliation state.
The adapter clears only confirmed terminal keys; pending reconciliation retains
the key and blocks automatic repurchase. The reviewer rechecked the correction
and found no additional substantive issue in the reviewed scope.

This is safe refusal and terminal recovery, not automatic provider expiry
reconciliation. Sessions expired externally within 23 hours are not detected
without provider retrieval; unresolved old pending orders require manual
reconciliation. No new provider call, payment, key or listener was used here.

Final local focused suite: **138 passed, 4 PostgreSQL-only skips**. Full offline
backend: **414 passed, the same 6 inherited failures, 4 skips**. Frontend offline,
TypeScript and mocked browser checks passed, including paid/failed/stale Checkout
recovery without redirecting to a dead URL. The billing-disabled frontend build
also passed, retaining the nonfatal dynamic-font lookup warning. CI now covers deployment runtime
versions Python 3.11 / Node 20 as well as Python 3.12 / Node 22. Exact remote run
results are linked in PR #2 rather than inferred from local success.

[Deployment readiness](ziwei-deployment-readiness.md) records actual callback and
build-variable sources, optional persistent-staging prerequisites, additive migration,
webhook requirements for persistent deployments, bearer-device ownership, rollback/drain constraints and production
blockers. Existing deployment docs were corrected to describe builds in Actions
and image pulls on the VPS, not manual VPS builds. No deployment configuration,
main branch, release tag, credential or access setting was changed.

## Implementation completion checks — 2026-10-29

Follow-up development remains on `integration/ziwei-stripe-test`; PR #2 is open
and draft. No AGENTS.md or local skill files were found. No new provider session,
payment, listener, credential, trust setting, network rule, or production change
was needed for this follow-up.

### Corrections and regression coverage

- Cancellation now retains the same-pack Checkout key across return/reload so
  retry resumes the existing order. Server-confirmed paid/failed clears only the
  matching key. Server-paid state overrides an old cancel flag, and delayed
  responses from a previous navigation cannot replace the current return state.
- Asynchronous failure validates session purchase amount, currency, payment mode,
  order and account metadata before changing order state. A late failure cannot
  downgrade paid; delayed paid success after failure grants exactly once.
  Concurrent success/failure is covered on SQLite and PostgreSQL.
- Callback validation rejects malformed ports, ambiguous whitespace/backslashes,
  credentials, queries/fragments and path parameters. HTTP is limited to loopback;
  separate tester computers need a reachable nonproduction HTTPS callback to
  view return pages (not to prove payment through CLI-forwarded webhooks). No such host was provisioned and no deployed configuration changed.
- Added a non-deploying GitHub Actions workflow for this feature branch and
  relevant pull requests: focused SQLite regressions, PostgreSQL acceptance,
  frontend offline checks and TypeScript. It uses no Stripe/provider secrets and
  does not invoke either existing release/deployment workflow.

### Local verification

- Focused backend: **135 passed, 4 PostgreSQL-only skips**.
- Disposable PostgreSQL acceptance: **83 passed**. Verified zero remaining QA
  schemas and stopped/removed `ziwei-qa-postgres-20261029` afterward.
- Full backend with provider keys cleared, sockets blocked, and SQLite JSONB
  adapter: **411 passed, 6 inherited failures, 4 skips**.
- Independently extracted unchanged baseline `6c909b2` into `/tmp` and ran the
  two affected modules with the same offline harness: **22 passed, the same six
  failures**. Three seeded-content/count assertions are stale (including 9
  learning paths versus expected 7); three profile fixtures omit the existing
  required device identity. No related application behavior regressed, and these
  unrelated baseline tests were left unchanged.
- Frontend offline billing checks and TypeScript: **passed**.
- Production frontend build with billing disabled: **passed**, with the existing
  nonfatal dynamic Google-font lookup warning. Nothing was deployed.
- Local Chromium browser regressions: **passed**, including mocked cancellation,
  reload/same-key resume, server confirmation over cancel flags, stale-response
  rejection, newer-draft preservation, retry and credit refresh. All external
  requests were intercepted or blocked; none of these cases is a hosted Stripe
  cancellation or provider redelivery test.

Genuine Alipay success below remains the real-provider acceptance evidence.
Automated hosted Chromium, card/WeChat, hosted cancel/resume, genuine duplicate
redelivery and delayed provider success remain unverified. The implementation's
corresponding return/event behavior is covered locally; these limitations do not
justify further payments or security configuration changes without authorization.
Production release and reconciliation of subscription versus credit-pack product
intent remain separate decisions. Generation still holds database locks through
model execution, as documented in the original transaction review.

## Genuine Alipay sandbox payment and webhook — 2026-10-29

With explicit user approval, downloaded official Stripe CLI v1.55.3 Linux x86_64
from the GitHub release and verified the archive against its published
`stripe-linux-checksums.txt` (SHA-256
`a894f7891eac5eabb67a5ad5b4820a236626a805b9be544fb4c6e41c5ad91043`).
Extracted under `/tmp`; no system installation, login, persistent Dashboard
webhook registration, or trust/network changes occurred.

A temporary test-only listener subscribed to this account's
`checkout.session.completed`, `checkout.session.async_payment_succeeded`, and
`checkout.session.async_payment_failed` events and forwarded to
`127.0.0.1:8000/api/v1/billing/webhook`. The API key remained in process environment;
the signing secret was captured directly into memory and never written to files,
logs, or artifacts. The local application billing router used an isolated
in-memory SQLite database and zero starting credits. No AI calls were made.

The actual application service created one CNY 9.90 Checkout for ten credits.
Existing USD subscriptions remained unchanged. The user opened the hosted link
in their normal browser and authorized the Alipay test payment. This bypassed
neither Chromium's warning nor any security setting: automated browser testing
remains separately blocked as documented below.

### Verified result

- At **15:42:07 UTC**, Stripe generated the matching genuine
  `checkout.session.completed` event. Its object already had
  **`payment_status=paid`**, `mode=payment`, `livemode=false`, CNY amount 990.
- Event/session identity and order/account metadata matched the controlled test
  order. Event ID: `evt_1UVvStK1mmznAGURGnPpmavm`.
- The real webhook reached the unmodified application signature-verification and
  fulfillment route and returned **HTTP 200**. No synthetic event or manual grant
  was used.
- Local order changed to **paid**, and balance changed from **0 to exactly 10**.
  A subsequent status check still showed 10 and exactly one recorded delivery.
- Expanded Stripe retrieval independently confirmed payment method **alipay**,
  PaymentIntent **succeeded**, charge `paid=true`, charge `livemode=false`.
  Completion alone was not used as proof of payment: paid status was checked.
- Only one matching completed event and one delivery were observed. This verifies
  no extra credit grant in this flow; it does **not** test real duplicate webhook
  redelivery or the delayed asynchronous-success path.

Cleanup preserved the completed paid session, stopped the listener/backend, and
was confirmed by absent supervisor/listener processes and a closed localhost
backend port. Post-cleanup Stripe retrieval remained `complete`/`paid`. The
in-memory QA balance disappeared with the disposable process; no production
account was credited. CLI temporary files contain no credentials. The test
Checkout URL is intentionally omitted from this report.

Remaining coverage: automated Chromium hosted interaction, hosted cancellation
and resume, card/WeChat payments, delayed asynchronous payment, and genuine
webhook redelivery. Existing mocked regression coverage is separate. This
follow-up changes evidence only; main, production, and release tags are unchanged.

## Hosted browser follow-up — 2026-10-29

A separately approved diagnostic at 13:04:09 UTC used the normal HTTP proxy
`proxy:8080`: CONNECT to `checkout.stripe.com:443` returned 200, followed by an
HTTPS 302 to the `stripe.com` hostname. The redirect was not followed. This
established recovered tunnel access, not the cause of the earlier 403.

Resumed the authorized hosted test using local Next.js at `127.0.0.1:3100` and
an isolated FastAPI billing router at `127.0.0.1:8000`, with an in-memory SQLite
schema, zero free credits, and no AI calls. The published credential was checked
as test-classified; Stripe balance authentication confirmed `livemode=false`.
The SDK used the existing system CA bundle with verification enabled, as in the
prior API test. No credential was written into a script, log, or artifact.

Catalog reconciliation still found two Products and four active recurring USD
Prices, with no additional pages. Those subscriptions were not modified or
substituted for the existing one-time CNY credit-pack design.

- Local browser UI displayed test mode and zero credits.
- The UI called the actual application Checkout endpoint and created one test
  session: CNY 9.90, `open`/`unpaid`, local order `pending`, balance zero.
- The initial browser harness failed reading the response body during navigation.
  The existing session was retrieved and inspected before any further action;
  no duplicate Checkout was created.
- A bounded navigation to that same hosted session failed in system Chromium
  with **`net::ERR_CERT_AUTHORITY_INVALID`** for `checkout.stripe.com`.
  Certificate verification was not bypassed and no trust/security setting changed.
- Cleanup expired the open session. Retrieval verified `expired`/`unpaid`,
  `livemode=false`, local balance zero. No payment or credit grant occurred.

Hosted form rendering, cancellation, browser resume, and synthetic card payment
remain unverified because Chromium does not trust the presented certificate chain.
The successful verified curl/SDK requests do not establish Chromium trust. The
next checkpoint is a supported browser CA-trust configuration, followed by the
hosted flow; do not bypass certificate errors. Genuine webhook delivery remains
separately blocked pending explicit CLI/listener approval. No listener, signing
secret, or webhook registration was created. No production/main change occurred.
This follow-up changes evidence only; prior regression results were not rerun.

## Republished hosted-origin check — 2026-10-28 15:52 UTC

Fetched `integration/ziwei-stripe-test` at `16aec76` in the fresh published
workspace. Repository guidance was inspected; no local AGENTS.md or skills were
available. Chromium and Playwright are installed, but hosted browser acceptance
could not start because the Checkout origin remains inaccessible.

- Credential classification: test. Read-only Stripe balance authentication:
  **HTTP 200, livemode=false**. No key value was printed or persisted.
- `https://checkout.stripe.com/`: HTTPS proxy tunnel denied with
  **403 Forbidden**, before reaching the hosted page.
- `https://js.stripe.com/`: **HTTP 403**; root probe does not establish whether
  the JavaScript asset is usable.
- `https://hooks.stripe.com/`: **HTTP 404**; HTTPS connection succeeded, but this
  does not validate a specific authentication flow.
- GitHub repository fetch succeeded. Read-only GitHub API PR metadata lookup
  failed at transport level, so current draft/open status was not reverified.

No additional Checkout session, catalog object, test payment, credential,
webhook endpoint, or listener was created. No browser payment/cancellation result
or genuine credit fulfillment is claimed. There was no network/security change,
security-warning bypass, or alternate-route retry after the Checkout denial.

**Remaining blockers:** the environment proxy must permit the Checkout origin
before hosted cancellation/resume and synthetic card payment can run. Explicit
approval for downloading the official Stripe CLI and running the temporary local
sandbox webhook listener remains pending; neither action was attempted. Prior
automated results below remain historical and were not rerun for this docs-only
follow-up. Main and production were untouched.

## Published environment validation — 2026-10-28

PR #2 was fetched and inspected as open/draft at
`78cdcb5c499d290e4da4e085094f2393b3850156`. Work continued only on
`integration/ziwei-stripe-test`. Repository `CLAUDE.md` and acceptance guidance
were read; no `AGENTS.md` or local skill files were available. Explicit task
restrictions exclude the repository's normal production deployment workflow.

**Credential result: present; test-classified; authentication successful.**
A read-only `GET https://api.stripe.com/v1/balance` returned HTTP 200 with
`livemode=false`. No credential value or derived identifier was printed, logged,
hashed, persisted, or added to artifacts. Only the test key was used.

Before creating Checkout, complete Product/Price listings returned two products
and four active recurring USD prices (no further pages):

- Polaris: USD 79.99/month and USD 759.99/year.
- Vanguard: USD 24.99/month and USD 239.99/year.

These are subscriptions, whereas this branch implements one-time CNY Ziwei
credit packs. They were not substituted for the repository's `p10` pricing or
modified. This product-intent discrepancy remains for reconciliation before
expanding scope; current verification covers only the existing credit design.

### Actual Stripe API verification

Used the real `stripe_billing.create_checkout_session` service with an isolated
in-memory SQLite schema, synthetic device identity, zero free credits, test-only
settings, and `http://127.0.0.1:3100` callbacks. AI was never invoked.

The SDK's bundled CA trust initially rejected the environment proxy certificate
before reaching Stripe. The test process then selected the existing system CA
bundle (`ssl.get_default_verify_paths().cafile`) for the Stripe SDK. Certificate
verification stayed enabled; no trust store, network/security setting, persistent
configuration, or application code was changed. Before retrying with the same
idempotency input, the Stripe session listing confirmed zero existing sessions.

- Actual Checkout creation and retrieval succeeded: `mode=payment`,
  `livemode=false`, `amount_total=990`, `currency=cny`, `status=open`,
  `payment_status=unpaid`.
- Stripe accepted the application's requested `alipay`, `wechat_pay`, and `card`
  payment methods. This does not prove successful payment using each method.
- Actual stored success/cancel URLs target localhost and contain the order ID.
- Reusing the same application checkout key returned the same session/order;
  the synthetic account retained zero credits. This verifies application resume,
  not browser cancellation or provider-side replay after a lost response.
- The unpaid test session was explicitly expired and retrieved again as
  `expired`/`unpaid`. Final listings show exactly one session, two Products and
  four Prices, all test mode. No additional listed catalog objects were created.
- No payment was completed, and no charge or genuine fulfillment was performed.

### Fresh independent checks

- Focused SQLite backend command documented below: **112 passed, 4 skips**.
- Disposable PostgreSQL acceptance: **60 passed**, including cancellation/resume,
  fulfillment/idempotency, concurrent grants/debits, rollback, and lock contention.
- `node scripts/ziwei-billing-test.cjs`: **passed** (run from frontend).
- Frontend `tsc --noEmit`: **passed**.

The PostgreSQL recipe below used container `ziwei-qa-postgres-20261028`.
All QA schemas were removed (verified zero remaining) and that disposable
container was stopped/removed. Existing application database/cache containers
were untouched. These automated tests use synthetic signed events and mocked
Stripe calls; their fulfillment results are not genuine Stripe webhook delivery.
Full-suite, build and browser results remain historical, not rerun here.

### Remaining precise blockers

1. Hosted payment/cancellation: an HTTPS probe to `checkout.stripe.com` was
   denied by the environment proxy with `Tunnel connection failed: 403 Forbidden`.
   No retry or network-setting change followed the denial. The API allowlist
   change succeeded but does not authorize or enable this separate hosted origin.
   Hosted Checkout needs permitted access to that origin and any required assets;
   do not infer that unrestricted internet is required.
2. Genuine webhook delivery/redelivery: `STRIPE_WEBHOOK_SECRET` remains absent
   and Stripe CLI remains unavailable. An exact proposed next action requiring
   separate credential/access authorization is an ephemeral official Stripe CLI
   TEST listener forwarding only to an isolated local backend at
   `http://127.0.0.1:8000/api/v1/billing/webhook`, using its matching signing secret
   only in memory. No listener credentials or persistent webhook registrations
   were created; neither delivery nor payment completion is claimed.

No application fixes were needed. Changes in this follow-up only document
verification. No production/main change, merge, deploy, release tag, real charge,
credential creation, persistent access, or security/network change occurred.

## Fresh environment follow-up — 2026-10-25

Fetched PR #2 and verified it remained open/draft at
`20b3e7969696ff28a756fe3c8d9f4285c3c094a6`, on
`integration/ziwei-stripe-test`. Work continued on that feature branch.
Repository `CLAUDE.md` and test-contract guidance were inspected; no `AGENTS.md`
or local `.agents/skills` files were available. The explicit no-deployment scope
overrides the repository's normal release workflow.

Secret verification reports only: **present; test; authentication unverified**.
The read-only Stripe balance request could not traverse the environment proxy;
the transport reported `Tunnel connection failed: 403 Forbidden`, including on
the elevated execution path. This is not a Stripe authentication rejection and
does not establish whether the key is valid. No key value was printed, logged,
persisted, hashed, or placed in an artifact. No live key was used.

`STRIPE_WEBHOOK_SECRET` is absent and the Stripe CLI is unavailable. Actual
Checkout creation, hosted test payment/cancellation, payment-method availability,
and Stripe-originated webhook delivery/duplicate redelivery remain **blocked**.
The precise next checkpoints are permitted HTTPS access to `api.stripe.com`, then
test-key authentication, and an authorized matching test webhook signing secret
and delivery path to the isolated local backend. No proxy/security configuration,
listener credential, persistent access, or external webhook endpoint was created
or changed. No actual Stripe Checkout session or payment was created.

Added one acceptance regression joining the mocked checkout and signed synthetic
webhook paths: the cancellation callback targets localhost, return parameters and
an unpaid notification leave the order pending with zero credits, resuming the
same idempotency key reuses the order/session, and duplicate paid notifications
grant exactly ten credits. The signature uses a nonfunctional fixture secret.
This is **simulated cancellation and webhook delivery**, not hosted Checkout or
real Stripe delivery.

Fresh validation after that addition:

- Focused SQLite suite: **112 passed, 4 PostgreSQL-only skips**.
- Real disposable PostgreSQL **16.15** acceptance: **60 passed**, including the
  new flow, concurrent fulfillment/debits, rollback, lock contention and migration.
- Frontend offline billing checks: **passed**, including cancellation parsing.
- Frontend TypeScript `tsc --noEmit`: **passed**.
- `git diff --check`: **passed**.

Commands used the existing `/workspace/.portal-venv/bin/python` and the focused
test selection documented above. PostgreSQL used the cached `postgres:16-alpine`
image with the same localhost-only, tmpfs, disposable database recipe below,
container name `ziwei-qa-postgres-20261025`. All QA schemas were removed on test
teardown (verified count zero), and the container was stopped/removed afterward.
Application/provider effects remained mocked; the published Stripe key was cleared
inside the test process by the acceptance fixture before application imports.
The full backend suite and browser/build checks were not rerun; their prior
results, including six inherited backend failures, remain historical evidence.
No application code change, main merge, release tag, deployment, or real charge.

## Original integration checkpoint

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

The previously deferred legacy auto-adoption and callback-host fixes were explicitly
approved on 2026-10-22 and are now implemented; see the final security verification
below. No ownerless records were assigned, altered, or deleted.

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
The two previously denied security changes were subsequently approved and completed; see below.

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


## Final approved security verification — 2026-10-22

Both explicitly approved fixes are now implemented without a renewed denial:

- Profile listing never assigns NULL-owned records, even with stale auto-adopt=true.
  The deprecated setting defaults to false. Legacy profile, conversation and message
  data are preserved and hidden until separately authorized explicit recovery.
- Test callback hostname validation canonicalizes DNS root dots, case and IDNA on
  both sides before enforcing the existing production-host restrictions. Invalid
  hostname parsing fails closed. Local isolated test callbacks remain usable.

Fourteen new independent regression cases verify unchanged legacy rows across
repeated listing/read attempts by missing and different device identities, retained
access to already owned profiles, disabled explicit claim without configuration,
production hostname spelling variants, and local callback availability. Tests do
not perform recovery, create credentials, or contact Stripe.

Focused SQLite suite: **111 passed, 4 PostgreSQL-only skips**. Full backend:
**387 passed, 6 inherited failures, 4 skips** (the same six baseline failures
listed above). Real isolated PostgreSQL 16.15 acceptance: **59 passed**. All test
schemas were removed and the disposable container stopped after verification. Earlier frontend
browser/typecheck/build passes remain applicable: no frontend code changed in this
security correction. Existing Stripe integration was not accessed. Checkout uses
inline price_data/product_data and requires no pre-created Product/Price IDs.

Legacy recovery remains a separate authorized operation requiring verification of
rightful ownership. The existing code-protected bulk claim endpoint is unchanged,
not enabled, and also covers Qian records; it must not be treated as proof that a
visitor owns any particular legacy profile. No production data was touched.

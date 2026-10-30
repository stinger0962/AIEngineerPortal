# Ziwei test billing: deployment readiness

## Reviewed boundary

This branch implements **test-only** CNY credit packs. It rejects live Stripe keys
and callbacks on the configured production hostname or `leipan.cc` hosts. The
successful Alipay sandbox payment and genuine webhook were verified against a
disposable local database; that account/balance was discarded afterward. The
CLI listener is stopped and is not a durable deployment endpoint. This completed
flow is valid payment/fulfillment acceptance; a second server or permanent staging
environment is not required to accept it.

The final independent review found cached-session recovery bypassing the age
check. The corrected service returns owner-scoped paid/failed state before any
cached redirect and refuses unresolved retries older than 23 hours. The client
clears only terminal keys and keeps unresolved keys for reconciliation. A provider
session explicitly expired early, before that guard, is not detected locally;
there is no automated provider reconciliation/expiry recovery. Do not rotate an
uncertain intent into a new payment without checking its provider state.

No remaining substantive implementation finding was identified in the reviewed
scope. Green focused CI and local browser tests support review of this draft;
they do not authorize merge or rollout. Repository branch-protection requirements
and actual deployed environment values have not been inspected.

## Testing without new infrastructure

The recommended default is to use the completed Codex-backend + temporary Stripe
CLI + manual-browser result, together with the passing local return-flow tests.
No staging target is pending as an implementation or payment-acceptance gate.

- **Already verified:** the user completed an Alipay sandbox Checkout in their
  browser, the temporary CLI forwarded the genuine signed webhook to Codex, and
  the isolated account received exactly ten credits. The backend did not need a
  public incoming endpoint or a permanent Dashboard webhook.
- **Return-page limit:** the test used `STRIPE_TEST_BASE_URL=http://127.0.0.1:3100`.
  Its success/cancel redirects targeted `/ziwei?paid=1&order_id=…` and
  `/ziwei?canceled=1&order_id=…`. On the user's computer, localhost did not point
  to the Codex UI. Payment/fulfillment passed; actual hosted return-page behavior
  was not verified by that manual test. Mocked local browser tests cover the
  application's cancellation, resume, status and retry behavior separately.
- **Developer-local alternative:** run UI, backend, disposable test DB and CLI on
  the same computer as the browser. Localhost returns then reach the app, without
  another server, public webhook or production changes. Further provider test
  activity must stay within its explicitly approved scope.
- **Existing preview, if available:** a reachable authorized HTTPS preview could
  host return pages while the CLI forwards webhooks. No existing preview URL or
  port-publication capability has been established here; none was enabled. Do not
  invent a preview or enable a tunnel/access rule under an assumption of approval.
- **Existing-VPS alternative:** a separate test instance on the current host is
  optional, subject to capacity/data isolation checks and approval before changing
  the production host. A second Droplet is not inherently necessary.

The `leipan.cc` restriction is an existing application production-isolation guard,
not a Stripe infrastructure requirement. It was introduced in `31b3b61`, with
hostname canonicalization subsequently recorded as approved in `20b3e79`. The
no-new-server options do not require weakening it. Another project's test-mode
production deployment configuration cannot be copied into this app without
reviewing these different boundaries.

## What the repository actually configures

| Concern | Source and current behavior |
| --- | --- |
| Success/cancel base | Backend `STRIPE_TEST_BASE_URL`, parsed by `Settings`, validated by `stripe_billing.is_configured`, then used for `/ziwei?paid=1&order_id=…` and `/ziwei?canceled=1&order_id=…`. It is not derived from request headers, the frontend origin, or `APP_DOMAIN`. |
| Production host | `PUBLIC_BASE_URL` defaults to `https://portal.leipan.cc` and is used to reject a production callback, not as a fallback callback. |
| Test checkout enablement | `STRIPE_TEST_ENABLED` defaults false. Existing production Compose does not pass this setting or `STRIPE_TEST_BASE_URL`; secrets alone cannot enable Checkout. |
| Frontend | `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_ZIWEI_TEST_BILLING` are build-time values. Current frontend Dockerfile exposes only the API URL build argument. Changing runtime Compose environment alone cannot enable the test panel. |
| Credit requirement | Production Compose passes `ZIWEI_REQUIRE_CREDITS`, default false. Do not enable credit enforcement while purchase/fulfillment is unavailable. Its actual deployed value is unknown. |
| Webhook | `/api/v1/billing/webhook`, raw-body signature verification using `STRIPE_WEBHOOK_SECRET`. Caddy routes `/api/*` to backend. Temporary CLI forwarding already supported the supervised local test; a stable endpoint/secret binding is needed only for a chosen persistent deployment. |
| Release mechanism | `.github/workflows/deploy.yml`: GitHub Actions builds/pushes images, then VPS pulls/recreates containers. Triggered by `v*` tag or manual dispatch; both target production. No staging deployment workflow currently exists. |
| Runtime versions | Backend image Python 3.11; frontend image Node 20. Test CI covers these plus Python 3.12 / Node 22. |

## Optional persistent staging, only if requested

These steps apply if a persistent shared environment is desired. They are not
prerequisites for the completed test acceptance, and do not require a separate
server if an existing host can safely accommodate an approved isolated instance.

1. Select a nonproduction HTTPS hostname and isolated persistent database/cache.
   Approve provisioning/deployment and any access/credential bindings separately.
   The current production workflow must not be reused as an assumed staging job.
2. Snapshot an existing test DB if reusing one. Review the additive
   `backend/scripts/migrations/20261021_billing_requests.sql`: one new table,
   `billing_requests`, referencing existing accounts. No existing order/ledger
   rewrite is required. Fresh schemas use `Base.metadata.create_all`.
   Startup also performs schema patches and seed synchronization; test those
   against the chosen isolated DB before traffic. No external migration has run.
3. Build a separate test frontend with the test API URL and
   `NEXT_PUBLIC_ZIWEI_TEST_BILLING=true`; add explicit staging build wiring rather
   than changing the production default. Set backend `STRIPE_TEST_ENABLED=true`
   and `STRIPE_TEST_BASE_URL` to that approved HTTPS UI host. Keep provider AI
   disabled/mocked unless separately approved. Localhost URLs work only for
   browsers on the machine hosting the UI.
4. With approval, bind the existing test API credential and a matching signing
   secret for a stable test webhook endpoint. Subscribe to completed,
   async-payment-succeeded, and async-payment-failed Checkout events. A
   temporary CLI listener is sufficient for a supervised local test, not staging
   persistence. No new key is inherently required; no secret value belongs in
   source, PR descriptions, logs, or documentation.
5. Verify health, schema, UI/API test gating, owner-scoped order lookup, and
   signature rejection before enabling test credit enforcement. Then perform
   separately authorized provider acceptance on that staging URL. Query flags
   are never payment proof; check paid session/event and exact ledger balance.

## Ownership and data expectations

`X-Device-Id` is the existing bearer identity, generated/stored in browser local
storage. Orders and credits belong to that device's account; a receipt email does
not bind or recover an account automatically. This is not authenticated-user
identity and does not protect a stolen device identifier. Changing that access
model is separate work. Legacy ownerless profiles stay hidden and unchanged;
`ZIWEI_AUTO_ADOPT` does not claim them. Do not enable the bulk claim-code recovery
operation without a separately authorized ownership review.

## Rollback and operational limits

Keep DB snapshots and immutable tested image references before any approved
rollout. Preserve `billing_requests`, orders and ledger across code rollback:
dropping retry records destroys replay protection. The migration's drop-table
comment is for stopped disposable test traffic, not a production rollback recipe.

Drain/reconcile outstanding sessions and deliveries before disabling the backend
Stripe test flag: that flag gates both checkout and webhook processing. Disabling
only the frontend panel does not prevent direct Checkout API calls. There is no
separate administrative purchase-pause control in this scope. A rollback must
preserve a compatible validated webhook consumer until outstanding payments are
settled. Do not blindly roll back to the original main billing implementation,
which predates these validation/concurrency fixes. Any actual rollback/release
still requires the repository's approved Actions workflow and separate approval.

Generation retains database locks through model execution. PostgreSQL tests
verify bounded contention at READ COMMITTED, not production load or capacity.

## Merge review versus production blockers

- The known six full-suite failures also reproduce on unchanged baseline: three
  stale content/count assertions and three profile fixtures missing device
  identity. They are not new billing regressions. The new focused CI does not
  pretend the full suite is green; resolve or explicitly triage these before a
  general production release.
- Hosted cancellation/resume, card/WeChat payment, genuine webhook redelivery,
  and delayed provider settlement are additional provider coverage. Local signed
  fixtures cover their event/state logic; only genuine Alipay success is proven.
  They are not grounds for silently making more payments or changing browser
  trust. Automated Chromium still has an unexplained certificate-verifier error.
- Production live billing is **not enabled or implemented by this test-only
  rollout**. It requires an explicit product decision (CNY credit packs versus
  existing USD subscriptions), live-mode design/configuration review, operational
  pause/reconciliation/rollback planning, stable webhook provisioning, and an
  approved release. Do not remove test guards merely to make production work.

There is no required staging target or infrastructure purchase pending. The
implementation and reviewed test acceptance can proceed to PR review without one.
Merge, deployment/release tags, production-host changes, credential/access or
trust changes, new public exposure/tunnels, and payment activity outside the
approved test scope remain separate authorization boundaries. Permanent staging
is an optional choice, not the mandatory next step. None of those actions was
performed by this readiness assessment.

# Ziwei test billing: deployment readiness

## Reviewed boundary

This branch implements **test-only** CNY credit packs. It rejects live Stripe keys
and callbacks on the configured production hostname or `leipan.cc` hosts. The
successful Alipay sandbox payment and genuine webhook were verified against a
disposable local database; that account/balance was discarded afterward. The
CLI listener is stopped and is not a durable deployment endpoint.

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

## What the repository actually configures

| Concern | Source and current behavior |
| --- | --- |
| Success/cancel base | Backend `STRIPE_TEST_BASE_URL`, parsed by `Settings`, validated by `stripe_billing.is_configured`, then used for `/ziwei?paid=1&order_id=…` and `/ziwei?canceled=1&order_id=…`. It is not derived from request headers, the frontend origin, or `APP_DOMAIN`. |
| Production host | `PUBLIC_BASE_URL` defaults to `https://portal.leipan.cc` and is used to reject a production callback, not as a fallback callback. |
| Test checkout enablement | `STRIPE_TEST_ENABLED` defaults false. Existing production Compose does not pass this setting or `STRIPE_TEST_BASE_URL`; secrets alone cannot enable Checkout. |
| Frontend | `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_ZIWEI_TEST_BILLING` are build-time values. Current frontend Dockerfile exposes only the API URL build argument. Changing runtime Compose environment alone cannot enable the test panel. |
| Credit requirement | Production Compose passes `ZIWEI_REQUIRE_CREDITS`, default false. Do not enable credit enforcement while purchase/fulfillment is unavailable. Its actual deployed value is unknown. |
| Webhook | `/api/v1/billing/webhook`, raw-body signature verification using `STRIPE_WEBHOOK_SECRET`. Caddy routes `/api/*` to backend. Stable delivery and secret binding must be configured for the chosen test environment. |
| Release mechanism | `.github/workflows/deploy.yml`: GitHub Actions builds/pushes images, then VPS pulls/recreates containers. Triggered by `v*` tag or manual dispatch; both target production. No staging deployment workflow currently exists. |
| Runtime versions | Backend image Python 3.11; frontend image Node 20. Test CI covers these plus Python 3.12 / Node 22. |

## Minimum staging steps, requiring a separate approved target

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

The next external decision is whether to provision/deploy a named isolated
HTTPS staging target with persistent test webhook delivery. Merge, production
rollout, release tags, credential/access changes and real payments remain
separate approvals; none has been performed by this readiness assessment.

# Ziwei Stripe test-mode acceptance

Independent QA tests against baseline `6c909b235fed2c81f1153a67d8f4bed36dab3fb5`.
No application code, migrations, deployment configuration, or existing billing tests are changed.
These are acceptance gates: failures are deliberately not hidden with xfail/skip.

## Reproduce locally

From repository root:

```sh
python -m venv /tmp/ziwei-qa-venv
/tmp/ziwei-qa-venv/bin/pip install -r backend/requirements.txt
/tmp/ziwei-qa-venv/bin/python -m pytest backend/tests/acceptance -q --tb=short
```

The suite uses a fresh temporary SQLite file per test, a standalone FastAPI app
with only billing and Ziwei routers, mocked AI, and synthetic Stripe event bodies.
It forbids socket connections during tests, overrides database dependencies and
stream persistence sessions, clears external-service keys before app imports,
and supplies nonfunctional placeholder signing/API strings only in memory.
Stripe SDK signature verification runs locally against HMAC-generated payloads.
No credentials are provisioned. No production or Stripe API endpoint is contacted.

Existing focused baseline command (from `backend/`):

```sh
DATABASE_URL=sqlite:// ANTHROPIC_API_KEY='' OPENAI_API_KEY='' MINIMAX_API_KEY='' STRIPE_SECRET_KEY='' STRIPE_WEBHOOK_SECRET='' ZIWEI_REQUIRE_CREDITS=false /tmp/ziwei-qa-venv/bin/python -m pytest tests/test_billing_stripe.py tests/test_credits.py tests/test_ziwei_oracle_routes.py tests/test_ziwei_stream.py -q
```

## Recorded results, 2026-10-21

- Baseline: **24 passed, 3 failed**. The three streaming fixture tests expect
  successful access/no-chart validation but omit device ownership and get 404:
  `test_oracle_stream_emits_events_and_persists`,
  `test_oracle_stream_emits_error_and_salvages_partial`,
  `test_oracle_stream_400_no_chart`.
- Final acceptance run: **8 passed, 10 failed**, exit 1.
- Passing: sequential duplicate and distinct success-event idempotency; invalid
  signature rejection; purchase credits remain with the order account; different
  device cannot read private profile/conversation or start its oracle; failed
  generation retains credit; success exhausts one credit; upstream stream error
  retains credit; closing the stream generator retains credit.
- Failing: amount mismatch, currency mismatch, object livemode, event livemode,
  account metadata mismatch, live API key gating, simultaneous notifications,
  forced overlapping order reads, concurrent ledger consumption, and simultaneous
  readings with one credit. Both simultaneous readings returned 200.
- The ordinary concurrent notification probe is schedule-dependent (passed on
  an earlier run); the separate overlapping-order-read probe forces the current
  check/write race. It is intended for this baseline's Session.scalar path.
  Adapt that instrumentation when backend locking/claiming implementation changes.

## Contract assumptions and remaining acceptance blockers

The parent's new backend API contract has not been supplied. Tests use current
`/api/v1/billing/{checkout,balance,webhook}`, existing `p10` pricing, current Ziwei
oracle paths, and X-Device-Id identity. The proposed fail-closed live-key response
is HTTP 503; adjust only that status assertion if the agreed contract differs.
Payment amount/currency, account metadata, and event/session livemode must match
the stored order/test-mode context before granting credits. Refund/expiry and
new order lookup APIs require additional contract-specific tests if introduced.
There is currently no order-detail route: cross-account coverage checks balance
and grant ownership, **not** authorization of a nonexistent order lookup endpoint.
X-Device-Id is a bearer identity; tests do not claim authenticated-user security
or resistance to theft of another device identifier.

SQLite exercises current service transactions but does not establish PostgreSQL
locking behavior. Repeat concurrency tests against a separately authorized,
disposable PostgreSQL database after integration. The one-credit race uses
pre-existing conversations to avoid SQLite conversation-insert serialization.
The deterministic consume probe intercepts balance reads; a future lock-before-read
implementation may require adapting that probe to avoid an artificial timeout.

Failed upstream streaming and explicit generator.close() are covered. Actual ASGI
client disconnects, process termination after reservation/commit, durable recovery,
and credit refund exactly-once semantics remain pending the reservation contract.
There is no real Stripe end-to-end pass; test Checkout redirect and actual Stripe
test webhook delivery remain untested. No live payments are authorized.

## Deployment inspection

Only `.github/workflows/deploy.yml` and `release.yml` exist at the baseline.
Both trigger on pushed `v*` tags; deploy also supports `workflow_dispatch`.
No branch-push or pull-request trigger is configured. A feature-branch commit or
local integration alone does not trigger these workflows. **Do not create/push
v-tags or manually dispatch deploy**: it pushes `latest` images, SSHs to the
production droplet, rewrites production environment secrets (including Stripe),
checks out the selected SHA and recreates production containers. There is no
branch/environment approval guard in the workflow file itself. Remote GitHub
protection settings have not been inspected, so none are assumed.

No push, merge, deployment, production connection, credential change, or Qian
charging change was performed. QA acceptance is blocked by the failing gates and
pending backend contract/integration, not by an approval denial.

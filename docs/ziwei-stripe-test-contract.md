# Ziwei Stripe test milestone — backend contract

Base: `/api/v1`. Qian charging is out of scope. Prices remain CNY: p10 = 10 credits / 990 cents; p40 = 40 / 2990; p100 = 100 / 6800. One successful Ziwei oracle request costs one credit.

## Identity and responses

Use `X-Device-Id` on billing and oracle calls. This is the existing anonymous **bearer credential**, not a verified user login: protect it like a password. Possession grants account access. Missing/other device credentials cannot read an order, Ziwei profile, or Qian reading. Qian list and detail now enforce ownership; NULL legacy readings are hidden. Account recovery and stronger authentication are separate work.

- `GET /billing/balance`: `{balance, require_credits, free_credits, paid_enabled, packs, currency:"cny", mode:"test"}`. Packs contain `key`, `credits`, `amount_cents`, `label`. With a device, first access creates the account and existing welcome credit allocation. Without one, balance is zero.
- `POST /billing/checkout`: body `{pack:"p10"}`; header `Idempotency-Key` required (8–128 chars; use a UUID). Returns `{url, order_id, mode:"test"}`. Redirect to `url`.
- `GET /billing/orders/{order_id}`: owner-only `{order_id, status, pack, credits, amount_cents, currency, mode:"test"}`. Status is `pending`, `paid`, or `failed`. Unknown/unowned orders return 404. No Stripe customer data or credentials are exposed.
- Success/cancel redirects use the explicitly configured test site `/ziwei?paid=1&order_id=...` or `?canceled=1&order_id=...`. Query parameters are not payment evidence. Poll order status and refresh balance; only signed, validated webhooks grant credits. Stop polling on paid/failed; pending async payments may take longer and can be checked later.
- Both `/ziwei/profiles/{id}/oracle` and `/oracle/stream` require `Idempotency-Key` when `ZIWEI_REQUIRE_CREDITS=true`. Insufficient credits: HTTP 402, `{"detail":{"code":"insufficient_credits","balance":0,"required":1}}`.
- Invalid/missing key: HTTP 400, `detail.code="invalid_idempotency_key"`. Reusing a key for different input: HTTP 409, `detail.code="idempotency_conflict"`.

## Retry semantics

Checkout keys are scoped to account + checkout operation. Repeat same pack/key returns the saved URL/order, including after payment. Use a new key only for an intentional new purchase. Intent is committed before Stripe is called; network retries use the same provider key. Unresolved requests older than 23 hours return HTTP 409 `checkout_reconciliation_required`: inspect/reconcile the test session before attempting another purchase. Stripe can prune idempotency keys after 24 hours: [Stripe idempotency documentation](https://docs.stripe.com/api/idempotent_requests).

Oracle keys are scoped to account + oracle operation (shared between sync and stream). Fingerprint covers profile and the request body. Same completed request returns HTTP 409 `request_already_completed`, with no additional AI call/debit; recover messages through the existing owned conversation endpoints. Responses/SSE are not replayed. Failure rolls back both debit and key, allowing a retry with the same key. An overlapping request waits on the account lock, then observes the completed key or balance. Do not generate new keys for transport retries.

Debit, successful response persistence, and idempotency record commit together. Failure/empty output rolls back; partial stream salvage is uncharged. A disconnect before completion releases the transaction; a response already persisted before the connection is lost remains charged, recoverable from conversation history. The transaction deliberately holds a lock across generation: PostgreSQL serializes requests per account; SQLite serializes writers. This is a test milestone throughput limitation, not a production scaling design. Lock waits are bounded as described below; retry using the same key.

### Bounded contention and retries

`BILLING_LOCK_TIMEOUT_MS` defaults to **2000 ms** and accepts 50–10000 ms; zero/unbounded values are rejected by settings validation. Billing routes and paid generation transactions apply it before writes, including account creation, conversation creation, account locking, webhook fulfillment, and Checkout final persistence. A transaction-start hook reapplies the timeout after commits/rollbacks (including the durable Checkout intent boundary).

PostgreSQL uses transaction-local `set_config('lock_timeout', ..., true)`, bounding each lock acquisition attempt, not the duration of generation or the entire HTTP request. See [PostgreSQL lock_timeout](https://www.postgresql.org/docs/current/runtime-config-client.html#GUC-LOCK-TIMEOUT). SQLite uses connection-level `PRAGMA busy_timeout`; this can persist on a reused pooled connection and may fail immediately for some lock conflicts. See [SQLite busy_timeout](https://www.sqlite.org/pragma.html#pragma_busy_timeout). This does **not** eliminate SQLite's database-wide writer serialization: another user's generation can make checkout, fulfillment, or generation return busy. PostgreSQL ordinarily isolates the generation reservation lock to one account; real PostgreSQL concurrency validation remains pending.

Recognized SQLite BUSY/LOCKED and PostgreSQL lock-timeout/deadlock errors roll back the failed transaction and return HTTP **503**, header `Retry-After: 2`, body `{"detail":{"code":"billing_busy","retryable":true,"retry_after_seconds":2}}`. Unrelated SQL/provider errors are not mislabeled as contention. Wait at least two seconds, add jitter/backoff, and retry the **same** request/key. Keep pending purchase state rather than initiating a new purchase. Stripe may retry a 503 webhook normally. If persistence encounters contention after SSE headers have been sent, the stream emits `{"type":"error","code":"billing_busy","retryable":true,"retry_after_seconds":2}` instead of changing the HTTP status; its debit/key are rolled back.

A timed-out generation attempt does not retain a debit or completed key. If Checkout already committed its intent before a later contention failure, that pending order/key intentionally survives: retry uses the same provider idempotency key and order. Database lock waits are bounded, but this is not an AI/network execution deadline or a connection-pool deadline; generation still holds its acquired lock through completion.

Webhook processing checks signature on the raw payload, event/object `livemode=false`, expected amount/currency, payment mode, paid status, order ID, and account metadata. A conditional order status update and ledger insertion share one commit. Duplicate/concurrent success cannot grant twice. Unknown sessions return 503 for Stripe retry (session creation may still be saving); mismatched/live events grant nothing. Failure notifications never downgrade a paid order. Customer email is not automatically used as an account recovery binding.

## Isolated test setup and migration

The original implementation performed no credential setup, external migration, or deployment. A later explicitly approved temporary CLI test listener and Alipay sandbox payment were completed and cleaned up; see the QA report. No live payment or paid AI call was made. Existing deployment credentials are untouched.

1. Provision an empty, disposable test database. Set `DATABASE_URL` explicitly for every test server/command; never point at production or restore production personal data. Startup runs existing schema/bootstrap/seed logic, so verify the target **before** starting the app.
2. New table: `billing_requests` only. Fresh DBs use existing `Base.metadata.create_all`. For an existing PostgreSQL test DB, review `backend/scripts/migrations/20261021_billing_requests.sql`. Existing accounts, ledger, orders, prices, and currency need no data rewrite. Migration has not been run on any external DB.
3. Default billing remains disabled. Future secure configuration requires `STRIPE_TEST_ENABLED=true`, `STRIPE_SECRET_KEY` beginning `sk_test_`, `STRIPE_WEBHOOK_SECRET` from the test endpoint, and an explicit `STRIPE_TEST_BASE_URL` such as `http://localhost:3000`. There is no fallback to `PUBLIC_BASE_URL`; that host and `leipan.cc` hosts are rejected. Keep secrets out of source, logs, and chat. Persistent credential setup needs user approval.
4. Configure any future Stripe test webhook forwarding **only** to the isolated backend `/api/v1/billing/webhook`, never production. Configure a separate test signing secret. Payment methods remain the existing Alipay/WeChat/card model; actual sandbox payment-method availability is not yet verified.
5. Mock AI in local tests. Enabling paid generation against real providers was not authorized. Keep provider keys unset and use injected fake clients. Public profile listing never adopts ownerless legacy rows, even if a stale environment sets `ZIWEI_AUTO_ADOPT=true`; that deprecated setting defaults to false.
6. Tests create temporary SQLite files and override DB dependencies. Example from repo root, with dependencies installed in a temporary virtualenv:

```sh
DATABASE_URL=sqlite:////tmp/ziwei-import-only.db ANTHROPIC_API_KEY='' OPENAI_API_KEY='' MINIMAX_API_KEY='' STRIPE_SECRET_KEY='' python -m pytest backend/tests/test_credits.py backend/tests/test_billing_stripe.py backend/tests/test_ziwei_oracle_routes.py backend/tests/test_ziwei_stream.py backend/tests/test_qian_routes.py -q
```

A genuine Alipay sandbox payment and signed webhook have now been verified (2026-10-29); other hosted payment paths remain unverified. Local isolated PostgreSQL 16.15 acceptance, concurrency, rollback and migration checks pass; see [integration QA report](integration/ziwei-stripe-qa-report.md). No main merge, deployment, or release is included.


## Approved security corrections — 2026-10-22

Public profile listing is read-only for ownership. Ownerless legacy Ziwei profiles,
conversations, and messages remain stored unchanged, but are unavailable to visitors
until an explicit authorized recovery verifies the rightful owner. No ownership
migration or recovery was run. The existing code-protected `/ziwei/claim` operation
is unchanged and disabled when `ZIWEI_CLAIM_CODE` is empty; it is a bulk recovery
operation covering ownerless Ziwei and Qian records, not a per-profile proof of
ownership. Do not enable it or invent ownership assignments without a separate
recovery review. Existing owned profiles remain available to their device owner.

Callback validation canonicalizes both configured production and test DNS hostnames
(case, IDNA spelling, and terminal root dot) before applying the existing host
restrictions. Thus `portal.leipan.cc.` and equivalent production spellings cannot
enable Checkout. Malformed hostname parsing fails closed. No broader allowlist or
new credentials were introduced.

Checkout uses inline Stripe `price_data` and `product_data` from server-side packs;
pre-created Stripe Product/Price IDs are not required. No other Stripe integration
was inspected or modified.

## Return and asynchronous-event follow-up — 2026-10-29

Use an explicit HTTPS nonproduction test base URL when testers run in a separate
browser/computer. HTTP is accepted only for loopback development (localhost,
127.0.0.1, or ::1); these callbacks are reachable only from the machine running
the UI. Invalid ports, whitespace/backslashes, URL credentials, query strings,
fragments, and path parameters fail configuration before contacting Stripe.
No public callback host or deployment is provisioned by this feature branch.

Cancel navigation retains the same-pack Checkout retry key; it never cancels the
provider order or grants credits. Server-confirmed paid/failed states clear only
the matching order's key. A paid server result overrides stale cancel flags.
Failure webhooks validate amount, currency, mode and ownership metadata before
changing state. An unpaid completion grants nothing; later paid success grants
once, including after a failure delivered earlier. Late failure cannot downgrade
a paid order. These orderings are tested with locally signed fixtures.

Deployment boundaries and concrete next steps: [deployment readiness](integration/ziwei-deployment-readiness.md). Cached paid/failed checkouts return structured state for client recovery; unresolved intents older than 23 hours require reconciliation rather than another redirect or automatic purchase. Early provider-side expiry is not detected without provider reconciliation.

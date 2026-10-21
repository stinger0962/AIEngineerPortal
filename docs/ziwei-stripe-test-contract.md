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

Debit, successful response persistence, and idempotency record commit together. Failure/empty output rolls back; partial stream salvage is uncharged. A disconnect before completion releases the transaction; a response already persisted before the connection is lost remains charged, recoverable from conversation history. The transaction deliberately holds a lock across generation: PostgreSQL serializes requests per account; SQLite serializes writers. This is a test milestone throughput limitation, not a production scaling design. Lock timeout errors should be retried using the same key.

Webhook processing checks signature on the raw payload, event/object `livemode=false`, expected amount/currency, payment mode, paid status, order ID, and account metadata. A conditional order status update and ledger insertion share one commit. Duplicate/concurrent success cannot grant twice. Unknown sessions return 503 for Stripe retry (session creation may still be saving); mismatched/live events grant nothing. Failure notifications never downgrade a paid order. Customer email is not automatically used as an account recovery binding.

## Isolated test setup and migration

No credentials, database migration, deployment, or Stripe configuration were performed. No live payment or paid AI call was made. Existing deployment credentials are untouched.

1. Provision an empty, disposable test database. Set `DATABASE_URL` explicitly for every test server/command; never point at production or restore production personal data. Startup runs existing schema/bootstrap/seed logic, so verify the target **before** starting the app.
2. New table: `billing_requests` only. Fresh DBs use existing `Base.metadata.create_all`. For an existing PostgreSQL test DB, review `backend/scripts/migrations/20261021_billing_requests.sql`. Existing accounts, ledger, orders, prices, and currency need no data rewrite. Migration has not been run on any external DB.
3. Default billing remains disabled. Future secure configuration requires `STRIPE_TEST_ENABLED=true`, `STRIPE_SECRET_KEY` beginning `sk_test_`, `STRIPE_WEBHOOK_SECRET` from the test endpoint, and an explicit `STRIPE_TEST_BASE_URL` such as `http://localhost:3000`. There is no fallback to `PUBLIC_BASE_URL`; that host and `leipan.cc` hosts are rejected. Keep secrets out of source, logs, and chat. Persistent credential setup needs user approval.
4. Configure any future Stripe test webhook forwarding **only** to the isolated backend `/api/v1/billing/webhook`, never production. Configure a separate test signing secret. Payment methods remain the existing Alipay/WeChat/card model; actual sandbox payment-method availability is not yet verified.
5. Mock AI in local tests. Enabling paid generation against real providers was not authorized. Keep provider keys unset and use injected fake clients. Set `ZIWEI_AUTO_ADOPT=false` on the test instance to avoid the legacy profile auto-adoption path.
6. Tests create temporary SQLite files and override DB dependencies. Example from repo root, with dependencies installed in a temporary virtualenv:

```sh
DATABASE_URL=sqlite:////tmp/ziwei-import-only.db ANTHROPIC_API_KEY='' OPENAI_API_KEY='' MINIMAX_API_KEY='' STRIPE_SECRET_KEY='' python -m pytest backend/tests/test_credits.py backend/tests/test_billing_stripe.py backend/tests/test_ziwei_oracle_routes.py backend/tests/test_ziwei_stream.py backend/tests/test_qian_routes.py -q
```

Real Stripe sandbox end-to-end validation and PostgreSQL concurrency validation remain pending. No push, merge, or release is included.

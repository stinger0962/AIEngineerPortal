# Offline webhook and local ledger reliability

This milestone validates **test-mode** events and inspects local accounting
invariants. It does not reconcile with Stripe, contact a provider, issue refunds,
repair data or enable payments.

## Webhook boundary

Signature verification still precedes event processing. The processor checks
mapping structure, recognized event type, exact `livemode=false` flags, and
required checkout field/metadata types before querying or mutating a database.
Boolean/floating-point amounts cannot masquerade as integer cents. Malformed
input is rejected without granting credits. A structurally valid unknown checkout
still requests delivery retry, since its webhook can arrive before the session
response is saved. Existing atomic order transition plus ledger insertion remains
the source of duplicate-delivery safety; late failure cannot undo a confirmed
payment, and a valid later success can supersede a failed state exactly once.

Refund/dispute event families return `unsupported_financial_event` with no order
or ledger mutation. This is an explicit **unsupported outcome**, not a refund
receipt, durable reconciliation queue or monitoring system. No real refunds work
through this code. Before live launch, implement and authorize the provider's
refund/dispute lifecycle, auditing, reconciliation and operational alerts.

## Read-only local audit

Show help without connecting:

```sh
PYTHONPATH=backend python -m app.cli.paid_billing_audit --help
```

On the already-running disposable local preview only:

```sh
docker compose -f compose.paid-local.yml exec -T backend python -m app.cli.paid_billing_audit
```

The CLI requires explicit dedicated `PAID_DATABASE_URL` and a distinct
`DATABASE_URL`; it never loads an implicit `.env` or creates a missing file.
It opens SQLite read-only or a PostgreSQL read-only repeatable-read transaction,
validates the paid schema and prints aggregate counts only. No account IDs,
emails, tokens, amounts, URLs or row-level records are printed. There is no apply
or repair option, and no schedule is installed.

Checks flag paid orders without exactly one matching account/credit grant,
purchase grants on unpaid orders, unknown order states, orphan purchase/account
references, negative balances, and payment-linked refund ledger entries whose
provider lifecycle is unsupported. Reading-failure refunds without an order link
are not classified as payment refunds. Pending intents older than the safe
23-hour Checkout retry window are flagged for review, never marked failed or
recreated automatically.

Exit 0 means local invariants hold and no old pending intents need review; exit 2
means findings need investigation; exit 1 means inspection failed. Even exit 0
**always reports `provider_reconciled: false` and
`payment_refunds_supported: false`**. A locally consistent ledger is not evidence
of provider settlement or an authorized live launch. Do not infer a need to
charge/refund from this report or automatically repair it.

## Verification boundaries

Tests use disposable SQLite/PostgreSQL fixtures and synthetic Stripe-shaped
objects. They cover malformed input, SDK event mappings, reordered/duplicate
notifications, no-grant/no-mutation guarantees, injected accounting discrepancies
and read-only snapshots. CI also audits the empty Docker preview. No provider
credentials, external requests, customer funds or production changes are used.

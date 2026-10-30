# Ziwei test billing frontend integration

This branch is frontend-only. Nothing is deployed, pushed, or enabled in production. Qian is unchanged. No credentials are created or required for the offline checks.

## Local opt-in

Run the frontend with `NEXT_PUBLIC_ZIWEI_TEST_BILLING=true` only against a local/test backend. The default is off. This flag does not change the backend paywall. Real AI calls are not needed for the checks below.

## Confirmed backend contract

`frontend/src/lib/ziwei/billing.ts` contains the entire payment HTTP adapter. `CreditPanel` also accepts an injected `BillingAdapter` for mocks. The implementation matches the backend owner's October 21 contract:

- `GET /api/v1/billing/balance`: existing `balance`, `paid_enabled`, `require_credits`, server-defined `packs` (`key`, `label`, `credits`, `amount_cents`), plus `mode: "test"` and `currency: "cny"`. Missing/non-test mode disables buying.
- `POST /api/v1/billing/checkout`, body `{ "pack": "<server key>" }`, with `Idempotency-Key`: returns `url`, `order_id`, `mode: "test"`. The adapter rechecks mode before posting and accepts only HTTPS `checkout.stripe.com/c/pay/cs_test_…` redirects. Server enforcement of test keys remains essential.
- `GET /api/v1/billing/orders/{order_id}`: `status: "pending" | "paid" | "failed"`, `mode: "test"`, and order details. Scoped to `X-Device-Id`; wrong/missing identity gives 404. Only webhook-confirmed `paid` displays payment success.
- Requests send the existing device identity and use no-store. No identity means no billing request.
- Return URL `?paid=1&order_id=…` means pending, never proof of payment. `?canceled=1` (also `cancelled=1`) displays cancellation of navigation only and never asserts server order cancellation. Polling is bounded to 10 attempts, with manual refresh thereafter. Missing/unavailable order status stays pending.
- Checkout keys persist for same-pack retries, including uncertain network outcomes. Changing packs or starting again after server-confirmed paid/failed rotates the key. Returning from cancellation keeps the same key so the next same-pack attempt resumes the existing Checkout; the server is checked for any payment completed in the meantime. Responses from a previous return navigation cannot overwrite the current order. Keys and drafts are retained in tab sessionStorage with an in-memory fallback.
- Both oracle APIs send idempotency keys. Identical failed/uncertain payloads reuse their key; successful `done`/JSON completion clears it so another intentional submission gets a new key. Changed payloads rotate keys. Structured API errors expose `code`, including insufficient credits, completed duplicates, conflicts, and invalid keys.
- HTTP 503 `billing_busy` preserves `Retry-After` and displays a temporary-busy prompt (2 seconds by default). Retryable SSE errors restore the question with the same manual-retry prompt. Both retain their request key; neither triggers automatic resubmission.
- HTTP 402 restores the submitted question, removes the rejected duplicate bubble, and links to test packs when enabled. Profile selection and per-profile drafts survive Checkout navigation. SSE `done` refreshes balance and clears only the matching sent draft. No automatic reading retry occurs after payment.

Backend integration still needs its feature branch applied alongside this frontend patch; this frontend branch does not alter any backend route/schema/configuration. Backend activation requires its test-only settings; no settings are changed here.

## Offline validation

From `frontend`:

```
node scripts/ziwei-billing-test.cjs
npx tsc --noEmit
npm run build
```

The offline script uses TypeScript's existing transpiler, Node assertions and React server rendering; no test dependency is added. It checks server pack preservation, identity propagation, refusal of non-test Checkout and missing test flags, payment state parsing/validation, API errors, persisted retry keys, both oracle APIs with mocked 402/409/success responses, and initial component markup. The repo has no browser/component interaction runner configured; full browser interaction and a signed webhook integration test remain for backend integration. No live Stripe or paid AI call is made.

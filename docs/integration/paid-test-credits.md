# Paid account test credits and order reliability

The paid-only `/credits` page lets a verified account inspect its shared test
balance and ten most recent test orders without opening Checkout. It is linked
from product navigation and the signed-in account panel; unauthenticated or
disabled accounts remain gated. Personal portal routes are not added.

`GET /api/v1/billing/orders?limit=10` is read-only and owner-scoped. The server
bounds the limit to 1–20 and orders by creation time then ID descending. It never
creates an account/order or contacts a provider. Responses omit Stripe session
IDs, URLs, idempotency keys, email and credentials. Paid mode uses the existing
verified cookie identity; the original portal retains its existing device scope.

The test checkout UI remains opt-in with `NEXT_PUBLIC_ZIWEI_TEST_BILLING=true`;
the normal paid build does not expose purchase buttons even if a mocked server
reports billing enabled. Server test-key and configured-provider checks remain
independent. No flag, key, provider, payment, paywall, price or Qian entitlement is
enabled or invented here.

## Uncertainty and failure

- Return parameters are hints, never proof of payment. Only a verified test-mode
  server response may show paid/failed; pending stays unconfirmed.
- Returning/canceling the checkout screen does not imply provider cancellation,
  a refund or a credit grant.
- Balance, payment-status and Checkout errors are independent. A successful
  refresh cannot erase a failure from another request.
- Request generations reject late balance/status responses, including prior
  navigation. Failed balance refresh hides stale balance and fails purchase
  eligibility closed. Invalid/live-mode order and balance responses are rejected.
- Recent orders show last-read state and have their own explicit refresh. Failed
  reads clear the old list rather than present it as current.
- This page does not implement refunds. Reading-failure credit return must be
  checked against server balance. A failed payment state is not a refund receipt.
  Real payment refund/reconciliation support remains a launch requirement.

## Validation

Backend tests use disposable identities/databases and forbid provider calls.
Frontend contracts cover malformed/test-mode responses and cookie identity.
Mocked browser tests cover return-state verification, unavailable balance/history,
retries, account switches, default checkout off and narrow screens. Existing real
account integration, duplicate-checkout/idempotency and webhook tests continue
alongside them. No real provider, credentials or customer funds are involved.

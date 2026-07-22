# 紫微斗数 付费点数 (Paid Credits) — Design of Record

**Approved:** 2026-07-22. Model = per-round credits, Stripe (Alipay primary + WeChat), keep overseas hosting.

## Goal
Charge for AI 解盘 (each Opus 4.8 round costs ~¥0.3). Chinese users pay via 支付宝/微信 through Stripe. No mainland ICP / entity required.

## Cost basis (measured from ai_feedback, since 2026-07-17)
- Per round: P50 $0.031 / avg $0.037 / P95 $0.060. Per profile: P50 $0.116 / avg $0.279 / P95 $1.18 (heavy skew; one user did 40 rounds).
- ⇒ Per-round charging caps token exposure; heavy users self-fund. No unlimited subscription.

## Pricing (approved)
- Free credits on new account: **3**.
- Packs: `¥9.9 / 10` · `¥29.9 / 40` · `¥68 / 100`. Currency CNY.
- Consume: **1 credit per successful 解盘 round** (ziwei_oracle). Charge only on success.

## Identity (no heavy login)
- Anonymous per-browser `device_id` (existing X-Device-Id) → `account`. First oracle use auto-creates an account, maps the device, grants 3 free credits.
- Purchase: Stripe Checkout collects email → stored on account (for receipts + recovery).
- **Email recovery (in scope):** user enters email → 6-digit code emailed → enter code → current device linked to that account (credits merge). Requires SMTP env. Existing device-找回码 also still works as a fallback.

## Data model (new tables, auto-created by create_all)
- `account`(id, email nullable unique, created_at)
- `account_device`(id, account_id, device_id unique, created_at)
- `credit_ledger`(id, account_id, delta int, reason, order_id nullable, created_at) — balance = SUM(delta)
- `payment_order`(id, account_id, pack, credits, amount_cents, currency, stripe_session_id unique, status[pending|paid|failed], created_at)
- `email_code`(id, email, code, expires_at, consumed) — one-time login codes

## Backend flow
- **Resolve account**: `X-Device-Id` → account_device → account (auto-create + 3 free if new).
- **Balance**: `SELECT SUM(delta) FROM credit_ledger WHERE account_id=?`.
- **Checkout**: `POST /billing/checkout {pack}` → server picks credits+amount from a server-side PACKS table (never trust client) → create Stripe Checkout Session (payment_method_types alipay/wechat_pay, currency cny, metadata: account_id, pack, credits) → insert payment_order(pending, stripe_session_id) → return session URL.
- **Webhook**: `POST /billing/webhook` → verify signature (STRIPE_WEBHOOK_SECRET) → on `checkout.session.completed`, look up order by session_id; if not already paid (idempotent), set order.paid + insert credit_ledger(+credits, reason='purchase', order_id) + set account.email from session customer_details.email.
- **Gate**: ziwei_oracle(+stream): if `settings.ziwei_require_credits` and balance < 1 → 402 "余额不足". Consume 1 credit (ledger -1, reason='ziwei_oracle') on successful completion (in the non-stream reply / stream `_persist` on done). Free rounds are just the 3 welcome credits — no separate free path.
- **Email recovery**: `POST /billing/email/send {email}` (rate-limited) → store code + email code → SMTP send. `POST /billing/email/verify {email, code}` → if valid, map current device_id to the account owning that email (create account if none) → merge.

## Config / env (user sets in VPS .env.production)
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
- `SMTP_HOST/PORT/USER/PASSWORD/FROM` (email recovery; if unset, recovery endpoints return 503, device-找回码 still works)
- `ZIWEI_REQUIRE_CREDITS` (default `false` — flip to `true` to turn on the paywall once everything is verified)

## Frontend
- Balance + buy panel on /ziwei (3 packs → redirect to Stripe). Stripe success return → poll balance.
- On 402 from oracle → "去充值" prompt opening the buy panel.
- Email recovery UI (enter email → code → linked) in the identity panel area.

## Phasing (each deployable behind the flag)
1. Credit infra: models, account resolution, ledger, free credits, gate behind `ziwei_require_credits` (off). Tests.
2. Stripe: checkout + webhook (backend). Tests (mock Stripe).
3. Frontend: balance + buy + 402 handling.
4. Email recovery (backend SMTP + frontend).
5. Flip `ZIWEI_REQUIRE_CREDITS=true`.

## Correctness / security invariants
- Server sets pack price/credits; client only names the pack.
- Webhook signature verified; crediting idempotent per stripe_session_id.
- Credit consumed only on successful reading; failure never charges.
- Never expose raw device_id or Stripe secrets to clients.

# Fresh paid-product foundation

This opt-in product starts fresh on a future domain. It reuses the existing lacquer folding-screen homepage, double-door transition/sound, Ziwei and Qian components. It does not copy users, credits, readings, cookies, or local storage from the personal portal. No domain, DNS, production or payment configuration is changed by this branch.

## Product boundaries

- Build the frontend with `NEXT_PUBLIC_PRODUCT_MODE=paid`. Default mode stays the personal portal.
- Paid home has Ziwei, Qian and Explore doors. `src/lib/product/config.ts` is the feature registry; the catalogue and navigation derive from it. The original door renderer is shared, not copied.
- The middleware returns 404 for personal-portal routes in paid mode. This is route isolation, not authentication. The API must use the dedicated paid entrypoint below, never the portal API.
- Shared Next.js source still builds personal pages into the artifact. They are blocked by middleware, not removed from source. Do not treat this as a code-confidentiality boundary.
- The fresh-account layer now gates private features with verified email sessions. Legacy device identity/recovery is not used for paid-product authorization. Existing portal storage is never imported. See [fresh accounts](paid-fresh-accounts.md).
- Live payments remain unavailable. No plan, pricing or payment-provider eligibility is asserted by the catalogue.
- `SITE_URL` supplies metadata for the eventual new domain. Current branding is provisional 方寸 · 玄. There is no hard-coded new domain.

## Local isolated preview

Use separate terminals from the repository root. The URLs below are local examples, not a deployment recipe.

```sh
# Backend: use a NEW disposable local file, never the portal database.
PAID_DATABASE_URL=sqlite:////tmp/paid-product-preview.db \
CORS_ORIGINS=http://localhost:3001 \
STRIPE_TEST_ENABLED=false ZIWEI_REQUIRE_CREDITS=false \
uvicorn app.paid_main:app --app-dir backend --port 8001

# Frontend
cd frontend
NEXT_PUBLIC_PRODUCT_MODE=paid \
NEXT_PUBLIC_API_BASE_URL=http://localhost:8001/api/v1 \
SITE_URL=http://localhost:3001 npm run dev -- --port 3001
```

An optional `frontend/Dockerfile.paid` builds the separate artifact; no existing deployment workflow selects it. It has not been container-tested locally.

Use the same environment when building and starting: `npm run build` then `npm run start -- --port 3001`. Paid artifacts go to `.next-paid`, portal artifacts to `.next`. For a future HTTPS launch, serve API under the product origin and set `NEXT_PUBLIC_API_BASE_URL=/api/v1`; reverse-proxy configuration must route it to `app.paid_main`, not `app.main`.

`PAID_DATABASE_URL` is required and must differ from `DATABASE_URL`. The paid app creates only required oracle/billing tables, skips portal seeds and runtime migrations, rejects unrelated existing tables and legacy-claim configuration, and rejects non-test Stripe keys. Exact URL and table checks are safeguards, not proof of an empty database or protection against equivalent aliases. The operator must select a genuinely separate database. Qian background streaming persists to the request's database.

## Adding features

1. Add a stable feature ID, route, text and accent to `paidFeatures`.
2. Implement its page and tests. Keep the root door count curated; Explore is the scalable catalogue.
3. Add only its required router/tables to the paid API, with isolation tests.
4. Reuse a reviewed account/billing layer when introduced. Do not implement a second payment ledger per feature.

## PR #19 assessment and next milestones

Fresh verified accounts are implemented separately in [this nonproduction milestone](paid-fresh-accounts.md), without legacy adoption; real email remains disconnected.

PR #19 is not a dependency. Its legacy binding, adoption and domain migration work are not needed for this fresh product. Its proof-of-mailbox, hashed one-time challenges, secure sessions, revocation and rate-limit approach can inform a fresh-account implementation, but should be extracted and tested without the legacy adoption flow. Email delivery still needs implementation and testing; the foundation alone does not supply signup.

Before a paid launch: implement fresh verified accounts and shared entitlements for both features; select sender/domain and test email transport; review proxy/rate limits and retention; confirm Stripe card/business eligibility independently (Alipay fortune-telling restriction still applies); test payment webhooks and refunds; choose and authorize deployment/DNS. None is silently enabled by this foundation.

## Checks

- `node frontend/scripts/paid-product-test.cjs`: mode/registry/SSR contracts.
- Existing billing offline script and TypeScript/build checks.
- `backend/tests/test_paid_product.py`: isolated API/data/startup contracts.
- `frontend/scripts/paid-product-browser-test.cjs`: local Chromium navigation/animation tests with mocked API; does not validate real email, AI or payments.

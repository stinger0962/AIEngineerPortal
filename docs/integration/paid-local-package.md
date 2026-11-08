# Isolated paid-product package (not a launch)

This package is a disposable **local preview**, separate from the personal
portal's Compose and deployment workflows. It preserves the shared door-opening
homepage and catalog while accounts, email, payments and external AI stay off.
It does not migrate data or install credentials, DNS or a production service.

## Local use

Requirements: Docker with Compose v2 and Python 3. Run from the repository root:

```sh
docker compose -f compose.paid-local.yml config --quiet
docker compose -f compose.paid-local.yml up --build -d --wait
python3 scripts/check-paid-preview.py
# Open http://127.0.0.1:3100
# Stop the preview; its tmpfs database disappears when the backend stops.
docker compose -f compose.paid-local.yml down
```

These commands are a runbook, not evidence that any user computer or production
host has run them. CI builds and starts only an isolated hosted-runner preview.
No registry push or deploy action is configured.

Only the proxy is published, bound to loopback port 3100. It serves Next and the
paid API at the same origin. Backend/frontend ports are not published. The
runtime network is internal, the containers run without root and with read-only
root filesystems, and writable caches/database live in tmpfs. Dependencies still
need Internet access at image-build time. Restarting the backend loses preview
data deliberately. Do not use this package for real customers or records.

The package has literal disabled settings and no inherited env files. It must not
be repurposed by injecting a live `.env`. Paid-specific Docker context ignore
files exclude local env files, databases, caches and dependencies; existing
personal-portal Dockerfiles/Compose are unchanged. The API is `app.paid_main`,
not `app.main`. Nginx does not trust caller forwarding headers. No production
proxy trust or client-IP rate-limit policy is claimed by this local setup.

## What the check means

`check-paid-preview.py` only reads a loopback HTTP origin. It rejects external
URLs/credentials, disables environment proxies and redirects, and does not print
response bodies. It checks the product health identity, door homepage, disabled
fresh accounts/private features/billing, and absence of portal/recovery routes.
A successful result is `preview_ready: true`, **always `launch_ready: false`**.
It is not an authorization record and cannot enable anything.

## Before public launch

- Choose the final domain and brand; authorize DNS and deployment explicitly.
- Provision a genuinely dedicated production database; test backup and restore.
- Validate real HTTPS, secure host-only sessions, production reverse-proxy trust,
  trusted client IPs/rate limits, account isolation and security review.
- Select an authorized verified sender/domain, securely supply credentials, test
  real mailbox delivery, failure handling and abuse limits. Adapter availability
  is not delivery confirmation.
- Install and verify authentication-material retention scheduling.
- Confirm payment-provider eligibility, pricing, refund policy and tax obligations;
  test signed webhooks, retries, reconciliation and refunds before live payments.
- Review feature scope and paid entitlements, especially Qian, whose price was not
  invented by these infrastructure milestones.

These are deliberately unresolved launch requirements, not reasons to stop safe
feature development. Review draft PRs #20–#22 and this package in stack order;
merging into main can trigger production and is a separate controlled action.

# Interactive narration reliability (offline verification)

This milestone keeps all provider credentials and live services disabled. It
changes failure handling, not feature availability or pricing. Narration is
best-effort decoration: a voice failure must not hold the reading UI indefinitely.

## Browser behavior

- Cloud request **and response-body consumption** share a 15-second deadline.
- Audio playback and browser speech have 30-second watchdogs. These are safety
  ceilings, not promises of provider completion or the length of a reading.
- A failed cloud request or playback falls back to browser speech once. No cloud
  retry is automatic. A 503 disables cloud attempts for that narration instance.
- Paid 401 invalidates the local paid session and does not read private text via
  fallback. Portal-mode fallback remains compatible.
- Cancel/supersede stops pending playback and speech, releases waiters and object
  URLs, and ignores late network completions. An abort is not provider rollback.
- Silent narration cancels its previous timer when superseded.

Browser speech can be unavailable or blocked by browser policy; text remains the
primary result. A watchdog may stop unusually long spoken segments rather than
freeze interaction. No real model, TTS voice or delivery quality was tested.

## Backend transport limits

Interactive oracle requests use a 60-second SDK transport timeout and disable
SDK automatic retries, without changing other portal AI clients. Interactive TTS
uses a 10-second HTTP transport timeout; the shared long-form podcast helper
keeps its existing 120-second default. TTS timeouts return generic 504 and other
provider failures generic 502, without logging raw provider exception details.

These backend limits are transport/inactivity limits, **not total generation
wall-clock deadlines**. A stream making continual progress can last longer.
Tests verify configured limits and synthetic failure handling, not a real
provider's timing or billing behavior.

## Operator checks before a real preview

1. Keep existing preview defaults: no credentials, live checkout or real email.
2. Run offline narration/stream regressions and paid browser integration; use the
   existing disposable preview package for navigation and disabled-state checks.
3. If later authorized to test a provider, inspect latency, cost limits and
   provider cancellation semantics separately. A browser timeout stops waiting;
   it does not prove a remote request stopped running or was not billed.
4. Never automatically repeat an uncertain reading/payment operation. Inspect
   history/balance and the read-only audit before deciding on a retry.
5. Preserve the separate launch checklist in `paid-stack-review.md`. Green mocks
   do not establish provider eligibility, real email delivery or public readiness.

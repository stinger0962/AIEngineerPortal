# Whole-stack review: fresh paid product (#20–#27)

Scope: the complete fresh-product stack, not only the latest PR. This is a
nonproduction review. No credentials, provider traffic, real customer data,
production configuration or deployment is involved. Passing local/CI tests is
not authorization for public launch.

## Substantive integration findings

### P1: incomplete Qian streams can leave the experience stuck

The Qian SSE client accepted end-of-file without a terminal done/error event,
leaving its playback queue open and the UI waiting indefinitely. Empty backend
generation could also report success without a saved reading. The correction
closes incomplete flows as failures, preserves cancellation behavior and
never calls success for missing output. Synthetic truncated/empty streams verify
this without AI provider requests.

### P1: interrupted persistence could duplicate reading history

Qian and Ziwei salvaged generated text after a persistence exception. If a commit
had succeeded but its acknowledgement was lost, that salvage could insert the
same reading/messages again. Both streams now distinguish provider interruption
from a persistence attempt and never retry persistence after that attempt.
Synthetic commit-then-raise tests assert one attempt and the resulting exact
reading/message/usage/debit counts. An error after uncertain commit is still not
proof of rollback; users should inspect history/balance before retrying.

### P2: browser drafts and retry memory survived account switches

Test-mode private drafts were keyed by profile ID, which SQLite can reuse after
deletion. Clearing storage on explicit login did not cover another-tab account
switch or the in-memory retry cache. Before private children mount, the gate now
synchronizes the verified account with a nonsecret tab marker, clears old drafts,
selected profile and retry references on identity change, and resets retry
memory. Same-account reloads preserve labelled drafts; unlabelled legacy state
is not adopted. Offline and browser switch tests verify isolation.

### P2: paid cloud narration missed the fresh-account request contract

The shared narration client lacked the paid client header/session options. The
paid API correctly rejected it, but automatic browser-voice fallback masked the
integration failure. The fix applies the same cookie/header/no-store contract as
other paid APIs, invalidates expired sessions and stops private narration rather
than continuing fallback after paid authentication failure. Personal-portal
fallback behavior remains unchanged. Offline tests inspect requests and fallback
behavior; real speech-provider delivery is not claimed.

### P2: startup database separation relied on URL spelling

Retention tooling already rejected file aliases, but the paid app startup used
only URL-object equality. A SQLite symlink/hardlink or equivalent path could
therefore target the portal file before the unrelated-table guard caught it.
Startup and read-only/retention maintenance now share a pure guard that rejects
identifiable aliases before opening/creating storage. Disposable alias fixtures verify this, without touching portal files.
No URL/schema guard can prove two arbitrary network hostnames route to distinct
physical production databases; the operator must still provision isolated data.

## Cross-stack boundaries reviewed

- New signup/session identity is independent of legacy device ownership and PR19.
- Ziwei/Qian private APIs and credits/history require the verified paid account;
  client headers or return query parameters cannot grant ownership/payment.
- Reading storage and paid-owner records stay on the requested paid database.
- Test fulfillment keeps order transition and credit grant transactional;
  duplicate/reordered delivery is tested. Refund/dispute processing remains
  explicitly unsupported, not misrepresented as completed.
- Account switches remount private UI; request generations reject stale billing
  responses. Default builds show unavailable accounts/checkout truthfully.
- Preview packaging is loopback-only with disposable data; maintenance tools are
  dry-run/read-only by default and have no installed production schedules.

## Remaining release blockers and unverified assumptions

1. **Public domain/deployment:** final domain/brand, explicit deployment approval,
   dedicated database, backups/restore and actual HTTPS/browser validation.
2. **Identity operations:** authorized sender/domain/credentials, real email
   delivery and abuse controls; production proxy/client-IP trust and retention
   cadence/alerting. Injectable test mail is not real mail delivery.
3. **Product/AI:** real model/TTS integration, capacity/cost limits and failure
   monitoring. Qian's pricing/entitlement policy has not been invented.
4. **Payments:** business/payment-provider eligibility, final prices/currency,
   tax/refund policies, provider reconciliation and real refund/dispute lifecycle.
   Existing synthetic tests do not establish provider eligibility or settlement.
5. **Scope:** private-data retention/deletion policy and support process remain
   distinct from expired-auth-material cleanup. Focused accessibility checks are
   not a full WCAG/security/compliance certification.

The PR stack is draft and unmerged. Main can auto-deploy the personal portal, so
merge/release remains a separately controlled action. Safe offline development
can continue without claiming these launch requirements are resolved.

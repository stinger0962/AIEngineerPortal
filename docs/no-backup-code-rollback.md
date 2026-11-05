# No-backup release and code-only rollback preparation

The user has chosen to proceed without database backups for this Portal release.
Backups are optional risk protection, not a technical prerequisite imposed here.
Code rollback cannot recover damaged/deleted data, files or lost writes.

## Bounded helper

`scripts/release-image-state.py` has two bounded operations for later integration
into the current trusted deployment workflow:

- `record <candidate-sha>`: before checkout, retagging or app replacement, require
  healthy existing backend/frontend containers, capture their immutable local image
  IDs and previous checkout SHA, and record the Compose file hash. Store only
  metadata in a private sibling directory outside the repository's git-clean scope.
  Exclusive creation refuses to overwrite existing evidence.
- `rollback <candidate-sha>`: accept no image-reference input. Read the captured
  record, enforce strict schema/ownership/permissions, reject symlinks and changed
  Compose content, verify both images still exist locally, then retag only those
  images and recreate only backend/frontend with no dependencies/build/pull.
  Verify both restored image IDs and container health with bounded retries.

A private nonblocking operation lock rejects overlapping helper invocations.
The current workflow's release-wide concurrency must still cover the full forward
release between capture and replacement.

No database restore, table removal, volume deletion, image prune, registry pull,
secret printing or old-workflow checkout is included. Current DB/media data and
the additive `billing_requests` table remain intact. Reverting application images
also reintroduces the prior privacy/payment behavior and bugs.

The latest preflight observed both running application images locally. Registry
retrievability was not tested. This helper fails if a recorded image has been
removed; it never substitutes `latest` or downloads an arbitrary reference.
Private state protects against accidental/unprivileged tampering, not compromise
of the trusted deployment account. A missing or partial record fails closed.

The repository checkout remains on the candidate when application images roll
back. Therefore Git HEAD alone is not evidence of the running application version;
use the recorded/restored image IDs. A failed partial rollback needs investigation,
not an automatic database restore or repeated blind retries.

## Required integration boundary

Forward releases use main pushes or manual dispatch; rollback remains manual only. The helper
can be tested entirely with temporary files and mocked commands.

The reviewed integration must use the current trusted fingerprint-pinned
SSH workflow and its existing serialized release group for both forward release
and rollback. Capture the record before changing the checkout or aliases; preserve
existing images; run public HTTPS smoke checks after rollback. Do not invoke an
old tagged workflow. No deployment or rollback has been executed by this work.

The forward CI gate only permits current main. The bounded rollback mode bypasses
that forward-only SHA rule solely for captured previous local images while retaining
trusted workflow source, fixed host, serialization, state validation and health checks.
Do not enable an automatic production trigger before that integration is reviewed.

## Health timing and configuration limits

Rollback health verification has a five-minute monotonic deadline, allowing
legitimate container startup delays beyond the earlier short retry window.
Individual inspection calls are bounded by the remaining deadline. Tests include
a delayed healthy startup and deadline exhaustion.

Only application image selection is restored. The production environment file,
repository checkout and database/media contents are not rolled back. Environment
changes must be reviewed for compatibility with the previous application before
using code rollback; this helper does not prove that compatibility.

Before activation, rehearse the actual Docker/Compose commands in an isolated
environment with disposable containers and volumes. Mocked tests establish command
bounds and logic, not successful rollback on the production Docker installation.

CI now includes an opt-in real-Docker rehearsal on the disposable GitHub runner:
two local fixture image revisions, recorded previous IDs, replacement and rollback,
and a sentinel file checked in the fixture volume after rollback. It requires
preexisting fixture resource names to be absent, uses the already pulled official
PostgreSQL base image with network-disabled builds, and removes only its own
fixture resources. It never connects to the Portal server. A successful rehearsal
validates actual Docker/Compose command behavior on CI, not production compatibility.

## Existing manual workflow integration

The existing Build & Deploy workflow now offers `operation: deploy` (default)
and `operation: rollback`. Merging the automatic-main workflow activates forward
deployment, including for its own merge commit; preparation on a branch does not.

Forward release captures previous local application images before any environment
upserts, checkout or replacement. A rerun uses the original valid state for that
candidate SHA and rechecks both old images remain available; it never overwrites
the original rollback point. Corrupt/incompatible state fails closed.

For rollback, select the current `main` workflow and supply the exact candidate
release SHA that captured the desired previous images. This path does not build,
pull, upsert environment settings or run the forward current-main CI gate. It uses
current reviewed helper source, the same trusted SSH pin and whole-workflow
serialization, strict recorded-image validation, internal health and public HTTPS
checks. An unrecorded SHA fails before image mutation. Do not use an old workflow.

There is no automatic database restore and no backup gate. User data and the extra
billing table remain. Environment compatibility must still be considered because
the environment file is not rolled back. The manual production release was verified in [run 42012305298](https://github.com/stinger0962/AIEngineerPortal/actions/runs/42012305298).
A production rollback and the automatic deployment path remain unverified; CI's
rehearsal uses disposable fixtures.

Before forward capture, the renderer supplies the candidate Compose SHA256 and
the helper requires the installed Compose to match exactly. A future Compose
change stops before environment updates, image replacement or state creation;
it requires a separately reviewed compatibility path, not a bypass.

Immediately before rollback SSH, the workflow checks GitHub's current main SHA
against the executing workflow SHA. Merely having a main ref name is insufficient:
re-running an older main workflow fails closed. This check does not require
forward-release CI eligibility for the old application images. As with the forward
gate, it is a point-in-time check, not a lock preventing subsequent main commits.

## Safe failure diagnostics

The helper reports only fixed stage/category labels, never raw exception messages,
paths, command output, image references, or configuration values. Every failure
still returns nonzero; diagnostics do not relax validation or retry an operation.
For example, `stage=previous_commit category=command_failed` identifies a failed
Git read, while `stage=candidate_compatibility category=candidate_compose_incompatible`
means capture stopped before its state-directory/lock writes. A later capture
failure may leave those private state files; it does not imply an app rollout.
The workflow skips forward deployment after capture failure. Investigate the
reported stage rather than rerunning unchanged or bypassing a guard. An unknown
failure remains `category=operation_failed` without disclosing its exception.

The fixed Git revision read additionally classifies stderr into
`git_dubious_ownership`, `git_not_repository`, `git_permission_denied`, or
`git_command_failed`. These are diagnostic hints, not permission to bypass a
check. Raw stderr/stdout remain private; no arbitrary environment/config inheritance,
ownership change, or safe-directory exception is introduced. Unknown messages still fail
closed. A category must be observed before attributing a production failure to it.

### Existing account Git configuration

Only the fixed Git revision read receives HOME from the operating system account
record for the effective UID, after validating an absolute, nonsymlink directory
owned by that UID. Incoming HOME, XDG_CONFIG_HOME, GIT_CONFIG_* and SUDO_UID are not
inherited. Git may therefore read the account's already-existing configuration;
no configuration is written and no safe.directory exception is added. Git's own
ownership check still applies and may still reject the repository. Docker keeps
its original scrubbed environment and fixed local socket. This corrects a context
difference from the successful preflight, but does not prove the server has an
existing applicable trust entry or guarantee a successful release.

## Automatic replay and manual recovery

Automatic `prepare-auto` applies the same candidate Compose check and operation
lock as manual `prepare`, but exclusively creates the capture record. An existing
record fails closed before forward environment/checkout/image changes. It cannot
reuse a SHA after a prior automatic/manual attempt or rollback, including when the
automatic run was queued behind that rollback. Automatic run attempts beyond 1
are also rejected. Keep the private state records: they now serve both rollback
and automatic duplicate prevention. A partial record also blocks automatic replay.

A fresh manual deployment on current main can reuse the original validated record
for deliberate recovery. No automatic rollback or data restore is added. A newer
main SHA may still deploy after rollback; rollback does not freeze future releases.
GitHub concurrency does not promise FIFO or that a queued rollback will execute:
a newer pending run can replace it. Confirm the rollback run and health results.

If rollback must remain in place, pause merges to main and inspect pending forward
runs in GitHub Actions. Cancel pending forward runs deliberately and verify their
status before relying on rollback; do not assume serialization freezes deployment.
A different/newer SHA already queued can still deploy after rollback. Cancellation
of a running deployment requires separate investigation because it may already
have changed production.

Failure after capture but before rollout still consumes the automatic attempt for
that SHA. Preserve the record, investigate the failure, then use a fresh manual
`operation: deploy` from current main for deliberate recovery. Do not rerun an
automatic push workflow or delete capture evidence to force a retry.

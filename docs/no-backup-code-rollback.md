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

The integration below uses only the existing manual/tag trigger family. The helper
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
and `operation: rollback`. Automatic main-push deployment is still not enabled.
No production operation has been executed by this integration work.

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
the environment file is not rolled back. The first production release and rollback
remain unverified until actually run; CI's rehearsal uses disposable fixtures.

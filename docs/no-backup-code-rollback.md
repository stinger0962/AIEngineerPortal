# No-backup release and code-only rollback preparation

The user has chosen to proceed without database backups for this Portal release.
Backups are optional risk protection, not a technical prerequisite imposed here.
Code rollback cannot recover damaged/deleted data, files or lost writes.

## Implemented helper, not activated workflow

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

This PR does not edit deployment triggers or wire these operations into a live
workflow. It can be tested entirely with temporary files and mocked commands.

A follow-on reviewed integration must use the current trusted fingerprint-pinned
SSH workflow and its existing serialized release group for both forward release
and rollback. Capture the record before changing the checkout or aliases; preserve
existing images; run public HTTPS smoke checks after rollback. Do not invoke an
old tagged workflow. No deployment or rollback has been executed by this work.

The existing manual workflow has no rollback selector and its forward CI gate
only permits current main. A bounded rollback mode must bypass that forward-only
SHA rule solely for the captured previous local images while retaining trusted
workflow source, fixed host, serialization, state validation and health checks.
Do not enable an automatic production trigger before that integration is reviewed.

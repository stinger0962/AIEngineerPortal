# Release Process

## Automatic main deployment and activation

After this workflow change is merged, every push to `main` starts one deployment
candidate using that push's exact SHA. **Merging this PR activates the trigger and
starts a candidate for the merge commit itself.** A feature branch or draft PR
runs nonproduction CI only. Automatic deployment is not operationally verified
until an automatic run completes successfully.

1. Make changes on a feature branch and open a PR.
2. Run relevant tests and review the PR, including its production impact.
3. Merge to main when ready for production. The deploy workflow waits up to about
   15 minutes for successful push CI for that exact current main SHA.
4. Verify the Build & Deploy Portal run, internal health and public HTTPS checks.
5. Optionally publish a `v*` tag for release notes. Tags no longer trigger deployment;
   this avoids deploying the main commit twice. Release notes are not rollout proof.

No workflow creates commits or tags, and no CI-completion trigger retries a release.
Manual `workflow_dispatch` on current main retains `deploy` and `rollback` choices.
Tag-selected manual deployments are rejected. Use main for deliberate recovery.

## Eligibility, duplicates and rollback

The release gate checks current main and successful exact-SHA push CI before builds
and again immediately before production mutation. PR CI cannot authorize a release.
Stale SHA, failed, missing, incomplete, timed-out or unverifiable CI fails closed.
A newer main push can make an older candidate stale; the check is point-in-time,
not a lock against subsequent commits. Each candidate builds and deploys its exact
SHA, never a newly resolved main checkout.

`production-release` concurrency serializes deploy and manual rollback without
cancelling a running operation. GitHub does not guarantee FIFO: it may replace an
older pending run, including a pending rollback. Verify the rollback actually ran.

Automatic push runs require attempt 1. Rerunning such a run is rejected; use a fresh
manual deploy on current main after investigation. Before server checkout,
environment updates or application replacement, automatic capture exclusively
creates the existing per-candidate image record. Any existing record blocks that
SHA automatically, including after partial failure, a manual deployment or rollback.
Thus an automatic run queued behind rollback of that same candidate cannot undo it.
This durable guard depends on retaining the private release-state directory. Never
remove its records to bypass a failure. Builds/registry pushes can precede this
guard, but the guarded server deployment is skipped on failure.

A fresh manual deploy explicitly permits reuse of the original valid capture record
and may redeploy a rolled-back SHA. A distinct newer main SHA is a new candidate
and can deploy after a rollback; rollback is not a permanent deployment freeze.
There is no automatic rollback, data restore or automatic production retry policy.

Previous images are retained without release-time pruning; this is not a disk-space
guarantee. See [bounded code rollback](no-backup-code-rollback.md). The user chose
no backup requirement. **Code-image rollback cannot recover lost or damaged data**
and does not restore environment configuration. Compose changes fail compatibility
checks and require separate review. Keep billing disabled unless separately approved.

## Verified baseline

[Manual production run 42012305298](https://github.com/stinger0962/AIEngineerPortal/actions/runs/42012305298)
succeeded on `159dd483c4a6dd099201757ce9c8b62acf31974b`, including image capture,
internal health and public HTTPS checks. That verifies the manual rollout and the
health-check User-Agent fix. A real production rollback and the future automatic
path remain unverified; CI rollback rehearsals use disposable fixtures.

## Read-only production preflight

The manual-only `production-preflight.yml` workflow runs only on `main`.
Its unauthenticated observation step requires `VPS_HOST` to resolve exclusively
to the owner's confirmed **AIEngineerPortal** Droplet, `146.190.124.162`.
The previously assumed `64.225.43.230` belongs to a different project and is
not an allowed Portal inspection target.

Supply a SHA256 host-key fingerprint obtained from the Portal Droplet's trusted
console or an already trusted connection. Observed network fingerprints are
diagnostics only and must never be used to establish trust. The subsequent SSH
action still verifies the supplied trusted fingerprint before authentication.
A target mismatch or observation error stops the workflow before that action.

This workflow only inspects fixed metadata; merging a preflight fix does not
deploy the application, change repository secrets, or change server trust.

## Trusted deployment endpoint and public smoke checks

All deployment SSH steps now require the Portal ECDSA host-key fingerprint
confirmed from its trusted console and matched by the read-only preflight.
A mismatch fails SSH; do not replace the pin with an unauthenticated observation
or disable verification to proceed. A legitimate host-key rotation requires a new
trusted verification, not a retry with a guessed fingerprint.

After internal health verification, fixed HTTPS checks require
`https://portal.leipan.cc/health` to return HTTP 200 JSON `{"status":"ok"}`
and the root page to return HTTP 200 HTML. Certificate/hostname verification is
mandatory, redirects are refused, retries/timeouts are bounded, and response
bodies/errors are not logged. These checks confirm public routing and basic
responses, not full application behavior or the deployed commit identity.

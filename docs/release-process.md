# Release Process

This repository uses a deployment-first workflow.

## Standard procedure for each version

1. Make code changes locally in the repository.
2. Run the relevant verification steps.
3. Commit to `main`.
4. Create a Git tag for the version.
5. Push both the branch and the tag to GitHub.
6. Let GitHub create a Release entry with release notes for that tag.
7. Let GitHub Actions build/push images, then SSH into the VPS to fetch the tagged commit, pull/recreate containers, and check container health.
8. Verify the live site at `https://portal.leipan.cc`.

## Default expectation

Unless the user explicitly says otherwise, changes should follow the full path:

- commit
- push to GitHub
- create/push version tag
- create a GitHub Release with notes
- deploy to VPS

## Versioning

Use simple semantic-style version tags:

- `v0.1.0`
- `v0.1.1`
- `v0.2.0`

## Release notes

Each release should include:

- what changed
- which commits are included
- deployment target
- what was verified
- any known issues or follow-up work

By default, the GitHub release workflow generates release notes from the commit range included in the version tag.

## Deployment behavior

Production deployment is tag-driven.

- A pushed `v*` tag triggers the deploy workflow.
- The workflow writes production secrets onto the VPS.
- The VPS checks out the exact `GITHUB_SHA` tied to that workflow run.
- GitHub Actions builds images; Docker Compose recreates services using those images with `--force-recreate --remove-orphans`.
- GitHub Actions checks backend container health via SSH; public-site smoke testing is a separate verification step.

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

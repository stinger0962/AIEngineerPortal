# Release Process

This repository uses a deployment-first workflow.

## Standard procedure for each version

1. Make code changes locally in the repository.
2. Run the relevant verification steps.
3. Commit to `main`.
4. Create a Git tag for the version.
5. Push both the branch and the tag to GitHub.
6. Let GitHub create a Release entry with release notes for that tag.
7. Trigger deployment to the VPS.
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

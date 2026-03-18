# Release Process

This repository uses a deployment-first workflow.

## Standard procedure for each version

1. Make code changes locally in the repository.
2. Run the relevant verification steps.
3. Commit to `main` and push to GitHub.
4. The `Auto Release & Deploy` workflow automatically:
   - Bumps the patch version (e.g., v0.2.5 → v0.2.6)
   - Creates and pushes the Git tag
   - Publishes a GitHub Release with auto-generated notes
   - SSHs into the VPS, fetches the exact commit, rebuilds containers
   - Verifies the public health endpoint

## Manual release (optional)

For major/minor version bumps, create a tag manually:

```bash
git tag -a v0.3.0 -m "Release v0.3.0"
git push origin v0.3.0
```

This triggers the `Deploy Portal` and `Create Release` workflows.

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

Production deployment happens automatically on push to `main` via the `Auto Release & Deploy` workflow. Manual `v*` tags also trigger the `Deploy Portal` workflow as a fallback.

- The workflow writes production secrets onto the VPS.
- The VPS checks out the exact `GITHUB_SHA` tied to that workflow run.
- Docker Compose rebuilds with `--force-recreate --remove-orphans`.
- GitHub Actions performs a public health check with retries after deployment.

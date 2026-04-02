# Claude Code Instructions

## Deployment Rules (STRICT)

1. **NEVER SSH into the VPS to manually deploy.** No `docker compose up --build` via SSH. No manual `git checkout` on the VPS.
2. **All deployments happen through GitHub Actions.** The only workflow is:
   ```
   git add → git commit → git push origin main → git tag vX.Y.Z → git push origin vX.Y.Z
   → GitHub Actions triggers → builds images in CI → pushes to GHCR → SSHes into VPS to pull & restart
   ```
3. **Never run `docker build` on the VPS.** The 2GB droplet will OOM. Images are built in CI and pulled from GHCR.
4. **A change is not done until it is deployed via GitHub Actions.** Committed and pushed is not done. Tagged and pipeline green is done.
5. **If a deploy fails**, debug the GitHub Actions workflow and fix it — do not bypass it.
6. **If the VPS is down**, power cycle from the DigitalOcean console. Containers are configured to auto-restart.

# AI Engineer Portal

AI Engineer Portal is a private personal operating system for a senior full-stack engineer transitioning into AI engineering. The product is live through Phase 3, and Phase 4 now focuses on turning the learning system into real curriculum depth. The portal currently includes:

- a personalized dashboard
- a structured learning center
- curated course tracks
- a Python practice hub
- an AI knowledge library
- a projects workspace
- interview preparation scaffolding
- PostgreSQL/Redis-backed local infrastructure
- Docker-ready deployment assets for a VPS

## Monorepo layout

```text
frontend/   Next.js App Router frontend
backend/    FastAPI application, models, services, routes, tests
infra/      Deployment-oriented compose and Docker assets
docs/       Architecture, contracts, route map, and seed strategy
scripts/    Helper scripts and entrypoints
```

## Quick start

1. Copy `.env.example` values into `frontend/.env.local` and `backend/.env`.
2. Start infrastructure:

```powershell
docker compose up -d postgres redis
```

3. Install backend dependencies and run the API:

```powershell
py -3.8 -m pip install -r backend\requirements.txt
py -3.8 -m uvicorn app.main:app --reload --app-dir backend
```

4. Install frontend dependencies and run the app:

```powershell
& 'C:\Program Files\nodejs\npm.cmd' install --prefix frontend
& 'C:\Program Files\nodejs\npm.cmd' run dev --prefix frontend
```

5. Open `http://localhost:3000`.

## Primary endpoints

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000/api/v1`
- API docs: `http://localhost:8000/docs`

## Product status

- The product is single-user and private for now.
- Reference content is synced automatically on backend startup so deployed environments can pick up learning, exercise, article, and interview content improvements without wiping user activity.
- Phase 2 and Phase 3 are live: the portal now includes market intelligence, signal-driven recommendations, interview planning, skill-gap surfacing, and portfolio-readiness scoring.
- Phase 4 is active and focuses on real curriculum depth across lessons, courses, practice, knowledge, interview prep, and project blueprints.
- Deployment assets are included under [`infra/`](D:\AIEngineerPortal\infra) for local/VPS parity.

Checkpoints and roadmap:

- [`docs/phase-1-checkpoint.md`](D:\AIEngineerPortal\docs\phase-1-checkpoint.md)
- [`docs/phase-2-checkpoint.md`](D:\AIEngineerPortal\docs\phase-2-checkpoint.md)
- [`docs/phase-3-checkpoint.md`](D:\AIEngineerPortal\docs\phase-3-checkpoint.md)
- [`docs/revised-roadmap.md`](D:\AIEngineerPortal\docs\revised-roadmap.md)
- [`docs/phase-4-plan.md`](D:\AIEngineerPortal\docs\phase-4-plan.md)

## Production deployment

The repo is prepared for GitHub Actions based deployment to a VPS.

### GitHub repository secrets

- `VPS_HOST`
- `VPS_USER`
- `VPS_SSH_KEY`
- `APP_DOMAIN`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`

### Droplet bootstrap

Run once on the server:

```bash
curl -fsSL https://raw.githubusercontent.com/stinger0962/AIEngineerPortal/main/scripts/bootstrap-droplet.sh | bash
```

### Deploy flow

1. Point your DNS `A` record to the Droplet IP.
2. Add the GitHub secrets above.
3. Push a version tag such as `v0.2.2`.
4. GitHub Actions SSHes into the Droplet, checks out the exact tagged commit in `/opt/ai-engineer-portal`, and runs:

```bash
docker compose --env-file infra/.env.production -f infra/docker-compose.prod.yml up -d --build
```

The public entrypoint is handled by Caddy with HTTPS.

## Release convention

This project follows a standard release procedure documented in [`docs/release-process.md`](D:\AIEngineerPortal\docs\release-process.md).

By default, each completed version should be:

- committed to `main`
- pushed to GitHub
- tagged with a version
- deployed to the VPS

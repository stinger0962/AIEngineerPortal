# Architecture Decision Notes

## Chosen stack

- Frontend: Next.js App Router, TypeScript, Tailwind CSS, TanStack Query, Recharts
- Backend: FastAPI, Pydantic v2, SQLAlchemy 2.x
- Data: PostgreSQL for primary storage, Redis reserved for caching/background work

## Key decisions

1. Single monorepo for simpler iteration and shared documentation.
2. Single-user Phase 1 model with a seeded profile and auth deferred.
3. Seeded content first so the portal is useful before live ingestion exists.
4. Rule-based recommendations and dashboard aggregation before AI-native automation.
5. Dockerized local infrastructure with deployment-oriented assets for VPS parity.

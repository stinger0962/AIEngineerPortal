# Phase 1 Checkpoint

This checkpoint closes the Phase 1 MVP gap between "working scaffold" and "usable private learning portal."

## What this release introduces

- A stronger reference-content library for the live portal:
  - 7 learning paths
  - 35 lessons
  - 40 practice exercises
  - 30 knowledge articles
  - 24 interview questions
- Fresh-start progress defaults:
  - no seeded fake lesson completion
  - no seeded fake practice attempts
  - no seeded fake interview score inflation
- Production-safe frontend data loading:
  - local mock fallback remains available in development
  - production no longer silently masks backend failures with mock data
- Startup content syncing for deployed environments:
  - learning paths, lessons, courses, exercises, articles, and interview questions now sync into an existing database on backend startup
  - existing user progress is preserved
  - seeded project templates are inserted only when the project table is empty

## What should feel different

- The portal should read more like a real study system than a demo.
- Dashboard progress should start from actual activity instead of seed noise.
- Learning, practice, knowledge, and interview sections should contain materially better topic coverage.
- If production data is unavailable, the site should fail loudly instead of pretending everything is healthy.

## Verification checklist

Use the live portal at `https://portal.leipan.cc`.

### Dashboard

- Open the dashboard.
- Confirm the learning completion stat starts at `0.0%` on a fresh account state.
- Confirm the recommended lesson points to the first unfinished lesson rather than a random seeded completion state.

### Learning center

- Open `/learn`.
- Confirm there are 7 learning paths.
- Open `Python for AI Engineers`.
- Confirm the lessons are practical and specific to AI engineering work rather than generic placeholders.
- Complete one lesson and return to the dashboard.
- Confirm the learning completion stat changes.

### Practice hub

- Open `/practice/python`.
- Confirm the catalog is substantially populated.
- Open a few exercises from different categories such as Python refresh, retrieval, evaluation, and async/provider work.
- Submit one attempt.
- Confirm the attempt is saved and reflected in dashboard practice stats.

### Knowledge hub

- Open `/knowledge`.
- Search for topics such as `rag`, `evaluation`, or `deployment`.
- Confirm the results are topical and not generic sample-note filler.

### Interview center

- Open `/interview`.
- Confirm the questions cover Python, RAG, evaluation, agents, deployment, system design, and behavioral transition stories.

### Reliability check

- If a backend issue occurs in production, the frontend should no longer quietly render dev mocks.
- A production data failure should be visible so it can be fixed instead of hidden.

## Local verification used for this checkpoint

- Backend API tests
- Frontend production build
- Live deployment verification after release

## Follow-up after Phase 1

The next serious milestone is Phase 2:

- live news and jobs ingestion
- AI-assisted summarization and tagging
- durable content operations beyond seed-driven updates
- deeper personalization based on real activity instead of static rules

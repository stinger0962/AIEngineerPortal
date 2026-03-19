# Phase 2 Checkpoint

## Summary

Phase 2 moves the portal from static internal curriculum into a live intelligence loop that tracks external AI signals and job-market movement, ranks them, and turns them into concrete next actions inside the product.

Released checkpoints through this phase:

- `v0.2.2` to `v0.2.5`: early live deployment and intelligence scaffolding
- `v0.2.6` to `v0.2.8`: progress-aware and saved-signal-aware recommendations
- `v0.2.9` to `v0.2.11`: dashboard polish, activity-aware guidance, and project-proof-aware recommendations
- `v0.2.12`: precise signal-to-gap mapping and Phase 2 closeout

## What Phase 2 Introduced

- Real `news` and `jobs` modules backed by persisted data rather than static placeholders
- Live ingestion, ranking, dedupe, stale refresh windows, and seeded fallback behavior
- Fit analysis for jobs with concrete skill-gap extraction
- Actionable news and job cards with "why this matters" and "suggested action"
- Saved-signal prioritization so the dashboard follows user-marked items
- Activity-aware dashboard selection for next lesson and recommended practice
- Recommendation logic that adapts to project proof and interview readiness
- Precise signal metadata on intelligence cards:
  - focus area
  - best next learning path
  - best next drill category
  - primary job gap

## Verification Checklist

### News

- Open `/news`
- Confirm cards show:
  - `Why this matters`
  - `Focus area`
  - `Best next path`
  - `Best next drill`
- Click `Refresh feed`
- Save one item and confirm the saved state persists on refresh

### Jobs

- Open `/jobs`
- Confirm cards show:
  - `Fit read`
  - `Primary gap`
  - `Best next path`
  - `Best next drill`
- Click `Analyze fit`
- Save one role and confirm the saved state persists on refresh

### Dashboard

- Open `/`
- Confirm:
  - next lesson reflects the most relevant unfinished path
  - recommended practice can rotate away from already-attempted categories
  - highlights mention tracked and saved signals
- Save one news item and one job
- Refresh `/` and confirm the dashboard follows those saved signals

### API

- `GET /api/v1/news`
- `GET /api/v1/jobs`
- `GET /api/v1/recommendations/next-actions`
- `GET /api/v1/dashboard/summary`
- `GET /api/v1/dashboard/today`

## Known Limits After Phase 2

- External ingestion still depends on the quality and availability of public feeds
- Job/news reasoning is rule-based, not LLM-generated
- No admin moderation workflow exists yet for curating imported signals
- No background scheduler is running beyond request-time stale refresh logic

## Phase 3 Starting Point

Phase 3 should build on this intelligence base with:

- deeper personalization
- skill-gap tracking over time
- stronger interview planning
- richer portfolio readiness scoring

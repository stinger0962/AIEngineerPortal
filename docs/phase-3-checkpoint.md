# Phase 3 Checkpoint

## Summary

Phase 3 turns the portal from a signal-aware system into a personalized career-transition engine.

This phase focuses on:

- personalized interview planning
- portfolio-readiness scoring
- interview practice tracking
- skill-gap visibility across jobs, learning, and projects

## What Was Added

- Personalized interview roadmap at `/api/v1/interview/roadmap`
- Portfolio-readiness summary at `/api/v1/interview/portfolio-readiness`
- Skill-gap summary at `/api/v1/interview/skill-gaps`
- Interview question practice tracking at `/api/v1/interview/questions/{id}/practice`
- Interview page upgraded from static content to a live planning surface

## User-Facing Outcomes

- The interview center now shows:
  - readiness score
  - strongest signals
  - gaps to close
  - next best moves
  - weekly rhythm
  - interview question practice history
- Practicing interview questions now changes the portal state instead of being read-only
- Readiness scoring now gives partial credit for active project motion, not only completed artifacts

## Verification

- Open `/interview`
- Confirm the page shows:
  - readiness score
  - weekly plan
  - skill gap cards
  - interactive interview question rep buttons
- Click one `Log rep` button on a question
- Refresh `/interview`
- Confirm:
  - question practice count increases
  - last practiced timestamp appears
  - average confidence updates

## API Checks

- `GET /api/v1/interview/roadmap`
- `GET /api/v1/interview/portfolio-readiness`
- `GET /api/v1/interview/skill-gaps`
- `POST /api/v1/interview/questions/{id}/practice`

## Current Limits

- Lesson bodies still need deeper authored content
- Readiness scoring is deterministic and heuristic-based, not model-generated
- Skill-gap history is current-state oriented, not yet longitudinal

## What Phase 3 Achieved

The portal now adapts to:

- your project state
- your learning progress
- your practice history
- your saved market signals
- your live interview reps

That completes the first serious personalization layer of the product.

# Agents Content Enrichment + AI-Graded Exercise Feedback

**Date**: 2026-03-27
**Status**: Approved
**Phase**: 5.5 (between Phase 5 Adaptive Learning and Phase 6 AI Copilot)

## Context

The AI Engineer Portal has 6 learning paths with static seed content. The Agents path has the thinnest content (5 lessons with 2-3 sentence outlines, 0 agent-specific exercises, 0 agent knowledge articles). The user is a senior full-stack engineer transitioning to AI engineering on the application side — harnessing agents and making them efficient is a core duty of the target role.

All portal content is currently static (hand-authored in `backend/app/seed/data.py`). No LLM integration exists — no API keys, no generation libraries, no dynamic content. Exercise feedback uses keyword matching only.

## Goals

1. Deepen the Agents learning path with real, content-rich teaching material
2. Add the first dynamic AI feature: Claude-powered exercise grading with retry flow
3. Establish the AI service architecture that supports future dynamic features
4. All content framed for a full-stack engineer harnessing agents, not building foundational models

## Non-Goals

- On-demand lesson deep-dives (future iteration)
- AI-generated exercise variations (future iteration)
- Interview answer coaching (future iteration)
- Replacing all static content immediately (progressive replacement over time)

## Architecture Decision

**Option A (now)**: Direct API service — thin `AIService` wrapping Anthropic SDK with structured prompt templates. Synchronous JSON responses (SSE deferred to future free-text features).

**Option C (future evolution)**: Agent-based generation using Claude Agent SDK with tools for reading curriculum, checking mastery state, and generating contextual content.

Option A matches the existing clean service layer pattern and is fast to ship. The `ai_feedback` table is designed to support Option C evolution — agents can query past feedback as tool context.

---

## Part A: Static Content Enrichment (Agents Path)

### Lessons (5 rewritten)

Each lesson: 500-2000 words with this structure:
- **Why this matters** — connect to real AI engineering work
- **Core concepts** — explained for a full-stack dev, not a researcher
- **Working example** — real Python code showing the pattern (not pseudocode)
- **Common mistakes** — what goes wrong in production
- **Try it yourself** — a prompt to experiment

| # | Lesson | Focus | Example Code |
|---|--------|-------|-------------|
| 1 | Tool design for LLM agents | Function schemas, error handling, return contracts | Tool that queries an API with validation + fallback |
| 2 | Planning & reasoning loops | ReAct, plan-then-execute, reflection patterns | ReAct loop that decomposes a multi-step task |
| 3 | Multi-agent orchestration | Handoffs, supervisor patterns, message passing | Supervisor agent delegating to specialist sub-agents |
| 4 | Agent memory & state | Conversation history, working memory, persistence | Agent with sliding window + summary memory |
| 5 | Benchmarking & guardrails | Eval harnesses, cost tracking, safety rails | Test harness that scores agent task completion |

### Exercises (8 new, agent-specific)

Each exercise includes: rich problem statement (what you're building and why), starter code, full solution with example code, detailed explanation, and retry support.

Examples:
- Build a tool registry that validates function schemas
- Implement a ReAct loop for a research task
- Add retry/fallback logic to an agent tool call
- Build a conversation memory manager with token budgeting
- Create a multi-agent handoff protocol
- Design an agent evaluation harness
- Implement structured output parsing with error recovery
- Build a cost-tracking middleware for agent tool calls

### Knowledge Articles (3-5 new)

- Agent architecture patterns (comparison: ReAct vs Plan-Execute vs Tree-of-Thought)
- Tool design best practices for production agents
- Agent evaluation: how to measure if your agent actually works

### Interview Questions (expanded + new)

- Existing agent questions: expand from ~150 to 400-800 word self-study answers
- Add 5-8 new questions covering current patterns (MCP, Claude Agent SDK, tool use, orchestration)
- Self-study style, not FAANG template (content evolves too rapidly)

---

## Part B: AI Generation Layer (Backend)

### New Dependency

`anthropic` SDK added to `backend/requirements.txt`

### New Config

`ANTHROPIC_API_KEY` added to:
- `backend/app/core/config.py` (Settings class)
- `backend/.env.example`
- `infra/.env.production` on VPS
- GitHub repository secret

### New Service: `ai_service.py`

```
AIService
├── grade_exercise(code, exercise, attempts_history) → structured feedback
├── generate_deep_dive(topic, lesson_context) → markdown content   [stub]
├── generate_exercise_variation(seed_exercise) → new exercise       [stub]
├── coach_interview_answer(question, user_answer) → feedback        [stub]
```

Only `grade_exercise` is wired up this iteration. Others are method stubs documenting the future interface.

**`grade_exercise` details:**
- Input: user's submitted code, exercise definition (prompt, solution, explanation), previous attempt history
- Prompt template: "You're reviewing code from a full-stack engineer learning AI agent patterns. Grade against the solution, give specific feedback with example code fixes, and encourage retry."
- Output structure:
  ```json
  {
    "strengths": ["string"],
    "issues": ["string"],
    "suggestions": ["string"],
    "example_fixes": "string (markdown with code blocks)",
    "score": 0-100,
    "should_retry": true/false
  }
  ```
- Returns synchronous JSON response (SSE deferred to future free-text features)

### New Endpoint

`POST /api/v1/exercises/{exercise_id}/ai-feedback`
- Accepts: `{ "code": "string" }`
- Returns: JSON response (synchronous). SSE streaming deferred to future iteration.
  **Rationale**: Claude returns structured JSON as a complete response — field-by-field SSE streaming of structured output adds complexity without benefit for v1. SSE streaming will be added when we implement free-text features (deep-dives, interview coaching) where progressive rendering improves UX.
  ```json
  {
    "id": 123,
    "feature": "exercise_grade",
    "reference_id": 1,
    "cached": false,
    "strengths": ["..."],
    "issues": ["..."],
    "suggestions": ["..."],
    "example_fixes": "markdown with code blocks",
    "score": 85,
    "should_retry": false,
    "model": "claude-sonnet-4-20250514",
    "input_tokens": 1200,
    "output_tokens": 800,
    "latency_ms": 3200
  }
  ```
- Stores: final feedback saved to `ai_feedback` table, linked to `UserExerciseAttempt`
- Rate limit: simple per-minute Redis counter using existing Redis instance (cost protection)
- Daily token budget: configurable cap (default 100k tokens/day) with hard cutoff returning "daily limit reached" error

### Caching Strategy

- Cache key: `SHA-256(exercise_id + submitted_code)` — scoped by exercise to prevent cross-exercise collisions
- Cache hit → return stored `ai_feedback` record directly (no API call)
- Cache miss → fresh generation, store result
- Redis TTL: 24h

### Error Handling

- API timeout → return partial feedback + "generation interrupted" message
- Rate limit hit → return friendly "try again in X seconds"
- Daily budget exceeded → return "daily AI feedback limit reached, try again tomorrow"
- API key missing → exercise feedback gracefully degrades to existing keyword matching

---

## Part C: Frontend — Exercise Retry & AI Feedback UX

### New Flow

1. **Write code** in exercise editor (starter code pre-filled)
2. **Submit** → code goes to `POST /exercises/{id}/ai-feedback`
3. **Streaming feedback** appears below editor — strengths, issues, suggestions, example code fixes
4. **Score + retry prompt** — if `should_retry` is true, "Try Again" button appears, editor stays populated
5. **Attempt history** — sidebar/accordion shows all previous attempts with AI feedback for progression tracking
6. **Final pass** — when AI says solution is solid, marked complete with summary of learnings across attempts

### UX Details

- Editor never cleared on submit — code stays for iteration
- AI feedback renders markdown (code blocks, bullet points)
- Each attempt saved to `UserExerciseAttempt` with `ai_feedback_id` FK
- "View Solution" always available with nudge: "Try one more time before peeking"
- Fallback: if Claude API down, falls back to existing keyword matching with note

---

## Part D: Data Model

### New Table: `ai_feedback`

Uses `Integer` primary key to match all existing models in `entities.py`.

| Column | Type | Purpose |
|--------|------|---------|
| id | Integer | PK (auto-increment, matches existing convention) |
| user_id | Integer | FK to `users.id` — enables per-user cost tracking and future non-exercise features |
| feature | enum | `exercise_grade`, `deep_dive`, `variation`, `interview_coach` |
| reference_id | Integer | Logical reference (not a DB-level FK constraint) — see mapping below |
| user_input_hash | text | SHA-256 of `exercise_id + submitted_code` — enables cache hits |
| prompt_template | text | System prompt used (debugging/iteration) |
| response_json | JSONB | Structured AI response |
| model | text | Configurable via settings, e.g. `claude-sonnet-4-20250514` |
| input_tokens | int | Cost tracking |
| output_tokens | int | Cost tracking |
| latency_ms | int | Performance tracking |
| created_at | timestamp | |

**Polymorphic `reference_id` mapping** (discriminated by `feature`):

| feature | reference_id points to |
|---------|----------------------|
| `exercise_grade` | `exercises.id` |
| `deep_dive` | `lessons.id` |
| `variation` | `exercises.id` |
| `interview_coach` | `interview_questions.id` |

`reference_id` is a logical reference, not a database-level FK constraint, because it references different tables depending on `feature`.

### Changes to Existing Tables

- `UserExerciseAttempt`: add `ai_feedback_id` FK (nullable, Integer) — links attempt to AI feedback
- No changes to `Exercise`, `Lesson`, `InterviewQuestion` — AI layer supplements, doesn't modify

### Evolution Path to Option C

The `ai_feedback` table supports agent evolution:
- Agents can query past feedback as tool context ("what feedback have I given before?")
- `feature` enum extensible for new generation types
- `prompt_template` column enables A/B testing different prompts
- Token tracking enables cost budgeting per feature
- `user_id` column enables per-user cost caps and personalization

---

## Implementation Approach

### Batch 1: Static Content (Agents Path)
- Rewrite 5 agent lessons in `seed/data.py`
- Add 8-10 agent exercises with starter code, solutions, explanations
- Add 3-5 knowledge articles
- Expand + add interview questions

### Batch 2: AI Service Layer
- Add `anthropic` to requirements
- Add `ANTHROPIC_API_KEY` to config (with configurable model name and daily token budget)
- Create `ai_feedback` table (SQLAlchemy model + Alembic migration)
- Implement `AIService.grade_exercise()`
- Add `POST /exercises/{id}/ai-feedback` endpoint (sync JSON response)
- Add caching + rate limiting using existing Redis instance
- Pin exercise count to 8 (more can be added later)

**Note**: Alembic migration must run before the endpoint is deployed. The deploy script should run `alembic upgrade head` as part of startup.

### Batch 3: Frontend AI Feedback UX
- Update exercise detail page with AI feedback display component
- Add retry flow (keep code, show "Try Again")
- Add attempt history with AI feedback display
- Add fallback to keyword matching when API unavailable

### Batch 4: Integration & Deploy
- End-to-end testing
- Add `ANTHROPIC_API_KEY` to VPS `.env.production`
- Deploy via tag → GitHub Actions pipeline
- Verify on production

---

## Key Files to Modify

**Backend (new):**
- `backend/app/services/ai_service.py` — Claude API wrapper
- `backend/app/api/v1/routes/ai_feedback.py` — AI grading endpoint

**Backend (modify):**
- `backend/app/seed/data.py` — Agent content enrichment
- `backend/app/models/entities.py` — `AIFeedback` model, `UserExerciseAttempt` FK
- `backend/app/core/config.py` — `ANTHROPIC_API_KEY` setting
- `backend/app/api/v1/api.py` — Register new router
- `backend/app/schemas/portal.py` — AI feedback schemas
- `backend/requirements.txt` — Add `anthropic`

**Frontend (modify):**
- `frontend/src/app/practice/python/[exerciseId]/page.tsx` — AI feedback + retry UX
- `frontend/src/components/forms/exercise-attempt-form.tsx` — Streaming integration
- `frontend/src/lib/api/portal.ts` — AI feedback API client
- `frontend/src/lib/types/portal.ts` — AI feedback types

**Infra:**
- `backend/.env.example` — Document `ANTHROPIC_API_KEY`
- VPS `.env.production` — Add `ANTHROPIC_API_KEY`

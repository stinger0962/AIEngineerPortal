# Generated Exercise Variations

**Date**: 2026-03-28
**Status**: Approved
**Depends on**: v0.6.0 (AI grading infrastructure)

## Context

The portal has 48+ static exercises (8 agent-specific). Content only changes when someone commits new seed data. Users want fresh practice material without waiting for manual content updates. The AI grading infrastructure (AIService, ai_feedback table, Anthropic SDK) is already live.

## Goal

Let users generate unlimited exercise variations from any seed exercise, practice them with AI grading, and pin the best ones to their library for future review.

## Architecture

Ephemeral generation + selective pinning. Variations are generated on-demand via Claude, displayed in a temporary panel. Users can practice and get AI feedback on the variation. If it's good, they pin it — which saves it as a real Exercise row linked to its parent.

---

## Backend

### New Endpoint: Generate Variation

`POST /api/v1/exercises/{exercise_id}/variation`

Query param: `variation_type` — one of `"scenario"` (default), `"concept"`, `"harder"`
- `scenario`: Same learning objective, different domain/scenario
- `concept`: Different topic within the same category
- `harder`: Same exercise with added constraints, edge cases, or sophistication

Returns JSON (NOT saved to DB):
```json
{
  "title": "...",
  "prompt_md": "...",
  "starter_code": "...",
  "solution_code": "...",
  "explanation_md": "...",
  "variation_type": "scenario",
  "parent_exercise_id": 1,
  "parent_title": "Build a tool registry"
}
```

Claude generates the `title` field — a descriptive name for the variation (not mechanical concatenation).

Tracks generation cost in `ai_feedback` table with `feature = "variation"`.

Rate limited: uses existing Redis per-minute counter. Subject to daily token budget.

### New Endpoint: Pin Variation

`POST /api/v1/exercises/{exercise_id}/variation/pin`

Request body: the generated exercise content (title, prompt_md, starter_code, solution_code, explanation_md, variation_type)

**Input validation:**
- All content fields required and non-empty
- Max length: `prompt_md` 10K chars, `starter_code` 5K, `solution_code` 10K, `explanation_md` 10K
- `variation_type` must be one of `scenario`, `concept`, `harder`

Creates a new `Exercise` row:
- `title`: From request body (Claude-generated)
- `slug`: Slugified title + 4-char hex suffix from UUID to prevent collisions (e.g., `weather-api-tool-registry-a3f1`)
- `category`: Same as parent
- `difficulty`: Same as parent (harder variations keep same difficulty string — the added complexity is in the prompt, not the label)
- `is_generated`: True
- `parent_exercise_id`: FK to seed exercise
- All content fields from the request body
- `tags_json`: Parent tags + `["generated", variation_type]`

Returns the new exercise with its ID and slug.

### AIService.generate_exercise_variation()

Updates existing stub signature from `(self, seed_exercise: Dict) -> Dict` to `(self, seed_exercise: Dict, variation_type: str) -> Dict`.

Prompt template instructs Claude to:
- Keep the same category and difficulty (unless "harder")
- Generate all four content fields (prompt_md, starter_code, solution_code, explanation_md)
- Match the quality level of the seed exercise
- For "scenario": change the domain but keep the same pattern
- For "concept": teach a different pattern within the same category
- For "harder": add constraints, edge cases, multi-step requirements
- Return valid JSON

Error handling: same as grade_exercise (timeout, connection error, malformed response).

---

## Data Model

### Exercise table: 2 new columns

Added via bootstrap patching (same pattern as `ai_feedback_id`):

```sql
ALTER TABLE exercises ADD COLUMN is_generated BOOLEAN DEFAULT FALSE
ALTER TABLE exercises ADD COLUMN parent_exercise_id INTEGER REFERENCES exercises(id)
```

Uses the existing Python-side column existence check in `bootstrap.py` (no `IF NOT EXISTS` in SQL — matches established pattern).

ORM model additions:
```python
is_generated: Mapped[bool] = mapped_column(Boolean, default=False)
parent_exercise_id: Mapped[Optional[int]] = mapped_column(
    Integer, ForeignKey("exercises.id"), nullable=True
)
```

### ai_feedback table

Existing table, `feature = "variation"`. The `reference_id` points to the parent exercise. `response_json` stores the generated content for cost tracking.

---

## Frontend

### Exercise Detail Page

Add a "Generate Variation" section below the main exercise content:

1. **Dropdown + button**: Select variation type (Scenario / Different Concept / Harder) and click "Generate Variation"
2. **Loading state**: Spinner with "Generating a new variation..."
3. **Variation panel**: Distinct styled panel showing the generated exercise:
   - Generated prompt_md
   - Starter code pre-filled in the existing code editor
   - Two action buttons: "Pin to Library" (ember) and "Discard" (text button)
4. **After pinning**: Redirect to the new exercise page (or show success message with link)
5. **AI grading on unpinned variations**: The variation panel includes its own code editor + "Get AI Feedback" button. For unpinned variations, the grading endpoint is called with the parent exercise ID, but an additional `reference_solution` field is passed in the request body containing the variation's generated solution. The grading prompt uses this override instead of the parent's solution. After pinning, grading works normally via the new exercise ID.

### Practice List Page

- Pinned variations show a small "Generated" badge
- Can filter to show/hide generated exercises
- Generated exercises link back to their parent via `parent_exercise_id`

---

## Key Files

**Backend (new):**
- `backend/app/api/v1/routes/exercise_variations.py` — variation + pin endpoints

**Backend (modify):**
- `backend/app/services/ai_service.py` — implement `generate_exercise_variation()` (update stub signature)
- `backend/app/models/entities.py` — add `is_generated`, `parent_exercise_id` to Exercise
- `backend/app/db/bootstrap.py` — add column patches for existing DB
- `backend/app/schemas/portal.py` — add variation request/response schemas, add optional `reference_solution` to `AIFeedbackRequest`
- `backend/app/api/v1/api.py` — register variation router
- `backend/app/api/v1/routes/ai_feedback.py` — accept optional `reference_solution` override for grading unpinned variations

**Frontend (modify):**
- `frontend/src/app/practice/python/[exerciseId]/page.tsx` — add variation generation UI
- `frontend/src/lib/api/portal.ts` — add variation + pin API methods
- `frontend/src/lib/types/portal.ts` — add variation types
- `frontend/src/app/practice/python/page.tsx` — add "Generated" badge to list

**Frontend (new):**
- `frontend/src/components/forms/exercise-variation-panel.tsx` — variation display + pin/discard

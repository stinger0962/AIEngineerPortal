# Generated Exercise Variations — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users generate unlimited exercise variations from any seed exercise via Claude, practice them with AI grading, and pin the best ones to their library.

**Architecture:** Ephemeral generation via `AIService.generate_exercise_variation()` → temporary UI panel → optional pin to Exercise table. Reuses existing AI grading, rate limiting, and cost tracking infrastructure.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Anthropic SDK, Redis, Next.js 15, React 19

**Spec:** `docs/superpowers/specs/2026-03-28-exercise-variations-design.md`

---

## File Structure

### New Files
| File | Responsibility |
|------|---------------|
| `backend/app/api/v1/routes/exercise_variations.py` | Generate + pin endpoints |
| `backend/tests/test_exercise_variations.py` | Tests for variation generation and pinning |
| `frontend/src/components/forms/exercise-variation-panel.tsx` | Variation display with pin/discard + code editor |

### Modified Files
| File | Changes |
|------|---------|
| `backend/app/services/ai_service.py` | Implement `generate_exercise_variation()` (replace stub) |
| `backend/app/models/entities.py` | Add `is_generated`, `parent_exercise_id` to Exercise |
| `backend/app/db/bootstrap.py` | Add column patches for existing exercises table |
| `backend/app/schemas/portal.py` | Add variation schemas, add `reference_solution` to `AIFeedbackRequest` |
| `backend/app/api/v1/api.py` | Register variation router |
| `backend/app/api/v1/routes/ai_feedback.py` | Accept optional `reference_solution` for grading unpinned variations |
| `frontend/src/lib/types/portal.ts` | Add `ExerciseVariation` type |
| `frontend/src/lib/api/portal.ts` | Add `generateVariation()`, `pinVariation()` methods |
| `frontend/src/app/practice/python/[exerciseId]/page.tsx` | Add variation generation UI |
| `frontend/src/app/practice/python/page.tsx` | Add "Generated" badge to list |

---

## Chunk 1: Backend — Model, Service, Endpoints

### Task 1: Add Exercise model columns and bootstrap patches

**Files:**
- Modify: `backend/app/models/entities.py`
- Modify: `backend/app/db/bootstrap.py`

- [ ] **Step 1: Add columns to Exercise model in entities.py**

In `backend/app/models/entities.py`, add two columns to the `Exercise` class (after `tags_json`):

```python
is_generated: Mapped[bool] = mapped_column(Boolean, default=False)
parent_exercise_id: Mapped[Optional[int]] = mapped_column(
    Integer, ForeignKey("exercises.id"), nullable=True
)
```

Ensure `Boolean` is in the SQLAlchemy imports at the top of the file (it likely already is — check first).

- [ ] **Step 2: Add bootstrap patches in bootstrap.py**

In `backend/app/db/bootstrap.py`, add to `PHASE_FIVE_COLUMN_PATCHES`:

```python
"exercises": [
    (
        "is_generated",
        "ALTER TABLE exercises ADD COLUMN is_generated BOOLEAN DEFAULT FALSE",
    ),
    (
        "parent_exercise_id",
        "ALTER TABLE exercises ADD COLUMN parent_exercise_id INTEGER REFERENCES exercises(id)",
    ),
],
```

- [ ] **Step 3: Verify model loads**

Run: `cd D:/AIEngineerPortal/backend && python -c "from app.models.entities import Exercise; from sqlalchemy import inspect; m = inspect(Exercise); print('is_generated' in {c.key for c in m.columns}, 'parent_exercise_id' in {c.key for c in m.columns})"`
Expected: `True True`

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/entities.py backend/app/db/bootstrap.py
git commit -m "feat: add is_generated and parent_exercise_id columns to Exercise model"
```

---

### Task 2: Add variation schemas and update AIFeedbackRequest

**Files:**
- Modify: `backend/app/schemas/portal.py`

- [ ] **Step 1: Add variation schemas at the end of portal.py**

```python
class VariationRequest(BaseModel):
    """Query params for variation generation."""
    variation_type: str = "scenario"  # "scenario", "concept", or "harder"


class VariationResponse(BaseModel):
    """Ephemeral variation returned from generation (not yet saved)."""
    title: str
    prompt_md: str
    starter_code: str
    solution_code: str
    explanation_md: str
    variation_type: str
    parent_exercise_id: int
    parent_title: str


class PinVariationRequest(BaseModel):
    """Request to pin a generated variation to the exercise library."""
    title: str
    prompt_md: str
    starter_code: str
    solution_code: str
    explanation_md: str
    variation_type: str


class PinVariationResponse(BaseModel):
    """Response after pinning a variation."""
    id: int
    slug: str
    title: str
```

- [ ] **Step 2: Add is_generated and parent_exercise_id to ExerciseOut schema**

Find the existing `ExerciseOut` class in `portal.py` and add:

```python
is_generated: bool = False
parent_exercise_id: Optional[int] = None
```

This ensures the API serializes these fields to the frontend so the "Generated" badge can render.

- [ ] **Step 3: Add optional reference_solution to AIFeedbackRequest**

Find the existing `AIFeedbackRequest` class and update it:

```python
class AIFeedbackRequest(BaseModel):
    """Request body for AI exercise grading."""
    code: str
    reference_solution: Optional[str] = None  # Override for grading unpinned variations
```

- [ ] **Step 4: Verify schemas compile**

Run: `cd D:/AIEngineerPortal/backend && python -c "from app.schemas.portal import VariationRequest, VariationResponse, PinVariationRequest, PinVariationResponse, AIFeedbackRequest; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/portal.py
git commit -m "feat: add variation schemas and reference_solution to AIFeedbackRequest"
```

---

### Task 3: Implement AIService.generate_exercise_variation()

**Files:**
- Modify: `backend/app/services/ai_service.py`
- Create: `backend/tests/test_exercise_variations.py`

- [ ] **Step 1: Write tests for generate_exercise_variation**

Create `backend/tests/test_exercise_variations.py`:

```python
"""Tests for exercise variation generation."""
import json
import pytest
from app.services.ai_service import AIService


@pytest.fixture
def ai_service():
    return AIService(api_key="test-key", model="claude-sonnet-4-20250514")


@pytest.fixture
def seed_exercise():
    return {
        "id": 1,
        "title": "Build a tool registry",
        "category": "agents",
        "difficulty": "intermediate",
        "prompt_md": "Create a registry that validates tool schemas.",
        "starter_code": "class ToolRegistry:\n    pass",
        "solution_code": "class ToolRegistry:\n    def register(self, tool): ...",
        "explanation_md": "The registry validates JSON schemas...",
    }


class TestBuildVariationPrompt:
    def test_scenario_prompt_mentions_different_domain(self, ai_service, seed_exercise):
        prompt = ai_service._build_variation_prompt(seed_exercise, "scenario")
        assert "different domain" in prompt["system"].lower() or "different scenario" in prompt["system"].lower()
        assert "Build a tool registry" in prompt["user"]

    def test_concept_prompt_mentions_different_pattern(self, ai_service, seed_exercise):
        prompt = ai_service._build_variation_prompt(seed_exercise, "concept")
        assert "different" in prompt["system"].lower()

    def test_harder_prompt_mentions_constraints(self, ai_service, seed_exercise):
        prompt = ai_service._build_variation_prompt(seed_exercise, "harder")
        assert "harder" in prompt["system"].lower() or "constraint" in prompt["system"].lower()

    def test_includes_seed_exercise_content(self, ai_service, seed_exercise):
        prompt = ai_service._build_variation_prompt(seed_exercise, "scenario")
        assert seed_exercise["prompt_md"] in prompt["user"]
        assert seed_exercise["solution_code"] in prompt["user"]


class TestParseVariationResponse:
    def test_parses_valid_json(self, ai_service):
        raw = json.dumps({
            "title": "Weather API tool registry",
            "prompt_md": "Build a registry for weather tools...",
            "starter_code": "class WeatherRegistry:\n    pass",
            "solution_code": "class WeatherRegistry:\n    def register(self): ...",
            "explanation_md": "The weather registry...",
        })
        result = ai_service._parse_variation_response(raw)
        assert result["title"] == "Weather API tool registry"
        assert "prompt_md" in result
        assert "starter_code" in result

    def test_handles_malformed_json(self, ai_service):
        result = ai_service._parse_variation_response("not json")
        assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd D:/AIEngineerPortal/backend && python -m pytest tests/test_exercise_variations.py -v`
Expected: FAIL — `_build_variation_prompt` not found

- [ ] **Step 3: Implement generate_exercise_variation in ai_service.py**

Replace the `generate_exercise_variation` stub method with:

```python
def _build_variation_prompt(
    self,
    seed_exercise: Dict[str, Any],
    variation_type: str,
) -> Dict[str, str]:
    """Build prompt for generating an exercise variation."""
    type_instructions = {
        "scenario": (
            "Generate a variation with a DIFFERENT domain/scenario but the SAME learning objective. "
            "For example, if the original uses a database, use a weather API instead. "
            "Keep the same difficulty and the same core pattern being taught."
        ),
        "concept": (
            "Generate a DIFFERENT exercise within the same category. "
            "Teach a different pattern or concept, but keep the same difficulty level. "
            "The exercise should feel fresh, not like a rephrasing."
        ),
        "harder": (
            "Generate a HARDER version of this exercise. Add constraints, edge cases, "
            "or require more sophisticated patterns. The core topic stays the same "
            "but the implementation demands more engineering skill."
        ),
    }

    system = (
        "You are a senior AI engineer creating practice exercises for a full-stack engineer "
        "learning AI agent patterns. Generate a high-quality exercise variation.\n\n"
        f"{type_instructions.get(variation_type, type_instructions['scenario'])}\n\n"
        "Respond with valid JSON matching this schema:\n"
        '{"title": "short descriptive title", '
        '"prompt_md": "200+ word problem statement in markdown", '
        '"starter_code": "Python starter with TODOs and type hints", '
        '"solution_code": "complete working Python solution", '
        '"explanation_md": "300+ word explanation with key decisions"}\n\n'
        "The exercise must feel like real engineering work, not a toy problem."
    )

    user = (
        f"## Seed Exercise: {seed_exercise.get('title', '')}\n"
        f"Category: {seed_exercise.get('category', '')}\n"
        f"Difficulty: {seed_exercise.get('difficulty', '')}\n\n"
        f"### Problem\n{seed_exercise.get('prompt_md', '')}\n\n"
        f"### Starter Code\n```python\n{seed_exercise.get('starter_code', '')}\n```\n\n"
        f"### Solution\n```python\n{seed_exercise.get('solution_code', '')}\n```\n\n"
        f"### Explanation\n{seed_exercise.get('explanation_md', '')}"
    )

    return {"system": system, "user": user}

def _parse_variation_response(self, raw: str) -> Optional[Dict[str, Any]]:
    """Parse Claude's JSON response into a variation dict. Returns None on failure."""
    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1])
        data = json.loads(cleaned)
        required = ["title", "prompt_md", "starter_code", "solution_code", "explanation_md"]
        if not all(k in data and data[k] for k in required):
            return None
        return {k: data[k] for k in required}
    except (json.JSONDecodeError, ValueError):
        return None

def generate_exercise_variation(
    self,
    seed_exercise: Dict[str, Any],
    variation_type: str = "scenario",
) -> Optional[Dict[str, Any]]:
    """Generate an exercise variation using Claude. Returns variation dict or None."""
    prompt = self._build_variation_prompt(seed_exercise, variation_type)
    start = time.time()

    try:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            system=prompt["system"],
            messages=[{"role": "user", "content": prompt["user"]}],
        )
    except (anthropic.APITimeoutError, anthropic.APIConnectionError):
        return None

    latency_ms = int((time.time() - start) * 1000)
    raw_text = response.content[0].text
    parsed = self._parse_variation_response(raw_text)

    if parsed:
        parsed["_meta"] = {
            "model": self.model,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "latency_ms": latency_ms,
            "prompt_template": prompt["system"],
        }

    return parsed
```

Also add `from typing import Optional` to the imports if not already present (check first).

Remove the old stub:
```python
def generate_exercise_variation(self, seed_exercise: Dict) -> Dict:
    """[Future] Generate a new exercise variation from a seed exercise."""
    raise NotImplementedError("Exercise variation generation coming in next iteration")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd D:/AIEngineerPortal/backend && python -m pytest tests/test_exercise_variations.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ai_service.py backend/tests/test_exercise_variations.py
git commit -m "feat: implement generate_exercise_variation() with prompt templates and parsing"
```

---

### Task 4: Create variation endpoints and register router

**Files:**
- Create: `backend/app/api/v1/routes/exercise_variations.py`
- Modify: `backend/app/api/v1/api.py`
- Modify: `backend/app/api/v1/routes/ai_feedback.py`

- [ ] **Step 1: Create the variation endpoints**

Create `backend/app/api/v1/routes/exercise_variations.py`:

```python
"""Exercise variation generation and pinning endpoints."""
import uuid
import re
from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select, func
from sqlalchemy.orm import Session

import redis as redis_lib

from app.db.session import get_db
from app.models.entities import AIFeedback, Exercise, User
from app.schemas.portal import PinVariationRequest, PinVariationResponse
from app.services.ai_service import AIService
from app.core.config import get_settings

router = APIRouter(prefix="/exercises", tags=["exercise-variations"])


def _get_redis() -> Optional[redis_lib.Redis]:
    try:
        settings = get_settings()
        return redis_lib.from_url(settings.redis_url)
    except Exception:
        return None


def _check_rate_limit(r: Optional[redis_lib.Redis], user_id: int) -> bool:
    if r is None:
        return True
    key = f"ai_variation_rate:{user_id}:{datetime.utcnow().strftime('%Y%m%d%H%M')}"
    count = r.incr(key)
    if count == 1:
        r.expire(key, 120)
    return count <= 3  # Max 3 variations per minute


def _get_user_id(db: Session) -> int:
    return db.scalar(select(User.id).limit(1)) or 1


def _slugify(title: str) -> str:
    """Convert title to slug with 4-char hex suffix for uniqueness."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:190]
    suffix = uuid.uuid4().hex[:4]
    return f"{slug}-{suffix}"


@router.post("/{exercise_id}/variation")
def generate_variation(
    exercise_id: int,
    variation_type: str = Query(default="scenario", pattern="^(scenario|concept|harder)$"),
    db: Session = Depends(get_db),
):
    """Generate an ephemeral exercise variation from a seed exercise."""
    settings = get_settings()
    svc = AIService()

    if not svc.is_available:
        raise HTTPException(503, "AI is not available — no API key configured")

    user_id = _get_user_id(db)

    # Check per-minute rate limit via Redis
    r = _get_redis()
    if not _check_rate_limit(r, user_id):
        raise HTTPException(429, "Too many requests — try again in a minute")

    # Check daily token budget
    today_start = datetime.combine(date.today(), datetime.min.time())
    used_today = db.scalar(
        select(
            func.coalesce(
                func.sum(AIFeedback.input_tokens + AIFeedback.output_tokens), 0
            )
        ).where(AIFeedback.created_at >= today_start)
    ) or 0
    if used_today >= settings.ai_daily_token_budget:
        raise HTTPException(429, "Daily AI limit reached, try again tomorrow")

    # Fetch seed exercise
    exercise = db.get(Exercise, exercise_id)
    if not exercise:
        raise HTTPException(404, "Exercise not found")

    seed = {
        "id": exercise.id,
        "title": exercise.title,
        "category": exercise.category,
        "difficulty": exercise.difficulty,
        "prompt_md": exercise.prompt_md,
        "starter_code": exercise.starter_code,
        "solution_code": exercise.solution_code,
        "explanation_md": exercise.explanation_md,
    }

    result = svc.generate_exercise_variation(seed, variation_type)
    if result is None:
        raise HTTPException(502, "Failed to generate variation — try again")

    user_id = _get_user_id(db)
    meta = result.pop("_meta", {})

    # Track cost in ai_feedback
    feedback = AIFeedback(
        user_id=user_id,
        feature="variation",
        reference_id=exercise_id,
        user_input_hash=f"variation-{variation_type}-{exercise_id}-{uuid.uuid4().hex[:8]}",
        prompt_template=meta.get("prompt_template"),
        response_json=result,
        model=meta.get("model"),
        input_tokens=meta.get("input_tokens"),
        output_tokens=meta.get("output_tokens"),
        latency_ms=meta.get("latency_ms"),
    )
    db.add(feedback)
    db.commit()

    return JSONResponse({
        **result,
        "variation_type": variation_type,
        "parent_exercise_id": exercise.id,
        "parent_title": exercise.title,
    })


@router.post("/{exercise_id}/variation/pin")
def pin_variation(
    exercise_id: int,
    payload: PinVariationRequest,
    db: Session = Depends(get_db),
):
    """Pin a generated variation to the exercise library."""
    # Validate parent exists
    parent = db.get(Exercise, exercise_id)
    if not parent:
        raise HTTPException(404, "Parent exercise not found")

    # Input validation
    if not payload.title.strip():
        raise HTTPException(400, "Title cannot be empty")
    if not payload.prompt_md.strip():
        raise HTTPException(400, "Prompt cannot be empty")
    if len(payload.prompt_md) > 10_000:
        raise HTTPException(400, "Prompt too long (max 10,000 chars)")
    if len(payload.starter_code) > 5_000:
        raise HTTPException(400, "Starter code too long (max 5,000 chars)")
    if len(payload.solution_code) > 10_000:
        raise HTTPException(400, "Solution too long (max 10,000 chars)")
    if len(payload.explanation_md) > 10_000:
        raise HTTPException(400, "Explanation too long (max 10,000 chars)")
    if payload.variation_type not in ("scenario", "concept", "harder"):
        raise HTTPException(400, "Invalid variation type")

    slug = _slugify(payload.title)

    new_exercise = Exercise(
        title=payload.title,
        slug=slug,
        category=parent.category,
        difficulty=parent.difficulty,
        prompt_md=payload.prompt_md,
        starter_code=payload.starter_code,
        solution_code=payload.solution_code,
        explanation_md=payload.explanation_md,
        tags_json=(parent.tags_json or []) + ["generated", payload.variation_type],
        is_generated=True,
        parent_exercise_id=parent.id,
    )
    db.add(new_exercise)
    db.commit()
    db.refresh(new_exercise)

    return PinVariationResponse(
        id=new_exercise.id,
        slug=new_exercise.slug,
        title=new_exercise.title,
    )
```

- [ ] **Step 2: Register the router in api.py**

In `backend/app/api/v1/api.py`, add:

```python
from app.api.v1.routes import exercise_variations
api_router.include_router(exercise_variations.router)
```

- [ ] **Step 3: Update ai_feedback.py to accept reference_solution**

In `backend/app/api/v1/routes/ai_feedback.py`, find the line that builds `exercise_dict` (around line 100) and update it to use the optional `reference_solution` override:

```python
exercise_dict = {
    "id": exercise.id,
    "title": exercise.title,
    "prompt_md": exercise.prompt_md,
    "solution_code": payload.reference_solution or exercise.solution_code,
    "explanation_md": exercise.explanation_md,
}
```

This allows the frontend to pass the variation's solution when grading an unpinned variation.

- [ ] **Step 4: Verify routes are registered**

Run: `cd D:/AIEngineerPortal/backend && python -c "from app.api.v1.api import api_router; routes = [r.path for r in api_router.routes]; print([r for r in routes if 'variation' in r])" 2>/dev/null || echo "Import check skipped (needs DB)"`

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/routes/exercise_variations.py backend/app/api/v1/api.py backend/app/api/v1/routes/ai_feedback.py
git commit -m "feat: add variation generation and pinning endpoints"
```

---

## Chunk 2: Frontend — Variation UI

### Task 5: Add variation types and API methods

**Files:**
- Modify: `frontend/src/lib/types/portal.ts`
- Modify: `frontend/src/lib/api/portal.ts`

- [ ] **Step 1: Add variation types to portal.ts**

In `frontend/src/lib/types/portal.ts`, add:

```typescript
export type VariationType = "scenario" | "concept" | "harder";

export interface ExerciseVariation {
  title: string;
  prompt_md: string;
  starter_code: string;
  solution_code: string;
  explanation_md: string;
  variation_type: VariationType;
  parent_exercise_id: number;
  parent_title: string;
}

export interface PinnedExercise {
  id: number;
  slug: string;
  title: string;
}
```

- [ ] **Step 2: Add variation API methods to portal.ts**

In `frontend/src/lib/api/portal.ts`, add to the `portalApi` object:

```typescript
async generateVariation(exerciseId: number, variationType: VariationType = "scenario"): Promise<ExerciseVariation> {
  const res = await fetch(
    `${API_BASE}/exercises/${exerciseId}/variation?variation_type=${variationType}`,
    { method: "POST" }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Variation generation failed" }));
    throw new Error(err.detail || `Generation failed (${res.status})`);
  }
  return res.json();
},

async pinVariation(exerciseId: number, variation: ExerciseVariation): Promise<PinnedExercise> {
  const res = await fetch(
    `${API_BASE}/exercises/${exerciseId}/variation/pin`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: variation.title,
        prompt_md: variation.prompt_md,
        starter_code: variation.starter_code,
        solution_code: variation.solution_code,
        explanation_md: variation.explanation_md,
        variation_type: variation.variation_type,
      }),
    }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Pin failed" }));
    throw new Error(err.detail || `Pin failed (${res.status})`);
  }
  return res.json();
},
```

Import `VariationType`, `ExerciseVariation`, and `PinnedExercise` from the types file.

Also update the existing `submitForAIFeedback` method to accept an optional `referenceSolution` parameter:

```typescript
async submitForAIFeedback(exerciseId: number, code: string, referenceSolution?: string): Promise<AIFeedbackResponse> {
  const body: Record<string, string> = { code };
  if (referenceSolution) {
    body.reference_solution = referenceSolution;
  }
  const res = await fetch(
    `${API_BASE}/exercises/${exerciseId}/ai-feedback`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "AI feedback unavailable" }));
    throw new Error(err.detail || `AI feedback failed (${res.status})`);
  }
  return res.json();
},
```

This replaces the current `submitForAIFeedback` method. The new optional third parameter enables grading unpinned variations against their generated solution.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/types/portal.ts frontend/src/lib/api/portal.ts
git commit -m "feat: add variation types and API client methods"
```

---

### Task 6: Create ExerciseVariationPanel component

**Files:**
- Create: `frontend/src/components/forms/exercise-variation-panel.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/forms/exercise-variation-panel.tsx` with a `"use client"` directive. The component must:

**Props:**
```typescript
interface Props {
  variation: ExerciseVariation;
  exerciseId: number;
  onDiscard: () => void;
  onPinned: (pinned: PinnedExercise) => void;
}
```

**Layout:**
- Distinct panel with a colored left border (ember) to visually distinguish from the seed exercise
- Header: variation title + variation type badge (scenario/concept/harder)
- Generated prompt_md displayed as text
- Code editor (textarea) pre-filled with `variation.starter_code`
- "Get AI Feedback" button — calls `portalApi.submitForAIFeedback(exerciseId, code)` but passes `reference_solution: variation.solution_code` in the request. Display feedback using `AIFeedbackDisplay`.
- Two action buttons at the bottom:
  - "Pin to Library" (ember bg) — calls `portalApi.pinVariation()`, then calls `onPinned` with the result
  - "Discard" (text button) — calls `onDiscard`
- After pinning, show a success message with link to the new exercise page

**Styling:** Use the portal's color palette (ink, cream, ember, sand, pine, mint). The panel should feel like a "draft" — distinct from committed content.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/forms/exercise-variation-panel.tsx
git commit -m "feat: create ExerciseVariationPanel component with AI grading support"
```

---

### Task 7: Wire variation generation into exercise detail page

**Files:**
- Modify: `frontend/src/app/practice/python/[exerciseId]/page.tsx`

- [ ] **Step 1: Read the current exercise detail page**

Read `frontend/src/app/practice/python/[exerciseId]/page.tsx` to understand its current structure.

- [ ] **Step 2: Add variation generation section**

The page needs a new client component section (or convert relevant parts to client components). Add below the existing `ExerciseAttemptForm`:

1. **"Generate Variation" section** with:
   - A select dropdown for variation type: Scenario (default) / Different Concept / Harder
   - A "Generate Variation" button (ember bg)
   - Loading state: spinner with "Generating a new variation..."
   - Error state: error message panel

2. When a variation is generated, render `ExerciseVariationPanel` passing the variation data.

3. When discarded, clear the variation state.

4. When pinned, show a success message with a link to the new exercise, or redirect.

**Implementation note:** The page is currently an async server component. The variation section needs client interactivity. Create a small client wrapper component (e.g., `VariationSection`) that handles the state and renders inside the server page.

- [ ] **Step 3: Verify frontend builds**

Run: `cd D:/AIEngineerPortal/frontend && npx tsc --noEmit`
Expected: No TypeScript errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/practice/python/\[exerciseId\]/page.tsx
git commit -m "feat: add variation generation UI to exercise detail page"
```

---

### Task 8: Add "Generated" badge to practice list page

**Files:**
- Modify: `frontend/src/app/practice/python/page.tsx`

- [ ] **Step 1: Read the current practice list page**

Read `frontend/src/app/practice/python/page.tsx` to see how exercises are rendered.

- [ ] **Step 2: Add "Generated" badge for pinned variations**

In the exercise card rendering, check if the exercise has `is_generated === true`. If so, show a small badge:

```tsx
{exercise.is_generated && (
  <span className="text-xs bg-ember/10 text-ember px-2 py-0.5 rounded-full">
    Generated
  </span>
)}
```

Also add `is_generated?: boolean` and `parent_exercise_id?: number` to the Exercise type in `frontend/src/lib/types/portal.ts` if not already present.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/practice/python/page.tsx frontend/src/lib/types/portal.ts
git commit -m "feat: add Generated badge to practice list for AI-created exercises"
```

---

## Chunk 3: Deploy

### Task 9: Apply DB migration on VPS, push, and deploy

- [ ] **Step 1: Apply column patches on VPS**

```bash
ssh root@146.190.124.162 "cd /opt/ai-engineer-portal && docker compose -f infra/docker-compose.prod.yml --env-file infra/.env.production exec -T postgres psql -U portal -d ai_engineer_portal -c \"
ALTER TABLE exercises ADD COLUMN IF NOT EXISTS is_generated BOOLEAN DEFAULT FALSE;
ALTER TABLE exercises ADD COLUMN IF NOT EXISTS parent_exercise_id INTEGER REFERENCES exercises(id);
\""
```

- [ ] **Step 2: Push to main**

```bash
git push origin main
```

- [ ] **Step 3: Tag and deploy**

```bash
git tag v0.7.0
git push origin v0.7.0
```

- [ ] **Step 4: Wait for deploy and verify**

Wait for GitHub Actions to complete, then verify:
```bash
ssh root@146.190.124.162 "cd /opt/ai-engineer-portal && docker compose -f infra/docker-compose.prod.yml --env-file infra/.env.production ps --format 'table {{.Name}}\t{{.Status}}'"
```
Expected: All containers Up, backend not restarting.

### Task 10: End-to-end verification

- [ ] **Step 1: Open portal.leipan.cc → Practice → pick an agent exercise**
- [ ] **Step 2: Select "Scenario" variation type and click "Generate Variation"**
- [ ] **Step 3: Verify variation appears in a distinct panel with title, prompt, starter code**
- [ ] **Step 4: Write code in the variation's editor, click "Get AI Feedback"**
- [ ] **Step 5: Verify AI feedback grades against the variation's solution (not the parent's)**
- [ ] **Step 6: Click "Pin to Library" and verify success**
- [ ] **Step 7: Navigate to Practice list and verify the pinned exercise shows "Generated" badge**
- [ ] **Step 8: Open the pinned exercise and verify it works like any other exercise**
- [ ] **Step 9: Test "Discard" flow — generate another variation and discard it**
- [ ] **Step 10: Test "Harder" variation type — verify increased complexity**

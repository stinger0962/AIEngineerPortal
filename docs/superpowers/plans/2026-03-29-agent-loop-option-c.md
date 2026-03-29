# Agent-Powered Exercise Variations Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evolve exercise variation generation from direct Claude API calls to an agent loop with tools that query learner mastery, exercise history, and feedback before generating personalized variations.

**Architecture:** New `AgentLoop` class uses Anthropic Messages API with `tools` parameter. Four tool functions query existing DB models. `generate_exercise_variation()` tries the agent first, falls back to direct generation on failure. No frontend changes — same endpoint contract.

**Tech Stack:** Anthropic Python SDK (already installed), SQLAlchemy (existing), FastAPI (existing)

---

## File Structure

| File | Responsibility | Status |
|------|---------------|--------|
| `backend/app/services/agent_tools.py` | 4 tool functions + JSON schemas for Anthropic tool_use | **New** |
| `backend/app/services/agent_loop.py` | AgentLoop class — multi-round tool_use orchestration | **New** |
| `backend/app/services/ai_service.py` | Delegate to AgentLoop, rename direct method as fallback | **Modify** |
| `backend/app/api/v1/routes/exercise_variations.py` | Pass `db` and `user_id` to AIService | **Modify** |
| `backend/tests/test_agent_tools.py` | Unit tests for tool functions | **New** |
| `backend/tests/test_agent_loop.py` | Unit tests for agent loop with mocked Claude client | **New** |

---

## Chunk 1: Agent Tools

### Task 1: Create agent tool functions

**Files:**
- Create: `backend/app/services/agent_tools.py`
- Test: `backend/tests/test_agent_tools.py`

- [ ] **Step 1: Write test for check_mastery tool**

```python
# backend/tests/test_agent_tools.py
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from app.services.agent_tools import check_mastery, get_exercise_history, get_recent_feedback, read_lesson_summary, TOOL_SCHEMAS


def test_check_mastery_returns_path_data(db_session):
    """check_mastery should return mastery data for each learning path."""
    result = check_mastery(db_session, user_id=1)
    assert "paths" in result
    assert isinstance(result["paths"], list)
    # Each path should have name, mastery_pct, practice_reps, weakest_area
    if result["paths"]:
        path = result["paths"][0]
        assert "name" in path
        assert "mastery_pct" in path
        assert "practice_reps" in path


def test_check_mastery_empty_user(db_session):
    """check_mastery with nonexistent user should return empty paths."""
    result = check_mastery(db_session, user_id=99999)
    assert result == {"paths": []}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd D:/AIEngineerPortal/backend && python -m pytest tests/test_agent_tools.py::test_check_mastery_returns_path_data -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.agent_tools'`

- [ ] **Step 3: Implement all 4 tool functions + JSON schemas**

```python
# backend/app/services/agent_tools.py
"""Agent tools for querying learner state. Used by AgentLoop with Anthropic tool_use."""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select, desc
from sqlalchemy.orm import Session

from app.models.entities import (
    Exercise,
    Lesson,
    LearningPath,
    User,
    UserExerciseAttempt,
    AIFeedback,
)
from app.services.adaptive_service import build_mastery_profile


# ── Tool JSON schemas (Anthropic tool_use format) ──────────────────────

TOOL_SCHEMAS = [
    {
        "name": "check_mastery",
        "description": (
            "Get the learner's mastery profile across all learning paths. "
            "Returns mastery percentage, practice reps, and weakest area per path. "
            "Call this FIRST to understand what the learner needs to work on."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_exercise_history",
        "description": (
            "Get the learner's recent exercise attempts with scores and categories. "
            "Use this to avoid generating exercises similar to ones recently practiced."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max exercises to return (default 10)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_recent_feedback",
        "description": (
            "Get recent AI feedback given to the learner on exercises. "
            "Shows strengths and recurring issues to help target weaknesses."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max feedback entries to return (default 5)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "read_lesson_summary",
        "description": (
            "Read a lesson's title, path, and summary to understand what was taught. "
            "Use when you need to reference specific lesson content for context."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lesson_slug": {
                    "type": "string",
                    "description": "The slug identifier for the lesson",
                },
            },
            "required": ["lesson_slug"],
        },
    },
]


# ── Tool implementations ───────────────────────────────────────────────

def check_mastery(db: Session, user_id: int) -> dict[str, Any]:
    """Return mastery profile across all learning paths."""
    user = db.get(User, user_id)
    if not user:
        return {"paths": []}

    profile = build_mastery_profile(db)
    return {
        "paths": [
            {
                "name": p.get("path_name", ""),
                "slug": p.get("path_slug", ""),
                "mastery_pct": round(p.get("mastery_score", 0), 1),
                "practice_reps": p.get("practice_reps", 0),
                "avg_score": round(p.get("practice_avg_score", 0), 1),
                "weakest_area": p.get("weakest_signal", ""),
            }
            for p in profile
        ]
    }


def get_exercise_history(db: Session, user_id: int, limit: int = 10) -> dict[str, Any]:
    """Return recent exercise attempts with scores."""
    rows = db.execute(
        select(
            Exercise.title,
            Exercise.category,
            UserExerciseAttempt.score,
            UserExerciseAttempt.attempted_at,
        )
        .join(Exercise, UserExerciseAttempt.exercise_id == Exercise.id)
        .where(UserExerciseAttempt.user_id == user_id)
        .order_by(desc(UserExerciseAttempt.attempted_at))
        .limit(min(limit, 20))
    ).all()

    return {
        "exercises": [
            {
                "title": title,
                "category": category,
                "score": score,
                "attempted_at": attempted_at.isoformat() if attempted_at else None,
            }
            for title, category, score, attempted_at in rows
        ]
    }


def get_recent_feedback(db: Session, user_id: int, limit: int = 5) -> dict[str, Any]:
    """Return recent AI feedback entries showing strengths and issues."""
    rows = db.execute(
        select(AIFeedback)
        .where(AIFeedback.user_id == user_id, AIFeedback.feature == "exercise_grade")
        .order_by(desc(AIFeedback.created_at))
        .limit(min(limit, 10))
    ).scalars().all()

    feedback_list = []
    for fb in rows:
        resp = fb.response_json or {}
        exercise = db.get(Exercise, fb.reference_id)
        feedback_list.append({
            "exercise_title": exercise.title if exercise else "Unknown",
            "strengths": resp.get("strengths", []),
            "issues": resp.get("issues", []),
            "score": resp.get("score"),
        })

    return {"feedback": feedback_list}


def read_lesson_summary(db: Session, user_id: int, lesson_slug: str) -> dict[str, Any]:
    """Return lesson title, path, and first 500 chars of content."""
    lesson = db.scalar(select(Lesson).where(Lesson.slug == lesson_slug))
    if not lesson:
        return {"error": f"Lesson '{lesson_slug}' not found"}

    path = db.get(LearningPath, lesson.path_id)
    content = lesson.content_md or ""

    return {
        "title": lesson.title,
        "path_name": path.title if path else "Unknown",
        "summary": content[:500] + ("..." if len(content) > 500 else ""),
    }


# ── Tool dispatcher ────────────────────────────────────────────────────

TOOL_FUNCTIONS = {
    "check_mastery": check_mastery,
    "get_exercise_history": get_exercise_history,
    "get_recent_feedback": get_recent_feedback,
    "read_lesson_summary": read_lesson_summary,
}


def execute_tool(tool_name: str, tool_input: dict, db: Session, user_id: int) -> dict[str, Any]:
    """Execute a tool by name. Returns result dict or error dict."""
    fn = TOOL_FUNCTIONS.get(tool_name)
    if not fn:
        return {"error": f"Unknown tool: {tool_name}"}

    try:
        # read_lesson_summary needs lesson_slug, others just need db + user_id
        if tool_name == "read_lesson_summary":
            return fn(db, user_id, lesson_slug=tool_input.get("lesson_slug", ""))
        elif tool_name in ("get_exercise_history", "get_recent_feedback"):
            return fn(db, user_id, limit=tool_input.get("limit", 10 if tool_name == "get_exercise_history" else 5))
        else:
            return fn(db, user_id)
    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}"}
```

- [ ] **Step 4: Write additional tests**

```python
# Append to backend/tests/test_agent_tools.py

def test_get_exercise_history_empty(db_session):
    result = get_exercise_history(db_session, user_id=1, limit=10)
    assert "exercises" in result
    assert isinstance(result["exercises"], list)


def test_get_recent_feedback_empty(db_session):
    result = get_recent_feedback(db_session, user_id=1, limit=5)
    assert "feedback" in result
    assert isinstance(result["feedback"], list)


def test_read_lesson_summary_not_found(db_session):
    result = read_lesson_summary(db_session, user_id=1, lesson_slug="nonexistent")
    assert "error" in result


def test_tool_schemas_valid():
    """All tool schemas should have required fields."""
    for schema in TOOL_SCHEMAS:
        assert "name" in schema
        assert "description" in schema
        assert "input_schema" in schema
        assert schema["input_schema"]["type"] == "object"


def test_execute_tool_unknown():
    """Unknown tool should return error."""
    from app.services.agent_tools import execute_tool
    result = execute_tool("nonexistent_tool", {}, MagicMock(), 1)
    assert "error" in result
```

- [ ] **Step 5: Run tests**

Run: `cd D:/AIEngineerPortal/backend && python -m pytest tests/test_agent_tools.py -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/agent_tools.py backend/tests/test_agent_tools.py
git commit -m "feat: add agent tools for querying learner mastery, history, and feedback"
```

---

### Task 2: Create AgentLoop class

**Files:**
- Create: `backend/app/services/agent_loop.py`
- Test: `backend/tests/test_agent_loop.py`

- [ ] **Step 1: Write test for agent loop**

```python
# backend/tests/test_agent_loop.py
import json
import pytest
from unittest.mock import MagicMock, patch

from app.services.agent_loop import AgentLoop


def _mock_tool_use_response(tool_name, tool_input):
    """Create a mock Claude response that requests a tool call."""
    mock_resp = MagicMock()
    mock_resp.stop_reason = "tool_use"
    block = MagicMock()
    block.type = "tool_use"
    block.id = "call_123"
    block.name = tool_name
    block.input = tool_input
    mock_resp.content = [block]
    mock_resp.usage = MagicMock(input_tokens=500, output_tokens=100)
    return mock_resp


def _mock_text_response(text):
    """Create a mock Claude response with final text output."""
    mock_resp = MagicMock()
    mock_resp.stop_reason = "end_turn"
    block = MagicMock()
    block.type = "text"
    block.text = text
    mock_resp.content = [block]
    mock_resp.usage = MagicMock(input_tokens=800, output_tokens=400)
    return mock_resp


def test_agent_loop_calls_tools_then_generates():
    """Agent should call tools, gather context, then generate final output."""
    mock_client = MagicMock()
    mock_db = MagicMock()

    # Round 1: Claude requests check_mastery
    # Round 2: Claude generates final answer
    variation_json = json.dumps({
        "title": "Test Variation",
        "prompt_md": "Build something",
        "starter_code": "# TODO",
        "solution_code": "# done",
        "explanation_md": "This teaches X",
    })
    mock_client.messages.create.side_effect = [
        _mock_tool_use_response("check_mastery", {}),
        _mock_text_response(variation_json),
    ]

    agent = AgentLoop(db=mock_db, user_id=1, client=mock_client, model="test-model")

    with patch("app.services.agent_loop.execute_tool", return_value={"paths": []}):
        result = agent.run(
            task="generate_variation",
            context={"seed_exercise": {"title": "test"}, "variation_type": "scenario"},
        )

    assert result is not None
    assert result["title"] == "Test Variation"
    assert "_meta" in result
    assert result["_meta"]["rounds"] == 2
    assert len(result["_meta"]["tool_calls"]) == 1


def test_agent_loop_max_rounds():
    """Agent should stop after max_rounds even if still calling tools."""
    mock_client = MagicMock()
    mock_db = MagicMock()

    # All rounds return tool_use — agent never generates
    mock_client.messages.create.return_value = _mock_tool_use_response("check_mastery", {})

    agent = AgentLoop(db=mock_db, user_id=1, client=mock_client, model="test-model")

    with patch("app.services.agent_loop.execute_tool", return_value={"paths": []}):
        result = agent.run(
            task="generate_variation",
            context={"seed_exercise": {"title": "test"}, "variation_type": "scenario"},
            max_rounds=2,
        )

    # Should return None since agent never produced final output
    assert result is None


def test_agent_loop_no_tool_calls():
    """If Claude generates immediately without tools, still works."""
    mock_client = MagicMock()
    mock_db = MagicMock()

    variation_json = json.dumps({
        "title": "Direct Variation",
        "prompt_md": "Build something",
        "starter_code": "# TODO",
        "solution_code": "# done",
        "explanation_md": "Explanation",
    })
    mock_client.messages.create.return_value = _mock_text_response(variation_json)

    agent = AgentLoop(db=mock_db, user_id=1, client=mock_client, model="test-model")

    result = agent.run(
        task="generate_variation",
        context={"seed_exercise": {"title": "test"}, "variation_type": "scenario"},
    )

    assert result is not None
    assert result["title"] == "Direct Variation"
    assert result["_meta"]["rounds"] == 1
    assert result["_meta"]["tool_calls"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd D:/AIEngineerPortal/backend && python -m pytest tests/test_agent_loop.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement AgentLoop**

```python
# backend/app/services/agent_loop.py
"""Agent loop for multi-round tool_use with Claude. Used by AIService for personalized generation."""
from __future__ import annotations

import json
import time
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.services.agent_tools import TOOL_SCHEMAS, execute_tool


class AgentLoop:
    """Orchestrates multi-round Claude interactions with tool_use for personalized content generation."""

    def __init__(self, db: Session, user_id: int, client: Any, model: str):
        self.db = db
        self.user_id = user_id
        self.client = client
        self.model = model

    def run(
        self,
        task: str,
        context: dict[str, Any],
        max_rounds: int = 3,
    ) -> Optional[dict[str, Any]]:
        """Run the agent loop. Returns parsed result dict with _meta, or None on failure."""
        system_prompt = self._build_system_prompt(task, context)
        user_message = self._build_user_message(task, context)

        messages = [{"role": "user", "content": user_message}]
        tool_calls_log: list[dict] = []
        total_input_tokens = 0
        total_output_tokens = 0
        start_time = time.time()

        for round_num in range(1, max_rounds + 1):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4000,
                    system=system_prompt,
                    messages=messages,
                    tools=TOOL_SCHEMAS,
                    timeout=30.0,
                )
            except Exception:
                return None

            total_input_tokens += response.usage.input_tokens
            total_output_tokens += response.usage.output_tokens

            # Check if Claude wants to use tools
            if response.stop_reason == "tool_use":
                # Process all tool_use blocks in the response
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        tool_start = time.time()
                        tool_output = execute_tool(
                            block.name, block.input, self.db, self.user_id
                        )
                        tool_latency = int((time.time() - tool_start) * 1000)

                        tool_calls_log.append({
                            "tool": block.name,
                            "input": block.input,
                            "output": tool_output,
                            "latency_ms": tool_latency,
                        })

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(tool_output),
                        })

                # Add assistant response + tool results to conversation
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
                continue

            # Claude generated final text response
            for block in response.content:
                if block.type == "text":
                    total_latency = int((time.time() - start_time) * 1000)
                    parsed = self._parse_output(block.text)
                    if parsed:
                        parsed["_meta"] = {
                            "model": self.model,
                            "input_tokens": total_input_tokens,
                            "output_tokens": total_output_tokens,
                            "latency_ms": total_latency,
                            "rounds": round_num,
                            "tool_calls": tool_calls_log,
                            "total_tokens": total_input_tokens + total_output_tokens,
                            "prompt_template": system_prompt,
                        }
                    return parsed

        # Max rounds exceeded without final output
        return None

    def _build_system_prompt(self, task: str, context: dict) -> str:
        """Build system prompt with agent instructions."""
        variation_type = context.get("variation_type", "scenario")
        seed = context.get("seed_exercise", {})

        return (
            "You are an AI engineering tutor generating a personalized exercise variation.\n\n"
            "## Your tools\n"
            "You have tools to understand this specific learner. Use them to personalize the exercise:\n"
            "1. Call `check_mastery` FIRST to understand overall gaps\n"
            "2. Optionally call `get_exercise_history` to see what's been practiced recently\n"
            "3. Optionally call `get_recent_feedback` to see recurring strengths/weaknesses\n"
            "4. Call `read_lesson_summary` only if you need specific lesson context\n\n"
            "After gathering context (1-2 tool calls is usually enough), generate the variation.\n\n"
            "## Personalization rules\n"
            "- Target the learner's WEAKEST area — don't generate more of what they're already good at\n"
            "- Avoid topics from their last 5 exercises (use history to check)\n"
            "- If they have recurring issues in feedback, design the exercise to practice fixing those\n"
            "- Match difficulty to their mastery level — don't overwhelm beginners or bore advanced learners\n\n"
            "## Learner profile\n"
            "Senior full-stack engineer transitioning to AI engineering (application-level, not research).\n"
            "Focus: harnessing LLMs and agents, making them efficient, building production systems.\n\n"
            f"## Variation type: {variation_type}\n"
            f"## Seed exercise: {seed.get('title', 'Unknown')}\n"
            f"## Seed category: {seed.get('category', 'Unknown')}\n\n"
            "## Output format\n"
            "After gathering learner context, respond with ONLY valid JSON:\n"
            "{\n"
            '  "title": "Concise, specific title",\n'
            '  "prompt_md": "200-400 word problem statement in markdown",\n'
            '  "starter_code": "Python with imports, types, TODOs. 30-80 lines.",\n'
            '  "solution_code": "Complete, production-quality Python. 50-150 lines.",\n'
            '  "explanation_md": "300-600 word teaching explanation in markdown"\n'
            "}"
        )

    def _build_user_message(self, task: str, context: dict) -> str:
        """Build the initial user message with seed exercise."""
        seed = context.get("seed_exercise", {})
        variation_type = context.get("variation_type", "scenario")

        return (
            f"Generate a '{variation_type}' variation of this exercise.\n\n"
            f"**Seed Exercise:** {seed.get('title', '')}\n"
            f"**Category:** {seed.get('category', '')}\n"
            f"**Difficulty:** {seed.get('difficulty', '')}\n\n"
            f"### Problem\n{seed.get('prompt_md', '')}\n\n"
            f"### Starter Code\n```python\n{seed.get('starter_code', '')}\n```\n\n"
            f"### Solution\n```python\n{seed.get('solution_code', '')}\n```\n\n"
            "First, use your tools to understand what this learner needs, "
            "then generate a personalized variation."
        )

    def _parse_output(self, raw: str) -> Optional[dict[str, Any]]:
        """Parse Claude's JSON output into variation dict."""
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
```

- [ ] **Step 4: Run tests**

Run: `cd D:/AIEngineerPortal/backend && python -m pytest tests/test_agent_loop.py -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/agent_loop.py backend/tests/test_agent_loop.py
git commit -m "feat: add AgentLoop class for multi-round tool_use orchestration"
```

---

## Chunk 2: Integration and Deploy

### Task 3: Integrate AgentLoop into AIService

**Files:**
- Modify: `backend/app/services/ai_service.py`

- [ ] **Step 1: Rename `generate_exercise_variation` to `_direct_generate_variation`**

In `ai_service.py`, rename the existing method:
```python
def _direct_generate_variation(self, seed_exercise, variation_type="scenario"):
```

- [ ] **Step 2: Create new `generate_exercise_variation` with agent delegation**

Add this method to the AIService class:

```python
def generate_exercise_variation(
    self,
    seed_exercise: Dict[str, Any],
    variation_type: str = "scenario",
    db: Optional[Any] = None,
    user_id: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """Generate a variation, using agent loop if db context available, else direct."""
    if self.is_available and db is not None and user_id is not None:
        try:
            from app.services.agent_loop import AgentLoop
            agent = AgentLoop(db=db, user_id=user_id, client=self.client, model=self.model)
            result = agent.run(
                task="generate_variation",
                context={"seed_exercise": seed_exercise, "variation_type": variation_type},
                max_rounds=3,
            )
            if result:
                return result
        except Exception:
            pass  # fall through to direct generation

    return self._direct_generate_variation(seed_exercise, variation_type)
```

Add `from typing import Optional` if not already imported (it should be).

- [ ] **Step 3: Verify import works**

Run: `cd D:/AIEngineerPortal/backend && python -c "from app.services.ai_service import AIService; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/ai_service.py
git commit -m "feat: delegate variation generation to AgentLoop with direct fallback"
```

---

### Task 4: Pass db and user_id through endpoint

**Files:**
- Modify: `backend/app/api/v1/routes/exercise_variations.py`

- [ ] **Step 1: Update the generate_variation endpoint**

Find the line that calls `svc.generate_exercise_variation(seed, variation_type)` and change it to:

```python
result = svc.generate_exercise_variation(seed, variation_type, db=db, user_id=user_id)
```

The `db` and `user_id` variables are already available in the function scope (db from Depends, user_id from `_get_user_id(db)`).

- [ ] **Step 2: Verify endpoint imports work**

Run: `cd D:/AIEngineerPortal/backend && python -c "from app.api.v1.routes.exercise_variations import router; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/v1/routes/exercise_variations.py
git commit -m "feat: pass db and user_id to AIService for agent-powered variations"
```

---

### Task 5: Push and deploy

- [ ] **Step 1: Run all tests**

Run: `cd D:/AIEngineerPortal/backend && python -m pytest tests/ -v`
Expected: All pass

- [ ] **Step 2: Push to GitHub**

```bash
cd D:/AIEngineerPortal && git push origin main
```

- [ ] **Step 3: Tag and deploy**

```bash
git tag v0.10.0 && git push origin v0.10.0
```

- [ ] **Step 4: SSH deploy if Actions fails**

```bash
ssh root@146.190.124.162 "cd /opt/ai-engineer-portal && git tag -d v0.10.0 2>/dev/null; git fetch --all --tags --prune --force && git checkout v0.10.0 && git reset --hard v0.10.0 && docker compose --env-file infra/.env.production -f infra/docker-compose.prod.yml up -d --build --force-recreate --remove-orphans"
```

- [ ] **Step 5: Verify backend is healthy**

```bash
ssh root@146.190.124.162 "docker compose -f /opt/ai-engineer-portal/infra/docker-compose.prod.yml --env-file /opt/ai-engineer-portal/infra/.env.production ps --format 'table {{.Name}}\t{{.Status}}'"
```
Expected: All containers Up, backend not restarting

- [ ] **Step 6: Commit version bump**

If deploy succeeds, no additional commit needed — the tag is the release marker.

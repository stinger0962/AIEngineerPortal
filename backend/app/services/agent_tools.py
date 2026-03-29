"""agent_tools.py — Tool functions for the adaptive learning agent.

Each tool can be called by the Anthropic tool_use API.  The module exposes:
- TOOL_SCHEMAS   list of 4 Anthropic-compatible tool schema dicts
- execute_tool   dispatcher that routes a tool call to the right function
- Individual tool functions (also importable for unit-testing)
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import AIFeedback, Exercise, Lesson, LearningPath, UserExerciseAttempt
from app.services.adaptive_service import build_mastery_profile

# ---------------------------------------------------------------------------
# Anthropic tool_use JSON schemas
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict] = [
    {
        "name": "check_mastery",
        "description": (
            "Returns the learner's mastery profile across every learning path. "
            "Use this to understand which areas are solid, developing, or fragile "
            "before making a study recommendation."
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
            "Returns the learner's most recent coding exercise attempts with scores. "
            "Useful for spotting practice gaps or recent momentum."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of attempts to return (default 10).",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_recent_feedback",
        "description": (
            "Returns the most recent AI-generated exercise-grade feedback entries. "
            "Each entry contains strengths, issues, and a score so you can spot "
            "recurring weaknesses."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of feedback entries to return (default 5).",
                }
            },
            "required": [],
        },
    },
    {
        "name": "read_lesson_summary",
        "description": (
            "Returns the title and a brief summary of a specific lesson given its slug. "
            "Use this when you want to describe what a lesson covers before recommending it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lesson_slug": {
                    "type": "string",
                    "description": "The URL slug that uniquely identifies the lesson.",
                }
            },
            "required": ["lesson_slug"],
        },
    },
]

# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------


def check_mastery(db: Session, user_id: int) -> dict:
    """Return mastery profile per learning path.

    Delegates entirely to build_mastery_profile which fetches the user
    internally.  The returned dict normalises the adaptive_service output
    into a compact shape the agent can reason over.
    """
    raw: list[dict] = build_mastery_profile(db)
    paths = [
        {
            "name": entry["area_title"],
            "slug": entry["area_slug"],
            "mastery_pct": entry["mastery_score"],
            "weakest_area": entry.get("weakest_signal", ""),
        }
        for entry in raw
    ]
    return {"paths": paths}


def get_exercise_history(db: Session, user_id: int, limit: int = 10) -> dict:
    """Return the learner's most recent exercise attempts."""
    rows = db.execute(
        select(
            Exercise.title,
            Exercise.category,
            UserExerciseAttempt.score,
            UserExerciseAttempt.attempted_at,
        )
        .select_from(UserExerciseAttempt)
        .join(Exercise, Exercise.id == UserExerciseAttempt.exercise_id)
        .where(UserExerciseAttempt.user_id == user_id)
        .order_by(UserExerciseAttempt.attempted_at.desc())
        .limit(limit)
    ).all()

    exercises = [
        {
            "title": title,
            "category": category,
            "score": round(float(score), 1) if score is not None else None,
            "attempted_at": attempted_at.isoformat() if attempted_at else None,
        }
        for title, category, score, attempted_at in rows
    ]
    return {"exercises": exercises}


def get_recent_feedback(db: Session, user_id: int, limit: int = 5) -> dict:
    """Return the most recent exercise-grade AI feedback entries."""
    rows = db.scalars(
        select(AIFeedback)
        .where(
            AIFeedback.user_id == user_id,
            AIFeedback.feature == "exercise_grade",
        )
        .order_by(AIFeedback.created_at.desc())
        .limit(limit)
    ).all()

    feedback_list = []
    for fb in rows:
        payload: dict = fb.response_json or {}
        # Resolve the exercise title via reference_id (exercise attempt id).
        exercise_title = _resolve_exercise_title(db, fb.reference_id)
        feedback_list.append(
            {
                "exercise_title": exercise_title,
                "strengths": payload.get("strengths", []),
                "issues": payload.get("issues", []),
                "score": payload.get("score"),
            }
        )
    return {"feedback": feedback_list}


def read_lesson_summary(db: Session, user_id: int, lesson_slug: str) -> dict:
    """Return title and summary for a lesson identified by slug."""
    lesson: Lesson | None = db.scalar(
        select(Lesson).where(Lesson.slug == lesson_slug)
    )
    if lesson is None:
        return {"error": f"Lesson '{lesson_slug}' not found."}

    path: LearningPath | None = db.scalar(
        select(LearningPath).where(LearningPath.id == lesson.learning_path_id)
    )
    path_name = path.title if path else ""

    # Return first 500 chars of content_md as the summary snippet.
    content_snippet = (lesson.content_md or "")[:500]

    return {
        "title": lesson.title,
        "path_name": path_name,
        "summary": content_snippet or lesson.summary,
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _resolve_exercise_title(db: Session, attempt_id: int) -> str:
    """Look up the exercise title for a given attempt id."""
    row = db.execute(
        select(Exercise.title)
        .select_from(UserExerciseAttempt)
        .join(Exercise, Exercise.id == UserExerciseAttempt.exercise_id)
        .where(UserExerciseAttempt.id == attempt_id)
    ).first()
    return row[0] if row else f"attempt #{attempt_id}"


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_TOOL_MAP = {
    "check_mastery": check_mastery,
    "get_exercise_history": get_exercise_history,
    "get_recent_feedback": get_recent_feedback,
    "read_lesson_summary": read_lesson_summary,
}


def execute_tool(
    tool_name: str,
    tool_input: dict[str, Any],
    db: Session,
    user_id: int,
) -> dict:
    """Dispatch a tool call by name and return its result dict.

    Returns an error dict for unknown tool names or any exception raised
    during execution so the agent can surface the problem gracefully.
    """
    fn = _TOOL_MAP.get(tool_name)
    if fn is None:
        return {"error": f"Unknown tool: '{tool_name}'."}

    try:
        return fn(db=db, user_id=user_id, **tool_input)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Tool '{tool_name}' raised {type(exc).__name__}: {exc}"}

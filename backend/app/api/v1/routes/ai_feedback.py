"""AI-powered exercise feedback endpoint."""
import json
from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select, func
from sqlalchemy.orm import Session

import redis as redis_lib

from app.db.session import get_db
from app.models.entities import (
    AIFeedback, Exercise, User, UserExerciseAttempt,
)
from app.schemas.portal import AIFeedbackRequest
from app.services.ai_service import AIService
from app.core.config import get_settings

router = APIRouter(prefix="/exercises", tags=["ai-feedback"])


def _get_redis() -> Optional[redis_lib.Redis]:
    try:
        settings = get_settings()
        return redis_lib.from_url(settings.redis_url)
    except Exception:
        return None


def _check_rate_limit(r: Optional[redis_lib.Redis], user_id: int) -> bool:
    if r is None:
        return True
    key = f"ai_feedback_rate:{user_id}:{datetime.utcnow().strftime('%Y%m%d%H%M')}"
    count = r.incr(key)
    if count == 1:
        r.expire(key, 120)
    return count <= 5


def _get_user_id(db: Session) -> int:
    return db.scalar(select(User.id).limit(1)) or 1


@router.post("/{exercise_id}/ai-feedback")
def ai_feedback(
    exercise_id: int,
    payload: AIFeedbackRequest,
    db: Session = Depends(get_db),
):
    settings = get_settings()
    svc = AIService()

    if not svc.is_available:
        raise HTTPException(503, "AI feedback is not available — no API key configured")

    user_id = _get_user_id(db)

    r = _get_redis()
    if not _check_rate_limit(r, user_id):
        raise HTTPException(429, "Too many requests — try again in a minute")

    today_start = datetime.combine(date.today(), datetime.min.time())
    used_today = db.scalar(
        select(
            func.coalesce(
                func.sum(AIFeedback.input_tokens + AIFeedback.output_tokens), 0
            )
        ).where(AIFeedback.created_at >= today_start)
    ) or 0
    if used_today >= settings.ai_daily_token_budget:
        raise HTTPException(429, "Daily AI feedback limit reached, try again tomorrow")

    exercise = db.get(Exercise, exercise_id)
    if not exercise:
        raise HTTPException(404, "Exercise not found")

    code = payload.code
    if not code.strip():
        raise HTTPException(400, "Code cannot be empty")

    cache_hash = svc.cache_key(exercise_id, code)
    cached = db.scalar(
        select(AIFeedback).where(
            AIFeedback.user_input_hash == cache_hash,
            AIFeedback.feature == "exercise_grade",
            AIFeedback.user_id == user_id,
        )
    )
    if cached:
        resp = cached.response_json or {}
        return JSONResponse({
            "id": cached.id,
            "feature": cached.feature,
            "reference_id": cached.reference_id,
            "cached": True,
            **resp,
        })

    attempts = db.scalars(
        select(UserExerciseAttempt)
        .where(
            UserExerciseAttempt.exercise_id == exercise_id,
            UserExerciseAttempt.user_id == user_id,
        )
        .order_by(UserExerciseAttempt.attempted_at.desc())
        .limit(5)
    ).all()
    history = [
        {"code": a.submitted_code, "score": a.score}
        for a in attempts
    ]

    exercise_dict = {
        "id": exercise.id,
        "title": exercise.title,
        "prompt_md": exercise.prompt_md,
        "solution_code": payload.reference_solution or exercise.solution_code,
        "explanation_md": exercise.explanation_md,
    }

    result = svc.grade_exercise(code, exercise_dict, history)

    feedback = AIFeedback(
        user_id=user_id,
        feature="exercise_grade",
        reference_id=exercise_id,
        user_input_hash=cache_hash,
        prompt_template=result.get("prompt_template"),
        response_json={
            "strengths": result["strengths"],
            "issues": result["issues"],
            "suggestions": result["suggestions"],
            "example_fixes": result["example_fixes"],
            "score": result["score"],
            "should_retry": result["should_retry"],
        },
        model=result.get("model"),
        input_tokens=result.get("input_tokens"),
        output_tokens=result.get("output_tokens"),
        latency_ms=result.get("latency_ms"),
    )
    db.add(feedback)
    db.flush()

    attempt = UserExerciseAttempt(
        user_id=user_id,
        exercise_id=exercise_id,
        submitted_code=code,
        score=result["score"],
        status="solid" if result["score"] >= 85 else "needs-review" if result["score"] >= 70 else "retry",
        ai_feedback_id=feedback.id,
    )
    db.add(attempt)
    db.commit()

    return JSONResponse({
        "id": feedback.id,
        "feature": feedback.feature,
        "reference_id": feedback.reference_id,
        "cached": False,
        **feedback.response_json,
        "model": feedback.model,
        "input_tokens": feedback.input_tokens,
        "output_tokens": feedback.output_tokens,
        "latency_ms": feedback.latency_ms,
    })

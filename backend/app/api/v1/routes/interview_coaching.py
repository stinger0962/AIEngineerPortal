"""Interview answer coaching endpoints."""
import uuid
from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

import redis as redis_lib

from app.db.session import get_db
from app.models.entities import AIFeedback, InterviewQuestion, User
from app.schemas.portal import CoachingRequest, CoachingResponse
from app.services.ai_service import AIService
from app.core.config import get_settings

router = APIRouter(prefix="/interview", tags=["interview-coaching"])


def _get_redis() -> Optional[redis_lib.Redis]:
    try:
        settings = get_settings()
        return redis_lib.from_url(settings.redis_url)
    except Exception:
        return None


def _check_rate_limit(r: Optional[redis_lib.Redis], user_id: int) -> bool:
    if r is None:
        return True
    key = f"ai_coaching_rate:{user_id}:{datetime.utcnow().strftime('%Y%m%d%H%M')}"
    count = r.incr(key)
    if count == 1:
        r.expire(key, 120)
    return count <= 3


def _get_user_id(db: Session) -> int:
    return db.scalar(select(User.id).limit(1)) or 1


@router.post("/questions/{question_id}/coach", response_model=CoachingResponse)
def coach_interview_answer(
    question_id: int,
    payload: CoachingRequest,
    db: Session = Depends(get_db),
):
    """Submit an interview answer and receive AI coaching feedback."""
    settings = get_settings()
    svc = AIService()

    if not svc.is_available:
        raise HTTPException(503, "AI is not available — no API key configured")

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
        raise HTTPException(429, "Daily AI limit reached, try again tomorrow")

    question = db.get(InterviewQuestion, question_id)
    if not question:
        raise HTTPException(404, "Interview question not found")

    question_context = {
        "question": question.question_text,
        "category": question.category,
        "difficulty": question.difficulty,
        "answer_outline": question.answer_outline_md,
    }

    result = svc.coach_interview_answer(payload.answer, question_context)
    if result is None:
        raise HTTPException(502, "Failed to generate coaching feedback — try again")

    meta = result.pop("_meta", {})

    feedback = AIFeedback(
        user_id=user_id,
        feature="interview_coach",
        reference_id=question_id,
        user_input_hash=f"coach-{question_id}-{uuid.uuid4().hex[:8]}",
        prompt_template=meta.get("prompt_template"),
        response_json={
            "answer": payload.answer,
            "overall_score": result.get("overall_score", 0),
            "strengths": result.get("strengths", []),
            "gaps": result.get("gaps", []),
            "improvements": result.get("improvements", []),
            "example_answer_section": result.get("example_answer_section", ""),
            "ready_for_interview": result.get("ready_for_interview", False),
        },
        model=meta.get("model"),
        input_tokens=meta.get("input_tokens"),
        output_tokens=meta.get("output_tokens"),
        latency_ms=meta.get("latency_ms"),
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    return CoachingResponse(
        id=feedback.id,
        question_id=question_id,
        overall_score=result.get("overall_score", 0),
        strengths=result.get("strengths", []),
        gaps=result.get("gaps", []),
        improvements=result.get("improvements", []),
        example_answer_section=result.get("example_answer_section", ""),
        ready_for_interview=result.get("ready_for_interview", False),
        model=feedback.model,
        input_tokens=feedback.input_tokens,
        output_tokens=feedback.output_tokens,
        latency_ms=feedback.latency_ms,
        created_at=feedback.created_at.isoformat() if feedback.created_at else None,
    )


@router.get("/questions/{question_id}/coaching-history", response_model=List[CoachingResponse])
def list_coaching_history(
    question_id: int,
    db: Session = Depends(get_db),
):
    """Retrieve previous coaching sessions for an interview question."""
    question = db.get(InterviewQuestion, question_id)
    if not question:
        raise HTTPException(404, "Interview question not found")

    rows = db.scalars(
        select(AIFeedback)
        .where(
            AIFeedback.feature == "interview_coach",
            AIFeedback.reference_id == question_id,
        )
        .order_by(AIFeedback.created_at.desc())
    ).all()

    results = []
    for fb in rows:
        resp_json = fb.response_json or {}
        results.append(
            CoachingResponse(
                id=fb.id,
                question_id=question_id,
                overall_score=resp_json.get("overall_score", 0),
                strengths=resp_json.get("strengths", []),
                gaps=resp_json.get("gaps", []),
                improvements=resp_json.get("improvements", []),
                example_answer_section=resp_json.get("example_answer_section", ""),
                ready_for_interview=resp_json.get("ready_for_interview", False),
                model=fb.model,
                input_tokens=fb.input_tokens,
                output_tokens=fb.output_tokens,
                latency_ms=fb.latency_ms,
                created_at=fb.created_at.isoformat() if fb.created_at else None,
            )
        )

    return results

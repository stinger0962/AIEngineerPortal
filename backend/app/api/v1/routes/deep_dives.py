"""Lesson deep-dive generation and history endpoints."""
import uuid
from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

import redis as redis_lib

from app.db.session import get_db
from app.models.entities import AIFeedback, Lesson, LearningPath, User
from app.schemas.portal import DeepDiveRequest, DeepDiveResponse
from app.services.ai_service import AIService
from app.core.config import get_settings

router = APIRouter(prefix="/learning", tags=["deep-dives"])


def _get_redis() -> Optional[redis_lib.Redis]:
    try:
        settings = get_settings()
        return redis_lib.from_url(settings.redis_url)
    except Exception:
        return None


def _check_rate_limit(r: Optional[redis_lib.Redis], user_id: int) -> bool:
    if r is None:
        return True
    key = f"ai_deepdive_rate:{user_id}:{datetime.utcnow().strftime('%Y%m%d%H%M')}"
    count = r.incr(key)
    if count == 1:
        r.expire(key, 120)
    return count <= 3


def _get_user_id(db: Session) -> int:
    return db.scalar(select(User.id).limit(1)) or 1


@router.post("/lessons/{lesson_id}/deep-dive", response_model=DeepDiveResponse)
def generate_deep_dive(
    lesson_id: int,
    payload: DeepDiveRequest,
    db: Session = Depends(get_db),
):
    """Generate an AI deep-dive answer for a specific question about a lesson."""
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

    lesson = db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")

    # Resolve learning path name for richer prompt context
    path_name = ""
    if lesson.learning_path_id:
        lp = db.get(LearningPath, lesson.learning_path_id)
        if lp:
            path_name = lp.title

    lesson_context = {
        "title": lesson.title,
        "content_md": lesson.content_md,
        "path_name": path_name,
    }

    result = svc.generate_deep_dive(payload.question, lesson_context)
    if result is None:
        raise HTTPException(502, "Failed to generate deep-dive — try again")

    meta = result.pop("_meta", {})

    feedback = AIFeedback(
        user_id=user_id,
        feature="deep_dive",
        reference_id=lesson_id,
        user_input_hash=f"deepdive-{lesson_id}-{uuid.uuid4().hex[:8]}",
        prompt_template=meta.get("prompt_template"),
        response_json={
            "question": payload.question,
            "answer_md": result.get("answer_md", ""),
            "related_concepts": result.get("related_concepts", []),
        },
        model=meta.get("model"),
        input_tokens=meta.get("input_tokens"),
        output_tokens=meta.get("output_tokens"),
        latency_ms=meta.get("latency_ms"),
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    return DeepDiveResponse(
        id=feedback.id,
        question=payload.question,
        answer_md=result.get("answer_md", ""),
        related_concepts=result.get("related_concepts", []),
        model=feedback.model,
        input_tokens=feedback.input_tokens,
        output_tokens=feedback.output_tokens,
        latency_ms=feedback.latency_ms,
        created_at=feedback.created_at.isoformat() if feedback.created_at else None,
    )


@router.get("/lessons/{lesson_id}/deep-dives", response_model=List[DeepDiveResponse])
def list_deep_dives(
    lesson_id: int,
    db: Session = Depends(get_db),
):
    """Retrieve previous deep-dive Q&A pairs for a lesson."""
    lesson = db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")

    rows = db.scalars(
        select(AIFeedback)
        .where(
            AIFeedback.feature == "deep_dive",
            AIFeedback.reference_id == lesson_id,
        )
        .order_by(AIFeedback.created_at.desc())
    ).all()

    results = []
    for fb in rows:
        resp_json = fb.response_json or {}
        results.append(
            DeepDiveResponse(
                id=fb.id,
                question=resp_json.get("question", ""),
                answer_md=resp_json.get("answer_md", ""),
                related_concepts=resp_json.get("related_concepts", []),
                model=fb.model,
                input_tokens=fb.input_tokens,
                output_tokens=fb.output_tokens,
                latency_ms=fb.latency_ms,
                created_at=fb.created_at.isoformat() if fb.created_at else None,
            )
        )

    return results

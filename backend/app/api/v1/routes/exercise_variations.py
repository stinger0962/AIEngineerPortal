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
    return count <= 3


def _get_user_id(db: Session) -> int:
    return db.scalar(select(User.id).limit(1)) or 1


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:190]
    suffix = uuid.uuid4().hex[:4]
    return f"{slug}-{suffix}"


@router.post("/{exercise_id}/variation")
def generate_variation(
    exercise_id: int,
    variation_type: str = Query(default="scenario", pattern="^(scenario|concept|harder)$"),
    db: Session = Depends(get_db),
):
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

    result = svc.generate_exercise_variation(seed, variation_type, db=db, user_id=user_id)
    if result is None:
        raise HTTPException(502, "Failed to generate variation — try again")

    meta = result.pop("_meta", {})

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
    parent = db.get(Exercise, exercise_id)
    if not parent:
        raise HTTPException(404, "Parent exercise not found")

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

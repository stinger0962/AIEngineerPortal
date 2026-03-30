"""AI Study Copilot chat endpoint."""
from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import redis as redis_lib

from app.db.session import get_db
from app.models.entities import AIFeedback, User
from app.services.copilot_loop import CopilotLoop
from app.services.ai_service import AIService
from app.core.config import get_settings

router = APIRouter(prefix="/copilot", tags=["copilot"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class SuggestedAction(BaseModel):
    type: str
    title: str
    slug: str


class ChatResponse(BaseModel):
    response: str
    suggested_actions: list[SuggestedAction] = []
    model: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_ms: Optional[int] = None


def _get_redis() -> Optional[redis_lib.Redis]:
    try:
        settings = get_settings()
        return redis_lib.from_url(settings.redis_url)
    except Exception:
        return None


def _get_user_id(db: Session) -> int:
    return db.scalar(select(User.id).limit(1)) or 1


@router.post("/chat", response_model=ChatResponse)
def copilot_chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
):
    settings = get_settings()
    svc = AIService()

    if not svc.is_available:
        raise HTTPException(503, "AI copilot is not available — no API key configured")

    user_id = _get_user_id(db)

    # Rate limit: 5 per minute
    r = _get_redis()
    if r:
        key = f"copilot_rate:{user_id}:{datetime.utcnow().strftime('%Y%m%d%H%M')}"
        count = r.incr(key)
        if count == 1:
            r.expire(key, 120)
        if count > 5:
            raise HTTPException(429, "Too many requests — try again in a minute")

    # Daily token budget check
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

    # Convert to plain dicts for CopilotLoop
    messages = [{"role": m.role, "content": m.content} for m in payload.messages]

    copilot = CopilotLoop(db=db, user_id=user_id, client=svc.client, model=svc.model)
    result = copilot.run(messages=messages, max_rounds=3)

    if result is None:
        raise HTTPException(502, "I'm having trouble thinking right now. Try again.")

    meta = result.get("_meta", {})

    # Track in ai_feedback
    feedback = AIFeedback(
        user_id=user_id,
        feature="copilot",
        reference_id=None,
        user_input_hash=None,
        prompt_template=None,
        response_json={"response": result["response"], "actions": result["suggested_actions"]},
        model=meta.get("model"),
        input_tokens=meta.get("input_tokens"),
        output_tokens=meta.get("output_tokens"),
        latency_ms=meta.get("latency_ms"),
    )
    db.add(feedback)
    db.commit()

    return ChatResponse(
        response=result["response"],
        suggested_actions=[
            SuggestedAction(**a) for a in result.get("suggested_actions", [])
        ],
        model=meta.get("model"),
        input_tokens=meta.get("input_tokens"),
        output_tokens=meta.get("output_tokens"),
        latency_ms=meta.get("latency_ms"),
    )

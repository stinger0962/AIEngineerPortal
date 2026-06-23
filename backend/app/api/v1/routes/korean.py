"""Korean course endpoints: map, node fetch, completion, reset, TTS, boss roleplay (SSE)."""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.core.config import get_settings
from app.db.session import SessionLocal, get_db
from app.models import KoreanConversation, KoreanMessage, User
from app.services.ai_service import AIService
from app.services.korean import service as ksvc
from app.services.korean.oracle import KoreanOracle
from app.services.podcast_service import _tts_bytes

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/korean", tags=["korean"])


def get_user_id(db: Session) -> int:
    return db.scalar(select(User.id).limit(1))


class CompleteRequest(BaseModel):
    score: float = 1.0
    stars: int = 1


class TtsRequest(BaseModel):
    text: str


class BossTurn(BaseModel):
    message: str
    conversation_id: int | None = None


@router.get("/map")
def get_map(db: Session = Depends(get_db)):
    return ksvc.get_map(db, get_user_id(db))


@router.get("/nodes/{slug}")
def get_node(slug: str, db: Session = Depends(get_db)):
    node = ksvc.get_node(db, slug)
    if node is None:
        raise HTTPException(404, "Unknown node")
    return {
        "slug": node.slug, "kind": node.kind, "title": node.title,
        "order_index": node.order_index, "content_json": node.content_json or {},
    }


@router.post("/nodes/{slug}/complete")
def complete_node(slug: str, payload: CompleteRequest, db: Session = Depends(get_db)):
    try:
        return ksvc.complete_node(db, get_user_id(db), slug, payload.score, payload.stars)
    except ValueError:
        raise HTTPException(404, "Unknown node")


@router.delete("/progress")
def reset_progress(db: Session = Depends(get_db)):
    return ksvc.reset_progress(db, get_user_id(db))


@router.post("/tts")
def korean_tts(payload: TtsRequest):
    settings = get_settings()
    if not settings.minimax_api_key or not settings.minimax_group_id:
        raise HTTPException(503, "TTS not configured")
    text = (payload.text or "").strip()[:400]
    if not text:
        raise HTTPException(400, "Empty text")
    try:
        mp3 = _tts_bytes(
            text, settings.minimax_korean_voice_id, settings.minimax_api_key,
            settings.minimax_group_id, settings.minimax_model, settings.minimax_api_base,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("korean tts failed")
        raise HTTPException(502, "TTS upstream error") from exc
    return Response(content=mp3, media_type="audio/mpeg", headers={"Cache-Control": "public, max-age=86400"})


@router.post("/nodes/{slug}/boss")
def boss_turn(slug: str, payload: BossTurn, db: Session = Depends(get_db)):
    """One roleplay turn. Streams the assistant reply, then a done event with goal_met."""
    node = ksvc.get_node(db, slug)
    if node is None or node.kind != "boss":
        raise HTTPException(404, "Unknown boss node")
    user_id = get_user_id(db)
    boss = node.content_json or {}

    conv_id = payload.conversation_id
    if conv_id is None:
        conv = KoreanConversation(user_id=user_id, node_id=node.id)
        db.add(conv)
        db.commit()
        db.refresh(conv)
        conv_id = conv.id
    else:
        conv = db.get(KoreanConversation, conv_id)
        if conv is None or conv.node_id != node.id or conv.user_id != user_id:
            raise HTTPException(404, "Conversation not found")
    db.add(KoreanMessage(conversation_id=conv_id, role="user", content=payload.message))
    db.commit()

    history = [
        {"role": m.role, "content": m.content}
        for m in db.scalars(
            select(KoreanMessage).where(KoreanMessage.conversation_id == conv_id).order_by(KoreanMessage.id.asc())
        ).all()
    ]

    svc = AIService(model=get_settings().korean_model)

    def event_stream():
        if not svc.is_available:
            fallback = "네, 알겠습니다."
            db2 = SessionLocal()
            try:
                db2.add(KoreanMessage(conversation_id=conv_id, role="assistant", content=fallback))
                db2.commit()
            finally:
                db2.close()
            yield {"data": json.dumps({"type": "text", "delta": fallback}, ensure_ascii=False)}
            yield {"data": json.dumps({"type": "done", "conversation_id": conv_id, "goal_met": False}, ensure_ascii=False)}
            return

        oracle = KoreanOracle(client=svc.client, model=svc.model)
        result = oracle.run(boss=boss, messages=history)
        if result is None:
            logger.warning("korean boss oracle returned None for node %s", slug)
            yield {"data": json.dumps({"type": "error"}, ensure_ascii=False)}
            return
        reply, goal_met = result["response"], result["goal_met"]
        db2 = SessionLocal()
        try:
            db2.add(KoreanMessage(conversation_id=conv_id, role="assistant", content=reply))
            db2.commit()
        finally:
            db2.close()
        yield {"data": json.dumps({"type": "text", "delta": reply}, ensure_ascii=False)}
        yield {"data": json.dumps({"type": "done", "conversation_id": conv_id, "goal_met": goal_met}, ensure_ascii=False)}

    return EventSourceResponse(event_stream())

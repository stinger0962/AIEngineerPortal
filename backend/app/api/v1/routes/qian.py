"""观音灵签 求签 + AI 解签 端点。"""
import json
import logging
import time
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.core.config import get_settings
from app.db.session import SessionLocal, get_db
from app.models.entities import AIFeedback, QianReading, User
from app.services.ai_service import AIService
from app.services.qian.draw import draw_sign
from app.services.qian.oracle import QianOracle
from app.services.qian.signs import get_sign
from app.services.ziwei.oracle_tools import StreamMarkerParser

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/qian", tags=["qian"])


class QianRequest(BaseModel):
    question: str
    sign_id: int | None = None


def _get_user_id(db: Session) -> int:
    try:
        return db.scalar(select(User.id).limit(1)) or 1
    except Exception:
        return 1


@router.post("/oracle/stream")
def qian_oracle_stream(payload: QianRequest, db: Session = Depends(get_db)):
    question = (payload.question or "").strip()
    if not question:
        raise HTTPException(400, "请先写下你的问题")

    settings = get_settings()
    svc = AIService()
    if not svc.is_available:
        raise HTTPException(503, "解签师未启用（缺少 API Key）")

    today_start = datetime.combine(date.today(), datetime.min.time())
    used_today = db.scalar(
        select(func.coalesce(func.sum(AIFeedback.input_tokens + AIFeedback.output_tokens), 0))
        .where(AIFeedback.created_at >= today_start)
    ) or 0
    if used_today >= settings.ai_daily_token_budget:
        raise HTTPException(429, "今日额度已用尽，请明日再来")

    sign = get_sign(payload.sign_id) if payload.sign_id else draw_sign()
    if sign is None:
        raise HTTPException(404, "签不存在")

    oracle = QianOracle(client=svc.client, model=svc.model)
    system_prompt = oracle.system_prompt(sign, question)
    model, client = svc.model, svc.client
    uid = _get_user_id(db)

    def _persist(clean, cameras, segments, in_tok, out_tok, start):
        if not clean and not (in_tok or out_tok):
            return
        _db = SessionLocal()
        try:
            if clean:
                _db.add(QianReading(
                    question=question, sign_id=sign["id"], grade=sign["grade"], response=clean,
                    context_json={"sign": sign, "camera_commands": cameras, "segments": segments},
                ))
            _db.add(AIFeedback(
                user_id=uid, feature="qian_oracle", reference_id=sign["id"],
                user_input_hash="", prompt_template=None,
                response_json={"response": clean, "camera_commands": cameras},
                model=model, input_tokens=in_tok, output_tokens=out_tok,
                latency_ms=int((time.time() - start) * 1000),
            ))
            _db.commit()
        finally:
            _db.close()

    def event_stream():
        parser = StreamMarkerParser()
        in_tok = out_tok = 0
        start = time.time()
        yield {"data": json.dumps({"type": "sign", "sign": sign}, ensure_ascii=False)}
        try:
            with client.messages.stream(model=model, max_tokens=1200, system=system_prompt,
                                        messages=[{"role": "user", "content": question}]) as stream:
                for delta in stream.text_stream:
                    for kind, val in parser.feed(delta):
                        if kind == "text":
                            yield {"data": json.dumps({"type": "text", "delta": val}, ensure_ascii=False)}
                        else:
                            yield {"data": json.dumps({"type": "camera", "command": val}, ensure_ascii=False)}
                final = stream.get_final_message()
                in_tok, out_tok = final.usage.input_tokens, final.usage.output_tokens
            trailing, clean, segments, cameras = parser.finish()
            if trailing:
                yield {"data": json.dumps({"type": "text", "delta": trailing}, ensure_ascii=False)}
            _persist(clean, cameras, segments, in_tok, out_tok, start)
            yield {"data": json.dumps({"type": "done", "meta": {"model": model, "total_tokens": in_tok + out_tok}}, ensure_ascii=False)}
        except Exception:
            logger.exception("qian oracle stream failed (sign=%s)", sign["id"])
            try:
                _, clean, segments, cameras = parser.finish()
                _persist(clean, cameras, segments, in_tok, out_tok, start)
            except Exception:
                logger.exception("qian salvage-persist failed")
            yield {"data": json.dumps({"type": "error"}, ensure_ascii=False)}

    return EventSourceResponse(event_stream())


@router.get("/readings")
def list_readings(db: Session = Depends(get_db)):
    rows = db.scalars(select(QianReading).order_by(QianReading.id.desc())).all()
    return [{
        "id": r.id, "question": r.question, "sign_id": r.sign_id, "grade": r.grade,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in rows]


@router.get("/readings/{reading_id}")
def get_reading(reading_id: int, db: Session = Depends(get_db)):
    r = db.get(QianReading, reading_id)
    if not r:
        raise HTTPException(404, "记录不存在")
    return {
        "id": r.id, "question": r.question, "sign_id": r.sign_id, "grade": r.grade,
        "response": r.response, "context_json": r.context_json or {},
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }

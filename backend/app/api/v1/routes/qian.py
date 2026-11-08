"""观音灵签 求签 + AI 解签 端点。"""
import hashlib
import json
import logging
import time
from datetime import date, datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.core.config import get_settings
from app.db.session import SessionLocal, get_db
from app.models.entities import AIFeedback, QianReading, User
from app.services.paid_identity import PaidPrincipal
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
    return db.scalar(select(User.id).limit(1)) or 1


def get_device_id(x_device_id: str = Header(default="")) -> str:
    """匿名浏览器归属：灵签求签记录按 device 私有（无登录）。"""
    return (x_device_id or "").strip()


@router.post("/oracle/stream")
def qian_oracle_stream(payload: QianRequest, db: Session = Depends(get_db), device: str = Depends(get_device_id)):
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

    oracle = QianOracle(client=svc.client, model=settings.oracle_model)
    system_prompt = oracle.system_prompt(sign, question)
    model, client = settings.oracle_model, svc.client
    uid = _get_user_id(db)
    # Persist streaming output in the request database, including isolated products.
    persistence_bind = db.get_bind()

    def _persist(clean, cameras, segments, in_tok, out_tok, start):
        if not clean and not (in_tok or out_tok):
            return
        _db = SessionLocal(bind=persistence_bind)
        try:
            if clean:
                reading = QianReading(
                    device_id=None if isinstance(device, PaidPrincipal) else device or None, question=question, sign_id=sign["id"], grade=sign["grade"], response=clean,
                    context_json={"sign": sign, "camera_commands": cameras, "segments": segments},
                )
                _db.add(reading)
                if isinstance(device, PaidPrincipal):
                    from app.models.paid_accounts import PaidQianOwner
                    _db.flush()
                    _db.add(PaidQianOwner(reading_id=reading.id, account_id=device.account_id))
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
        persistence_attempted = False
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
            if not clean.strip():
                raise ValueError("empty_generation")
            persistence_attempted = True
            _persist(clean, cameras, segments, in_tok, out_tok, start)
            yield {"data": json.dumps({"type": "done", "meta": {"model": model, "total_tokens": in_tok + out_tok}}, ensure_ascii=False)}
        except Exception:
            logger.exception("qian oracle stream failed (sign=%s)", sign["id"])
            # A failed commit may already have succeeded remotely. Never retry
            # persistence blindly; salvage is only for provider/parse failures.
            try:
                _, clean, segments, cameras = parser.finish()
                if not persistence_attempted:
                    _persist(clean, cameras, segments, in_tok, out_tok, start)
            except Exception:
                logger.exception("qian salvage-persist failed")
            yield {"data": json.dumps({"type": "error"}, ensure_ascii=False)}

    return EventSourceResponse(event_stream())


# Reading history is private to the bearer device identifier; legacy NULL rows stay hidden.
_MASK_LEN = 12


def _mask_question(q: str) -> str:
    q = q or ""
    return q[:_MASK_LEN] + "……" if len(q) > _MASK_LEN else q


def _device_label(device_id: str | None) -> str:
    """匿名分组标签：device_id 的不可逆短哈希（用于「哪几条来自同一台」/ 有几个用户
    的调研）。绝不回传真实 device_id——它就是找回码，泄露=别人能进你的紫微档案。"""
    if not device_id:
        return "—"  # 旧数据无归属
    return "dev#" + hashlib.sha256(device_id.encode("utf-8")).hexdigest()[:6]


@router.get("/readings")
def list_readings(db: Session = Depends(get_db), device: str = Depends(get_device_id)):
    if not device:
        return []
    query = select(QianReading)
    if isinstance(device, PaidPrincipal):
        from app.models.paid_accounts import PaidQianOwner
        query = query.join(PaidQianOwner, PaidQianOwner.reading_id == QianReading.id).where(
            PaidQianOwner.account_id == device.account_id)
    else:
        query = query.where(QianReading.device_id == device)
    rows = db.scalars(query.order_by(QianReading.id.desc()).limit(50)).all()
    return [{
        "id": r.id, "question": _mask_question(r.question), "sign_id": r.sign_id, "grade": r.grade,
        "device": _device_label(r.device_id),
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in rows]


@router.get("/readings/{reading_id}")
def get_reading(reading_id: int, db: Session = Depends(get_db), device: str = Depends(get_device_id)):
    r = db.get(QianReading, reading_id)
    if isinstance(device, PaidPrincipal):
        from app.models.paid_accounts import PaidQianOwner
        owner = db.get(PaidQianOwner, reading_id)
        owned = owner is not None and owner.account_id == device.account_id
    else:
        owned = bool(device and r and r.device_id == device)
    if not r or not owned:
        raise HTTPException(404, "记录不存在")
    return {
        "id": r.id, "question": r.question, "sign_id": r.sign_id, "grade": r.grade,
        "response": r.response, "context_json": r.context_json or {},
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }

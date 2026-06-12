"""Ziwei Dou Shu (紫微斗数) profile endpoints."""
import json
import logging
import re
import time
from datetime import date, datetime
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.core.config import get_settings
from app.db.session import SessionLocal, get_db
from app.models.entities import (
    AIFeedback,
    User,
    ZiweiConversation,
    ZiweiMessage,
    ZiweiProfile,
)
from app.services.ai_service import AIService
from app.services.podcast_service import _tts_bytes
from app.services.ziwei.oracle import ZiweiOracle
from app.services.ziwei.oracle_tools import StreamMarkerParser

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ziwei", tags=["ziwei"])

VALID_RELATIONS = {"self", "family", "friend"}
VALID_GENDERS = {"male", "female"}
VALID_PERSONAS = {"sage", "taoist", "analyst"}
BIRTH_DATE_PATTERN = re.compile(r"^\d{4}-\d{1,2}-\d{1,2}$")

_MD_RE = re.compile(r"\*\*|\*|__|_|`|~~|#")


def _strip_markdown(text: str) -> str:
    """去掉 markdown 强调符号，避免 TTS 把 ** 念成「星号星号」。"""
    return _MD_RE.sub("", text).strip()


class ProfileCreate(BaseModel):
    name: str
    relation: str = "self"
    gender: str
    birth_date: str
    birth_time_index: int
    is_lunar_input: bool = False
    is_leap_month: bool = False
    chart_json: Dict = {}


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    relation: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[str] = None
    birth_time_index: Optional[int] = None
    is_lunar_input: Optional[bool] = None
    is_leap_month: Optional[bool] = None
    chart_json: Optional[Dict] = None
    persona: Optional[str] = None


class TtsRequest(BaseModel):
    text: str


def _validate(field: str, value, allowed=None) -> None:
    if field == "birth_time_index" and not 0 <= value <= 12:
        raise HTTPException(400, "birth_time_index must be 0-12")
    if field == "birth_date" and not BIRTH_DATE_PATTERN.match(value):
        raise HTTPException(400, "birth_date must be YYYY-M-D")
    if allowed is not None and value not in allowed:
        raise HTTPException(400, f"{field} must be one of {sorted(allowed)}")


def _profile_out(p: ZiweiProfile) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "relation": p.relation,
        "gender": p.gender,
        "birth_date": p.birth_date,
        "birth_time_index": p.birth_time_index,
        "is_lunar_input": p.is_lunar_input,
        "is_leap_month": p.is_leap_month,
        "chart_json": p.chart_json or {},
        "persona": p.persona,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


@router.get("/profiles")
def list_profiles(db: Session = Depends(get_db)):
    profiles = db.scalars(select(ZiweiProfile).order_by(ZiweiProfile.id.asc())).all()
    return [_profile_out(p) for p in profiles]


@router.post("/profiles")
def create_profile(payload: ProfileCreate, db: Session = Depends(get_db)):
    _validate("relation", payload.relation, VALID_RELATIONS)
    _validate("gender", payload.gender, VALID_GENDERS)
    _validate("birth_time_index", payload.birth_time_index)
    _validate("birth_date", payload.birth_date)

    profile = ZiweiProfile(**payload.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return _profile_out(profile)


@router.get("/profiles/{profile_id}")
def get_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = db.get(ZiweiProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    return _profile_out(profile)


@router.put("/profiles/{profile_id}")
def update_profile(profile_id: int, payload: ProfileUpdate, db: Session = Depends(get_db)):
    profile = db.get(ZiweiProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")

    updates = payload.model_dump(exclude_unset=True, exclude_none=True)  # 列均非空，显式 null 视为无操作
    if "relation" in updates:
        _validate("relation", updates["relation"], VALID_RELATIONS)
    if "gender" in updates:
        _validate("gender", updates["gender"], VALID_GENDERS)
    if "persona" in updates:
        _validate("persona", updates["persona"], VALID_PERSONAS)
    if "birth_time_index" in updates:
        _validate("birth_time_index", updates["birth_time_index"])
    if "birth_date" in updates:
        _validate("birth_date", updates["birth_date"])

    for key, value in updates.items():
        setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return _profile_out(profile)


@router.delete("/profiles/{profile_id}")
def delete_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = db.get(ZiweiProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    db.delete(profile)
    db.commit()
    return {"deleted": profile_id}


class OracleRequest(BaseModel):
    scenario: str = "natal"
    message: str
    conversation_id: Optional[int] = None


def _get_user_id(db: Session) -> int:
    return db.scalar(select(User.id).limit(1)) or 1


@router.post("/profiles/{profile_id}/oracle")
def ask_oracle(profile_id: int, payload: OracleRequest, db: Session = Depends(get_db)):
    profile = db.get(ZiweiProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    if not (profile.chart_json or {}).get("palaces"):
        raise HTTPException(400, "Profile has no chart data")

    from app.core.config import get_settings
    settings = get_settings()
    svc = AIService()
    if not svc.is_available:
        raise HTTPException(503, "AI oracle is not available — no API key configured")

    today_start = datetime.combine(date.today(), datetime.min.time())
    used_today = db.scalar(
        select(func.coalesce(func.sum(AIFeedback.input_tokens + AIFeedback.output_tokens), 0)).where(AIFeedback.created_at >= today_start)
    ) or 0
    if used_today >= settings.ai_daily_token_budget:
        raise HTTPException(429, "Daily AI limit reached, try again tomorrow")

    if payload.conversation_id:
        conv = db.get(ZiweiConversation, payload.conversation_id)
        if not conv or conv.profile_id != profile_id:
            raise HTTPException(404, "Conversation not found")
    else:
        conv = ZiweiConversation(profile_id=profile_id, scenario=payload.scenario, title=payload.message[:40])
        db.add(conv)
        db.flush()  # assigns conv.id without committing; rolls back on failure

    history = db.scalars(select(ZiweiMessage).where(ZiweiMessage.conversation_id == conv.id).order_by(ZiweiMessage.id.asc())).all()
    messages = [{"role": m.role, "content": m.content} for m in history]
    messages.append({"role": "user", "content": payload.message})

    oracle = ZiweiOracle(client=svc.client, model=svc.model)
    result = oracle.run(
        chart_json=profile.chart_json, persona=profile.persona, scenario=payload.scenario,
        portrait=profile.portrait_json or {}, messages=messages,
    )
    if result is None:
        raise HTTPException(502, "解盘师一时失神，请稍后再问。")

    meta = result["_meta"]
    db.add(ZiweiMessage(conversation_id=conv.id, role="user", content=payload.message, chart_context_json={}))
    db.add(ZiweiMessage(
        conversation_id=conv.id, role="assistant", content=result["response"],
        chart_context_json={"camera_commands": result["camera_commands"], "segments": result.get("segments", []), "scenario": payload.scenario},
    ))
    db.add(AIFeedback(
        user_id=_get_user_id(db), feature="ziwei_oracle", reference_id=profile_id,
        user_input_hash="", prompt_template=None,
        response_json={"response": result["response"], "camera_commands": result["camera_commands"]},
        model=meta.get("model"), input_tokens=meta.get("input_tokens"),
        output_tokens=meta.get("output_tokens"), latency_ms=meta.get("latency_ms"),
    ))
    db.commit()

    return {
        "conversation_id": conv.id, "response": result["response"],
        "camera_commands": result["camera_commands"], "segments": result.get("segments", []), "meta": meta,
    }


@router.post("/profiles/{profile_id}/oracle/stream")
def ask_oracle_stream(profile_id: int, payload: OracleRequest, db: Session = Depends(get_db)):
    profile = db.get(ZiweiProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    if not (profile.chart_json or {}).get("palaces"):
        raise HTTPException(400, "Profile has no chart data")

    from app.core.config import get_settings
    settings = get_settings()
    svc = AIService()
    if not svc.is_available:
        raise HTTPException(503, "AI oracle is not available — no API key configured")

    today_start = datetime.combine(date.today(), datetime.min.time())
    used_today = db.scalar(
        select(func.coalesce(func.sum(AIFeedback.input_tokens + AIFeedback.output_tokens), 0)).where(AIFeedback.created_at >= today_start)
    ) or 0
    if used_today >= settings.ai_daily_token_budget:
        raise HTTPException(429, "Daily AI limit reached, try again tomorrow")

    if payload.conversation_id:
        conv = db.get(ZiweiConversation, payload.conversation_id)
        if not conv or conv.profile_id != profile_id:
            raise HTTPException(404, "Conversation not found")
    else:
        conv = ZiweiConversation(profile_id=profile_id, scenario=payload.scenario, title=payload.message[:40])
        db.add(conv)
        db.commit()  # 提交以拿稳 conv.id（流式生成器用新 session 持久化消息）
        db.refresh(conv)

    history = db.scalars(select(ZiweiMessage).where(ZiweiMessage.conversation_id == conv.id).order_by(ZiweiMessage.id.asc())).all()
    messages = [{"role": m.role, "content": m.content} for m in history]
    messages.append({"role": "user", "content": payload.message})
    claude_messages = messages[-10:] if len(messages) > 10 else messages

    oracle = ZiweiOracle(client=svc.client, model=svc.model)
    system_prompt = oracle._system_prompt(profile.chart_json, profile.persona, payload.scenario, profile.portrait_json or {})

    conv_id = conv.id
    client = svc.client
    model = svc.model
    user_message = payload.message
    scenario = payload.scenario
    uid = _get_user_id(db)

    def _persist(clean: str, cameras: list, segments: list, in_tok: int, out_tok: int, start: float) -> None:
        """用新 session 持久化本轮对话 + token 计量。
        即便 clean 为空也记 AIFeedback（只要花了 token），否则每日额度计量会漏算。"""
        if not clean and not (in_tok or out_tok):
            return
        _db = SessionLocal()
        try:
            if clean:
                _db.add(ZiweiMessage(conversation_id=conv_id, role="user", content=user_message, chart_context_json={}))
                _db.add(ZiweiMessage(
                    conversation_id=conv_id, role="assistant", content=clean,
                    chart_context_json={"camera_commands": cameras, "segments": segments, "scenario": scenario},
                ))
            _db.add(AIFeedback(
                user_id=uid, feature="ziwei_oracle", reference_id=profile_id,
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
        try:
            with client.messages.stream(model=model, max_tokens=1200, system=system_prompt, messages=claude_messages) as stream:
                for delta in stream.text_stream:
                    for kind, val in parser.feed(delta):
                        if kind == "text":
                            yield {"data": json.dumps({"type": "text", "delta": val}, ensure_ascii=False)}
                        else:
                            yield {"data": json.dumps({"type": "camera", "command": val}, ensure_ascii=False)}
                final = stream.get_final_message()
                in_tok = final.usage.input_tokens
                out_tok = final.usage.output_tokens
            trailing, clean, segments, cameras = parser.finish()
            if trailing:
                yield {"data": json.dumps({"type": "text", "delta": trailing}, ensure_ascii=False)}
            _persist(clean, cameras, segments, in_tok, out_tok, start)
            yield {"data": json.dumps({"type": "done", "conversation_id": conv_id, "meta": {"model": model, "total_tokens": in_tok + out_tok, "latency_ms": int((time.time() - start) * 1000)}}, ensure_ascii=False)}
        except Exception:
            # 流中途失败：尽力保住已生成的文字 + 计量（非原子；前端收到 error 应清掉屏幕上的半截文本）
            logger.exception("ziwei oracle stream failed (profile=%s conv=%s)", profile_id, conv_id)
            try:
                _, clean, segments, cameras = parser.finish()
                _persist(clean, cameras, segments, in_tok, out_tok, start)
            except Exception:
                logger.exception("ziwei oracle stream salvage-persist failed")
            yield {"data": json.dumps({"type": "error"}, ensure_ascii=False)}

    return EventSourceResponse(event_stream())


@router.get("/profiles/{profile_id}/conversations")
def list_conversations(profile_id: int, db: Session = Depends(get_db)):
    convs = db.scalars(select(ZiweiConversation).where(ZiweiConversation.profile_id == profile_id).order_by(ZiweiConversation.id.desc())).all()
    return [{"id": c.id, "scenario": c.scenario, "title": c.title, "created_at": c.created_at.isoformat() if c.created_at else None} for c in convs]


@router.get("/conversations/{conversation_id}/messages")
def list_messages(conversation_id: int, db: Session = Depends(get_db)):
    msgs = db.scalars(select(ZiweiMessage).where(ZiweiMessage.conversation_id == conversation_id).order_by(ZiweiMessage.id.asc())).all()
    return [{"id": m.id, "role": m.role, "content": m.content, "chart_context_json": m.chart_context_json or {}, "created_at": m.created_at.isoformat() if m.created_at else None} for m in msgs]


@router.post("/tts")
def ziwei_tts(payload: TtsRequest):
    settings = get_settings()
    if not settings.minimax_api_key or not settings.minimax_group_id:
        raise HTTPException(503, "TTS not configured")
    text = _strip_markdown(payload.text or "")[:800]
    if not text:
        raise HTTPException(400, "Empty text")
    try:
        mp3 = _tts_bytes(
            text,
            settings.minimax_oracle_voice_id,
            settings.minimax_api_key,
            settings.minimax_group_id,
            settings.minimax_model,
            settings.minimax_api_base,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("ziwei tts failed")
        raise HTTPException(502, "TTS upstream error") from exc
    return Response(content=mp3, media_type="audio/mpeg", headers={"Cache-Control": "no-store"})

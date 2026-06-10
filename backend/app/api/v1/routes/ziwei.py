"""Ziwei Dou Shu (紫微斗数) profile endpoints."""
import re
from datetime import date, datetime
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import (
    AIFeedback,
    User,
    ZiweiConversation,
    ZiweiMessage,
    ZiweiProfile,
)
from app.services.ai_service import AIService
from app.services.ziwei.oracle import ZiweiOracle

router = APIRouter(prefix="/ziwei", tags=["ziwei"])

VALID_RELATIONS = {"self", "family", "friend"}
VALID_GENDERS = {"male", "female"}
VALID_PERSONAS = {"sage", "taoist", "analyst"}
BIRTH_DATE_PATTERN = re.compile(r"^\d{4}-\d{1,2}-\d{1,2}$")


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
    return db.scalar(select(User.id).limit(1))


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
        db.commit()
        db.refresh(conv)

    history = db.scalars(select(ZiweiMessage).where(ZiweiMessage.conversation_id == conv.id).order_by(ZiweiMessage.id.asc())).all()
    messages = [{"role": m.role, "content": m.content} for m in history]
    messages.append({"role": "user", "content": payload.message})

    db.add(ZiweiMessage(conversation_id=conv.id, role="user", content=payload.message, chart_context_json={}))
    db.commit()

    oracle = ZiweiOracle(client=svc.client, model=svc.model)
    result = oracle.run(
        chart_json=profile.chart_json, persona=profile.persona, scenario=payload.scenario,
        portrait=profile.portrait_json or {}, messages=messages,
    )
    if result is None:
        raise HTTPException(502, "解盘师一时失神，请稍后再问。")

    meta = result["_meta"]
    db.add(ZiweiMessage(
        conversation_id=conv.id, role="assistant", content=result["response"],
        chart_context_json={"camera_commands": result["camera_commands"], "scenario": payload.scenario},
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
        "camera_commands": result["camera_commands"], "meta": meta,
    }


@router.get("/profiles/{profile_id}/conversations")
def list_conversations(profile_id: int, db: Session = Depends(get_db)):
    convs = db.scalars(select(ZiweiConversation).where(ZiweiConversation.profile_id == profile_id).order_by(ZiweiConversation.id.desc())).all()
    return [{"id": c.id, "scenario": c.scenario, "title": c.title, "created_at": c.created_at.isoformat() if c.created_at else None} for c in convs]


@router.get("/conversations/{conversation_id}/messages")
def list_messages(conversation_id: int, db: Session = Depends(get_db)):
    msgs = db.scalars(select(ZiweiMessage).where(ZiweiMessage.conversation_id == conversation_id).order_by(ZiweiMessage.id.asc())).all()
    return [{"id": m.id, "role": m.role, "content": m.content, "chart_context_json": m.chart_context_json or {}, "created_at": m.created_at.isoformat() if m.created_at else None} for m in msgs]

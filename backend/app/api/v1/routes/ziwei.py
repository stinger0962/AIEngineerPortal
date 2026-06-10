"""Ziwei Dou Shu (紫微斗数) profile endpoints."""
import re
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import ZiweiProfile

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

    updates = payload.model_dump(exclude_unset=True)
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

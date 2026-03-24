from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import AdaptiveFocusOut, MasteryAreaOut
from app.services.adaptive_service import build_adaptive_focus, build_mastery_profile

router = APIRouter(prefix="/adaptive", tags=["adaptive"])


@router.get("/mastery", response_model=List[MasteryAreaOut])
def get_mastery_profile(db: Session = Depends(get_db)) -> List[MasteryAreaOut]:
    return [MasteryAreaOut(**item) for item in build_mastery_profile(db)]


@router.get("/focus", response_model=Optional[AdaptiveFocusOut])
def get_adaptive_focus(db: Session = Depends(get_db)) -> Optional[AdaptiveFocusOut]:
    focus = build_adaptive_focus(db)
    return AdaptiveFocusOut(**focus) if focus else None

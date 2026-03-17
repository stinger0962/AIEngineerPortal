from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import RecommendationOut
from app.services.recommendation_service import next_actions

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/next-actions", response_model=List[RecommendationOut])
def get_next_actions(db: Session = Depends(get_db)) -> List[RecommendationOut]:
    return [RecommendationOut(**item) for item in next_actions(db)]

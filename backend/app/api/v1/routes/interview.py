from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import InterviewQuestionOut, InterviewRoadmap, PortfolioReadiness
from app.services.interview_service import build_portfolio_readiness, build_roadmap, list_questions

router = APIRouter(prefix="/interview", tags=["interview"])


@router.get("/questions", response_model=List[InterviewQuestionOut])
def get_questions(category: Optional[str] = Query(default=None), db: Session = Depends(get_db)) -> List[InterviewQuestionOut]:
    return [InterviewQuestionOut.model_validate(question) for question in list_questions(db, category)]


@router.get("/roadmap", response_model=InterviewRoadmap)
def get_roadmap(db: Session = Depends(get_db)) -> InterviewRoadmap:
    return InterviewRoadmap(**build_roadmap(db))


@router.get("/portfolio-readiness", response_model=PortfolioReadiness)
def get_portfolio_readiness(db: Session = Depends(get_db)) -> PortfolioReadiness:
    return PortfolioReadiness(**build_portfolio_readiness(db))

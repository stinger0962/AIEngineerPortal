from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import InterviewPracticeIn, InterviewPracticeOut, InterviewQuestionOut, InterviewRoadmap, PortfolioReadiness, SkillGapInsight
from app.services.interview_service import build_portfolio_readiness, build_roadmap, build_skill_gap_summary, list_questions, record_question_practice

router = APIRouter(prefix="/interview", tags=["interview"])


@router.get("/questions", response_model=List[InterviewQuestionOut])
def get_questions(category: Optional[str] = Query(default=None), db: Session = Depends(get_db)) -> List[InterviewQuestionOut]:
    return [InterviewQuestionOut.model_validate(question) for question in list_questions(db, category)]


@router.post("/questions/{question_id}/practice", response_model=InterviewPracticeOut)
def practice_question(question_id: int, payload: InterviewPracticeIn, db: Session = Depends(get_db)) -> InterviewPracticeOut:
    practice = record_question_practice(db, question_id, payload.confidence_score, payload.notes)
    if not practice:
        raise HTTPException(status_code=404, detail="Interview question not found")
    return InterviewPracticeOut(**practice)


@router.get("/roadmap", response_model=InterviewRoadmap)
def get_roadmap(db: Session = Depends(get_db)) -> InterviewRoadmap:
    return InterviewRoadmap(**build_roadmap(db))


@router.get("/portfolio-readiness", response_model=PortfolioReadiness)
def get_portfolio_readiness(db: Session = Depends(get_db)) -> PortfolioReadiness:
    return PortfolioReadiness(**build_portfolio_readiness(db))


@router.get("/skill-gaps", response_model=List[SkillGapInsight])
def get_skill_gaps(db: Session = Depends(get_db)) -> List[SkillGapInsight]:
    return [SkillGapInsight(**gap) for gap in build_skill_gap_summary(db)]

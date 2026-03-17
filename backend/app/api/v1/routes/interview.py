from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import InterviewQuestionOut, InterviewRoadmap
from app.services.interview_service import build_roadmap, list_questions

router = APIRouter(prefix="/interview", tags=["interview"])


@router.get("/questions", response_model=List[InterviewQuestionOut])
def get_questions(category: Optional[str] = Query(default=None), db: Session = Depends(get_db)) -> List[InterviewQuestionOut]:
    return [InterviewQuestionOut.model_validate(question) for question in list_questions(db, category)]


@router.get("/roadmap", response_model=InterviewRoadmap)
def get_roadmap() -> InterviewRoadmap:
    return InterviewRoadmap(**build_roadmap())

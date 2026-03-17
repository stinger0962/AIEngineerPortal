from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import User
from app.schemas import LearningPathOut, LessonCompletionResponse, LessonOut
from app.services.learning_service import complete_lesson, get_lesson_by_slug, get_path, list_paths

router = APIRouter(prefix="/learning", tags=["learning"])


def get_user_id(db: Session) -> int:
    return db.scalar(select(User.id).limit(1))


@router.get("/paths", response_model=List[LearningPathOut])
def get_paths(db: Session = Depends(get_db)) -> List[LearningPathOut]:
    return [LearningPathOut.model_validate(path) for path in list_paths(db, get_user_id(db))]


@router.get("/paths/{path_id}", response_model=LearningPathOut)
def get_path_detail(path_id: int, db: Session = Depends(get_db)) -> LearningPathOut:
    path = get_path(db, path_id, get_user_id(db))
    if not path:
        raise HTTPException(status_code=404, detail="Learning path not found")
    return LearningPathOut.model_validate(path)


@router.get("/lessons/{lesson_slug}", response_model=LessonOut)
def get_lesson(lesson_slug: str, db: Session = Depends(get_db)) -> LessonOut:
    lesson = get_lesson_by_slug(db, lesson_slug, get_user_id(db))
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return LessonOut.model_validate(lesson)


@router.post("/lessons/{lesson_id}/complete", response_model=LessonCompletionResponse)
def mark_lesson_complete(lesson_id: int, db: Session = Depends(get_db)) -> LessonCompletionResponse:
    pct = complete_lesson(db, lesson_id, get_user_id(db))
    return LessonCompletionResponse(lesson_id=lesson_id, completed=True, learning_completion_pct=pct)

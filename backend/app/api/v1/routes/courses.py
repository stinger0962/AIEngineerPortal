from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import CourseOut, CourseProgressIn
from app.services.course_service import get_course_by_slug, list_courses, update_course_progress

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("", response_model=List[CourseOut])
def get_courses(db: Session = Depends(get_db)) -> List[CourseOut]:
    return [CourseOut.model_validate(course) for course in list_courses(db)]


@router.get("/{course_slug}", response_model=CourseOut)
def get_course(course_slug: str, db: Session = Depends(get_db)) -> CourseOut:
    course = get_course_by_slug(db, course_slug)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return CourseOut.model_validate(course)


@router.post("/{course_id}/progress", response_model=CourseOut)
def set_course_progress(course_id: int, payload: CourseProgressIn, db: Session = Depends(get_db)) -> CourseOut:
    course = update_course_progress(db, course_id, payload.status)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return CourseOut.model_validate(course)

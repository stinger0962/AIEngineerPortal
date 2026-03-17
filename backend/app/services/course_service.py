from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Course


def list_courses(db: Session) -> list[Course]:
    return list(db.scalars(select(Course).order_by(Course.estimated_hours.asc())).all())


def get_course_by_slug(db: Session, slug: str) -> Course | None:
    return db.scalar(select(Course).where(Course.slug == slug))


def update_course_progress(db: Session, course_id: int, status: str) -> Course | None:
    course = db.scalar(select(Course).where(Course.id == course_id))
    if not course:
        return None
    course.status = status
    db.commit()
    db.refresh(course)
    return course

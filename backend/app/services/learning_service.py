from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import LearningPath, Lesson, LessonCompletion
from app.services.progress_service import refresh_progress_snapshot


def list_paths(db: Session, user_id: int) -> list[dict]:
    completions = set(db.scalars(select(LessonCompletion.lesson_id).where(LessonCompletion.user_id == user_id)).all())
    paths = db.scalars(
        select(LearningPath).options(selectinload(LearningPath.lessons)).order_by(LearningPath.order_index.asc())
    ).all()
    items = []
    for path in paths:
        lessons = sorted(path.lessons, key=lambda lesson: lesson.order_index)
        completed = len([lesson for lesson in lessons if lesson.id in completions])
        items.append(
            {
                **path.__dict__,
                "lessons": [{**lesson.__dict__, "is_completed": lesson.id in completions} for lesson in lessons],
                "completion_pct": round((completed / (len(lessons) or 1)) * 100, 1),
            }
        )
    return items


def get_path(db: Session, path_id: int, user_id: int) -> dict | None:
    return next((item for item in list_paths(db, user_id) if item["id"] == path_id), None)


def get_lesson_by_slug(db: Session, slug: str, user_id: int) -> dict | None:
    lesson = db.scalar(select(Lesson).where(Lesson.slug == slug))
    if not lesson:
        return None
    completions = set(db.scalars(select(LessonCompletion.lesson_id).where(LessonCompletion.user_id == user_id)).all())
    return {**lesson.__dict__, "is_completed": lesson.id in completions}


def complete_lesson(db: Session, lesson_id: int, user_id: int) -> float:
    existing = db.scalar(
        select(LessonCompletion).where(LessonCompletion.user_id == user_id, LessonCompletion.lesson_id == lesson_id)
    )
    if not existing:
        db.add(LessonCompletion(user_id=user_id, lesson_id=lesson_id))
        db.commit()
    snapshot = refresh_progress_snapshot(db, user_id)
    return snapshot.learning_completion_pct

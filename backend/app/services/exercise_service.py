from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import Exercise, UserExerciseAttempt
from app.services.progress_service import refresh_progress_snapshot


def list_exercises(db: Session, category: str | None = None, difficulty: str | None = None, search: str | None = None) -> list[Exercise]:
    query = select(Exercise)
    if category:
        query = query.where(Exercise.category == category)
    if difficulty:
        query = query.where(Exercise.difficulty == difficulty)
    if search:
        query = query.where(Exercise.title.ilike(f"%{search}%"))
    return list(db.scalars(query.order_by(Exercise.id.asc())).all())


def get_exercise_detail(db: Session, exercise_id: int, user_id: int) -> dict | None:
    exercise = db.scalar(select(Exercise).where(Exercise.id == exercise_id))
    if not exercise:
        return None
    attempts = list(
        db.scalars(
            select(UserExerciseAttempt)
            .where(UserExerciseAttempt.user_id == user_id, UserExerciseAttempt.exercise_id == exercise_id)
            .order_by(desc(UserExerciseAttempt.attempted_at))
        ).all()
    )
    return {"exercise": exercise, "attempts": attempts}


def create_attempt(db: Session, exercise_id: int, user_id: int, submitted_code: str, notes: str) -> UserExerciseAttempt:
    score = 88.0 if "return" in submitted_code else 72.0
    attempt = UserExerciseAttempt(
        user_id=user_id,
        exercise_id=exercise_id,
        submitted_code=submitted_code,
        notes=notes,
        status="completed" if score >= 80 else "submitted",
        score=score,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    refresh_progress_snapshot(db, user_id)
    return attempt


def recommended_exercises(db: Session) -> list[Exercise]:
    return list(
        db.scalars(
            select(Exercise)
            .where(Exercise.category.in_(["python-refresh", "evaluation", "retrieval"]))
            .order_by(Exercise.id.asc())
            .limit(6)
        ).all()
    )

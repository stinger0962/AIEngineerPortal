from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Lesson, LessonCompletion, ProgressSnapshot, Project, UserExerciseAttempt


def refresh_progress_snapshot(db: Session, user_id: int) -> ProgressSnapshot:
    total_lessons = db.scalar(select(func.count(Lesson.id))) or 0
    completed_lessons = db.scalar(
        select(func.count(LessonCompletion.id)).where(LessonCompletion.user_id == user_id)
    ) or 0
    total_attempts = db.scalar(
        select(func.count(UserExerciseAttempt.id)).where(UserExerciseAttempt.user_id == user_id)
    ) or 0
    completed_projects = db.scalar(select(func.count(Project.id)).where(Project.status == "complete")) or 0

    learning_completion_pct = round((completed_lessons / total_lessons) * 100, 1) if total_lessons else 0.0
    interview_readiness = min(100, int((learning_completion_pct * 0.5) + (total_attempts * 2)))

    snapshot = db.scalar(
        select(ProgressSnapshot)
        .where(ProgressSnapshot.user_id == user_id)
        .order_by(ProgressSnapshot.date.desc(), ProgressSnapshot.id.desc())
    )

    if snapshot and snapshot.date == date.today():
        snapshot.learning_completion_pct = learning_completion_pct
        snapshot.python_practice_count = total_attempts
        snapshot.projects_completed_count = completed_projects
        snapshot.interview_readiness_score = interview_readiness
        snapshot.notes = "Progress updated from current activity."
    else:
        snapshot = ProgressSnapshot(
            user_id=user_id,
            date=date.today(),
            learning_completion_pct=learning_completion_pct,
            python_practice_count=total_attempts,
            projects_completed_count=completed_projects,
            interview_readiness_score=interview_readiness,
            notes="Progress updated from current activity.",
        )
        db.add(snapshot)

    db.commit()
    db.refresh(snapshot)
    return snapshot

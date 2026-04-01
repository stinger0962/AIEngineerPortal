"""Daily streak and habit tracking endpoints."""
from datetime import datetime, date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, distinct, cast, Date
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import (
    User, UserExerciseAttempt, LessonCompletion,
    InterviewQuestionPractice, AIFeedback, MemoryCard
)

router = APIRouter(prefix="/streaks", tags=["streaks"])


def _get_user_id(db: Session) -> int:
    return db.scalar(select(User.id).limit(1)) or 1


def _get_active_dates(db: Session, user_id: int, days: int = 30) -> set[date]:
    """Get all dates where user had any activity."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    dates = set()

    # Exercise attempts
    rows = db.execute(
        select(cast(UserExerciseAttempt.attempted_at, Date))
        .where(UserExerciseAttempt.user_id == user_id, UserExerciseAttempt.attempted_at >= cutoff)
        .distinct()
    ).scalars().all()
    dates.update(r for r in rows if r)

    # Lesson completions
    rows = db.execute(
        select(cast(LessonCompletion.completed_at, Date))
        .where(LessonCompletion.user_id == user_id, LessonCompletion.completed_at >= cutoff)
        .distinct()
    ).scalars().all()
    dates.update(r for r in rows if r)

    # Interview practice
    rows = db.execute(
        select(cast(InterviewQuestionPractice.practiced_at, Date))
        .where(InterviewQuestionPractice.practiced_at >= cutoff)
        .distinct()
    ).scalars().all()
    dates.update(r for r in rows if r)

    # AI feedback (any AI feature usage)
    rows = db.execute(
        select(cast(AIFeedback.created_at, Date))
        .where(AIFeedback.user_id == user_id, AIFeedback.created_at >= cutoff)
        .distinct()
    ).scalars().all()
    dates.update(r for r in rows if r)

    # Memory card reviews
    rows = db.execute(
        select(cast(MemoryCard.last_reviewed_at, Date))
        .where(MemoryCard.last_reviewed_at >= cutoff)
        .distinct()
    ).scalars().all()
    dates.update(r for r in rows if r)

    return dates


@router.get("/summary")
def get_streak_summary(db: Session = Depends(get_db)):
    user_id = _get_user_id(db)
    active_dates = _get_active_dates(db, user_id, days=90)

    today = date.today()

    # Calculate current streak
    current_streak = 0
    check_date = today
    while check_date in active_dates:
        current_streak += 1
        check_date -= timedelta(days=1)

    # If today has no activity yet, check if yesterday continues a streak
    if today not in active_dates:
        current_streak = 0
        check_date = today - timedelta(days=1)
        while check_date in active_dates:
            current_streak += 1
            check_date -= timedelta(days=1)

    # Longest streak in last 90 days
    longest_streak = 0
    temp_streak = 0
    for i in range(90, -1, -1):
        d = today - timedelta(days=i)
        if d in active_dates:
            temp_streak += 1
            longest_streak = max(longest_streak, temp_streak)
        else:
            temp_streak = 0

    # Activity this week (Mon-Sun)
    week_start = today - timedelta(days=today.weekday())
    week_dates = [week_start + timedelta(days=i) for i in range(7)]
    week_activity = [d in active_dates for d in week_dates]

    # Today's activity count
    today_exercises = db.scalar(
        select(func.count(UserExerciseAttempt.id))
        .where(UserExerciseAttempt.user_id == user_id, cast(UserExerciseAttempt.attempted_at, Date) == today)
    ) or 0

    today_reviews = db.scalar(
        select(func.count(MemoryCard.id))
        .where(cast(MemoryCard.last_reviewed_at, Date) == today)
    ) or 0

    is_active_today = today in active_dates

    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "is_active_today": is_active_today,
        "week_activity": week_activity,  # [Mon, Tue, ..., Sun] booleans
        "today_exercises": today_exercises,
        "today_reviews": today_reviews,
        "total_active_days": len(active_dates),
    }

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Exercise, JobPosting, Lesson, LessonCompletion, NewsItem, ProgressSnapshot, Project, User
from app.services.progress_service import refresh_progress_snapshot


def get_default_user(db: Session) -> User:
    return db.scalar(select(User).limit(1))


def build_dashboard_summary(db: Session) -> dict:
    user = get_default_user(db)
    snapshot = refresh_progress_snapshot(db, user.id)
    completed_ids = set(
        db.scalars(select(LessonCompletion.lesson_id).where(LessonCompletion.user_id == user.id)).all()
    )

    next_lesson = None
    for lesson in db.scalars(select(Lesson).order_by(Lesson.id.asc())).all():
        if lesson.id not in completed_ids:
            next_lesson = lesson
            break

    recommended_exercise = db.scalar(
        select(Exercise).where(Exercise.category.in_(["python-refresh", "evaluation"])).order_by(Exercise.id.asc())
    )
    active_projects = db.scalars(select(Project).where(Project.status.in_(["active", "planned"])).limit(3)).all()

    return {
        "user_name": user.name,
        "headline": "Stay in execution mode: deepen Python, ship an AI project, and turn each milestone into interview leverage.",
        "learning_streak": max(3, int(snapshot.learning_completion_pct // 5) + 1),
        "stats": [
            {"label": "Learning completion", "value": f"{snapshot.learning_completion_pct}%", "tone": "primary"},
            {"label": "Practice attempts", "value": str(snapshot.python_practice_count), "tone": "secondary"},
            {"label": "Interview readiness", "value": f"{snapshot.interview_readiness_score}/100", "tone": "accent"},
        ],
        "next_lesson": {
            "id": next_lesson.id,
            "title": next_lesson.title,
            "slug": next_lesson.slug,
            "summary": next_lesson.summary,
        }
        if next_lesson
        else None,
        "recommended_exercise": {
            "id": recommended_exercise.id,
            "title": recommended_exercise.title,
            "category": recommended_exercise.category,
            "difficulty": recommended_exercise.difficulty,
        }
        if recommended_exercise
        else None,
        "active_projects": [
            {
                "id": project.id,
                "title": project.title,
                "status": project.status,
                "portfolio_score": project.portfolio_score,
            }
            for project in active_projects
        ],
        "recommendation_panel": [
            {"title": "Close the Python fluency gap", "reason": "Core Python repetition is still the fastest unlock."},
            {"title": "Keep a project in active motion", "reason": "Portfolio evidence compounds your transition story quickly."},
            {"title": "Review one interview prompt weekly", "reason": "Converting knowledge into spoken structure is a distinct skill."},
        ],
    }


def build_today_view(db: Session) -> dict:
    snapshot = db.scalar(select(ProgressSnapshot).order_by(ProgressSnapshot.date.desc(), ProgressSnapshot.id.desc()))
    news_count = len(db.scalars(select(NewsItem.id)).all())
    job_count = len(db.scalars(select(JobPosting.id)).all())
    return {
        "focus": [
            "Complete one lesson tied to a current portfolio project.",
            "Finish a Python or evaluation exercise and note what felt slow.",
            "Review one external signal or job posting and translate it into a next action.",
        ],
        "highlights": [
            f"Learning completion is at {snapshot.learning_completion_pct}%.",
            f"Interview readiness currently scores {snapshot.interview_readiness_score}/100.",
            f"You are tracking {news_count} news items and {job_count} opportunity signals.",
        ],
        "blockers": [
            "Python depth needs continued reps under time pressure.",
            "Evaluation patterns should move from theory into repeatable practice.",
        ],
    }

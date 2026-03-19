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
    top_news = _preferred_news_signal(db)
    top_job = _preferred_job_signal(db)

    recommendation_panel = [
        {"title": "Close the Python fluency gap", "reason": "Core Python repetition is still the fastest unlock."},
        {"title": "Keep a project in active motion", "reason": "Portfolio evidence compounds your transition story quickly."},
        {"title": "Review one interview prompt weekly", "reason": "Converting knowledge into spoken structure is a distinct skill."},
    ]
    if top_news:
        recommendation_panel.append(
            {
                "title": f"{'Revisit saved signal from' if top_news.is_saved else 'React to'} {top_news.source_name}",
                "reason": _dashboard_news_reason(top_news.category, top_news.is_saved),
            }
        )
    if top_job:
        recommendation_panel.append(
            {
                "title": f"{'Use saved role from' if top_job.is_saved else 'Use'} {top_job.company_name} as a target role",
                "reason": _dashboard_job_reason(top_job.fit_score, top_job.is_saved),
            }
        )

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
        "recommendation_panel": recommendation_panel[:5],
    }


def build_today_view(db: Session) -> dict:
    snapshot = db.scalar(select(ProgressSnapshot).order_by(ProgressSnapshot.date.desc(), ProgressSnapshot.id.desc()))
    news_count = len(db.scalars(select(NewsItem.id)).all())
    job_count = len(db.scalars(select(JobPosting.id)).all())
    saved_news_count = len(db.scalars(select(NewsItem.id).where(NewsItem.is_saved.is_(True))).all())
    saved_job_count = len(db.scalars(select(JobPosting.id).where(JobPosting.is_saved.is_(True))).all())
    top_news = _preferred_news_signal(db)
    top_job = _preferred_job_signal(db)
    focus = [
        "Complete one lesson tied to a current portfolio project.",
        "Finish a Python or evaluation exercise and note what felt slow.",
        "Review one external signal or job posting and translate it into a next action.",
    ]
    if top_news:
        focus[2] = _today_news_focus(top_news.category, top_news.is_saved)
    if top_job:
        focus.append(_today_job_focus(top_job.fit_score, top_job.is_saved))
    return {
        "focus": focus[:4],
        "highlights": [
            f"Learning completion is at {snapshot.learning_completion_pct}%.",
            f"Interview readiness currently scores {snapshot.interview_readiness_score}/100.",
            f"You are tracking {news_count} news items and {job_count} opportunity signals.",
            f"You have saved {saved_news_count} news items and {saved_job_count} roles to revisit.",
        ],
        "blockers": [
            "Python depth needs continued reps under time pressure.",
            "Evaluation patterns should move from theory into repeatable practice.",
        ],
    }


def _preferred_news_signal(db: Session) -> NewsItem | None:
    saved = db.scalar(select(NewsItem).where(NewsItem.is_saved.is_(True)).order_by(NewsItem.signal_score.desc(), NewsItem.published_at.desc()))
    if saved:
        return saved
    return db.scalar(select(NewsItem).order_by(NewsItem.signal_score.desc(), NewsItem.published_at.desc()))


def _preferred_job_signal(db: Session) -> JobPosting | None:
    saved = db.scalar(select(JobPosting).where(JobPosting.is_saved.is_(True)).order_by(JobPosting.fit_score.desc(), JobPosting.published_at.desc()))
    if saved:
        return saved
    return db.scalar(select(JobPosting).order_by(JobPosting.fit_score.desc(), JobPosting.published_at.desc()))


def _dashboard_news_reason(category: str, is_saved: bool = False) -> str:
    prefix = "You saved this signal already, so " if is_saved else ""
    return {
        "model-release": f"{prefix}model movement should feed directly into which APIs, evals, and experiments you prioritize.",
        "agents": f"{prefix}agent workflow changes are a prompt to sharpen orchestration, tool use, and guardrail thinking.",
        "retrieval": f"{prefix}retrieval signals are strongest when they feed your next RAG or evaluation improvement.",
        "evaluation": f"{prefix}evaluation news is most useful when it changes how you measure and inspect your own systems.",
        "open-source": f"{prefix}tooling momentum is worth comparing against the stack choices in your active projects.",
    }.get(category, f"{prefix}use the top external signal to make one concrete learning or project decision this week.")


def _dashboard_job_reason(fit_score: int, is_saved: bool = False) -> str:
    prefix = "You marked this role as important, so " if is_saved else ""
    if fit_score >= 85:
        return f"{prefix}this is strong evidence for what your portfolio should emphasize right now."
    if fit_score >= 70:
        return f"{prefix}you are close enough that one stronger project or interview proof point could materially improve alignment."
    return f"{prefix}treat this as a market signal for what skills to strengthen before targeting similar roles."


def _today_news_focus(category: str, is_saved: bool = False) -> str:
    prefix = "Revisit the saved signal and " if is_saved else ""
    return {
        "model-release": f"{prefix}note one experiment it suggests for your stack.",
        "agents": f"{prefix}translate it into one workflow or tool-use improvement for a project.",
        "retrieval": f"{prefix}use it to improve one RAG or evaluation note today.",
        "evaluation": f"{prefix}turn it into one benchmark or review task.",
        "open-source": f"{prefix}compare it against your current project stack and write down a yes/no decision.",
    }.get(category, f"{prefix}convert it into a concrete build or learning action.")


def _today_job_focus(fit_score: int, is_saved: bool = False) -> str:
    prefix = "Use your saved role as the bar and " if is_saved else ""
    if fit_score >= 85:
        return f"{prefix}treat it as a checklist for what your current project should prove this week."
    if fit_score >= 70:
        return f"{prefix}pick one portfolio or interview gap it exposes and close it this week."
    return f"{prefix}identify which topic deserves the next focused learning sprint."

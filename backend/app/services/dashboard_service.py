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
    top_news = db.scalar(select(NewsItem).order_by(NewsItem.signal_score.desc(), NewsItem.published_at.desc()))
    top_job = db.scalar(select(JobPosting).order_by(JobPosting.fit_score.desc(), JobPosting.published_at.desc()))

    recommendation_panel = [
        {"title": "Close the Python fluency gap", "reason": "Core Python repetition is still the fastest unlock."},
        {"title": "Keep a project in active motion", "reason": "Portfolio evidence compounds your transition story quickly."},
        {"title": "Review one interview prompt weekly", "reason": "Converting knowledge into spoken structure is a distinct skill."},
    ]
    if top_news:
        recommendation_panel.append(
            {
                "title": f"React to {top_news.source_name}'s top signal",
                "reason": _dashboard_news_reason(top_news.category),
            }
        )
    if top_job:
        recommendation_panel.append(
            {
                "title": f"Use {top_job.company_name} as a target role",
                "reason": _dashboard_job_reason(top_job.fit_score),
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
    top_news = db.scalar(select(NewsItem).order_by(NewsItem.signal_score.desc(), NewsItem.published_at.desc()))
    top_job = db.scalar(select(JobPosting).order_by(JobPosting.fit_score.desc(), JobPosting.published_at.desc()))
    focus = [
        "Complete one lesson tied to a current portfolio project.",
        "Finish a Python or evaluation exercise and note what felt slow.",
        "Review one external signal or job posting and translate it into a next action.",
    ]
    if top_news:
        focus[2] = _today_news_focus(top_news.category)
    if top_job:
        focus.append(_today_job_focus(top_job.fit_score))
    return {
        "focus": focus[:4],
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


def _dashboard_news_reason(category: str) -> str:
    return {
        "model-release": "Model movement should feed directly into which APIs, evals, and experiments you prioritize.",
        "agents": "Agent workflow changes are a prompt to sharpen orchestration, tool use, and guardrail thinking.",
        "retrieval": "Retrieval signals are strongest when they feed your next RAG or evaluation improvement.",
        "evaluation": "Evaluation news is most useful when it changes how you measure and inspect your own systems.",
        "open-source": "Tooling momentum is worth comparing against the stack choices in your active projects.",
    }.get(category, "Use the top external signal to make one concrete learning or project decision this week.")


def _dashboard_job_reason(fit_score: int) -> str:
    if fit_score >= 85:
        return "This is strong evidence for what your portfolio should emphasize right now."
    if fit_score >= 70:
        return "You are close enough that one stronger project or interview proof point could materially improve alignment."
    return "Treat this as a market signal for what skills to strengthen before targeting similar roles."


def _today_news_focus(category: str) -> str:
    return {
        "model-release": "Review the top model/platform release and note one experiment it suggests for your stack.",
        "agents": "Translate the top agent signal into one workflow or tool-use improvement for a project.",
        "retrieval": "Use the top retrieval signal to improve one RAG or evaluation note today.",
        "evaluation": "Take the top evaluation signal and turn it into one benchmark or review task.",
        "open-source": "Compare the top tooling signal against your current project stack and write down a yes/no decision.",
    }.get(category, "Review one external signal and convert it into a concrete build or learning action.")


def _today_job_focus(fit_score: int) -> str:
    if fit_score >= 85:
        return "Use the top-fit role as a checklist for what your current project should prove this week."
    if fit_score >= 70:
        return "Pick one portfolio or interview gap exposed by the current best-fit role and close it this week."
    return "Use the current job board to identify which topic deserves the next focused learning sprint."

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Exercise, JobPosting, Lesson, LessonCompletion, NewsItem, ProgressSnapshot, Project, User, UserExerciseAttempt
from app.services.progress_service import refresh_progress_snapshot
from app.services.learning_service import list_paths

NEWS_TO_PATH = {
    "model-release": "llm-app-foundations",
    "agents": "ai-agents-and-tools",
    "retrieval": "rag-systems",
    "evaluation": "evaluation-and-observability",
    "open-source": "ai-deployment-and-mlops",
}

NEWS_TO_EXERCISE_CATEGORIES = {
    "model-release": ["api-async", "prompt-formatting"],
    "agents": ["prompt-formatting", "api-async"],
    "retrieval": ["retrieval", "evaluation"],
    "evaluation": ["evaluation", "retrieval"],
    "open-source": ["python-refresh", "api-async"],
}

JOB_GAP_TO_PATH = {
    "MLOps depth": "ai-deployment-and-mlops",
    "Kubernetes operations": "ai-deployment-and-mlops",
    "Deep learning breadth": "python-for-ai-engineers",
    "PyTorch practice": "python-for-ai-engineers",
    "Workflow orchestration": "ai-agents-and-tools",
    "Distributed systems depth": "ai-deployment-and-mlops",
}

JOB_GAP_TO_EXERCISE_CATEGORIES = {
    "MLOps depth": ["evaluation", "api-async"],
    "Kubernetes operations": ["api-async", "evaluation"],
    "Deep learning breadth": ["python-refresh", "data-transformation"],
    "PyTorch practice": ["python-refresh", "data-transformation"],
    "Workflow orchestration": ["prompt-formatting", "api-async"],
    "Distributed systems depth": ["api-async", "evaluation"],
}

DEFAULT_EXERCISE_CATEGORIES = ["python-refresh", "evaluation", "retrieval", "api-async", "data-transformation", "prompt-formatting"]


def get_default_user(db: Session) -> User:
    return db.scalar(select(User).limit(1))


def build_dashboard_summary(db: Session) -> dict:
    user = get_default_user(db)
    snapshot = refresh_progress_snapshot(db, user.id)
    paths = list_paths(db, user.id)
    next_lesson = _select_next_lesson(db, user.id, paths)
    recommended_exercise = _select_recommended_exercise(db, user.id)
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


def _select_next_lesson(db: Session, user_id: int, paths: list[dict]) -> Lesson | None:
    preferred_slugs = _preferred_learning_path_slugs(db)
    target = _next_unfinished_from_paths(paths, preferred_slugs)
    if not target:
        target = _next_unfinished_from_paths(paths, [path["slug"] for path in sorted(paths, key=lambda item: item["order_index"])])
    if not target:
        return None
    return db.scalar(select(Lesson).where(Lesson.slug == target["slug"]))


def _preferred_learning_path_slugs(db: Session) -> list[str]:
    slugs: list[str] = []
    news = _preferred_news_signal(db)
    if news:
        path_slug = NEWS_TO_PATH.get(news.category)
        if path_slug:
            slugs.append(path_slug)
    job = _preferred_job_signal(db)
    if job:
        for gap in job.skill_gaps_json or []:
            path_slug = JOB_GAP_TO_PATH.get(gap)
            if path_slug and path_slug not in slugs:
                slugs.append(path_slug)
    return slugs


def _next_unfinished_from_paths(paths: list[dict], path_slugs: list[str]) -> dict | None:
    for slug in path_slugs:
        path = next((item for item in paths if item["slug"] == slug), None)
        if not path:
            continue
        lesson = next((item for item in path["lessons"] if not item["is_completed"]), None)
        if lesson:
            return lesson
    return None


def _select_recommended_exercise(db: Session, user_id: int) -> Exercise | None:
    attempt_counts = {
        category: count
        for category, count in db.execute(
            select(Exercise.category, func.count(UserExerciseAttempt.id))
            .select_from(Exercise)
            .outerjoin(
                UserExerciseAttempt,
                (UserExerciseAttempt.exercise_id == Exercise.id) & (UserExerciseAttempt.user_id == user_id),
            )
            .group_by(Exercise.category)
        ).all()
    }
    attempted_exercise_ids = set(
        db.scalars(select(UserExerciseAttempt.exercise_id).where(UserExerciseAttempt.user_id == user_id)).all()
    )
    preferred_categories = _preferred_exercise_categories(db)

    candidates = db.scalars(select(Exercise).order_by(Exercise.id.asc())).all()
    ranked = sorted(
        candidates,
        key=lambda exercise: (
            attempt_counts.get(exercise.category, 0),
            _category_priority(exercise.category, preferred_categories),
            1 if exercise.id in attempted_exercise_ids else 0,
            exercise.id,
        ),
    )
    return ranked[0] if ranked else None


def _preferred_exercise_categories(db: Session) -> list[str]:
    categories: list[str] = []
    news = _preferred_news_signal(db)
    if news:
        for category in NEWS_TO_EXERCISE_CATEGORIES.get(news.category, []):
            if category not in categories:
                categories.append(category)
    job = _preferred_job_signal(db)
    if job:
        for gap in job.skill_gaps_json or []:
            for category in JOB_GAP_TO_EXERCISE_CATEGORIES.get(gap, []):
                if category not in categories:
                    categories.append(category)
    for category in DEFAULT_EXERCISE_CATEGORIES:
        if category not in categories:
            categories.append(category)
    return categories


def _category_priority(category: str, preferred_categories: list[str]) -> int:
    try:
        return preferred_categories.index(category)
    except ValueError:
        return len(preferred_categories) + 1


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
    return {
        "model-release": "Revisit the saved signal and note one experiment it suggests for your stack."
        if is_saved
        else "Review the top model or platform release and note one experiment it suggests for your stack.",
        "agents": "Revisit the saved signal and translate it into one workflow or tool-use improvement for a project."
        if is_saved
        else "Translate the top agent signal into one workflow or tool-use improvement for a project.",
        "retrieval": "Revisit the saved signal and use it to improve one RAG or evaluation note today."
        if is_saved
        else "Use the top retrieval signal to improve one RAG or evaluation note today.",
        "evaluation": "Revisit the saved signal and turn it into one benchmark or review task."
        if is_saved
        else "Take the top evaluation signal and turn it into one benchmark or review task.",
        "open-source": "Revisit the saved signal and compare it against your current project stack before making a yes or no decision."
        if is_saved
        else "Compare the top tooling signal against your current project stack and write down a yes or no decision.",
    }.get(
        category,
        "Revisit the saved signal and convert it into a concrete build or learning action."
        if is_saved
        else "Review one external signal and convert it into a concrete build or learning action.",
    )


def _today_job_focus(fit_score: int, is_saved: bool = False) -> str:
    if fit_score >= 85:
        return (
            "Use your saved role as the bar and treat it as a checklist for what your current project should prove this week."
            if is_saved
            else "Use the top-fit role as a checklist for what your current project should prove this week."
        )
    if fit_score >= 70:
        return (
            "Use your saved role as the bar and pick one portfolio or interview gap it exposes to close this week."
            if is_saved
            else "Pick one portfolio or interview gap exposed by the current best-fit role and close it this week."
        )
    return (
        "Use your saved role as the bar and identify which topic deserves the next focused learning sprint."
        if is_saved
        else "Use the current job board to identify which topic deserves the next focused learning sprint."
    )

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ProgressSnapshot, Project, User
from app.services.learning_service import list_paths
from app.services.dashboard_service import build_dashboard_summary
from app.services.jobs_service import build_job_fit_summary, list_jobs
from app.services.news_service import build_news_why_it_matters, list_news


NEWS_ACTION_MAP = {
    "model-release": (
        "Turn the latest model signal into stack decisions",
        "/learn/llm-app-foundations",
    ),
    "agents": (
        "Translate agent movement into workflow design practice",
        "/learn/ai-agents-and-tools",
    ),
    "retrieval": (
        "Use retrieval signals to sharpen your RAG plan",
        "/learn/rag-systems",
    ),
    "evaluation": (
        "Fold the latest evaluation signal into your measurement habits",
        "/learn/evaluation-and-observability",
    ),
    "open-source": (
        "Review tooling momentum against your active project stack",
        "/projects",
    ),
}

JOB_GAP_ACTION_MAP = {
    "MLOps depth": "/learn/ai-deployment-and-mlops",
    "Kubernetes operations": "/learn/ai-deployment-and-mlops",
    "Deep learning breadth": "/learn/python-for-ai-engineers",
    "PyTorch practice": "/learn/python-for-ai-engineers",
    "Workflow orchestration": "/learn/ai-agents-and-tools",
    "Distributed systems depth": "/learn/ai-deployment-and-mlops",
}

 

def next_actions(db: Session) -> list[dict]:
    user = db.scalar(select(User).limit(1))
    summary = build_dashboard_summary(db)
    lesson = summary["next_lesson"]
    exercise = summary["recommended_exercise"]
    paths = list_paths(db, user.id) if user else []
    snapshot = _latest_progress_snapshot(db, user.id) if user else None
    project_action = _project_or_interview_action(db, snapshot)
    recommendations = [
        {
            "title": "Advance the next learning milestone",
            "reason": f"Your next lesson is {lesson['title']} and will keep momentum high.",
            "action_path": f"/learn/lesson/{lesson['slug']}",
            "source_kind": "learning",
        },
        {
            "title": "Strengthen implementation fluency",
            "reason": f"Practice {exercise['category']} through {exercise['title']}.",
            "action_path": "/practice/python",
            "source_kind": "practice",
        },
        {
            "title": project_action["title"],
            "reason": project_action["reason"],
            "action_path": project_action["action_path"],
            "source_kind": project_action["source_kind"],
        },
    ]

    news, is_saved_news = _preferred_news_item(db)
    if news:
        news_title, news_path, news_reason = _news_action_target(news.category, paths, is_saved_news)
        recommendations.append(
            {
                "title": news_title,
                "reason": f"{build_news_why_it_matters(news)} {news_reason}",
                "action_path": news_path,
                "source_kind": "news",
            }
        )

    job, is_saved_job = _preferred_job_item(db)
    if job:
        job_title, job_path, job_reason = _job_action_target(job, paths, is_saved_job)
        recommendations.append(
            {
                "title": job_title,
                "reason": job_reason,
                "action_path": job_path,
                "source_kind": "jobs",
            }
        )

    return recommendations


def _latest_progress_snapshot(db: Session, user_id: int) -> ProgressSnapshot | None:
    return db.scalar(
        select(ProgressSnapshot)
        .where(ProgressSnapshot.user_id == user_id)
        .order_by(ProgressSnapshot.date.desc(), ProgressSnapshot.id.desc())
    )


def _project_or_interview_action(db: Session, snapshot: ProgressSnapshot | None) -> dict:
    completed_projects = db.scalars(
        select(Project).where(Project.status == "complete").order_by(Project.portfolio_score.desc(), Project.id.asc())
    ).all()
    active_projects = db.scalars(
        select(Project).where(Project.status.in_(["active", "planned"])).order_by(Project.portfolio_score.desc(), Project.id.asc())
    ).all()
    readiness = snapshot.interview_readiness_score if snapshot else 0

    if not completed_projects:
        target = active_projects[0] if active_projects else None
        return {
            "title": "Convert project work into interview leverage",
            "reason": (
                f"Push {target.title} toward a finished, interview-ready story with clearer architecture decisions and metrics."
                if target
                else "Finish one project far enough that it becomes a credible interview story, not just a draft."
            ),
            "action_path": f"/projects/{target.slug}" if target else "/projects",
            "source_kind": "projects",
        }

    if readiness < 45:
        return {
            "title": "Turn completed work into interview reps",
            "reason": (
                f"You already have {len(completed_projects)} completed project proof point(s). The weaker gap is explaining them clearly under interview pressure."
            ),
            "action_path": "/interview",
            "source_kind": "interview",
        }

    if active_projects:
        target = active_projects[0]
        return {
            "title": "Keep one portfolio artifact improving",
            "reason": f"{target.title} is active, so tighten one metric, architecture note, or demo-quality workflow this week.",
            "action_path": f"/projects/{target.slug}",
            "source_kind": "projects",
        }

    return {
        "title": "Compound interview readiness with sharper stories",
        "reason": "Project proof exists now, so the highest-value move is sharpening system design and behavioral explanations.",
        "action_path": "/interview",
        "source_kind": "interview",
    }


def _preferred_news_item(db: Session):
    saved_news = list_news(db, saved_only=True)
    if saved_news:
        return saved_news[0], True
    top_news = list_news(db)[:1]
    return (top_news[0], False) if top_news else (None, False)


def _preferred_job_item(db: Session):
    saved_jobs = list_jobs(db, saved_only=True)
    if saved_jobs:
        return saved_jobs[0], True
    top_jobs = list_jobs(db, min_fit_score=60)[:1]
    return (top_jobs[0], False) if top_jobs else (None, False)


def _news_action_target(category: str, paths: list[dict], is_saved: bool = False) -> tuple[str, str, str]:
    default_title, default_path = NEWS_ACTION_MAP.get(category, ("Review one external AI signal", "/news"))
    suggested_path = _best_learning_target_for_news(category, paths)
    if suggested_path:
        title = "Act on a saved AI signal" if is_saved else default_title
        reason = f"You already flagged this signal. {suggested_path['reason']}" if is_saved else suggested_path["reason"]
        return title, suggested_path["action_path"], reason
    if default_path.startswith("/learn/"):
        reason = "You saved this signal, so convert it into one learning decision before it goes stale." if is_saved else "Use this signal to deepen the matching learning path before it becomes background noise."
        return ("Act on a saved AI signal" if is_saved else default_title), default_path, reason
    reason = "You saved this signal, so translate it into one concrete project or interview move this week." if is_saved else "Use this signal to make one clear project or learning decision this week."
    return ("Act on a saved AI signal" if is_saved else default_title), default_path, reason


def _job_action_target(job, paths: list[dict], is_saved: bool = False) -> tuple[str, str, str]:
    if job.fit_score >= 85:
        return (
            "Turn your saved target role into portfolio proof" if is_saved else "Use a strong-fit role to sharpen portfolio proof",
            "/projects",
            f"{build_job_fit_summary(job)} {'You saved this role, so ' if is_saved else ''}Update one active project so it clearly mirrors the system shape {job.company_name} is hiring for.",
        )
    if job.skill_gaps_json:
        top_gap = job.skill_gaps_json[0]
        learning_target = _best_learning_target_for_gap(top_gap, paths)
        return (
            "Close the top gap for your saved role" if is_saved else "Turn a job gap into a focused learning sprint",
            learning_target["action_path"] if learning_target else JOB_GAP_ACTION_MAP.get(top_gap, "/learn"),
            f"{build_job_fit_summary(job)} {'Because you saved this role, ' if is_saved else 'The '}clearest next move is to close {top_gap} with one targeted lesson or implementation task.",
        )
    return (
        "Use your saved role to tighten interview positioning" if is_saved else "Use this role to tighten interview positioning",
        "/interview",
        f"{build_job_fit_summary(job)} {'You saved it, so ' if is_saved else 'Treat '}this role as an interview calibration target and practice explaining your overlap clearly.",
    )


def _best_learning_target_for_news(category: str, paths: list[dict]) -> dict | None:
    category_to_path = {
        "model-release": "llm-app-foundations",
        "agents": "ai-agents-and-tools",
        "retrieval": "rag-systems",
        "evaluation": "evaluation-and-observability",
        "open-source": "ai-deployment-and-mlops",
    }
    return _next_unfinished_path_target(category_to_path.get(category), paths)


def _best_learning_target_for_gap(gap: str, paths: list[dict]) -> dict | None:
    path_slug = {
        "MLOps depth": "ai-deployment-and-mlops",
        "Kubernetes operations": "ai-deployment-and-mlops",
        "Deep learning breadth": "python-for-ai-engineers",
        "PyTorch practice": "python-for-ai-engineers",
        "Workflow orchestration": "ai-agents-and-tools",
        "Distributed systems depth": "ai-deployment-and-mlops",
    }.get(gap)
    return _next_unfinished_path_target(path_slug, paths)


def _next_unfinished_path_target(path_slug: str | None, paths: list[dict]) -> dict | None:
    if not path_slug:
        return None
    path = next((item for item in paths if item["slug"] == path_slug), None)
    if not path:
        return None
    next_lesson = next((lesson for lesson in path["lessons"] if not lesson["is_completed"]), None)
    if next_lesson:
        return {
            "action_path": f"/learn/lesson/{next_lesson['slug']}",
            "reason": f"The next unfinished lesson in {path['title']} is {next_lesson['title']}.",
        }
    return {
        "action_path": f"/learn/{path_slug}",
        "reason": f"Review {path['title']} and convert it into a project or interview proof point.",
    }

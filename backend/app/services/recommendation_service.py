from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
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
            "title": "Convert project work into interview leverage",
            "reason": "Update one project with concrete architecture decisions and metrics.",
            "action_path": "/projects",
            "source_kind": "projects",
        },
    ]

    top_news = list_news(db)[:1]
    if top_news:
        news = top_news[0]
        news_title, news_path, news_reason = _news_action_target(news.category, paths)
        recommendations.append(
            {
                "title": news_title,
                "reason": f"{build_news_why_it_matters(news)} {news_reason}",
                "action_path": news_path,
                "source_kind": "news",
            }
        )

    top_jobs = list_jobs(db, min_fit_score=60)[:1]
    if top_jobs:
        job = top_jobs[0]
        job_title, job_path, job_reason = _job_action_target(job, paths)
        recommendations.append(
            {
                "title": job_title,
                "reason": job_reason,
                "action_path": job_path,
                "source_kind": "jobs",
            }
        )

    return recommendations


def _news_action_target(category: str, paths: list[dict]) -> tuple[str, str, str]:
    default_title, default_path = NEWS_ACTION_MAP.get(category, ("Review one external AI signal", "/news"))
    suggested_path = _best_learning_target_for_news(category, paths)
    if suggested_path:
        return default_title, suggested_path["action_path"], suggested_path["reason"]
    if default_path.startswith("/learn/"):
        return default_title, default_path, "Use this signal to deepen the matching learning path before it becomes background noise."
    return default_title, default_path, "Use this signal to make one clear project or learning decision this week."


def _job_action_target(job, paths: list[dict]) -> tuple[str, str, str]:
    if job.fit_score >= 85:
        return (
            "Use a strong-fit role to sharpen portfolio proof",
            "/projects",
            f"{build_job_fit_summary(job)} Update one active project so it clearly mirrors the system shape {job.company_name} is hiring for.",
        )
    if job.skill_gaps_json:
        top_gap = job.skill_gaps_json[0]
        learning_target = _best_learning_target_for_gap(top_gap, paths)
        return (
            "Turn a job gap into a focused learning sprint",
            learning_target["action_path"] if learning_target else JOB_GAP_ACTION_MAP.get(top_gap, "/learn"),
            f"{build_job_fit_summary(job)} The clearest next move is to close {top_gap} with one targeted lesson or implementation task.",
        )
    return (
        "Use this role to tighten interview positioning",
        "/interview",
        f"{build_job_fit_summary(job)} Treat this role as an interview calibration target and practice explaining your overlap clearly.",
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

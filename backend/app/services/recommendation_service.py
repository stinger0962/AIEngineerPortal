from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.dashboard_service import build_dashboard_summary
from app.services.jobs_service import build_job_fit_summary, list_jobs
from app.services.news_service import build_news_why_it_matters, list_news

 

def next_actions(db: Session) -> list[dict]:
    summary = build_dashboard_summary(db)
    lesson = summary["next_lesson"]
    exercise = summary["recommended_exercise"]
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
        recommendations.append(
            {
                "title": "Review one external AI signal",
                "reason": build_news_why_it_matters(top_news[0]),
                "action_path": "/news",
                "source_kind": "news",
            }
        )

    top_jobs = list_jobs(db, min_fit_score=60)[:1]
    if top_jobs:
        recommendations.append(
            {
                "title": "Keep one relevant job in view",
                "reason": build_job_fit_summary(top_jobs[0]),
                "action_path": "/jobs",
                "source_kind": "jobs",
            }
        )

    return recommendations

from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.dashboard_service import build_dashboard_summary
from app.services.jobs_service import list_jobs
from app.services.news_service import list_news

 

def next_actions(db: Session) -> list[dict]:
    summary = build_dashboard_summary(db)
    lesson = summary["next_lesson"]
    exercise = summary["recommended_exercise"]
    recommendations = [
        {
            "title": "Advance the next learning milestone",
            "reason": f"Your next lesson is {lesson['title']} and will keep momentum high.",
            "action_path": f"/learn/lesson/{lesson['slug']}",
        },
        {
            "title": "Strengthen implementation fluency",
            "reason": f"Practice {exercise['category']} through {exercise['title']}.",
            "action_path": "/practice/python",
        },
        {
            "title": "Convert project work into interview leverage",
            "reason": "Update one project with concrete architecture decisions and metrics.",
            "action_path": "/projects",
        },
    ]

    top_news = list_news(db)[:1]
    if top_news:
        recommendations.append(
            {
                "title": "Review one external AI signal",
                "reason": f"{top_news[0].source_name} has a high-signal update worth translating into practice.",
                "action_path": "/news",
            }
        )

    top_jobs = list_jobs(db, min_fit_score=60)[:1]
    if top_jobs:
        recommendations.append(
            {
                "title": "Keep one relevant job in view",
                "reason": f"{top_jobs[0].company_name} has a role with a current fit score of {top_jobs[0].fit_score}.",
                "action_path": "/jobs",
            }
        )

    return recommendations

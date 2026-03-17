from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.dashboard_service import build_dashboard_summary


def next_actions(db: Session) -> list[dict]:
    summary = build_dashboard_summary(db)
    lesson = summary["next_lesson"]
    exercise = summary["recommended_exercise"]
    return [
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

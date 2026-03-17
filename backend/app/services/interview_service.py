from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import InterviewQuestion


def list_questions(db: Session, category: str | None = None) -> list[InterviewQuestion]:
    query = select(InterviewQuestion)
    if category:
        query = query.where(InterviewQuestion.category == category)
    return list(db.scalars(query.order_by(InterviewQuestion.category.asc(), InterviewQuestion.id.asc())).all())


def build_roadmap() -> dict:
    return {
        "focus_areas": [
            "Python fluency under interview pressure",
            "LLM system design and tradeoffs",
            "RAG retrieval and evaluation debugging",
            "Behavioral stories for the transition narrative",
        ],
        "weekly_plan": [
            "Monday: one Python drill and one architecture note",
            "Wednesday: one RAG or evaluation mock question",
            "Friday: rehearse one behavioral and one system design answer",
        ],
    }

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import KnowledgeArticle


def list_articles(db: Session, category: str | None = None, search: str | None = None) -> list[KnowledgeArticle]:
    query = select(KnowledgeArticle)
    if category:
        query = query.where(KnowledgeArticle.category == category)
    if search:
        query = query.where(KnowledgeArticle.title.ilike(f"%{search}%"))
    return list(db.scalars(query.order_by(KnowledgeArticle.title.asc())).all())


def get_article_by_slug(db: Session, slug: str) -> KnowledgeArticle | None:
    return db.scalar(select(KnowledgeArticle).where(KnowledgeArticle.slug == slug))

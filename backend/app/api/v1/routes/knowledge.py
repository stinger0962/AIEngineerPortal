from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import KnowledgeArticleOut
from app.services.knowledge_service import get_article_by_slug, list_articles

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("", response_model=List[KnowledgeArticleOut])
def get_articles(
    category: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> List[KnowledgeArticleOut]:
    return [KnowledgeArticleOut.model_validate(article) for article in list_articles(db, category, search)]


@router.get("/search", response_model=List[KnowledgeArticleOut])
def search_articles(query: str = Query(default=""), db: Session = Depends(get_db)) -> List[KnowledgeArticleOut]:
    return [KnowledgeArticleOut.model_validate(article) for article in list_articles(db, search=query)]


@router.get("/{slug}", response_model=KnowledgeArticleOut)
def get_article(slug: str, db: Session = Depends(get_db)) -> KnowledgeArticleOut:
    article = get_article_by_slug(db, slug)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return KnowledgeArticleOut.model_validate(article)

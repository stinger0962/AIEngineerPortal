from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import NewsItemOut
from app.services.news_service import get_news_item, list_news, refresh_news, set_news_saved

router = APIRouter(prefix="/news", tags=["news"])


@router.get("", response_model=List[NewsItemOut])
def get_news(
    category: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    saved_only: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> List[NewsItemOut]:
    return [NewsItemOut.model_validate(item) for item in list_news(db, category, search, saved_only)]


@router.post("/refresh", response_model=List[NewsItemOut])
def refresh_news_feed(db: Session = Depends(get_db)) -> List[NewsItemOut]:
    return [NewsItemOut.model_validate(item) for item in refresh_news(db)]


@router.post("/{news_id}/save", response_model=NewsItemOut)
def save_news_item(news_id: int, db: Session = Depends(get_db)) -> NewsItemOut:
    item = set_news_saved(db, news_id, True)
    if not item:
        raise HTTPException(status_code=404, detail="News item not found")
    return NewsItemOut.model_validate(item)


@router.get("/{news_id}", response_model=NewsItemOut)
def get_news_by_id(news_id: int, db: Session = Depends(get_db)) -> NewsItemOut:
    item = get_news_item(db, news_id)
    if not item:
        raise HTTPException(status_code=404, detail="News item not found")
    return NewsItemOut.model_validate(item)

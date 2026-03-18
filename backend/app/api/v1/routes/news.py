from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import FeedRefreshMetaOut, NewsItemOut
from app.services.news_service import (
    get_news_item,
    get_news_refresh_meta,
    list_news,
    refresh_news,
    refresh_news_if_stale,
    set_news_saved,
)

router = APIRouter(prefix="/news", tags=["news"])


@router.get("", response_model=List[NewsItemOut])
def get_news(
    category: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    saved_only: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> List[NewsItemOut]:
    if not category and not search and not saved_only:
        items = refresh_news_if_stale(db)
    else:
        items = list_news(db, category, search, saved_only)
    return [NewsItemOut.model_validate(item) for item in items]


@router.post("/refresh", response_model=List[NewsItemOut])
def refresh_news_feed(db: Session = Depends(get_db)) -> List[NewsItemOut]:
    return [NewsItemOut.model_validate(item) for item in refresh_news(db)]


@router.get("/meta", response_model=FeedRefreshMetaOut)
def get_news_meta(db: Session = Depends(get_db)) -> FeedRefreshMetaOut:
    refresh_news_if_stale(db)
    return FeedRefreshMetaOut(**get_news_refresh_meta(db))


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

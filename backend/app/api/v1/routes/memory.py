"""Memory card spaced repetition endpoints."""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import MemoryCard

router = APIRouter(prefix="/memory", tags=["memory"])


class ReviewRequest(BaseModel):
    confidence: int  # 1-5


class ReviewResponse(BaseModel):
    card_id: int
    confidence: int
    reviewed_at: str


def _next_review_date(confidence: int, review_count: int) -> datetime:
    """SM-2 inspired: higher confidence = longer interval, repeated success doubles."""
    base_days = {1: 1, 2: 1, 3: 3, 4: 7, 5: 14}
    days = base_days.get(confidence, 1)
    # Double interval for each successive strong review (confidence >= 4)
    if confidence >= 4 and review_count > 1:
        multiplier = min(2 ** (review_count // 3), 8)  # Cap at 8x
        days *= multiplier
    return datetime.utcnow() + timedelta(days=days)


@router.get("/cards")
def list_memory_cards(
    due_only: bool = False,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = select(MemoryCard).order_by(MemoryCard.next_review_at.asc().nullsfirst(), MemoryCard.id)

    if due_only:
        now = datetime.utcnow()
        query = query.where(
            (MemoryCard.next_review_at == None) | (MemoryCard.next_review_at <= now)
        )

    if category:
        query = query.where(MemoryCard.category == category)

    cards = list(db.scalars(query).all())

    return [
        {
            "id": c.id,
            "front_md": c.front_md,
            "back_md": c.back_md,
            "category": c.category,
            "source_kind": c.source_kind,
            "source_title": c.source_title,
            "difficulty": c.difficulty,
            "tags_json": c.tags_json or [],
            "review_count": c.review_count,
            "last_reviewed_at": c.last_reviewed_at.isoformat() if c.last_reviewed_at else None,
            "confidence": c.confidence,
            "next_review_at": c.next_review_at.isoformat() if c.next_review_at else None,
        }
        for c in cards
    ]


@router.post("/cards/{card_id}/review")
def review_memory_card(
    card_id: int,
    payload: ReviewRequest,
    db: Session = Depends(get_db),
):
    card = db.get(MemoryCard, card_id)
    if not card:
        raise HTTPException(404, "Card not found")

    if not 1 <= payload.confidence <= 5:
        raise HTTPException(400, "Confidence must be 1-5")

    now = datetime.utcnow()
    card.confidence = payload.confidence
    card.review_count += 1
    card.last_reviewed_at = now
    card.next_review_at = _next_review_date(payload.confidence, card.review_count)

    db.commit()

    return ReviewResponse(
        card_id=card.id,
        confidence=payload.confidence,
        reviewed_at=now.isoformat(),
    )

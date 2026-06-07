"""Summary generation routes (SSE generate + list + delete)."""
from __future__ import annotations

import json
import logging
from typing import AsyncGenerator, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import Summary
from app.services.ingestion_service import ingest
from app.services.summary_service import generate_summary

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/summary", tags=["summary"])

VALID_SOURCE_TYPES = {"text", "web", "youtube"}


class SummaryRequest(BaseModel):
    source_type: str
    value: str


class SummaryOut(BaseModel):
    id: int
    source_type: str
    source_url: Optional[str]
    title: str
    tldr: str
    key_points: List[str]
    takeaways: List[str]
    char_count: int
    created_at: str


def _to_out(s: Summary) -> dict:
    return {
        "id": s.id,
        "source_type": s.source_type,
        "source_url": s.source_url,
        "title": s.title,
        "tldr": s.tldr,
        "key_points": s.key_points or [],
        "takeaways": s.takeaways or [],
        "char_count": s.char_count,
        "created_at": s.created_at.isoformat(),
    }


@router.post("/generate")
async def generate(payload: SummaryRequest, db: Session = Depends(get_db)):
    if payload.source_type not in VALID_SOURCE_TYPES:
        raise HTTPException(status_code=422, detail="Invalid source_type")
    if not payload.value or not payload.value.strip():
        raise HTTPException(status_code=422, detail="value is required")

    settings = get_settings()

    async def event_stream() -> AsyncGenerator[dict, None]:
        try:
            yield {"data": json.dumps({"status": "fetching", "message": "Fetching content..."})}
            title, text = ingest(payload.source_type, payload.value)

            yield {"data": json.dumps({"status": "summarizing", "message": "Summarizing with Claude..."})}
            result = generate_summary(text, settings.anthropic_api_key, settings.ai_model)

            final_title = title or result["title"] or "未命名摘要"
            source_url = payload.value if payload.source_type in ("web", "youtube") else None

            summary = Summary(
                source_type=payload.source_type,
                source_url=source_url,
                title=final_title,
                tldr=result["tldr"],
                key_points=result["key_points"],
                takeaways=result["takeaways"],
                char_count=len(text),
            )
            db.add(summary)
            db.commit()
            db.refresh(summary)

            yield {"data": json.dumps({"status": "done", "summary": _to_out(summary)})}

        except ValueError as exc:
            db.rollback()
            logger.warning("Summary error: %s", exc)
            yield {"data": json.dumps({"status": "error", "message": str(exc)})}
        except Exception:
            db.rollback()
            logger.exception("Unexpected summary error")
            yield {"data": json.dumps({"status": "error", "message": "Could not generate summary — please try again."})}

    return EventSourceResponse(event_stream())


@router.get("/list", response_model=List[SummaryOut])
def list_summaries(db: Session = Depends(get_db)):
    rows = db.scalars(select(Summary).order_by(Summary.created_at.desc())).all()
    return [SummaryOut(**_to_out(s)) for s in rows]


@router.delete("/{summary_id}", status_code=204)
def delete_summary(summary_id: int, db: Session = Depends(get_db)):
    s = db.get(Summary, summary_id)
    if not s:
        raise HTTPException(status_code=404, detail="Summary not found")
    db.delete(s)
    db.commit()

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
from app.services.mindmap_service import generate_mindmap
from app.services.summary_service import generate_summary

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/summary", tags=["summary"])

VALID_SOURCE_TYPES = {"text", "web", "youtube"}
VALID_OUTPUT_TYPES = {"summary", "mindmap"}


class SummaryRequest(BaseModel):
    source_type: str
    value: str
    output_type: str = "summary"  # summary | mindmap


class Section(BaseModel):
    heading: str
    points: List[str]


class SummaryOut(BaseModel):
    id: int
    source_type: str
    source_url: Optional[str]
    title: str
    tldr: str
    sections: List[Section]
    char_count: int
    created_at: str
    output_type: str
    mindmap_md: Optional[str]


def _sections_for(s: Summary) -> list:
    if s.sections:
        return s.sections
    legacy = []
    if s.key_points:
        legacy.append({"heading": "关键要点", "points": s.key_points})
    if s.takeaways:
        legacy.append({"heading": "核心收获", "points": s.takeaways})
    return legacy


def _to_out(s: Summary) -> dict:
    return {
        "id": s.id,
        "source_type": s.source_type,
        "source_url": s.source_url,
        "title": s.title,
        "tldr": s.tldr,
        "sections": _sections_for(s),
        "char_count": s.char_count,
        "created_at": s.created_at.isoformat(),
        "output_type": s.output_type,
        "mindmap_md": s.mindmap_md,
    }


@router.post("/generate")
async def generate(payload: SummaryRequest, db: Session = Depends(get_db)):
    if payload.source_type not in VALID_SOURCE_TYPES:
        raise HTTPException(status_code=422, detail="Invalid source_type")
    if not payload.value or not payload.value.strip():
        raise HTTPException(status_code=422, detail="value is required")
    if payload.output_type not in VALID_OUTPUT_TYPES:
        raise HTTPException(status_code=422, detail="Invalid output_type")

    settings = get_settings()

    async def event_stream() -> AsyncGenerator[dict, None]:
        try:
            yield {"data": json.dumps({"status": "fetching", "message": "Fetching content..."})}
            title, text = ingest(payload.source_type, payload.value)
            source_url = payload.value if payload.source_type in ("web", "youtube") else None

            if payload.output_type == "mindmap":
                yield {"data": json.dumps({"status": "mapping", "message": "Building mind map..."})}
                mm = generate_mindmap(text, settings.anthropic_api_key, settings.ai_model)
                item = Summary(
                    source_type=payload.source_type,
                    source_url=source_url,
                    title=(title or mm["title"] or "思维导图"),
                    tldr="",
                    key_points=[],
                    takeaways=[],
                    sections=[],
                    output_type="mindmap",
                    mindmap_md=mm["markdown"],
                    char_count=len(text),
                )
            else:
                yield {"data": json.dumps({"status": "summarizing", "message": "Summarizing with Claude..."})}
                result = generate_summary(text, settings.anthropic_api_key, settings.ai_model)
                item = Summary(
                    source_type=payload.source_type,
                    source_url=source_url,
                    title=(title or result["title"] or "未命名摘要"),
                    tldr=result["tldr"],
                    key_points=[],
                    takeaways=[],
                    sections=result["sections"],
                    output_type="summary",
                    mindmap_md=None,
                    char_count=len(text),
                )

            db.add(item)
            db.commit()
            db.refresh(item)

            yield {"data": json.dumps({"status": "done", "summary": _to_out(item)})}

        except ValueError as exc:
            db.rollback()
            logger.warning("Loom generation error: %s", exc)
            yield {"data": json.dumps({"status": "error", "message": str(exc)})}
        except Exception:
            db.rollback()
            logger.exception("Unexpected Loom generation error")
            yield {"data": json.dumps({"status": "error", "message": "Generation failed — please try again."})}

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

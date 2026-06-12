"""录 Scribe routes: SSE transcribe + list + delete + download."""
from __future__ import annotations

import json
import logging
import tempfile
from typing import AsyncGenerator, List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import ScribeTranscript
from app.services.podcast_service import validate_youtube_url
from app.services.scribe_service import download_audio, transcribe_audio

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scribe", tags=["scribe"])


class ScribeRequest(BaseModel):
    youtube_url: str


class ScribeOut(BaseModel):
    id: int
    youtube_url: str
    title: str
    transcript: str
    char_count: int
    created_at: str


def _to_out(s: ScribeTranscript) -> dict:
    return {
        "id": s.id,
        "youtube_url": s.youtube_url,
        "title": s.title,
        "transcript": s.transcript,
        "char_count": s.char_count,
        "created_at": s.created_at.isoformat(),
    }


@router.post("/generate")
async def generate(payload: ScribeRequest, db: Session = Depends(get_db)):
    if not validate_youtube_url(payload.youtube_url):
        raise HTTPException(status_code=422, detail="Invalid YouTube URL")

    settings = get_settings()

    async def event_stream() -> AsyncGenerator[dict, None]:
        try:
            with tempfile.TemporaryDirectory() as tmp:
                yield {"data": json.dumps({"status": "downloading", "message": "Downloading audio..."})}
                title, audio_path = download_audio(payload.youtube_url, tmp)

                yield {"data": json.dumps({"status": "transcribing", "message": "Transcribing with Whisper..."})}
                transcript = transcribe_audio(audio_path, settings.openai_api_key)

            item = ScribeTranscript(
                youtube_url=payload.youtube_url,
                title=title,
                transcript=transcript,
                char_count=len(transcript),
            )
            db.add(item)
            db.commit()
            db.refresh(item)

            yield {"data": json.dumps({"status": "done", "item": _to_out(item)})}

        except ValueError as exc:
            db.rollback()
            logger.warning("Scribe error: %s", exc)
            yield {"data": json.dumps({"status": "error", "message": str(exc)})}
        except Exception:
            db.rollback()
            logger.exception("Unexpected scribe error")
            yield {"data": json.dumps({"status": "error", "message": "转写失败，请稍后重试。"})}

    return EventSourceResponse(event_stream())


@router.get("/list", response_model=List[ScribeOut])
def list_items(db: Session = Depends(get_db)):
    rows = db.scalars(select(ScribeTranscript).order_by(ScribeTranscript.created_at.desc())).all()
    return [ScribeOut(**_to_out(s)) for s in rows]


@router.delete("/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    s = db.get(ScribeTranscript, item_id)
    if not s:
        raise HTTPException(status_code=404, detail="Transcript not found")
    db.delete(s)
    db.commit()


@router.get("/{item_id}/download")
def download_item(item_id: int, db: Session = Depends(get_db)):
    s = db.get(ScribeTranscript, item_id)
    if not s:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return PlainTextResponse(
        s.transcript,
        headers={"Content-Disposition": f'attachment; filename="scribe-{item_id}.txt"'},
    )

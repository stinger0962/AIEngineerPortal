"""配 Dub routes: SSE generate + list + delete + video."""
from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path
from typing import AsyncGenerator, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import DubVideo
from app.services.podcast_service import validate_youtube_url, resolve_voice
from app.services.dub_service import (
    probe_duration, download_video, extract_segments,
    translate_segments, build_voice_track, compose, _ensure_dir,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dub", tags=["dub"])


class DubRequest(BaseModel):
    youtube_url: str
    voice_id: Optional[str] = None


class DubOut(BaseModel):
    id: int
    youtube_url: str
    title: str
    voice_id: str
    duration_secs: Optional[int]
    created_at: str


def _to_out(d: DubVideo) -> dict:
    return {
        "id": d.id,
        "youtube_url": d.youtube_url,
        "title": d.title,
        "voice_id": d.voice_id,
        "duration_secs": d.duration_secs,
        "created_at": d.created_at.isoformat(),
    }


@router.post("/generate")
async def generate(payload: DubRequest, db: Session = Depends(get_db)):
    if not validate_youtube_url(payload.youtube_url):
        raise HTTPException(status_code=422, detail="Invalid YouTube URL")

    settings = get_settings()

    async def event_stream() -> AsyncGenerator[dict, None]:
        try:
            yield {"data": json.dumps({"status": "downloading", "message": "下载视频中..."})}
            dur_s = probe_duration(payload.youtube_url)

            with tempfile.TemporaryDirectory() as tmp:
                title, video_path = download_video(payload.youtube_url, tmp)

                yield {"data": json.dumps({"status": "transcribing", "message": "转写中..."})}
                segments = extract_segments(video_path, settings.openai_api_key)

                yield {"data": json.dumps({"status": "translating", "message": "翻译中..."})}
                zh = translate_segments(segments, settings.anthropic_api_key, settings.ai_model)

                yield {"data": json.dumps({"status": "voicing", "message": "配音中..."})}
                voice_id = resolve_voice(payload.voice_id)
                voice_track = build_voice_track(
                    segments, zh, voice_id,
                    settings.minimax_api_key, settings.minimax_group_id,
                    settings.minimax_model, settings.minimax_api_base,
                    dur_s * 1000,
                )

                yield {"data": json.dumps({"status": "composing", "message": "合成视频中..."})}
                item = DubVideo(
                    youtube_url=payload.youtube_url, title=title, voice_id=voice_id,
                    video_path="pending", duration_secs=None,
                )
                db.add(item)
                db.flush()
                out_path = str(_ensure_dir() / f"{item.id}.mp4")
                duration = compose(video_path, voice_track, out_path)
                item.video_path = out_path
                item.duration_secs = duration
                db.commit()
                db.refresh(item)

            yield {"data": json.dumps({"status": "done", "item": _to_out(item)})}

        except ValueError as exc:
            db.rollback()
            logger.warning("Dub error: %s", exc)
            yield {"data": json.dumps({"status": "error", "message": str(exc)})}
        except Exception:
            db.rollback()
            logger.exception("Unexpected dub error")
            yield {"data": json.dumps({"status": "error", "message": "配音失败，请稍后重试。"})}

    return EventSourceResponse(event_stream())


@router.get("/list", response_model=List[DubOut])
def list_items(db: Session = Depends(get_db)):
    rows = db.scalars(select(DubVideo).order_by(DubVideo.created_at.desc())).all()
    return [DubOut(**_to_out(d)) for d in rows]


@router.delete("/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    d = db.get(DubVideo, item_id)
    if not d:
        raise HTTPException(status_code=404, detail="Dub not found")
    try:
        p = Path(d.video_path)
        if p.exists():
            p.unlink()
    except OSError:
        pass
    db.delete(d)
    db.commit()


@router.get("/{item_id}/video")
def get_video(item_id: int, db: Session = Depends(get_db)):
    d = db.get(DubVideo, item_id)
    if not d:
        raise HTTPException(status_code=404, detail="Dub not found")
    path = Path(d.video_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Video file missing")
    return FileResponse(path=str(path), media_type="video/mp4", filename=f"dub-{item_id}.mp4")

"""配 Dub routes: SSE generate (YouTube + upload) + list + delete + video."""
from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path
from typing import AsyncGenerator, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import DubVideo
from app.services.podcast_service import validate_youtube_url, resolve_voice
from app.services import dub_service
from app.services.dub_service import (
    probe_duration, download_video, extract_segments, merge_sentences,
    translate_segments, build_voice_track, compose, _ensure_dir,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dub", tags=["dub"])


class DubRequest(BaseModel):
    youtube_url: str
    voice_id: Optional[str] = None


class DubOut(BaseModel):
    id: int
    youtube_url: Optional[str]
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


def _sse(status: str, message: str) -> dict:
    return {"data": json.dumps({"status": status, "message": message})}


async def _process_video(
    db: Session, settings, *, video_path: str, title: str,
    source_url: Optional[str], voice_id_req: Optional[str], dur_s: int,
) -> AsyncGenerator[dict, None]:
    """Shared tail of the pipeline: transcribe → translate → voice → compose → save.
    Both the YouTube and upload routes call this once they have a local video_path."""
    # Every heavy call below is synchronous (yt-dlp/ffmpeg/Whisper/TTS) and would
    # block the event loop — starving sse-starlette's keepalive ping and dropping
    # the connection during the slow proxied download. Run them in a threadpool so
    # the loop stays free to ping and the SSE stream survives multi-minute phases.
    yield _sse("transcribing", "转写中...")
    segments = await run_in_threadpool(extract_segments, video_path, settings.openai_api_key)
    segments = merge_sentences(segments)  # C：碎片合并成完整句，避免半句单独配音

    yield _sse("translating", "翻译中...")
    zh = await run_in_threadpool(
        translate_segments, segments, settings.anthropic_api_key, settings.ai_model
    )

    yield _sse("voicing", "配音中...")
    voice_id = resolve_voice(voice_id_req)
    voice_track = await run_in_threadpool(
        build_voice_track,
        segments, zh, voice_id,
        settings.minimax_api_key, settings.minimax_group_id,
        settings.minimax_model, settings.minimax_api_base,
        dur_s * 1000,
    )

    yield _sse("composing", "合成视频中...")
    item = DubVideo(
        youtube_url=source_url, title=title, voice_id=voice_id,
        video_path="pending", duration_secs=None,
    )
    db.add(item)
    db.flush()
    out_path = str(_ensure_dir() / f"{item.id}.mp4")
    duration = await run_in_threadpool(compose, video_path, voice_track, out_path)
    item.video_path = out_path
    item.duration_secs = duration
    db.commit()
    db.refresh(item)

    yield {"data": json.dumps({"status": "done", "item": _to_out(item)})}


@router.post("/generate")
async def generate(payload: DubRequest, db: Session = Depends(get_db)):
    if not validate_youtube_url(payload.youtube_url):
        raise HTTPException(status_code=422, detail="Invalid YouTube URL")

    settings = get_settings()

    async def event_stream() -> AsyncGenerator[dict, None]:
        try:
            dub_service.purge_expired(db)
            yield _sse("downloading", "下载视频中...")
            dur_s = await run_in_threadpool(probe_duration, payload.youtube_url)

            with tempfile.TemporaryDirectory() as tmp:
                title, video_path = await run_in_threadpool(
                    download_video, payload.youtube_url, tmp
                )
                async for ev in _process_video(
                    db, settings, video_path=video_path, title=title,
                    source_url=payload.youtube_url, voice_id_req=payload.voice_id, dur_s=dur_s,
                ):
                    yield ev
        except ValueError as exc:
            db.rollback()
            logger.warning("Dub error: %s", exc)
            yield _sse("error", str(exc))
        except Exception:
            db.rollback()
            logger.exception("Unexpected dub error")
            yield _sse("error", "配音失败，请稍后重试。")

    return EventSourceResponse(event_stream())


@router.post("/generate-upload")
async def generate_upload(
    file: UploadFile = File(...),
    voice_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    settings = get_settings()

    # Read the upload eagerly while the request body is still open, then
    # stream the pipeline events.  Reading inside the SSE generator would
    # fail because the ASGI request body is closed by the time the
    # EventSourceResponse begins iterating.
    raw = await file.read()
    filename = file.filename or "video.mp4"

    async def event_stream() -> AsyncGenerator[dict, None]:
        try:
            dub_service.purge_expired(db)
            yield _sse("uploading", "接收文件中...")

            if len(raw) > dub_service.MAX_UPLOAD_BYTES:
                raise ValueError("文件超过 100MB 上限，请换更小的文件。")

            with tempfile.TemporaryDirectory() as tmp:
                suffix = Path(filename).suffix or ".mp4"
                dest = Path(tmp) / f"upload{suffix}"
                dest.write_bytes(raw)

                title = Path(filename).stem or "上传视频"
                dur_s = await run_in_threadpool(dub_service.probe_local_duration, str(dest))
                async for ev in _process_video(
                    db, settings, video_path=str(dest), title=title,
                    source_url=None, voice_id_req=voice_id, dur_s=dur_s,
                ):
                    yield ev
        except ValueError as exc:
            db.rollback()
            logger.warning("Dub upload error: %s", exc)
            yield _sse("error", str(exc))
        except Exception:
            db.rollback()
            logger.exception("Unexpected dub upload error")
            yield _sse("error", "配音失败，请稍后重试。")

    return EventSourceResponse(event_stream())


@router.get("/list", response_model=List[DubOut])
def list_items(db: Session = Depends(get_db)):
    dub_service.purge_expired(db)
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

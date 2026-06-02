"""Podcast generation routes."""
from __future__ import annotations

import json
import logging
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
from app.models.entities import PodcastEpisode
from app.services.podcast_service import (
    VOICE_CATALOG,
    extract_transcript,
    fetch_video_title,
    generate_audio_dialogue,
    generate_audio_single,
    generate_script,
    get_chinese_title,
    pick_random_voice,
    resolve_voice,
    validate_youtube_url,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/podcast", tags=["podcast"])


class GenerateRequest(BaseModel):
    youtube_url: str
    digest_length_mins: int = 5   # 5 or 10
    format: str = "single"        # "single" or "dialogue"
    voice_id: Optional[str] = None  # narration voice for single format; ignored for dialogue


class EpisodeOut(BaseModel):
    id: int
    youtube_url: str
    video_title: Optional[str]
    digest_length_mins: int
    format: str
    duration_secs: Optional[int]
    created_at: str


@router.post("/generate")
async def generate_podcast(payload: GenerateRequest, db: Session = Depends(get_db)):
    """
    SSE endpoint — streams progress events while generating the podcast.
    Events: {"status": "...", "message": "..."} or {"status": "done", "episode": {...}}
    """
    if not validate_youtube_url(payload.youtube_url):
        raise HTTPException(status_code=422, detail="Invalid YouTube URL")

    if payload.digest_length_mins not in (5, 10):
        raise HTTPException(status_code=422, detail="digest_length_mins must be 5 or 10")

    if payload.format not in ("single", "dialogue"):
        raise HTTPException(status_code=422, detail="format must be 'single' or 'dialogue'")

    settings = get_settings()

    async def event_stream() -> AsyncGenerator[dict, None]:
        episode: Optional[PodcastEpisode] = None
        try:
            # Step 1: extract transcript
            yield {"data": json.dumps({"status": "extracting", "message": "Fetching transcript..."})}
            video_title, transcript = extract_transcript(payload.youtube_url)

            # Step 2: Claude digest
            yield {"data": json.dumps({"status": "digesting", "message": "Digesting with Claude..."})}
            script_zh = generate_script(
                transcript=transcript,
                digest_length_mins=payload.digest_length_mins,
                fmt=payload.format,
                anthropic_api_key=settings.anthropic_api_key,
                model=settings.ai_model,
            )

            # Translate or infer Chinese title
            yield {"data": json.dumps({"status": "translating", "message": "Generating Chinese title..."})}
            video_title = get_chinese_title(
                english_title=video_title,
                transcript=transcript,
                anthropic_api_key=settings.anthropic_api_key,
                model=settings.ai_model,
            )

            # Step 3: TTS
            yield {"data": json.dumps({"status": "tts", "message": "Generating audio..."})}

            # Create a stub DB row to get the ID for the filename
            episode = PodcastEpisode(
                youtube_url=payload.youtube_url,
                video_title=video_title,
                digest_length_mins=payload.digest_length_mins,
                format=payload.format,
                script_zh=script_zh,
                audio_path="pending",
            )
            db.add(episode)
            db.flush()  # get episode.id without full commit

            if payload.format == "single":
                audio_path, duration_secs = generate_audio_single(
                    script=script_zh,
                    episode_id=episode.id,
                    voice_id_a=resolve_voice(payload.voice_id),
                    api_key=settings.minimax_api_key,
                    group_id=settings.minimax_group_id,
                    model=settings.minimax_model,
                    api_base=settings.minimax_api_base,
                )
            else:
                yield {"data": json.dumps({"status": "stitching", "message": "Stitching dialogue..."})}
                audio_path, duration_secs = generate_audio_dialogue(
                    script=script_zh,
                    episode_id=episode.id,
                    voice_id_a=pick_random_voice("female"),   # host A
                    voice_id_b=pick_random_voice("male"),     # host B
                    api_key=settings.minimax_api_key,
                    group_id=settings.minimax_group_id,
                    model=settings.minimax_model,
                    api_base=settings.minimax_api_base,
                )

            # Finalise DB row
            episode.audio_path = str(audio_path)
            episode.duration_secs = duration_secs
            db.commit()
            db.refresh(episode)

            episode_data = {
                "id": episode.id,
                "youtube_url": episode.youtube_url,
                "video_title": episode.video_title,
                "digest_length_mins": episode.digest_length_mins,
                "format": episode.format,
                "duration_secs": episode.duration_secs,
                "created_at": episode.created_at.isoformat(),
            }
            yield {"data": json.dumps({"status": "done", "episode": episode_data})}

        except ValueError as exc:
            db.rollback()
            logger.warning("Podcast generation error: %s", exc)
            yield {"data": json.dumps({"status": "error", "message": str(exc)})}
        except Exception as exc:
            db.rollback()
            logger.exception("Unexpected podcast generation error")
            yield {"data": json.dumps({"status": "error", "message": "Generation failed — please try again."})}

    return EventSourceResponse(event_stream())


@router.get("/voices")
def list_voices():
    """Return the curated MiniMax voice catalog for the single-narration dropdown."""
    return VOICE_CATALOG


@router.get("/episodes", response_model=List[EpisodeOut])
def list_episodes(db: Session = Depends(get_db)):
    """Return all episodes, newest first."""
    episodes = db.scalars(
        select(PodcastEpisode).order_by(PodcastEpisode.created_at.desc())
    ).all()
    return [
        EpisodeOut(
            id=ep.id,
            youtube_url=ep.youtube_url,
            video_title=ep.video_title,
            digest_length_mins=ep.digest_length_mins,
            format=ep.format,
            duration_secs=ep.duration_secs,
            created_at=ep.created_at.isoformat(),
        )
        for ep in episodes
    ]


@router.delete("/episodes/{episode_id}", status_code=204)
def delete_episode(episode_id: int, db: Session = Depends(get_db)):
    """Delete episode DB row and MP3 file from disk."""
    episode = db.get(PodcastEpisode, episode_id)
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    audio_path = Path(episode.audio_path)
    try:
        if audio_path.exists():
            audio_path.unlink()
    except OSError:
        pass  # best-effort file deletion — DB row removed regardless

    db.delete(episode)
    db.commit()


@router.get("/episodes/{episode_id}/download")
def download_episode(episode_id: int, db: Session = Depends(get_db)):
    """Stream the MP3 file for the given episode."""
    episode = db.get(PodcastEpisode, episode_id)
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    audio_path = Path(episode.audio_path)
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found on disk")

    filename = f"podcast-{episode_id}.mp3"
    return FileResponse(
        path=str(audio_path),
        media_type="audio/mpeg",
        filename=filename,
    )

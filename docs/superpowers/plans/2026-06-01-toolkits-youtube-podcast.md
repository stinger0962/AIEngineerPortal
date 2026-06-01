# Toolkits + YouTube Podcast Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Toolkits sidebar section with a YouTube Podcast tool that converts any YouTube video into a digested Chinese-language MP3 episode (single narrator or two-person dialogue) using yt-dlp, Claude, and ElevenLabs.

**Architecture:** FastAPI SSE endpoint orchestrates transcript extraction → Claude digest → ElevenLabs TTS → pydub stitching (dialogue only) and streams progress to the browser. Episodes are stored as MP3 files in a Docker volume with metadata in Postgres. Next.js split-panel UI renders the form and episode library.

**Tech Stack:** yt-dlp, anthropic SDK, elevenlabs SDK, pydub + ffmpeg, sse-starlette (backend); native EventSource + HTML5 audio (frontend); SQLAlchemy 2.0 Mapped columns; Tailwind CSS (existing portal palette).

---

## File Map

**Create:**
- `backend/app/api/v1/routes/podcast.py` — SSE generate, list episodes, download
- `backend/app/services/podcast_service.py` — transcript, Claude, TTS, stitching
- `frontend/src/app/toolkits/page.tsx` — Toolkits index KPI cards
- `frontend/src/app/toolkits/podcast/page.tsx` — split panel layout
- `frontend/src/components/toolkits/toolkit-card.tsx` — reusable KPI card
- `frontend/src/components/toolkits/podcast-generator.tsx` — left panel form + SSE
- `frontend/src/components/toolkits/podcast-episode-list.tsx` — right panel list

**Modify:**
- `backend/requirements.txt` — add yt-dlp, elevenlabs, sse-starlette, pydub
- `backend/Dockerfile` — add ffmpeg install
- `backend/app/core/config.py` — add ElevenLabs keys
- `.env.example` — add ElevenLabs key placeholders
- `backend/app/models/entities.py` — add PodcastEpisode model
- `backend/app/models/__init__.py` — export PodcastEpisode
- `backend/app/api/v1/api.py` — register podcast router
- `frontend/src/components/layout/sidebar-nav.tsx` — add Toolkits nav item
- `docker-compose.yml` — add podcast_audio volume

---

## Task 1: Backend dependencies + ffmpeg

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/Dockerfile`

- [ ] **Step 1: Add Python dependencies to requirements.txt**

Replace the contents of `backend/requirements.txt` with:

```
fastapi==0.115.6
uvicorn[standard]==0.33.0
sqlalchemy==2.0.36
pydantic==2.10.5
pydantic-settings==2.7.1
psycopg[binary]==3.2.3
alembic==1.14.0
redis==5.2.1
httpx==0.28.1
pytest==8.3.4
anthropic>=0.42.0
yt-dlp>=2024.1.0
elevenlabs>=1.0.0
sse-starlette>=2.1.0
pydub>=0.25.1
```

- [ ] **Step 2: Add ffmpeg to Dockerfile**

Replace `backend/Dockerfile` with:

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt backend/Dockerfile
git commit -m "chore: add yt-dlp, elevenlabs, pydub, ffmpeg for podcast feature"
```

---

## Task 2: Config + environment variables

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `.env.example`
- Modify: `.env` (local only, not committed)

- [ ] **Step 1: Add ElevenLabs settings to config.py**

In `backend/app/core/config.py`, add three fields to the `Settings` class after `ai_daily_token_budget`:

```python
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id_a: str = "21m00Tcm4TlvDq8ikWAM"   # Rachel — single + host A
    elevenlabs_voice_id_b: str = "AZnzlk1XvdvUeBnXmlld"   # Domi — host B (dialogue)
```

- [ ] **Step 2: Add placeholders to .env.example**

Append to `.env.example`:

```
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID_A=21m00Tcm4TlvDq8ikWAM
ELEVENLABS_VOICE_ID_B=AZnzlk1XvdvUeBnXmlld
```

- [ ] **Step 3: Add real key to local .env**

Append to `.env` (this file is gitignored — never commit it):

```
ELEVENLABS_API_KEY=ELEVENLABS_API_KEY_REDACTED
ELEVENLABS_VOICE_ID_A=21m00Tcm4TlvDq8ikWAM
ELEVENLABS_VOICE_ID_B=AZnzlk1XvdvUeBnXmlld
```

- [ ] **Step 4: Commit config changes (not .env)**

```bash
git add backend/app/core/config.py .env.example
git commit -m "feat: add ElevenLabs config settings"
```

---

## Task 3: PodcastEpisode database model

**Files:**
- Modify: `backend/app/models/entities.py`
- Modify: `backend/app/models/__init__.py`

The app uses `Base.metadata.create_all(bind=engine)` at startup — no migration files needed. Just add the model and it will be auto-created on next startup.

- [ ] **Step 1: Write a test that imports the model**

Add to `backend/tests/test_api.py` (at the bottom of the existing imports section):

```python
from app.models.entities import PodcastEpisode
```

- [ ] **Step 2: Run to confirm it fails**

```bash
cd backend && python -m pytest tests/test_api.py -x -q 2>&1 | head -20
```

Expected: `ImportError: cannot import name 'PodcastEpisode'`

- [ ] **Step 3: Add PodcastEpisode model to entities.py**

Append to the bottom of `backend/app/models/entities.py`:

```python
class PodcastEpisode(Base):
    __tablename__ = "podcast_episodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    youtube_url: Mapped[str] = mapped_column(Text, nullable=False)
    video_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    digest_length_mins: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    format: Mapped[str] = mapped_column(String(20), nullable=False, default="single")
    script_zh: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    audio_path: Mapped[str] = mapped_column(Text, nullable=False)
    duration_secs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 4: Export from models/__init__.py**

In `backend/app/models/__init__.py`, add `PodcastEpisode` to the import and `__all__` list:

```python
from app.models.entities import (
    Course,
    Exercise,
    InterviewQuestion,
    InterviewQuestionPractice,
    JobPosting,
    KnowledgeArticle,
    LearningPath,
    Lesson,
    LessonCompletion,
    MemoryCard,
    NewsItem,
    PodcastEpisode,
    ProgressSnapshot,
    Project,
    User,
    UserExerciseAttempt,
)

__all__ = [
    "Course",
    "Exercise",
    "InterviewQuestion",
    "InterviewQuestionPractice",
    "JobPosting",
    "KnowledgeArticle",
    "LearningPath",
    "Lesson",
    "LessonCompletion",
    "MemoryCard",
    "NewsItem",
    "PodcastEpisode",
    "ProgressSnapshot",
    "Project",
    "User",
    "UserExerciseAttempt",
]
```

- [ ] **Step 5: Run test to confirm import succeeds**

```bash
cd backend && python -m pytest tests/test_api.py -x -q 2>&1 | head -20
```

Expected: tests pass (or at least no ImportError)

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/entities.py backend/app/models/__init__.py backend/tests/test_api.py
git commit -m "feat: add PodcastEpisode model"
```

---

## Task 4: Podcast service — transcript extraction

**Files:**
- Create: `backend/app/services/podcast_service.py`

- [ ] **Step 1: Create the service file with transcript extraction**

Create `backend/app/services/podcast_service.py`:

```python
"""Podcast generation service: transcript extraction, Claude digest, ElevenLabs TTS."""
from __future__ import annotations

import io
import os
import re
import tempfile
from pathlib import Path
from typing import Generator, List, Optional, Tuple

import yt_dlp
from pydub import AudioSegment

AUDIO_DIR = Path(os.getenv("PODCAST_AUDIO_DIR", "/data/podcast_audio"))
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

YOUTUBE_REGEX = re.compile(
    r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})"
)


def validate_youtube_url(url: str) -> bool:
    """Return True if url looks like a valid YouTube video URL."""
    return bool(YOUTUBE_REGEX.search(url))


def extract_transcript(youtube_url: str) -> Tuple[str, str]:
    """
    Download auto-generated or manual subtitles using yt-dlp.

    Returns (video_title, transcript_text).
    Raises ValueError if no subtitles are available.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        ydl_opts = {
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en", "en-US", "en-GB"],
            "skip_download": True,
            "outtmpl": f"{tmpdir}/video.%(ext)s",
            "quiet": True,
            "no_warnings": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            video_title: str = info.get("title", "Unknown Video")

        # Find the downloaded subtitle file (.vtt or .srt)
        sub_files = list(Path(tmpdir).glob("video.*.vtt")) + list(
            Path(tmpdir).glob("video.*.srt")
        )
        if not sub_files:
            raise ValueError(
                "No subtitles found for this video. "
                "Try a video with auto-generated captions enabled."
            )

        raw = sub_files[0].read_text(encoding="utf-8")
        transcript = _parse_subtitle(raw, suffix=sub_files[0].suffix)

    return video_title, transcript


def _parse_subtitle(raw: str, suffix: str) -> str:
    """Strip timestamps and markup from VTT/SRT, return plain text."""
    # Remove VTT/SRT header
    text = re.sub(r"WEBVTT.*?\n\n", "", raw, flags=re.DOTALL)
    # Remove timestamp lines (both VTT and SRT formats)
    text = re.sub(
        r"\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[.,]\d{3}.*?\n",
        "",
        text,
    )
    # Remove sequence numbers (SRT)
    text = re.sub(r"^\d+\s*$", "", text, flags=re.MULTILINE)
    # Remove HTML/VTT tags
    text = re.sub(r"<[^>]+>", "", text)
    # Collapse whitespace
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    # Deduplicate consecutive identical lines (common in auto-captions)
    deduped: List[str] = []
    for ln in lines:
        if not deduped or ln != deduped[-1]:
            deduped.append(ln)
    return " ".join(deduped)
```

- [ ] **Step 2: Write unit tests for the helpers**

Create `backend/tests/test_podcast_service.py`:

```python
"""Unit tests for podcast_service helpers (no network calls)."""
import pytest
from app.services.podcast_service import validate_youtube_url, _parse_subtitle


def test_validate_youtube_url_standard():
    assert validate_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True


def test_validate_youtube_url_short():
    assert validate_youtube_url("https://youtu.be/dQw4w9WgXcQ") is True


def test_validate_youtube_url_invalid():
    assert validate_youtube_url("https://vimeo.com/123456") is False
    assert validate_youtube_url("not a url") is False


def test_parse_subtitle_vtt():
    raw = """WEBVTT

00:00:00.000 --> 00:00:02.000
Hello world

00:00:02.000 --> 00:00:04.000
Hello world

00:00:04.000 --> 00:00:06.000
This is a test
"""
    result = _parse_subtitle(raw, ".vtt")
    assert "Hello world" in result
    assert "This is a test" in result
    # Duplicate consecutive lines should be collapsed
    assert result.count("Hello world") == 1


def test_parse_subtitle_strips_tags():
    raw = """WEBVTT

00:00:00.000 --> 00:00:02.000
<c>Hello</c> <b>world</b>
"""
    result = _parse_subtitle(raw, ".vtt")
    assert "<c>" not in result
    assert "Hello world" in result
```

- [ ] **Step 3: Run tests**

```bash
cd backend && python -m pytest tests/test_podcast_service.py -v
```

Expected: 5 tests PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/podcast_service.py backend/tests/test_podcast_service.py
git commit -m "feat: podcast transcript extraction with yt-dlp"
```

---

## Task 5: Podcast service — Claude digest

**Files:**
- Modify: `backend/app/services/podcast_service.py`

- [ ] **Step 1: Write failing test for digest function**

Append to `backend/tests/test_podcast_service.py`:

```python
def test_build_single_prompt_contains_transcript():
    from app.services.podcast_service import _build_prompt
    prompt = _build_prompt("This is the transcript.", digest_length_mins=5, fmt="single")
    assert "This is the transcript." in prompt
    assert "30%" in prompt  # 5 min → 30%


def test_build_dialogue_prompt_contains_format_instruction():
    from app.services.podcast_service import _build_prompt
    prompt = _build_prompt("Transcript here.", digest_length_mins=10, fmt="dialogue")
    assert "主持人A:" in prompt
    assert "60%" in prompt  # 10 min → 60%
    assert "Transcript here." in prompt
```

- [ ] **Step 2: Run to confirm they fail**

```bash
cd backend && python -m pytest tests/test_podcast_service.py::test_build_single_prompt_contains_transcript -v
```

Expected: ImportError or AttributeError — `_build_prompt` not defined yet.

- [ ] **Step 3: Add `_build_prompt` and `generate_script` to podcast_service.py**

Append to `backend/app/services/podcast_service.py`:

```python
_DIGEST_PCT = {5: 30, 10: 60}

_SINGLE_PROMPT = """你是一位专业的中文播客主持人。请将以下英文视频讲稿整理为一期播客脚本。

要求：
1. 长度约为原文的{pct}%，提炼最核心的观点（目标时长：{target_mins}分钟）
2. 语气自然口语化，像在和听众轻松对话
3. 开头一句话引入主题，结尾一句话总结收尾
4. 保留最重要的例子、数据和结论
5. 直接输出播客脚本，不要任何说明或前言

讲稿内容：
{transcript}"""

_DIALOGUE_PROMPT = """你是两位中文播客主持人（主持人A：女声，主持人B：男声）。
请将以下英文视频讲稿改编为一段自然的双人对话播客脚本。

要求：
1. 长度约为原文的{pct}%，提炼最核心的观点（目标时长：{target_mins}分钟）
2. 对话要自然、有来有往，A和B轮流发言，每次发言2-4句话
3. A负责引入话题和总结，B负责追问、补充例子和表达观点
4. 语气轻松口语化，像朋友间的专业讨论
5. 严格按以下格式输出，每行一句发言，不要其他内容：

主持人A: [发言内容]
主持人B: [发言内容]
主持人A: [发言内容]
...

讲稿内容：
{transcript}"""


def _build_prompt(transcript: str, digest_length_mins: int, fmt: str) -> str:
    """Build the Claude prompt for the given format and length."""
    pct = _DIGEST_PCT.get(digest_length_mins, 30)
    template = _SINGLE_PROMPT if fmt == "single" else _DIALOGUE_PROMPT
    return template.format(pct=pct, target_mins=digest_length_mins, transcript=transcript)


def generate_script(
    transcript: str,
    digest_length_mins: int,
    fmt: str,
    anthropic_api_key: str,
    model: str = "claude-sonnet-4-20250514",
) -> str:
    """
    Call Claude to produce a Chinese podcast script.
    Returns the raw script text (plain for single, 主持人A/B: lines for dialogue).
    """
    import anthropic

    client = anthropic.Anthropic(api_key=anthropic_api_key)
    prompt = _build_prompt(transcript, digest_length_mins, fmt)
    message = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_podcast_service.py -v
```

Expected: all 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/podcast_service.py backend/tests/test_podcast_service.py
git commit -m "feat: Claude digest prompts for single and dialogue podcast formats"
```

---

## Task 6: Podcast service — ElevenLabs TTS + audio stitching

**Files:**
- Modify: `backend/app/services/podcast_service.py`

- [ ] **Step 1: Write failing tests for dialogue parsing and audio functions**

Append to `backend/tests/test_podcast_service.py`:

```python
def test_parse_dialogue_lines():
    from app.services.podcast_service import _parse_dialogue
    script = "主持人A: 你好，欢迎收听。\n主持人B: 谢谢，今天我们聊聊AI。\n主持人A: 对的。"
    lines = _parse_dialogue(script)
    assert lines == [
        ("A", "你好，欢迎收听。"),
        ("B", "谢谢，今天我们聊聊AI。"),
        ("A", "对的。"),
    ]


def test_parse_dialogue_skips_blank_lines():
    from app.services.podcast_service import _parse_dialogue
    script = "主持人A: 第一句。\n\n主持人B: 第二句。"
    lines = _parse_dialogue(script)
    assert len(lines) == 2
```

- [ ] **Step 2: Run to confirm they fail**

```bash
cd backend && python -m pytest tests/test_podcast_service.py::test_parse_dialogue_lines -v
```

Expected: ImportError — `_parse_dialogue` not defined yet.

- [ ] **Step 3: Add TTS and stitching functions to podcast_service.py**

Append to `backend/app/services/podcast_service.py`:

```python
def _parse_dialogue(script: str) -> List[Tuple[str, str]]:
    """
    Parse a dialogue script into (speaker, text) pairs.
    Expects lines like '主持人A: ...' or '主持人B: ...'
    Skips blank lines and any line not matching the pattern.
    """
    pairs: List[Tuple[str, str]] = []
    for line in script.splitlines():
        line = line.strip()
        if line.startswith("主持人A:"):
            pairs.append(("A", line[len("主持人A:"):].strip()))
        elif line.startswith("主持人B:"):
            pairs.append(("B", line[len("主持人B:"):].strip()))
    return pairs


def _tts_bytes(text: str, voice_id: str, api_key: str) -> bytes:
    """
    Call ElevenLabs TTS API and return raw MP3 bytes.
    Uses eleven_multilingual_v2 model for best Chinese quality.
    """
    from elevenlabs.client import ElevenLabs

    client = ElevenLabs(api_key=api_key)
    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )
    # The SDK returns a generator of bytes chunks
    return b"".join(audio)


def generate_audio_single(
    script: str,
    episode_id: int,
    voice_id_a: str,
    api_key: str,
) -> Tuple[Path, int]:
    """
    Generate a single-narrator MP3 from the full script.
    Returns (audio_path, duration_secs).
    """
    mp3_bytes = _tts_bytes(script, voice_id_a, api_key)
    audio_path = AUDIO_DIR / f"{episode_id}.mp3"
    audio_path.write_bytes(mp3_bytes)
    segment = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
    duration_secs = int(len(segment) / 1000)
    return audio_path, duration_secs


def generate_audio_dialogue(
    script: str,
    episode_id: int,
    voice_id_a: str,
    voice_id_b: str,
    api_key: str,
) -> Tuple[Path, int]:
    """
    Generate a two-person dialogue MP3 by calling ElevenLabs once per line
    and stitching with 300ms silence between turns.
    Returns (audio_path, duration_secs).
    """
    lines = _parse_dialogue(script)
    if not lines:
        raise ValueError("Dialogue script contains no parseable speaker lines.")

    silence = AudioSegment.silent(duration=300)  # 300ms between turns
    combined = AudioSegment.empty()

    for speaker, text in lines:
        voice_id = voice_id_a if speaker == "A" else voice_id_b
        mp3_bytes = _tts_bytes(text, voice_id, api_key)
        segment = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
        if len(combined) > 0:
            combined += silence
        combined += segment

    audio_path = AUDIO_DIR / f"{episode_id}.mp3"
    combined.export(str(audio_path), format="mp3")
    duration_secs = int(len(combined) / 1000)
    return audio_path, duration_secs
```

- [ ] **Step 4: Run all service tests**

```bash
cd backend && python -m pytest tests/test_podcast_service.py -v
```

Expected: all 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/podcast_service.py backend/tests/test_podcast_service.py
git commit -m "feat: ElevenLabs TTS and pydub dialogue stitching"
```

---

## Task 7: Podcast API routes (SSE + list + download)

**Files:**
- Create: `backend/app/api/v1/routes/podcast.py`

- [ ] **Step 1: Create the route file**

Create `backend/app/api/v1/routes/podcast.py`:

```python
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
    extract_transcript,
    generate_audio_dialogue,
    generate_audio_single,
    generate_script,
    validate_youtube_url,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/podcast", tags=["podcast"])


class GenerateRequest(BaseModel):
    youtube_url: str
    digest_length_mins: int = 5   # 5 or 10
    format: str = "single"        # "single" or "dialogue"


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
                    voice_id_a=settings.elevenlabs_voice_id_a,
                    api_key=settings.elevenlabs_api_key,
                )
            else:
                yield {"data": json.dumps({"status": "stitching", "message": "Stitching dialogue..."})}
                audio_path, duration_secs = generate_audio_dialogue(
                    script=script_zh,
                    episode_id=episode.id,
                    voice_id_a=settings.elevenlabs_voice_id_a,
                    voice_id_b=settings.elevenlabs_voice_id_b,
                    api_key=settings.elevenlabs_api_key,
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
            if episode:
                db.rollback()
            logger.warning("Podcast generation error: %s", exc)
            yield {"data": json.dumps({"status": "error", "message": str(exc)})}
        except Exception as exc:
            if episode:
                db.rollback()
            logger.exception("Unexpected podcast generation error")
            yield {"data": json.dumps({"status": "error", "message": "Generation failed — please try again."})}

    return EventSourceResponse(event_stream())


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
```

- [ ] **Step 2: Register the router in api.py**

In `backend/app/api/v1/api.py`, add the import and include:

```python
from app.api.v1.routes import adaptive, ai_feedback, copilot, courses, dashboard, deep_dives, exercise_variations, exercises, interview, interview_coaching, jobs, knowledge, learning, live_jobs, memory, news, podcast, projects, recommendations, resume, streaks
```

And add at the bottom of the includes:

```python
api_router.include_router(podcast.router)
```

- [ ] **Step 3: Verify the app starts without errors (local dev)**

```bash
cd backend && python -c "from app.main import app; print('OK')"
```

Expected: `OK` with no import errors.

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/routes/podcast.py backend/app/api/v1/api.py
git commit -m "feat: podcast SSE generate, list, and download routes"
```

---

## Task 8: Docker volume for audio storage

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: Add podcast_audio volume**

In `docker-compose.yml`, add a `backend` service if one doesn't exist yet, or add the volume to the existing backend service. The full updated file:

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-ai_engineer_portal}
      POSTGRES_USER: ${POSTGRES_USER:-portal}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-portal}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  backend:
    build: ./backend
    restart: unless-stopped
    env_file: .env
    ports:
      - "${BACKEND_PORT:-8000}:8000"
    depends_on:
      - postgres
      - redis
    volumes:
      - podcast_audio:/data/podcast_audio

  frontend:
    build: ./frontend
    restart: unless-stopped
    env_file: frontend/.env
    ports:
      - "${FRONTEND_PORT:-3000}:3000"
    depends_on:
      - backend

volumes:
  postgres_data:
  redis_data:
  podcast_audio:
```

- [ ] **Step 2: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: add podcast_audio Docker volume and backend/frontend services"
```

---

## Task 9: Frontend — ToolkitCard component

**Files:**
- Create: `frontend/src/components/toolkits/toolkit-card.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/toolkits/toolkit-card.tsx`:

```tsx
"use client";

import Link from "next/link";

interface Tag {
  label: string;
  variant?: "default" | "ready" | "soon";
}

interface ToolkitCardProps {
  icon: string;
  name: string;
  description: string;
  tags?: Tag[];
  href?: string;        // undefined = coming soon (non-clickable)
  comingSoon?: boolean;
}

export function ToolkitCard({
  icon,
  name,
  description,
  tags = [],
  href,
  comingSoon = false,
}: ToolkitCardProps) {
  const cardClasses = `
    relative rounded-2xl border p-5 transition-all duration-150
    ${comingSoon
      ? "border-dashed border-white/10 opacity-50 cursor-not-allowed"
      : "border-white/10 bg-white/5 hover:border-ember/50 hover:bg-ember/5 cursor-pointer"
    }
  `;

  const inner = (
    <div className={cardClasses}>
      {/* Top accent bar on hover */}
      {!comingSoon && (
        <div className="absolute top-0 left-0 right-0 h-[3px] rounded-t-2xl bg-ember opacity-0 group-hover:opacity-100 transition-opacity" />
      )}

      <div className="text-3xl mb-3">{icon}</div>
      <h3 className="text-sm font-bold text-cream mb-1">{name}</h3>
      <p className="text-xs text-cream/50 leading-relaxed mb-4">{description}</p>

      <div className="flex flex-wrap gap-1.5">
        {tags.map((tag) => (
          <span
            key={tag.label}
            className={`text-[10px] px-2 py-0.5 rounded font-medium ${
              tag.variant === "ready"
                ? "bg-ember/20 text-ember"
                : tag.variant === "soon"
                ? "bg-white/5 text-cream/30"
                : "bg-white/5 text-cream/40"
            }`}
          >
            {tag.label}
          </span>
        ))}
      </div>
    </div>
  );

  if (href && !comingSoon) {
    return (
      <Link href={href} className="group block">
        {inner}
      </Link>
    );
  }

  return <div className="group">{inner}</div>;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/toolkits/toolkit-card.tsx
git commit -m "feat: ToolkitCard component for Toolkits index page"
```

---

## Task 10: Frontend — Toolkits index page

**Files:**
- Create: `frontend/src/app/toolkits/page.tsx`

- [ ] **Step 1: Create the page**

Create `frontend/src/app/toolkits/page.tsx`:

```tsx
import { ToolkitCard } from "@/components/toolkits/toolkit-card";

export default function ToolkitsPage() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <span className="text-xs font-semibold uppercase tracking-[0.28em] text-ember">
          Toolkits
        </span>
        <h1 className="font-display text-3xl text-cream mt-1">Your toolkit.</h1>
        <p className="text-cream/50 text-sm mt-1">
          Standalone utilities to accelerate your AI engineering journey.
        </p>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <ToolkitCard
          icon="🎙"
          name="YouTube Podcast"
          description="Paste a YouTube URL and get a digested Chinese podcast episode — single narrator or two-person dialogue."
          href="/toolkits/podcast"
          tags={[
            { label: "TTS", variant: "default" },
            { label: "AI digest", variant: "default" },
            { label: "Ready", variant: "ready" },
          ]}
        />

        <ToolkitCard
          icon="📄"
          name="Doc Builder"
          description="Generate structured documents from raw notes and outlines."
          comingSoon
          tags={[{ label: "Coming soon", variant: "soon" }]}
        />

        <ToolkitCard
          icon="🔍"
          name="Job Scanner"
          description="Analyse job description fit against your resume and target role."
          comingSoon
          tags={[{ label: "Coming soon", variant: "soon" }]}
        />

        <ToolkitCard
          icon="＋"
          name="Request a tool"
          description="Have an idea for a useful utility? Let me know."
          comingSoon
          tags={[]}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/toolkits/page.tsx
git commit -m "feat: Toolkits index page with KPI cards"
```

---

## Task 11: Frontend — Episode list component

**Files:**
- Create: `frontend/src/components/toolkits/podcast-episode-list.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/toolkits/podcast-episode-list.tsx`:

```tsx
"use client";

interface Episode {
  id: number;
  video_title: string | null;
  digest_length_mins: number;
  format: string;
  duration_secs: number | null;
  created_at: string;
}

interface PodcastEpisodeListProps {
  episodes: Episode[];
  onNewEpisode?: (ep: Episode) => void;
}

function formatDuration(secs: number | null): string {
  if (!secs) return "—";
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${m}m ${s.toString().padStart(2, "0")}s`;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  if (diff < 86400000) return "Today";
  if (diff < 172800000) return "Yesterday";
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function PodcastEpisodeList({ episodes }: PodcastEpisodeListProps) {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

  if (episodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-20 text-center">
        <div className="text-5xl mb-4 opacity-30">🎙</div>
        <p className="text-cream/40 text-sm font-medium">No episodes yet</p>
        <p className="text-cream/25 text-xs mt-1">
          Generate your first podcast from the form on the left
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {episodes.map((ep) => (
        <div
          key={ep.id}
          className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 p-3 hover:border-white/20 transition-colors"
        >
          {/* Icon */}
          <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-ember/20 flex items-center justify-center text-base">
            🎙
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-cream truncate">
              {ep.video_title ?? "Untitled video"}
            </p>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-[10px] text-cream/40">
                {formatDuration(ep.duration_secs)}
              </span>
              <span className="text-[10px] text-cream/20">·</span>
              <span
                className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                  ep.format === "dialogue"
                    ? "bg-blue-500/20 text-blue-300"
                    : "bg-white/10 text-cream/40"
                }`}
              >
                {ep.format === "dialogue" ? "对话" : "单人"}
              </span>
              <span className="text-[10px] text-cream/20">·</span>
              <span className="text-[10px] text-cream/40">{formatDate(ep.created_at)}</span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 flex-shrink-0">
            {/* Inline audio player */}
            <audio
              controls
              src={`${apiBase}/podcast/episodes/${ep.id}/download`}
              className="h-7 w-32 opacity-70 hover:opacity-100 transition-opacity"
            />
            {/* Download */}
            <a
              href={`${apiBase}/podcast/episodes/${ep.id}/download`}
              download={`podcast-${ep.id}.mp3`}
              className="text-cream/40 hover:text-ember transition-colors p-1"
              title="Download MP3"
            >
              ↓
            </a>
          </div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/toolkits/podcast-episode-list.tsx
git commit -m "feat: PodcastEpisodeList component with play and download"
```

---

## Task 12: Frontend — Podcast generator form (SSE)

**Files:**
- Create: `frontend/src/components/toolkits/podcast-generator.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/toolkits/podcast-generator.tsx`:

```tsx
"use client";

import { useState } from "react";

interface Episode {
  id: number;
  video_title: string | null;
  digest_length_mins: number;
  format: string;
  duration_secs: number | null;
  created_at: string;
}

interface PodcastGeneratorProps {
  onEpisodeReady: (episode: Episode) => void;
}

type ProgressStatus =
  | "idle"
  | "extracting"
  | "digesting"
  | "tts"
  | "stitching"
  | "done"
  | "error";

const STATUS_LABELS: Record<ProgressStatus, string> = {
  idle: "",
  extracting: "Fetching transcript...",
  digesting: "Digesting with Claude...",
  tts: "Generating audio...",
  stitching: "Stitching dialogue...",
  done: "Done!",
  error: "Generation failed",
};

const YOUTUBE_RE =
  /(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/;

export function PodcastGenerator({ onEpisodeReady }: PodcastGeneratorProps) {
  const [url, setUrl] = useState("");
  const [digestMins, setDigestMins] = useState<5 | 10>(5);
  const [format, setFormat] = useState<"single" | "dialogue">("single");
  const [status, setStatus] = useState<ProgressStatus>("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
  const isGenerating = status !== "idle" && status !== "done" && status !== "error";
  const urlValid = YOUTUBE_RE.test(url);

  async function handleGenerate() {
    if (!urlValid || isGenerating) return;

    setStatus("extracting");
    setErrorMsg("");

    try {
      const response = await fetch(`${apiBase}/podcast/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          youtube_url: url,
          digest_length_mins: digestMins,
          format,
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error("Failed to start generation");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data:")) continue;
          try {
            const payload = JSON.parse(line.slice(5).trim());
            if (payload.status) setStatus(payload.status as ProgressStatus);
            if (payload.status === "done" && payload.episode) {
              onEpisodeReady(payload.episode);
              setUrl("");
            }
            if (payload.status === "error") {
              setErrorMsg(payload.message ?? "Unknown error");
            }
          } catch {
            // ignore malformed SSE lines
          }
        }
      }
    } catch (err) {
      setStatus("error");
      setErrorMsg("Connection failed — is the backend running?");
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <span className="text-xs font-semibold uppercase tracking-[0.28em] text-cream/40">
          Generate New Episode
        </span>
      </div>

      {/* URL input */}
      <div className="space-y-1.5">
        <label className="text-xs text-cream/60">YouTube URL</label>
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://youtube.com/watch?v=..."
          disabled={isGenerating}
          className={`w-full rounded-xl border px-3 py-2.5 text-sm bg-white/5 text-cream placeholder:text-cream/20 outline-none transition-colors ${
            url && !urlValid
              ? "border-red-500/50 focus:border-red-500"
              : "border-white/10 focus:border-ember/50"
          } disabled:opacity-40`}
        />
        {url && !urlValid && (
          <p className="text-[11px] text-red-400">Please enter a valid YouTube URL</p>
        )}
      </div>

      {/* Digest length */}
      <div className="space-y-1.5">
        <label className="text-xs text-cream/60">Digest length</label>
        <div className="flex gap-2">
          {([5, 10] as const).map((mins) => (
            <button
              key={mins}
              onClick={() => setDigestMins(mins)}
              disabled={isGenerating}
              className={`flex-1 rounded-xl py-2 text-sm font-medium transition-colors disabled:opacity-40 ${
                digestMins === mins
                  ? "bg-ember/20 text-ember border border-ember/40"
                  : "bg-white/5 text-cream/50 border border-white/10 hover:border-white/20"
              }`}
            >
              ~{mins} min
            </button>
          ))}
        </div>
      </div>

      {/* Format */}
      <div className="space-y-1.5">
        <label className="text-xs text-cream/60">Format</label>
        <div className="flex gap-2">
          {(["single", "dialogue"] as const).map((fmt) => (
            <button
              key={fmt}
              onClick={() => setFormat(fmt)}
              disabled={isGenerating}
              className={`flex-1 rounded-xl py-2 text-sm font-medium transition-colors disabled:opacity-40 ${
                format === fmt
                  ? "bg-ember/20 text-ember border border-ember/40"
                  : "bg-white/5 text-cream/50 border border-white/10 hover:border-white/20"
              }`}
            >
              {fmt === "single" ? "单人叙述" : "双人对话"}
            </button>
          ))}
        </div>
        <p className="text-[11px] text-cream/30">
          {format === "dialogue"
            ? "Two hosts (A + B) discuss the content — takes slightly longer"
            : "Single narrator reads the digest"}
        </p>
      </div>

      {/* Progress / Generate button */}
      {isGenerating ? (
        <div className="rounded-xl border border-ember/20 bg-ember/5 px-4 py-3">
          <div className="flex items-center gap-2">
            <svg
              className="animate-spin h-4 w-4 text-ember flex-shrink-0"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v8z"
              />
            </svg>
            <span className="text-sm text-ember">{STATUS_LABELS[status]}</span>
          </div>
        </div>
      ) : (
        <button
          onClick={handleGenerate}
          disabled={!urlValid}
          className="w-full rounded-xl bg-ember py-3 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-30"
        >
          🎙 Generate Podcast
        </button>
      )}

      {/* Success */}
      {status === "done" && (
        <div className="rounded-xl border border-green-500/20 bg-green-500/5 px-4 py-3 text-sm text-green-400">
          ✓ Episode ready — check the list on the right!
        </div>
      )}

      {/* Error */}
      {status === "error" && (
        <div className="rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3">
          <p className="text-sm text-red-400">{errorMsg}</p>
          <button
            onClick={() => setStatus("idle")}
            className="text-xs text-red-400/60 hover:text-red-400 mt-1 underline"
          >
            Try again
          </button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/toolkits/podcast-generator.tsx
git commit -m "feat: PodcastGenerator form with SSE progress streaming"
```

---

## Task 13: Frontend — Podcast tool page

**Files:**
- Create: `frontend/src/app/toolkits/podcast/page.tsx`

- [ ] **Step 1: Create the page**

Create `frontend/src/app/toolkits/podcast/page.tsx`:

```tsx
"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { PodcastGenerator } from "@/components/toolkits/podcast-generator";
import { PodcastEpisodeList } from "@/components/toolkits/podcast-episode-list";

interface Episode {
  id: number;
  video_title: string | null;
  digest_length_mins: number;
  format: string;
  duration_secs: number | null;
  created_at: string;
}

export default function PodcastPage() {
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

  // Load existing episodes on mount
  useEffect(() => {
    fetch(`${apiBase}/podcast/episodes`)
      .then((r) => r.json())
      .then((data: Episode[]) => setEpisodes(data))
      .catch(() => {});
  }, [apiBase]);

  const handleNewEpisode = useCallback((ep: Episode) => {
    setEpisodes((prev) => [ep, ...prev]);
  }, []);

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <Link
          href="/toolkits"
          className="text-xs text-cream/30 hover:text-cream/60 transition-colors mb-2 inline-flex items-center gap-1"
        >
          ← Toolkits
        </Link>
        <div className="flex items-center gap-3">
          <span className="text-3xl">🎙</span>
          <div>
            <span className="text-xs font-semibold uppercase tracking-[0.28em] text-ember">
              Toolkits
            </span>
            <h1 className="font-display text-2xl text-cream leading-tight">
              YouTube Podcast
            </h1>
          </div>
        </div>
        <p className="text-cream/40 text-sm mt-1 ml-12">
          Paste a YouTube link — get a digested Chinese podcast episode.
        </p>
      </div>

      {/* Split panel */}
      <div className="grid grid-cols-1 lg:grid-cols-[2fr_3fr] gap-0 rounded-2xl border border-white/10 overflow-hidden min-h-[600px]">
        {/* Left: generator */}
        <div className="border-b lg:border-b-0 lg:border-r border-white/10 bg-white/[0.02] p-6">
          <PodcastGenerator onEpisodeReady={handleNewEpisode} />
        </div>

        {/* Right: episode library */}
        <div className="p-6">
          <div className="mb-4">
            <span className="text-xs font-semibold uppercase tracking-[0.28em] text-cream/40">
              My Episodes
            </span>
            <span className="ml-2 text-[10px] text-cream/20">
              {episodes.length > 0 ? `${episodes.length} episode${episodes.length === 1 ? "" : "s"}` : ""}
            </span>
          </div>
          <PodcastEpisodeList episodes={episodes} />
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/toolkits/podcast/page.tsx
git commit -m "feat: YouTube Podcast split-panel page"
```

---

## Task 14: Sidebar nav update

**Files:**
- Modify: `frontend/src/components/layout/sidebar-nav.tsx`

- [ ] **Step 1: Add Wrench icon import and Toolkits nav item**

In `frontend/src/components/layout/sidebar-nav.tsx`, update the import line:

```tsx
import { Brain, Briefcase, FileText, Gauge, GraduationCap, Menu, MessageSquare, Search, Settings, SquareTerminal, BookOpen, Wrench, X } from "lucide-react";
```

Then update the `items` array to add Toolkits between Resume and Jobs:

```tsx
const items = [
  { href: "/", label: "Dashboard", icon: Gauge },
  { href: "/learn", label: "Learn", icon: GraduationCap },
  { href: "/practice", label: "Practice", icon: SquareTerminal },
  { href: "/review", label: "Review", icon: Brain },
  { href: "/interview", label: "Interview", icon: BookOpen },
  { href: "/projects", label: "Portfolio", icon: Briefcase },
  { href: "/resume", label: "Resume", icon: FileText },
  { href: "/toolkits", label: "Toolkits", icon: Wrench },
  { href: "/jobs/live", label: "Jobs", icon: Search },
  { href: "/copilot", label: "Copilot", icon: MessageSquare },
  { href: "/settings", label: "Settings", icon: Settings },
];
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/layout/sidebar-nav.tsx
git commit -m "feat: add Toolkits to sidebar navigation"
```

---

## Task 15: Deploy

- [ ] **Step 1: Tag and push to trigger CI/CD**

```bash
git tag v0.25.0
git push origin main
git push origin v0.25.0
```

- [ ] **Step 2: Monitor GitHub Actions**

Watch the Actions tab — the workflow should build both Docker images, push to GHCR, SSH into the VPS, pull the new images, and restart containers. Expected duration: ~4–6 minutes.

- [ ] **Step 3: Smoke test in production**

1. Open the portal, confirm **Toolkits** appears in the sidebar
2. Click Toolkits → confirm the KPI cards page renders
3. Click **YouTube Podcast** → confirm the split-panel page loads
4. Paste a short YouTube video URL (~5 min video), select **单人叙述**, click **Generate Podcast**
5. Confirm SSE progress steps appear in order
6. Confirm the episode appears in the right panel with a working audio player
7. Click download — confirm MP3 saves
8. Repeat with **双人对话** format — confirm the episode shows the `对话` badge

---

## Self-Review Notes

- ✅ Spec: Sidebar Toolkits entry → Task 14
- ✅ Spec: KPI card grid with coming-soon placeholders → Tasks 9 + 10
- ✅ Spec: Split panel layout (left form, right list) → Tasks 11 + 12 + 13
- ✅ Spec: SSE progress stream → Task 7 + Task 12
- ✅ Spec: Single narrative format (one ElevenLabs call) → Tasks 5 + 6 + 7
- ✅ Spec: Dialogue format (parse lines, two voices, pydub stitch) → Tasks 5 + 6 + 7
- ✅ Spec: format badge 单人/对话 in episode list → Task 11
- ✅ Spec: PodcastEpisode model with `format` column → Task 3
- ✅ Spec: ElevenLabs voice IDs A + B in config → Task 2
- ✅ Spec: Docker volume for audio storage → Task 8
- ✅ Spec: ffmpeg in Dockerfile → Task 1
- ✅ Spec: yt-dlp transcript extraction + error for no subtitles → Task 4
- ✅ Spec: Download endpoint → Task 7
- ✅ Spec: URL validation frontend + backend → Tasks 7 + 12

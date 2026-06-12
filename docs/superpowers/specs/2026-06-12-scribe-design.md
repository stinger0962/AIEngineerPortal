# 录 Scribe — Design Spec

**Date:** 2026-06-12
**Status:** Approved (risk spike passed)
**Suite:** 蒸馏所 Distill

---

## Overview

A new toolkit: **录 Scribe**. Paste a YouTube URL — especially **caption-less**
videos that 炼 Forge / 织 Loom can't handle — and get a faithful text transcript
in the spoken language, which you can read, copy, and download.

Scribe is the **audio→text foundation** for the suite: it unlocks audio sources,
and 配 Dub (next) will build directly on it.

### De-risk spike (already done)
Verified on the production VPS that **yt-dlp downloads YouTube audio through the
Webshare residential proxy with no bot block** (a 20s clip pulled cleanly). The
risky unknown is resolved before committing to the build.

---

## Scope

### In scope (v1)
- Input: **YouTube URL** (any language; primary value = caption-less videos)
- Pipeline: yt-dlp audio download (via proxy) → ffmpeg normalize → chunk →
  OpenAI Whisper → concatenated transcript
- Output: faithful **source-language transcript** (Whisper transcribes, does not
  translate — translation belongs to Loom / Dub)
- Persisted history: list, view (scrollable), copy, download `.txt`, delete
- SSE progress (downloading → transcribing → done)

### Out of scope (later)
- Audio file upload / direct audio URL / Bilibili / Ximalaya (future inputs)
- Translation or summary of the transcript (use 织 Loom on the text)
- 配 Dub (separate spec; builds on Scribe)
- Auto-fallback into Forge/Loom for caption-less videos (possible later)

---

## Architecture

```
YouTube URL
  → validate (reuse YOUTUBE_REGEX)
  → yt-dlp -f bestaudio --proxy <Webshare>   → audio file (+ video title from metadata)
  → ffmpeg → 16kHz mono mp3                    (small, Whisper-optimal)
  → if file > ~24MB: split into chunks (pydub)  (OpenAI 25MB/request limit)
  → OpenAI Whisper (whisper-1) per chunk → concatenate text
  → save ScribeTranscript row
  → SSE "done"; library shows it → view / copy / download / delete
```

---

## Backend

### New files
```
backend/app/services/scribe_service.py     # download + transcribe orchestration
backend/app/api/v1/routes/scribe.py        # SSE generate, list, delete, download
backend/tests/test_scribe_service.py
backend/tests/test_scribe_routes.py
```

### Dependencies (`requirements.txt`)
- Re-add `yt-dlp` (latest)
- Add `openai>=1.0` (Whisper client)
- `ffmpeg` (already in the Docker image) + `pydub` (already present) for
  normalize/chunk

### `scribe_service.py`
```python
def download_audio(youtube_url: str) -> tuple[str, str]:
    """yt-dlp -> (title, audio_path). Routes through the Webshare proxy when
    WEBSHARE_PROXY_USERNAME/PASSWORD are set. Post-processes to 16kHz mono mp3.
    Raises ValueError on download failure."""

def transcribe_audio(audio_path: str, openai_api_key: str) -> str:
    """Chunk if needed (>~24MB) and call OpenAI Whisper (whisper-1) per chunk;
    return the concatenated transcript. Raises ValueError on API failure."""

def scribe_youtube(youtube_url: str, openai_api_key: str) -> tuple[str, str]:
    """Orchestrator -> (title, transcript)."""
```
- yt-dlp options: `format="bestaudio"`, `proxy=<webshare>`, `noplaylist=True`,
  postprocessor `FFmpegExtractAudio` to mp3 + `postprocessor_args` for
  `-ar 16000 -ac 1`. Write to a temp dir; clean up after.
- Title comes from yt-dlp's `info["title"]` (no oEmbed needed).
- Chunking: load with pydub, split into ≤ ~10-minute / ≤24MB segments, Whisper
  each, join with spaces.
- Whisper call: `OpenAI(api_key=...).audio.transcriptions.create(model="whisper-1",
  file=open(path,"rb"))` → `.text`. No `language` forced (auto-detect).

### Data model — `ScribeTranscript` (`entities.py`)
```python
class ScribeTranscript(Base):
    __tablename__ = "scribe_transcripts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    youtube_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```
A **new table** → created automatically by `Base.metadata.create_all()` on startup
(no ALTER, no migration needed — only adding columns to existing tables requires
the bootstrap patch).

### Routes (`scribe.py`)
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/scribe/generate` | SSE: downloading → transcribing → done |
| `GET` | `/api/v1/scribe/list` | All transcripts, newest first |
| `DELETE` | `/api/v1/scribe/{id}` | Delete a transcript row |
| `GET` | `/api/v1/scribe/{id}/download` | Stream the transcript as `.txt` |

SSE events: `{"status":"downloading","message":"Downloading audio..."}`,
`{"status":"transcribing","message":"Transcribing with Whisper..."}`,
`{"status":"done","item":{...}}`, `{"status":"error","message":"..."}`.
Validate the YouTube URL (422 if invalid).

### Config / secret
- `openai_api_key: str = ""` in `Settings`; env `OPENAI_API_KEY`.
- Injected via the deploy workflow `upsert_env OPENAI_API_KEY` from a new GitHub
  secret. Docker-compose passes `OPENAI_API_KEY`.

---

## Frontend

### Hub card (`app/toolkits/page.tsx`)
Add a third ready card: **录 Scribe**, accent **indigo** (`#4f5bd5`), icon
`AudioLines` (lucide). Role line `YOUTUBE → 文字稿`, aux: "把无字幕的 YouTube
视频转写成文字稿（原语言）". The placeholders strip already collapses the rest.

### `/toolkits/scribe/page.tsx`
Same split-panel + mobile generate/library tabs as Forge/Loom, themed indigo
(reuse the pattern; indigo where Loom uses teal). Header icon = AudioLines in an
indigo gradient tile.

### Components
- `scribe-generator.tsx` — YouTube URL input + Generate; SSE progress
  (下载音频 → 转写中); on done, prepend to list + switch to library tab on mobile.
- `scribe-list.tsx` — transcript cards (title, date, char count); expand →
  scrollable transcript box + **复制 / 下载 .txt / 删除** actions.

### Dependencies
Frontend: none new.

---

## Error handling

| Scenario | Handling |
|----------|----------|
| Invalid YouTube URL | 422 before stream |
| yt-dlp download fails (blocked / private / unavailable) | SSE error: "无法下载该视频的音频，请稍后重试。" |
| Audio too long / Whisper API error | SSE error with a clear message |
| Empty transcript | SSE error: "转写结果为空。" |

---

## Testing

Backend (mock yt-dlp + OpenAI — no network):
- `download_audio`: builds correct yt-dlp opts incl. proxy; returns (title, path);
  download failure raises.
- `transcribe_audio`: chunking threshold logic; mock OpenAI client → concatenated
  text; API failure raises.
- Route: invalid URL → 422; list/delete (TestClient).

Frontend: `tsc --noEmit` passes; manual check of generate + view + copy/download on
desktop and mobile.

---

## Deployment

Standard pipeline (commit → tag → Actions → GHCR → VPS). `yt-dlp` + `openai` ship
in the backend image; `scribe_transcripts` table auto-created on startup. New
secret **`OPENAI_API_KEY`** (GitHub → injected via `upsert_env`).

**Build gate:** Task 1 of the plan re-confirms the yt-dlp→ffmpeg→Whisper chain on
the VPS (the spike already proved the download half) before wiring the full tool.

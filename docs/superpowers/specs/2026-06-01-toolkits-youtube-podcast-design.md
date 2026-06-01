# Toolkits + YouTube Podcast Feature — Design Spec

**Date:** 2026-06-01  
**Status:** Approved  

---

## Overview

Add a **Toolkits** section to the AI Engineer Portal — a hub for standalone utility tools. The first tool is **YouTube Podcast**: paste a YouTube URL, receive a digested Chinese-language MP3 podcast episode (~5 min) powered by Claude (digest + translate) and ElevenLabs TTS.

---

## UI Design Decisions

### Sidebar
- New nav item: `{ href: "/toolkits", label: "Toolkits", icon: Wrench }` added to `sidebar-nav.tsx`
- Positioned between Resume and Jobs

### `/toolkits` — Toolkits Index Page
- Layout: **Big KPI Cards** (Option C from mockup selection)
- 2-column grid of tool cards
- Each card: large emoji icon, tool name, short description, capability tags, status badge
- Placeholder "coming soon" cards for Doc Builder, Job Scanner, + Request a tool (dashed border)
- Clicking a card navigates to the tool's dedicated page

### `/toolkits/podcast` — Podcast Tool Page
- Layout: **Split Panel** (Option B from mockup selection)
- **Left panel (~45%):** Generate form
  - YouTube URL input
  - Digest length selector (5 min / 10 min)
  - Voice selector (dropdown, defaults to Xiaoxiao Neural)
  - Generate button with loading state
  - Real-time progress via SSE (Extracting transcript → Digesting → Translating → Generating audio)
- **Right panel (~55%):** Episode library
  - List of generated episodes (title, duration, date)
  - Play button (HTML5 audio inline)
  - Download button (MP3)
  - Empty state when no episodes yet

---

## Architecture

### Frontend (Next.js)

```
frontend/src/
  app/
    toolkits/
      page.tsx                   # Toolkits index — KPI cards grid
      podcast/
        page.tsx                 # Podcast tool — split panel UI
  components/
    toolkits/
      toolkit-card.tsx           # Reusable KPI card component
      podcast-generator.tsx      # Left panel: form + SSE progress
      podcast-episode-list.tsx   # Right panel: episode library
```

### Backend (FastAPI)

```
backend/app/
  api/v1/routes/
    podcast.py                   # Route handlers
  services/
    podcast_service.py           # Orchestration logic
  models/
    entities.py                  # PodcastEpisode model (added)
```

**Routes:**
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/podcast/generate` | Start generation job, stream SSE progress |
| `GET` | `/api/v1/podcast/episodes` | List all episodes |
| `GET` | `/api/v1/podcast/episodes/{id}/download` | Stream MP3 file |

### Database

New table: `podcast_episodes`

```sql
CREATE TABLE podcast_episodes (
    id          SERIAL PRIMARY KEY,
    youtube_url TEXT NOT NULL,
    video_title TEXT,
    digest_length_mins INTEGER NOT NULL DEFAULT 5,
    script_zh   TEXT,
    audio_path  TEXT NOT NULL,
    duration_secs INTEGER,
    created_at  TIMESTAMP DEFAULT now()
);
```

SQLAlchemy model added to `backend/app/models/entities.py`.  
Alembic migration created for the new table.

---

## Data Flow

```
1. User pastes YouTube URL + selects digest length → clicks Generate
2. Frontend opens SSE connection to POST /podcast/generate
3. Backend streams progress events:
   - {"status": "extracting", "message": "Fetching transcript..."}
   - {"status": "digesting",  "message": "Digesting with Claude..."}
   - {"status": "translating","message": "Translating to Chinese..."}
   - {"status": "tts",        "message": "Generating audio..."}
   - {"status": "done",       "episode": {...}}
4. yt-dlp extracts transcript (subtitles, auto-generated fallback)
5. Claude API: digest + translate to spoken Chinese podcast script
6. ElevenLabs API: text → MP3 bytes (zh-CN Xiaoxiao Neural voice)
7. MP3 saved to /data/podcast_audio/{episode_id}.mp3 (Docker volume)
8. Episode metadata saved to DB
9. SSE sends "done" event with episode data
10. Frontend adds episode to right panel list
```

---

## Claude Prompt Design

```python
PODCAST_PROMPT = """你是一位专业的中文播客主持人。请将以下英文视频讲稿整理为一期播客脚本。

要求：
1. 长度约为原文的{pct}%，提炼最核心的观点（目标时长：{target_mins}分钟）
2. 语气自然口语化，像在和听众轻松对话
3. 开头一句话引入主题，结尾一句话总结收尾
4. 保留最重要的例子、数据和结论
5. 直接输出播客脚本，不要任何说明或前言

讲稿内容：
{transcript}"""
```

Digest percentages: 5 min → 30% of original, 10 min → 60%.

---

## ElevenLabs Integration

- **Voice:** `Xiaoxiao` (zh-CN-XiaoxiaoNeural) via ElevenLabs multilingual v2 model
- **API endpoint:** `POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}`
- **Config:**
  ```
  ELEVENLABS_API_KEY=sk_8cc654...
  ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
  ```
- Key added to `Settings` in `backend/app/core/config.py`
- Key added to `.env` (not committed) and `.env.example` (placeholder)

---

## Docker / Storage

- New bind mount in `docker-compose.yml`:
  ```yaml
  volumes:
    - podcast_audio:/data/podcast_audio
  ```
- Audio files served directly via FastAPI `FileResponse`
- No CDN needed (personal use, low volume)

---

## Dependencies

**Backend (added to requirements.txt):**
```
yt-dlp
elevenlabs
sse-starlette
```

**Frontend:** No new npm packages — uses native `EventSource` for SSE, HTML5 `<audio>` for playback.

---

## Error Handling

| Scenario | Handling |
|----------|----------|
| Invalid YouTube URL | Frontend validates before submit; 422 from backend |
| Video has no subtitles | SSE error event: "This video has no available subtitles" |
| yt-dlp network failure | SSE error event with retry suggestion |
| ElevenLabs API error | SSE error event; 402 if quota exceeded |
| Claude API error | SSE error event |
| Audio file missing on download | 404 with clear message |

---

## Out of Scope

- User authentication (portal is single-user)
- Background job queue (synchronous SSE is sufficient for personal use)
- Audio player controls beyond play/pause (browser native handles it)
- Bilibili support (YouTube only for now)
- Voice cloning or custom voices

# 配 Dub — Design Spec

**Date:** 2026-06-12
**Status:** Approved
**Suite:** 蒸馏所 Distill

---

## Overview

A new toolkit: **配 Dub**. Paste a foreign-language YouTube URL → get a
**Chinese voice-over dubbed video** (mp4) you can play inline and download. The
original audio is ducked to a faint background; Chinese narration is time-aligned
to the original speech.

This is the suite's most complex tool — it handles **video** (not just text/audio)
and the **time-alignment** between Chinese narration and the original timing.

### Built on prior work (near-total reuse, zero new dependencies)
- yt-dlp (added for 录 Scribe) — video download via the Webshare proxy
- OpenAI Whisper (Scribe) — now with **segment timestamps** (`verbose_json`)
- Claude (Loom/Forge) — translation
- MiniMax `_tts_bytes` (炼 Forge) — Chinese narration
- ffmpeg + pydub (present) — speed-fit, ducking, muxing

---

## Scope

### In scope (v1)
- Input: **YouTube URL** (foreign language), **duration ≤ 10 minutes** (rejected otherwise)
- Voice: single MiniMax narrator, chosen from the existing narration picker (8 + 随机)
- Output: an **mp4** — original video, original audio ducked to ~12%, Chinese
  voice-over time-aligned to the original segments
- Persisted library: inline `<video>` playback, download mp4, delete
- SSE progress: downloading → transcribing → translating → voicing → composing → done

### Out of scope (later)
- Lip-sync (needs GPU / paid API — explicitly excluded)
- Length > 10 min, file upload, non-YouTube sources
- Per-segment voice/emotion control, multi-speaker casting
- Subtitle burn-in
- Auto-cleanup of old mp4s (manual delete for now)

---

## Architecture / data flow

```
YouTube URL
  → validate + yt-dlp metadata (extract_info download=False) → duration
       duration > 600s → SSE error "视频超过 10 分钟上限"
  → yt-dlp download merged mp4 (<=720p) via Webshare proxy → video_path
  → ffmpeg extract 16kHz mono mp3 (<=10min => <25MB, single Whisper call)
  → OpenAI Whisper response_format="verbose_json" → segments[{start,end,text}]
  → Claude (one call): translate all segment texts → Chinese (numbered, 1:1)
  → for each segment: MiniMax _tts_bytes(zh) → clip
  → ALIGN (see algorithm) → Chinese voice track
  → ffmpeg: duck original audio (-18dB ≈ ~12%) + overlay voice track → final audio
  → ffmpeg: mux final audio onto original video → out.mp4
  → save DubVideo row + /data/dub_videos/{id}.mp4
  → SSE "done"; library plays/downloads it
```

---

## The alignment algorithm (the quality crux)

Anchor each Chinese clip to the original segment's start; mild speed-up only when
needed; overflow pushes later clips so nothing overlaps.

```
MAX_SPEED = 1.25            # cap atempo (preserves pitch via ffmpeg)
DUCK_DB   = -18             # original audio gain ≈ 12% amplitude

base = silence(length = video_duration_ms)
cursor = 0                  # end position of the last placed clip (ms)
for seg, zh_text in zip(segments, zh_texts):
    start_ms = seg.start * 1000
    slot_ms  = (seg.end - seg.start) * 1000
    clip     = tts(zh_text)                     # natural MiniMax audio
    if len(clip) > slot_ms and slot_ms > 0:
        ratio = min(len(clip) / slot_ms, MAX_SPEED)
        clip  = atempo(clip, ratio)             # ffmpeg atempo, pitch-preserving
    pos  = max(start_ms, cursor)                # anchor to start, never overlap
    base = base.overlay(clip, position=pos)
    cursor = pos + len(clip)

final_audio = original_audio.apply_gain(DUCK_DB).overlay(base)
```

- **atempo** is applied via ffmpeg (`-filter:a atempo=<ratio>`, ratio ≤ 1.25) so
  pitch is preserved (pydub's `speedup` shifts pitch — not used).
- Short clips are left natural (silence fills the rest of the slot) — no slowing
  down, which sounds dragged.
- `cursor` carries cumulative drift forward so long passages stay in order.

---

## Backend

### New files
```
backend/app/services/dub_service.py        # download, transcribe(segments), translate, align, compose
backend/app/api/v1/routes/dub.py           # SSE generate, list, delete, video
backend/tests/test_dub_service.py          # alignment + translation-parse + duration guard
backend/tests/test_dub_routes.py
```

### `dub_service.py` (key functions)
```python
MAX_DURATION_S = 600

def probe_duration(youtube_url: str) -> int:
    """yt-dlp extract_info(download=False) -> duration seconds. Raises ValueError."""

def download_video(youtube_url: str, out_dir: str) -> tuple[str, str]:
    """yt-dlp merged mp4 (<=720p) via Webshare proxy. Returns (title, video_path)."""

def extract_segments(video_path: str, openai_api_key: str) -> list[dict]:
    """ffmpeg -> 16kHz mono mp3; Whisper verbose_json -> [{start,end,text}]."""

def translate_segments(segments: list[dict], anthropic_api_key: str, model: str) -> list[str]:
    """One Claude call, numbered 1:1. On count mismatch, fall back to original-length
    best-effort (pad/truncate) so alignment never crashes."""

def build_voice_track(segments, zh_texts, voice_id, mm_key, mm_group, mm_model, mm_base, video_ms) -> AudioSegment:
    """TTS each zh segment (reuse podcast_service._tts_bytes), speed-fit + anchor-place."""

def compose(video_path: str, voice_track, out_path: str) -> int:
    """Duck original audio, overlay voice track, mux onto video. Returns duration secs."""
```
- Reuse `validate_youtube_url`, `_tts_bytes`, `resolve_voice` from `podcast_service`.
- `_atempo(clip, ratio)` helper: export → ffmpeg atempo → reload.

### Data model — `DubVideo` (`entities.py`)
```python
class DubVideo(Base):
    __tablename__ = "dub_videos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    youtube_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    voice_id: Mapped[str] = mapped_column(Text, nullable=False)
    video_path: Mapped[str] = mapped_column(Text, nullable=False)
    duration_secs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```
New table → created by `create_all` (no migration).

### Routes (`dub.py`)
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/dub/generate` | SSE: downloading→transcribing→translating→voicing→composing→done |
| `GET` | `/api/v1/dub/list` | All dubs, newest first |
| `DELETE` | `/api/v1/dub/{id}` | Delete row + mp4 file |
| `GET` | `/api/v1/dub/{id}/video` | `FileResponse` mp4 (range-enabled → inline player + download) |

Request: `{ youtube_url, voice_id }` (voice_id may be `"random"` → `resolve_voice`).

### Storage
- mp4 saved to `/data/dub_videos/{id}.mp4`. New `dub_videos` named volume in
  `docker-compose.prod.yml` (mirrors `podcast_audio`).

### Config / deps
- Reuses `openai_api_key`, `anthropic_api_key`, `ai_model`, `minimax_*`. **No new
  secret.**
- **No new pip deps** (yt-dlp, openai, anthropic, pydub all present; ffmpeg in image).

---

## Frontend

### Hub card (`app/toolkits/page.tsx`)
Fourth ready card **配 Dub**, accent **rose** (Tailwind `rose-600`), icon
`Languages` (lucide). Role `外语视频 → 中文配音`, aux: "把外语 YouTube 视频配成中文
旁白视频（原声压低做背景）".

### `/toolkits/dub/page.tsx`
Split panel + mobile generate/library tabs, rose-themed (rose where Loom uses teal).

### Components
- `dub-generator.tsx` — YouTube URL + **voice picker** (fetch `GET /podcast/voices`,
  same 摘要/narration list + 随机) + Generate; multi-phase SSE progress
  (下载视频 → 转写 → 翻译 → 配音 → 合成).
- `dub-list.tsx` — video cards (title, duration, date) → expand to inline
  `<video controls src=/dub/{id}/video>` + 下载 + 删除.

### Dependencies
Frontend: none new.

---

## Error handling

| Scenario | Handling |
|----------|----------|
| Invalid URL | 422 before stream |
| Duration > 600s | SSE error: "视频超过 10 分钟上限，请换更短的视频。" |
| Download fails | SSE error: "无法下载该视频，请稍后重试。" |
| No speech / empty segments | SSE error: "未检测到可转写的语音。" |
| Translation count mismatch | best-effort pad/truncate (never crash); proceed |
| Whisper / TTS / ffmpeg failure | SSE error with a clear message |

---

## Testing

Backend (mock yt-dlp / OpenAI / MiniMax / ffmpeg — no network):
- `probe_duration` rejects > 600s.
- `build_voice_track` alignment: with fake clip durations + segments, assert
  placement positions, atempo applied only when over-slot + capped at 1.25, and
  overflow pushes the next clip (cursor logic).
- `translate_segments`: numbered parse 1:1; count-mismatch fallback.
- Route: invalid URL → 422; list/delete (TestClient).

Frontend: `tsc --noEmit` passes; manual check of generate + inline playback +
download on desktop and mobile.

---

## Deployment

Standard pipeline. New `dub_videos` volume; `dub_videos` table auto-created. No new
secret, no new pip dep. **Plan Task 1 = spike**: confirm yt-dlp downloads a real
YouTube *video* (merged mp4) through the proxy on the VPS before wiring the tool
(the audio half is already proven; video is the same mechanism, larger files).

**Disk note:** dubbed mp4s accumulate in the `dub_videos` volume (the deploy prune
does not touch named volumes). Users delete from the library; a future auto-cleanup
is out of scope.

**Time/cost note:** a 10-min video ≈ download + 1 Whisper call + 1 Claude call +
~dozens of MiniMax TTS calls + ffmpeg compose ≈ a few minutes wall-clock; SSE keeps
the user informed throughout.

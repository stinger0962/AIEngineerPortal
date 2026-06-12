# 配 Dub — 本地视频上传 Design Spec

**Date:** 2026-06-12
**Status:** Approved (pending spec review)
**Suite:** 蒸馏所 Distill
**Extends:** [配 Dub](2026-06-12-dub-design.md) (shipped v0.41.0)

---

## Overview

Add a second input source to **配 Dub**: instead of only a YouTube URL, the user
can **upload a local video file** (e.g. a video saved on their phone) and get the
same Chinese voice-over dubbed mp4 back. Everything downstream of "obtain a local
video file" is already source-agnostic and fully reused.

This is a thin front-of-pipeline extension — no change to the alignment/voicing/
compose core.

---

## Key decisions (user-approved)

| Decision | Value |
|----------|-------|
| Upload size cap | **100 MB** (client- AND server-enforced) |
| Duration cap | ≤ 10 min (existing), enforced on uploads via **ffprobe** |
| Uploaded original video | **Deleted immediately after compose** (lives only in a `TemporaryDirectory`) |
| Dubbed output mp4 | Persisted to the library (re-watch/download) |
| Output retention | **Auto-delete dubs older than 7 days** (opportunistic purge, no cron) |
| UI | A **「链接 / 上传」toggle** on the existing Dub page (not a new card) |

---

## Architecture / data flow

```
Upload mode:
  <input type=file accept=video/*>  → client rejects > 100 MB before upload
  → POST /dub/generate-upload (multipart: file + voice_id)  [SSE]
  → server rejects > 100 MB (Content-Length + byte count) → 413 / SSE error
  → save file into TemporaryDirectory()                     ← auto-deleted on exit
  → ffprobe duration; > 600s → SSE error "视频超过 10 分钟上限"
  → [SHARED PIPELINE] extract_segments → translate → build_voice_track → compose
  → save DubVideo row + /data/dub_videos/{id}.mp4
  → SSE "done"

YouTube mode: unchanged (POST /dub/generate, JSON).
Both call the same `_run_dub_pipeline(...)` generator after a local video_path exists.
```

The temp dir holding the uploaded file is the **same mechanism** the YouTube flow
already uses for its download, so "delete the original after the job" is automatic.

---

## De-risking (verified before spec)

- **`python-multipart` is NOT in `requirements.txt`** (only transitively present
  locally; FastAPI does not pull it by default). The prod image would 500 on the
  upload endpoint import. **Fix: add `python-multipart==0.0.17` to
  `requirements.txt`.** This is Task 1 and the single biggest risk.
- `ffprobe` ships with the ffmpeg already in the image — no new dep for duration.
- No existing multipart endpoint to copy — this is the first one.

---

## Backend

### Deps
- **Add `python-multipart==0.0.17`** to `backend/requirements.txt`. No other new dep.

### `dub_service.py` additions
```python
MAX_UPLOAD_BYTES = 100 * 1024 * 1024     # 100 MB
DUB_RETENTION_DAYS = 7

def probe_local_duration(video_path: str) -> int:
    """ffprobe -> duration seconds. Raises ValueError if unreadable or > 600s."""

def purge_expired(db) -> int:
    """Delete DubVideo rows (and their mp4 files) older than DUB_RETENTION_DAYS.
    Returns count purged. Best-effort: a missing file never blocks row deletion."""
```
- Refactor the YouTube generate handler's body (extract→translate→voice→compose)
  into a shared helper so both endpoints reuse identical logic. The shared helper
  takes a local `video_path` + `title` + `voice_id` and yields SSE phase events.

### Routes (`dub.py`)
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/dub/generate` | **unchanged** — YouTube URL, JSON, SSE |
| `POST` | `/api/v1/dub/generate-upload` | **new** — multipart `file` + `voice_id`, SSE. Saves to temp, ffprobe duration guard, shared pipeline. `title` = uploaded filename (sans extension). |
| `GET` | `/api/v1/dub/list` | unchanged (calls `purge_expired` first) |
| `DELETE` | `/api/v1/dub/{id}` | unchanged |
| `GET` | `/api/v1/dub/{id}/video` | unchanged |

- Size enforcement: reject if `Content-Length > MAX_UPLOAD_BYTES` early; while
  streaming the upload to disk, count bytes and abort + delete if the cap is
  exceeded (defends against a missing/lying Content-Length).
- `purge_expired(db)` is called opportunistically at the **start of every generate
  request** (both endpoints) and on `list` — no scheduler/cron needed for a
  low-traffic app.

### Data model — `DubVideo`
- Uploads have no URL. **Make `youtube_url` nullable** (a safe relax-NOT-NULL
  ALTER applied via the existing `apply_runtime_schema_patches` in `bootstrap.py`;
  new installs get it from the model definition). For uploads, `youtube_url = NULL`
  and `title` = the original filename. `youtube_url` is not shown in the card, so
  no other UI impact. `DubOut.youtube_url` becomes `Optional[str]`.

### Storage / cleanup
- Output unchanged: `/data/dub_videos/{id}.mp4` in the `dub_videos` volume.
- Auto-cleanup via `purge_expired` (7-day TTL). The uploaded **input** never
  touches the volume — it lives only in a temp dir and is gone after compose.

### Config / proxy / body size
- No new secret. Confirm Caddy passes 100 MB bodies (Caddy has **no** default
  request-body limit, so this should already work; the plan verifies it).

---

## Frontend

### `dub-generator.tsx`
- Add a segmented **「🔗 链接 / 📁 上传」toggle** at the top.
- **链接 mode:** the existing YouTube URL input + validation (unchanged).
- **上传 mode:** `<input type="file" accept="video/*">`; show selected filename +
  size; **client-side reject > 100 MB** with a clear message before any upload;
  Generate posts `FormData(file, voice_id)` to `/dub/generate-upload` and reads the
  same SSE stream.
- Shared: voice picker + the 5-phase SSE progress UI are reused as-is. During
  upload (before the first SSE event) show an indeterminate "上传中..." state.
- `Dub.youtube_url` type becomes `string | null`.

### Other files
- `dub-list.tsx`, `app/toolkits/dub/page.tsx`, hub card: unchanged (the card still
  reads "外语视频 → 中文配音"; copy may gain "支持链接或本地上传").

### Deps
Frontend: none new.

---

## Error handling

| Scenario | Handling |
|----------|----------|
| File > 100 MB | Client rejects pre-upload; server returns 413 / SSE error "文件超过 100MB 上限" |
| Non-video file | `accept="video/*"` + server ffprobe failure → SSE error "无法识别为视频文件" |
| Duration > 600s | SSE error "视频超过 10 分钟上限，请换更短的视频。" |
| No speech | existing "未检测到可转写的语音。" |
| Whisper/TTS/ffmpeg failure | existing clear SSE error |

---

## Testing

Backend (no network; mock OpenAI/MiniMax, real ffprobe on a tiny fixture or mocked):
- `probe_local_duration` rejects > 600s and unreadable files.
- `purge_expired` deletes rows + files older than 7 days, keeps fresh ones, and
  tolerates a missing file.
- Route: upload endpoint rejects oversize (413/error) and a valid small fixture
  reaches the pipeline (pipeline mocked).
- Existing dub tests stay green.

Frontend: `tsc --noEmit` clean; manual check of link↔upload toggle, client-side
size reject, and end-to-end upload → inline playback + download on mobile + desktop.

---

## Deployment

Standard pipeline (tag → Actions → GHCR → VPS). **One new pip dep**
(`python-multipart`), so the backend image rebuilds. New table column nullability
via `apply_runtime_schema_patches`. No new secret, no new volume.

**Out of scope (later):** real-time upload progress bar (MVP shows "上传中…"),
non-video uploads, resumable/chunked upload, >100 MB, configurable retention.

# 配 Dub — Local Video Upload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let 配 Dub accept a locally-uploaded video (≤100 MB) as an alternative to a YouTube URL, reusing the entire transcribe→translate→voice→compose pipeline.

**Architecture:** Add a new multipart SSE route `/dub/generate-upload` that saves the file into a `TemporaryDirectory` (auto-deleted after compose), validates duration via ffprobe, then runs a shared pipeline generator that both the YouTube and upload routes call. Outputs persist to the existing library; an opportunistic `purge_expired` deletes dubs older than 7 days. Frontend gains a 链接/上传 toggle.

**Tech Stack:** FastAPI (UploadFile/Form), `python-multipart`, ffprobe, SQLAlchemy, sse-starlette, Next.js/React/Tailwind.

**Spec:** `docs/superpowers/specs/2026-06-12-dub-upload-design.md`

---

## File structure

- `backend/requirements.txt` — add `python-multipart==0.0.17` (Task 1)
- `backend/app/models/entities.py` — `DubVideo.youtube_url` → nullable (Task 2)
- `backend/app/db/bootstrap.py` — add `NULLABILITY_PATCHES` + DROP NOT NULL logic (Task 2)
- `backend/app/services/dub_service.py` — add `MAX_UPLOAD_BYTES`, `DUB_RETENTION_DAYS`, `probe_local_duration`, `purge_expired` (Task 3)
- `backend/app/api/v1/routes/dub.py` — extract `_process_video` shared generator; add `/generate-upload`; `purge_expired` on generate+list; `DubOut.youtube_url` Optional (Task 4)
- `backend/tests/test_dub_service.py` — probe_local_duration + purge_expired tests (Task 3)
- `backend/tests/test_dub_model.py` — null youtube_url test (Task 2)
- `backend/tests/test_dub_routes.py` — upload oversize-reject test (Task 4)
- `frontend/src/components/toolkits/dub-generator.tsx` — 链接/上传 toggle + upload flow (Task 5)

---

## Task 1: Add python-multipart dependency

**Why first:** the upload route imports nothing new at module level, but FastAPI raises at request time ("Form data requires python-multipart") without it. The prod image installs only what's pinned in `requirements.txt`, and this package is currently absent. This is the single biggest deploy risk — pin it before any upload code exists.

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add the dependency**

Append to `backend/requirements.txt` (after `pydub>=0.25.1`):

```
python-multipart==0.0.17
```

- [ ] **Step 2: Verify it installs/imports**

Run: `cd backend && python -c "import multipart; print(multipart.__version__)"`
Expected: prints `0.0.17` (or compatible).

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "deps(dub): pin python-multipart for file uploads"
```

---

## Task 2: Make DubVideo.youtube_url nullable

**Files:**
- Modify: `backend/app/models/entities.py` (the `DubVideo` class)
- Modify: `backend/app/db/bootstrap.py`
- Test: `backend/tests/test_dub_model.py`

- [ ] **Step 1: Write the failing test**

Replace the contents of `backend/tests/test_dub_model.py` with:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.entities import DubVideo


def test_dubvideo_table_name():
    assert DubVideo.__tablename__ == "dub_videos"


def test_dubvideo_allows_null_youtube_url():
    """Uploaded videos have no source URL — the column must accept NULL."""
    engine = create_engine("sqlite://")
    DubVideo.__table__.create(bind=engine)
    with Session(engine) as s:
        d = DubVideo(youtube_url=None, title="local.mp4", voice_id="v1", video_path="/tmp/x.mp4")
        s.add(d)
        s.commit()
        s.refresh(d)
        assert d.id is not None
        assert d.youtube_url is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_dub_model.py -v`
Expected: `test_dubvideo_allows_null_youtube_url` FAILS — SQLite raises `IntegrityError: NOT NULL constraint failed: dub_videos.youtube_url`.

- [ ] **Step 3: Make the column nullable in the model**

In `backend/app/models/entities.py`, find the `DubVideo` class and change the `youtube_url` line from:

```python
    youtube_url: Mapped[str] = mapped_column(Text, nullable=False)
```

to:

```python
    youtube_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
```

(`Optional` is already imported in this module — it is used by `duration_secs`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_dub_model.py -v`
Expected: both tests PASS.

- [ ] **Step 5: Add the runtime nullability patch for the existing prod table**

`create_all` only relaxes the constraint on *new* databases; the existing prod `dub_videos` table (created at v0.41.0 with NOT NULL) needs an ALTER. In `backend/app/db/bootstrap.py`, add this constant after `SUMMARIES_COLUMN_PATCHES` (around line 50):

```python
# Columns whose NOT NULL must be relaxed on already-existing tables.
# (create_all handles new DBs; this handles the prod table created earlier.)
NULLABILITY_PATCHES = {
    "dub_videos": ["youtube_url"],
}
```

Then inside `apply_runtime_schema_patches`, immediately before the `# Apply index patches idempotently` comment (after the `all_patches` loop, around line 117), add:

```python
        # Relax NOT NULL on columns that gained nullable semantics later.
        # Postgres-only DDL; on SQLite the model's create_all already made it
        # nullable, so this is a guarded no-op there.
        if connection.dialect.name == "postgresql":
            for table_name, columns in NULLABILITY_PATCHES.items():
                if table_name not in existing_tables:
                    continue
                col_info = {c["name"]: c for c in inspector.get_columns(table_name)}
                for col in columns:
                    info = col_info.get(col)
                    if info is not None and info.get("nullable") is False:
                        connection.execute(
                            text(f"ALTER TABLE {table_name} ALTER COLUMN {col} DROP NOT NULL")
                        )
```

- [ ] **Step 6: Verify the whole backend suite still imports/passes**

Run: `cd backend && python -m pytest tests/test_dub_model.py tests/test_dub_service.py tests/test_dub_routes.py -v`
Expected: all PASS (existing dub tests unaffected; the new model test passes).

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/entities.py backend/app/db/bootstrap.py backend/tests/test_dub_model.py
git commit -m "feat(dub): make youtube_url nullable for uploaded videos (+ prod schema patch)"
```

---

## Task 3: dub_service — duration probe, retention purge, constants

**Files:**
- Modify: `backend/app/services/dub_service.py`
- Test: `backend/tests/test_dub_service.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_dub_service.py`:

```python
def test_probe_local_duration_rejects_too_long(monkeypatch):
    import app.services.dub_service as dub

    class R:
        stdout = "700.0"

    monkeypatch.setattr(dub.subprocess, "run", lambda *a, **k: R())
    with pytest.raises(ValueError, match="10 分钟"):
        dub.probe_local_duration("/tmp/x.mp4")


def test_probe_local_duration_returns_seconds(monkeypatch):
    import app.services.dub_service as dub

    class R:
        stdout = "300.5\n"

    monkeypatch.setattr(dub.subprocess, "run", lambda *a, **k: R())
    assert dub.probe_local_duration("/tmp/x.mp4") == 300


def test_probe_local_duration_rejects_non_video(monkeypatch):
    import app.services.dub_service as dub

    def boom(*a, **k):
        raise RuntimeError("not a video")

    monkeypatch.setattr(dub.subprocess, "run", boom)
    with pytest.raises(ValueError, match="无法识别为视频"):
        dub.probe_local_duration("/tmp/notvideo.txt")


def test_purge_expired_deletes_old_keeps_fresh(tmp_path):
    from datetime import datetime, timedelta
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    from app.models.entities import DubVideo
    import app.services.dub_service as dub

    engine = create_engine("sqlite://")
    DubVideo.__table__.create(bind=engine)

    old_file = tmp_path / "old.mp4"
    old_file.write_bytes(b"x")
    fresh_file = tmp_path / "fresh.mp4"
    fresh_file.write_bytes(b"y")

    now = datetime.utcnow()
    with Session(engine) as s:
        old = DubVideo(youtube_url=None, title="old", voice_id="v", video_path=str(old_file),
                       created_at=now - timedelta(days=8))
        fresh = DubVideo(youtube_url=None, title="fresh", voice_id="v", video_path=str(fresh_file),
                         created_at=now)
        missing = DubVideo(youtube_url=None, title="missing", voice_id="v",
                           video_path=str(tmp_path / "gone.mp4"),
                           created_at=now - timedelta(days=9))
        s.add_all([old, fresh, missing])
        s.commit()

        purged = dub.purge_expired(s)

        assert purged == 2  # old + missing
        remaining = s.scalars(select(DubVideo)).all()
        assert [d.title for d in remaining] == ["fresh"]

    assert not old_file.exists()      # file removed
    assert fresh_file.exists()        # fresh kept
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_dub_service.py -v -k "local_duration or purge"`
Expected: FAIL with `AttributeError: module 'app.services.dub_service' has no attribute 'probe_local_duration'` / `purge_expired`.

- [ ] **Step 3: Implement the constants and functions**

In `backend/app/services/dub_service.py`, update the constants block (lines 14-17) to add the two new constants:

```python
DUB_DIR = Path(os.getenv("DUB_VIDEO_DIR", "/data/dub_videos"))
MAX_DURATION_S = 600
MAX_UPLOAD_BYTES = 100 * 1024 * 1024   # 100 MB upload cap
DUB_RETENTION_DAYS = 7                  # auto-delete dubbed mp4s older than this
_MAX_SPEED = 1.25
_DUCK_DB = -18
```

Then append these two functions to the end of the file:

```python
def probe_local_duration(video_path: str) -> int:
    """ffprobe a local file for its duration (seconds). Raises ValueError if the
    file isn't a readable video or exceeds the 10-minute cap."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            check=True, capture_output=True, text=True,
        )
        dur = int(float(out.stdout.strip()))
    except Exception as exc:
        raise ValueError("无法识别为视频文件，请换一个文件。") from exc
    if dur <= 0:
        raise ValueError("无法读取视频时长。")
    if dur > MAX_DURATION_S:
        raise ValueError("视频超过 10 分钟上限，请换更短的视频。")
    return dur


def purge_expired(db) -> int:
    """Delete DubVideo rows (and their mp4 files) older than DUB_RETENTION_DAYS.
    Best-effort on files: a missing/unremovable file never blocks row deletion.
    Returns the number of rows purged."""
    from datetime import datetime, timedelta
    from sqlalchemy import select
    from app.models.entities import DubVideo

    cutoff = datetime.utcnow() - timedelta(days=DUB_RETENTION_DAYS)
    stale = db.scalars(select(DubVideo).where(DubVideo.created_at < cutoff)).all()
    count = 0
    for d in stale:
        try:
            p = Path(d.video_path)
            if p.exists():
                p.unlink()
        except OSError:
            pass
        db.delete(d)
        count += 1
    if count:
        db.commit()
    return count
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_dub_service.py -v`
Expected: all dub_service tests PASS (the 5 original + 4 new).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/dub_service.py backend/tests/test_dub_service.py
git commit -m "feat(dub): probe_local_duration + purge_expired (7-day TTL) + upload cap const"
```

---

## Task 4: dub.py — shared pipeline + upload route + purge wiring

**Files:**
- Modify: `backend/app/api/v1/routes/dub.py`
- Test: `backend/tests/test_dub_routes.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_dub_routes.py`:

```python
def test_dub_upload_rejects_oversize(monkeypatch):
    # Shrink the cap so a tiny test file trips the server-side byte counter.
    import app.services.dub_service as dub
    monkeypatch.setattr(dub, "MAX_UPLOAD_BYTES", 4)

    files = {"file": ("clip.mp4", b"way more than four bytes", "video/mp4")}
    r = client.post("/api/v1/dub/generate-upload", files=files, data={"voice_id": "random"})
    assert r.status_code == 200  # SSE stream opens, error is carried inside it
    assert "error" in r.text
    assert "100MB" in r.text  # the user-facing oversize message
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_dub_routes.py::test_dub_upload_rejects_oversize -v`
Expected: FAIL with 404 (route `/dub/generate-upload` does not exist yet).

- [ ] **Step 3: Rewrite `dub.py` with the shared pipeline, purge wiring, and upload route**

Replace the entire contents of `backend/app/api/v1/routes/dub.py` with:

```python
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

from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import DubVideo
from app.services.podcast_service import validate_youtube_url, resolve_voice
from app.services import dub_service
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
    yield _sse("transcribing", "转写中...")
    segments = extract_segments(video_path, settings.openai_api_key)

    yield _sse("translating", "翻译中...")
    zh = translate_segments(segments, settings.anthropic_api_key, settings.ai_model)

    yield _sse("voicing", "配音中...")
    voice_id = resolve_voice(voice_id_req)
    voice_track = build_voice_track(
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
    duration = compose(video_path, voice_track, out_path)
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
            dur_s = probe_duration(payload.youtube_url)

            with tempfile.TemporaryDirectory() as tmp:
                title, video_path = download_video(payload.youtube_url, tmp)
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

    async def event_stream() -> AsyncGenerator[dict, None]:
        try:
            dub_service.purge_expired(db)
            yield _sse("uploading", "接收文件中...")

            with tempfile.TemporaryDirectory() as tmp:
                suffix = Path(file.filename or "video.mp4").suffix or ".mp4"
                dest = Path(tmp) / f"upload{suffix}"
                size = 0
                with open(dest, "wb") as out:
                    while True:
                        chunk = await file.read(1024 * 1024)
                        if not chunk:
                            break
                        size += len(chunk)
                        if size > dub_service.MAX_UPLOAD_BYTES:
                            raise ValueError("文件超过 100MB 上限，请换更小的文件。")
                        out.write(chunk)

                title = Path(file.filename or "上传视频").stem or "上传视频"
                dur_s = dub_service.probe_local_duration(str(dest))
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
```

**Note on size enforcement:** the cap is enforced by counting bytes as the upload streams to disk (defends against a missing/lying `Content-Length`). FastAPI buffers the multipart body before the handler runs, so this is the authoritative server-side cap rather than a pre-upload reject; the client also rejects >100 MB before sending (Task 5). Resumable/chunked upload is out of scope.

- [ ] **Step 4: Run the upload test to verify it passes**

Run: `cd backend && python -m pytest tests/test_dub_routes.py -v`
Expected: all route tests PASS, including `test_dub_upload_rejects_oversize`.

- [ ] **Step 5: Run all dub tests to confirm no regression**

Run: `cd backend && python -m pytest tests/test_dub_model.py tests/test_dub_service.py tests/test_dub_routes.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/v1/routes/dub.py backend/tests/test_dub_routes.py
git commit -m "feat(dub): /generate-upload route (100MB cap) + shared pipeline + purge on generate/list"
```

---

## Task 5: Frontend — 链接/上传 toggle + upload flow

**Files:**
- Modify: `frontend/src/components/toolkits/dub-generator.tsx`

- [ ] **Step 1: Rewrite the generator component**

Replace the entire contents of `frontend/src/components/toolkits/dub-generator.tsx` with:

```tsx
"use client";

import { useEffect, useRef, useState } from "react";
import { API_BASE } from "@/lib/api";

export interface Dub {
  id: number;
  youtube_url: string | null;
  title: string;
  voice_id: string;
  duration_secs: number | null;
  created_at: string;
}

interface Voice {
  voice_id: string;
  name: string;
  gender: "female" | "male";
}

interface Props {
  onReady: (d: Dub) => void;
}

type Status =
  | "idle"
  | "uploading"
  | "downloading"
  | "transcribing"
  | "translating"
  | "voicing"
  | "composing"
  | "done"
  | "error";

const STATUS_LABELS: Record<Status, string> = {
  idle: "",
  uploading: "上传中...",
  downloading: "下载视频中...",
  transcribing: "转写中...",
  translating: "翻译中...",
  voicing: "配音中...",
  composing: "合成视频中...",
  done: "Done!",
  error: "Failed",
};

const VALID_STATUSES = new Set<string>(Object.keys(STATUS_LABELS));
const YOUTUBE_RE = /(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/;
const MAX_UPLOAD_BYTES = 100 * 1024 * 1024;

function fmtMB(bytes: number): string {
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function DubGenerator({ onReady }: Props) {
  const [mode, setMode] = useState<"link" | "upload">("link");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [voiceId, setVoiceId] = useState("random");
  const [voices, setVoices] = useState<Voice[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => () => abortRef.current?.abort(), []);
  useEffect(() => {
    fetch(`${API_BASE}/podcast/voices`)
      .then((r) => r.json())
      .then((data: Voice[]) => setVoices(data))
      .catch(() => setVoices([]));
  }, []);

  const femaleVoices = voices.filter((v) => v.gender === "female");
  const maleVoices = voices.filter((v) => v.gender === "male");
  const isBusy = status !== "idle" && status !== "done" && status !== "error";
  const urlValid = YOUTUBE_RE.test(url);
  const fileTooBig = file != null && file.size > MAX_UPLOAD_BYTES;
  const valid = mode === "link" ? urlValid : file != null && !fileTooBig;

  function onPickFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] ?? null;
    setFile(f);
    setErrorMsg("");
  }

  async function readSse(response: Response, controller: AbortController) {
    if (!response.ok || !response.body) throw new Error("Failed to start");
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done || controller.signal.aborted) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        if (!line.startsWith("data:")) continue;
        try {
          const payload = JSON.parse(line.slice(5).trim());
          if (payload.status && VALID_STATUSES.has(payload.status)) setStatus(payload.status as Status);
          if (payload.status === "done" && payload.item) {
            onReady(payload.item as Dub);
            setUrl("");
            setFile(null);
          }
          if (payload.status === "error") setErrorMsg(payload.message ?? "Unknown error");
        } catch {
          // ignore malformed SSE line
        }
      }
    }
  }

  async function handleGenerate() {
    if (!valid || isBusy) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setErrorMsg("");

    try {
      let response: Response;
      if (mode === "link") {
        setStatus("downloading");
        response = await fetch(`${API_BASE}/dub/generate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ youtube_url: url, voice_id: voiceId }),
          signal: controller.signal,
        });
      } else {
        setStatus("uploading");
        const form = new FormData();
        form.append("file", file as File);
        form.append("voice_id", voiceId);
        // No Content-Type header — the browser sets the multipart boundary.
        response = await fetch(`${API_BASE}/dub/generate-upload`, {
          method: "POST",
          body: form,
          signal: controller.signal,
        });
      }
      await readSse(response, controller);
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") return;
      setStatus("error");
      setErrorMsg("Connection failed — is the backend running?");
    }
  }

  return (
    <div className="space-y-5">
      <span className="text-xs font-semibold uppercase tracking-[0.28em] text-ink/40">配音 Dub</span>

      {/* 链接 / 上传 toggle */}
      <div className="flex gap-1.5 rounded-2xl bg-ink/5 p-1">
        <button
          onClick={() => setMode("link")}
          disabled={isBusy}
          className={`flex-1 rounded-xl py-2 text-sm font-semibold transition-colors disabled:opacity-40 ${
            mode === "link" ? "bg-white shadow-sm text-rose-600" : "text-ink/50"
          }`}
        >
          🔗 链接
        </button>
        <button
          onClick={() => setMode("upload")}
          disabled={isBusy}
          className={`flex-1 rounded-xl py-2 text-sm font-semibold transition-colors disabled:opacity-40 ${
            mode === "upload" ? "bg-white shadow-sm text-rose-600" : "text-ink/50"
          }`}
        >
          📁 上传
        </button>
      </div>

      {mode === "link" ? (
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-ink/60">YouTube URL（外语视频）</label>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://youtube.com/watch?v=..."
            disabled={isBusy}
            className={`w-full rounded-xl border px-3 py-2.5 text-sm bg-white text-ink placeholder:text-ink/30 outline-none transition-colors ${
              url && !urlValid ? "border-red-400 focus:border-red-500" : "border-ink/15 focus:border-rose-500"
            } disabled:opacity-40`}
          />
          {url && !urlValid && <p className="text-[11px] text-red-500">请输入有效的 YouTube 链接</p>}
          <p className="text-[11px] text-ink/40">≤ 10 分钟。原声会被压低做背景，中文旁白盖在上面。</p>
        </div>
      ) : (
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-ink/60">本地视频（手机/电脑）</label>
          <input
            type="file"
            accept="video/*"
            onChange={onPickFile}
            disabled={isBusy}
            className="block w-full text-sm text-ink/70 file:mr-3 file:rounded-lg file:border-0 file:bg-rose-600 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-white hover:file:opacity-90 disabled:opacity-40"
          />
          {file && (
            <p className={`text-[11px] ${fileTooBig ? "text-red-500" : "text-ink/50"}`}>
              {file.name} · {fmtMB(file.size)}
              {fileTooBig && " — 超过 100MB 上限，请换更小的文件"}
            </p>
          )}
          <p className="text-[11px] text-ink/40">≤ 100MB、≤ 10 分钟。原声压低做背景，中文旁白盖在上面。</p>
        </div>
      )}

      <div className="space-y-1.5">
        <label className="text-xs font-medium text-ink/60">旁白嗓音 Voice</label>
        <select
          value={voiceId}
          onChange={(e) => setVoiceId(e.target.value)}
          disabled={isBusy}
          className="w-full rounded-xl border border-ink/15 bg-white px-3 py-2.5 text-sm text-ink outline-none transition-colors focus:border-rose-500 disabled:opacity-40"
        >
          <option value="random">🎲 随机 Random</option>
          {femaleVoices.length > 0 && (
            <optgroup label="女声 Female">
              {femaleVoices.map((v) => (
                <option key={v.voice_id} value={v.voice_id}>{v.name}</option>
              ))}
            </optgroup>
          )}
          {maleVoices.length > 0 && (
            <optgroup label="男声 Male">
              {maleVoices.map((v) => (
                <option key={v.voice_id} value={v.voice_id}>{v.name}</option>
              ))}
            </optgroup>
          )}
        </select>
      </div>

      {isBusy ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 flex items-center gap-2">
          <svg className="animate-spin h-4 w-4 text-rose-500 flex-shrink-0" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
          </svg>
          <span className="text-sm text-rose-600">{STATUS_LABELS[status]}</span>
        </div>
      ) : (
        <button
          onClick={handleGenerate}
          disabled={!valid}
          className="w-full rounded-xl bg-rose-600 py-3 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-30"
        >
          <span aria-hidden="true">🎬</span> 生成配音视频 Dub
        </button>
      )}

      {status === "done" && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-600 font-medium">
          ✓ 配音视频已生成 — 见右侧列表！
        </div>
      )}
      {status === "error" && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3">
          <p className="text-sm text-red-600">{errorMsg}</p>
          <button onClick={() => setStatus("idle")} className="text-xs text-red-400 hover:text-red-600 mt-1 underline">
            Try again
          </button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc --noEmit -p tsconfig.json`
Expected: zero NEW errors. (Pre-existing `ziwei` 3D errors — `@react-three/fiber`, `@react-three/drei`, `three`, `iztro` missing declarations — are unrelated and acceptable.)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/toolkits/dub-generator.tsx
git commit -m "feat(dub): link/upload toggle — local video upload w/ 100MB client guard"
```

---

## Task 6: Deploy

**Files:** none (deploy via pipeline).

- [ ] **Step 1: Full backend test sweep**

Run: `cd backend && python -m pytest tests/test_dub_model.py tests/test_dub_service.py tests/test_dub_routes.py -v`
Expected: all dub tests PASS. (The repo-wide `pytest` shows ~21 pre-existing `test_api.py` errors from `JSONB`-on-SQLite — unrelated to this change; do not treat as regressions.)

- [ ] **Step 2: Frontend typecheck**

Run: `cd frontend && npx tsc --noEmit -p tsconfig.json`
Expected: zero new errors.

- [ ] **Step 3: Push main**

```bash
git -c http.sslVerify=false push origin main
```

- [ ] **Step 4: Tag the next free version and push the tag**

```bash
git tag -l "v*" | sort -V | tail -1   # confirm latest (expected v0.41.0)
git tag v0.42.0
git -c http.sslVerify=false push origin v0.42.0
```

(If `v0.42.0` already exists from parallel work, bump to the next free `v0.4x.0`.)

- [ ] **Step 5: Watch the deploy**

```bash
gh run list --workflow=deploy.yml --limit 1
gh run watch <run-id> --exit-status --interval 20
```
Expected: ✓ build, ✓ deploy, ✓ Verify health via SSH.

- [ ] **Step 6: Live verification**

In the browser on the live domain: open 蒸馏所 → 配 Dub, switch to 📁 上传, pick a short (<1 min) local video, confirm a >100MB file is rejected client-side, generate, and confirm the dubbed mp4 appears in 我的视频 with inline playback + download. Confirm the existing 🔗 链接 mode still works.

---

## Self-review notes

- **Spec coverage:** 100MB cap (Task 3 const + Task 4 server enforce + Task 5 client guard); ffprobe duration (Task 3); ephemeral input via TemporaryDirectory (Task 4); 7-day output TTL via purge_expired on generate+list (Tasks 3-4); nullable youtube_url + prod patch (Task 2); link/upload toggle (Task 5); python-multipart dep (Task 1). All covered.
- **Type consistency:** `youtube_url` is `Optional[str]` in the model, `DubOut`, and `_to_out`; `Dub.youtube_url` is `string | null` on the frontend (dub-list.tsx and page.tsx don't read `youtube_url`, so no further change). `MAX_UPLOAD_BYTES`/`probe_local_duration`/`purge_expired` are referenced as `dub_service.X` in the route so tests can monkeypatch them. SSE `_sse(status, message)` shape matches the frontend reader (`payload.status`, `payload.message`, `payload.item`). New `uploading` status is set client-side and present in `STATUS_LABELS` + `VALID_STATUSES`.
- **No placeholders:** every code step is complete and runnable.

# Summarize Anything Toolkit (Phase 1a) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a second toolkit — 内容摘要 / Summarize Anything — that turns pasted text, a web URL, or a YouTube URL into a structured Chinese summary, saved to a revisitable history.

**Architecture:** Pluggable ingestion (`source → clean text`) feeding a Claude structured-JSON summary call, streamed over SSE, persisted in a `summaries` table. Reuses `extract_transcript` (YouTube), the SSE pattern, the toolkit card/list components, and the mobile-collapse layout from the podcast tool.

**Tech Stack:** FastAPI, SQLAlchemy (`create_all` on startup — no migrations), Anthropic SDK, `trafilatura` (web extraction), Next.js/React/Tailwind, SSE via `fetch` ReadableStream.

**Spec:** `docs/superpowers/specs/2026-06-07-summarize-anything-toolkit-design.md`

---

## File Structure

**Backend (new):**
- `backend/app/services/ingestion_service.py` — `ingest(source_type, value) -> (title, text)` + adapters
- `backend/app/services/summary_service.py` — `generate_summary(text, key, model) -> dict`
- `backend/app/api/v1/routes/summary.py` — SSE generate, list, delete
- `backend/tests/test_ingestion_service.py`, `backend/tests/test_summary_service.py`

**Backend (modify):**
- `backend/requirements.txt` — add `trafilatura`
- `backend/app/models/entities.py` — add `Summary` model
- `backend/app/api/v1/api.py` — register `summary.router`

**Frontend (new):**
- `frontend/src/app/toolkits/summarize/page.tsx`
- `frontend/src/components/toolkits/summary-generator.tsx`
- `frontend/src/components/toolkits/summary-list.tsx`
- `frontend/src/components/toolkits/summary-view.tsx`

**Frontend (modify):**
- `frontend/src/app/toolkits/page.tsx` — add card + fix stale `text-cream` header

---

## Task 1: Backend dependency — trafilatura

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add the dependency**

Add this line to `backend/requirements.txt` (after `youtube-transcript-api>=0.6.0`):

```
trafilatura>=1.8.0
```

- [ ] **Step 2: Install locally to confirm it resolves**

Run: `cd backend && python -m pip install "trafilatura>=1.8.0"`
Expected: installs without error.

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "build: add trafilatura for web article extraction"
```

---

## Task 2: Summary model

**Files:**
- Modify: `backend/app/models/entities.py` (append a new class at end of file)
- Test: `backend/tests/test_summary_model.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_summary_model.py`:

```python
def test_summary_model_table_and_columns():
    from app.models.entities import Summary
    assert Summary.__tablename__ == "summaries"
    cols = set(Summary.__table__.columns.keys())
    assert {
        "id", "source_type", "source_url", "title",
        "tldr", "key_points", "takeaways", "char_count", "created_at",
    }.issubset(cols)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_summary_model.py -v`
Expected: FAIL with `ImportError: cannot import name 'Summary'`.

- [ ] **Step 3: Add the model**

Append to `backend/app/models/entities.py` (the file already imports `JSON, DateTime, Integer, String, Text`, `Mapped`, `mapped_column`, `datetime`, `List`, `Optional`, `Base`):

```python
class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)  # text|web|youtube
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    tldr: Mapped[str] = mapped_column(Text, nullable=False)
    key_points: Mapped[List] = mapped_column(JSON, default=list)
    takeaways: Mapped[List] = mapped_column(JSON, default=list)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_summary_model.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/entities.py backend/tests/test_summary_model.py
git commit -m "feat: add Summary model for summaries table"
```

---

## Task 3: Ingestion service

**Files:**
- Create: `backend/app/services/ingestion_service.py`
- Test: `backend/tests/test_ingestion_service.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_ingestion_service.py`:

```python
import pytest


def test_ingest_text_passthrough():
    from app.services.ingestion_service import ingest
    long_text = "你好世界。" * 60  # > 200 chars
    title, text = ingest("text", long_text)
    assert title == ""
    assert "你好世界" in text


def test_ingest_too_short_raises():
    from app.services.ingestion_service import ingest
    with pytest.raises(ValueError, match="too short"):
        ingest("text", "太短了")


def test_ingest_unknown_type_raises():
    from app.services.ingestion_service import ingest
    with pytest.raises(ValueError, match="Unknown source type"):
        ingest("pdf", "whatever")


def test_ingest_web_uses_trafilatura(monkeypatch):
    import app.services.ingestion_service as ing
    monkeypatch.setattr(ing, "_ingest_web", lambda url: ("Web Title", "网页正文。" * 80))
    title, text = ing.ingest("web", "https://example.com/article")
    assert title == "Web Title"
    assert "网页正文" in text


def test_ingest_web_empty_extraction_raises(monkeypatch):
    import app.services.ingestion_service as ing
    import trafilatura
    monkeypatch.setattr(trafilatura, "fetch_url", lambda url: "<html></html>")
    monkeypatch.setattr(trafilatura, "extract", lambda *a, **k: None)
    with pytest.raises(ValueError, match="extract article text"):
        ing._ingest_web("https://example.com/x")


def test_ingest_youtube_reuses_extract_transcript(monkeypatch):
    import app.services.ingestion_service as ing
    monkeypatch.setattr(ing, "_ingest_youtube", lambda url: ("Vid", "视频讲稿内容。" * 80))
    title, text = ing.ingest("youtube", "https://youtube.com/watch?v=abc12345678")
    assert title == "Vid"
    assert "视频讲稿" in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_ingestion_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.ingestion_service'`.

- [ ] **Step 3: Implement the service**

Create `backend/app/services/ingestion_service.py`:

```python
"""Ingestion layer: turn a source (text / web / youtube) into clean text.

Each adapter has the signature value -> (title, text). Adding a new source
later means registering one more adapter; nothing downstream changes.
"""
from __future__ import annotations

from typing import Tuple

MIN_CONTENT_CHARS = 200


def _ingest_text(value: str) -> Tuple[str, str]:
    """Pasted text: use as-is. Title is inferred later by Claude."""
    return "", value.strip()


def _ingest_web(url: str) -> Tuple[str, str]:
    """Fetch a web article and extract its main text via trafilatura."""
    import trafilatura

    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        raise ValueError("Could not fetch that URL.")
    text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
    if not text or not text.strip():
        raise ValueError("Could not extract article text from that URL.")

    title = ""
    try:
        meta = trafilatura.extract_metadata(downloaded)
        if meta and getattr(meta, "title", None):
            title = meta.title
    except Exception:
        title = ""
    return title, text.strip()


def _ingest_youtube(url: str) -> Tuple[str, str]:
    """Reuse the podcast tool's transcript extraction (proxy + retry built in)."""
    from app.services.podcast_service import extract_transcript

    return extract_transcript(url)


def ingest(source_type: str, value: str) -> Tuple[str, str]:
    """Dispatch to the right adapter and enforce a minimum content length.

    Returns (title, clean_text). Raises ValueError on failure or too-short content.
    """
    if source_type == "text":
        title, text = _ingest_text(value)
    elif source_type == "web":
        title, text = _ingest_web(value)
    elif source_type == "youtube":
        title, text = _ingest_youtube(value)
    else:
        raise ValueError(f"Unknown source type: {source_type}")

    if len(text.strip()) < MIN_CONTENT_CHARS:
        raise ValueError("Content too short to summarize (need ~200+ characters).")
    return title, text
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_ingestion_service.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ingestion_service.py backend/tests/test_ingestion_service.py
git commit -m "feat: ingestion service with text/web/youtube adapters"
```

---

## Task 4: Summary service (Claude structured JSON)

**Files:**
- Create: `backend/app/services/summary_service.py`
- Test: `backend/tests/test_summary_service.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_summary_service.py`:

```python
import pytest


def _mock_claude(monkeypatch, response_text):
    from unittest.mock import MagicMock
    import anthropic
    msg = MagicMock()
    msg.content = [MagicMock(text=response_text)]
    client = MagicMock()
    client.messages.create.return_value = msg
    monkeypatch.setattr(anthropic, "Anthropic", lambda api_key: client)
    return client


def test_generate_summary_parses_valid_json(monkeypatch):
    from app.services.summary_service import generate_summary
    _mock_claude(monkeypatch, '{"title":"标题","tldr":"一句话","key_points":["要点1","要点2"],"takeaways":["收获1"]}')
    out = generate_summary("正文内容", "fake_key", "fake_model")
    assert out["title"] == "标题"
    assert out["tldr"] == "一句话"
    assert out["key_points"] == ["要点1", "要点2"]
    assert out["takeaways"] == ["收获1"]


def test_generate_summary_strips_code_fences(monkeypatch):
    from app.services.summary_service import generate_summary
    _mock_claude(monkeypatch, '```json\n{"title":"T","tldr":"x","key_points":[],"takeaways":[]}\n```')
    out = generate_summary("正文", "k", "m")
    assert out["tldr"] == "x"


def test_generate_summary_malformed_raises(monkeypatch):
    from app.services.summary_service import generate_summary
    _mock_claude(monkeypatch, "this is not json at all")
    with pytest.raises(ValueError, match="parse summary"):
        generate_summary("正文", "k", "m")


def test_generate_summary_missing_tldr_raises(monkeypatch):
    from app.services.summary_service import generate_summary
    _mock_claude(monkeypatch, '{"title":"T","key_points":[],"takeaways":[]}')
    with pytest.raises(ValueError, match="tldr"):
        generate_summary("正文", "k", "m")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_summary_service.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement the service**

Create `backend/app/services/summary_service.py`:

```python
"""Summary generation via Claude — strict structured-JSON output."""
from __future__ import annotations

import json
import re
from typing import Dict

_MAX_INPUT_CHARS = 20000  # cap input to keep token cost bounded

_SUMMARY_PROMPT = """你是一位专业的中文内容编辑。请阅读以下内容，并输出一份结构化中文摘要。

严格按照以下 JSON 格式输出，不要任何额外文字、说明或前言：
{{
  "title": "简洁标题（不超过20字）",
  "tldr": "一句话总结核心内容",
  "key_points": ["关键要点1", "关键要点2"],
  "takeaways": ["核心收获1", "核心收获2"]
}}

要求：
- key_points 提炼 3-7 条最重要的观点
- takeaways 提炼 2-4 条值得记住或可执行的收获
- 全部使用中文，简洁清晰

内容：
{content}"""


def _extract_json(raw: str) -> dict:
    """Pull a JSON object out of Claude's response, tolerating code fences."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in summary response")
    return json.loads(raw[start : end + 1])


def generate_summary(text: str, anthropic_api_key: str, model: str) -> Dict:
    """Return {title, tldr, key_points[], takeaways[]} (all Chinese).

    Raises ValueError if the model output cannot be parsed or is missing a tldr.
    """
    import anthropic

    client = anthropic.Anthropic(api_key=anthropic_api_key)
    prompt = _SUMMARY_PROMPT.format(content=text[:_MAX_INPUT_CHARS])
    message = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text

    try:
        data = _extract_json(raw)
    except Exception as exc:
        raise ValueError(f"Could not parse summary: {exc}") from exc

    tldr = data.get("tldr")
    if not isinstance(tldr, str) or not tldr.strip():
        raise ValueError("Summary missing tldr")

    key_points = data.get("key_points") or []
    takeaways = data.get("takeaways") or []
    if not isinstance(key_points, list) or not isinstance(takeaways, list):
        raise ValueError("Summary key_points/takeaways must be lists")

    return {
        "title": (data.get("title") or "").strip(),
        "tldr": tldr.strip(),
        "key_points": [str(k).strip() for k in key_points if str(k).strip()],
        "takeaways": [str(t).strip() for t in takeaways if str(t).strip()],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_summary_service.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/summary_service.py backend/tests/test_summary_service.py
git commit -m "feat: summary service with Claude structured-JSON output"
```

---

## Task 5: Summary routes + router registration

**Files:**
- Create: `backend/app/api/v1/routes/summary.py`
- Modify: `backend/app/api/v1/api.py`
- Test: `backend/tests/test_summary_routes.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_summary_routes.py`:

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_generate_rejects_bad_source_type():
    r = client.post("/api/v1/summary/generate", json={"source_type": "pdf", "value": "x"})
    assert r.status_code == 422


def test_generate_rejects_empty_value():
    r = client.post("/api/v1/summary/generate", json={"source_type": "text", "value": "  "})
    assert r.status_code == 422


def test_list_summaries_returns_list():
    r = client.get("/api/v1/summary/list")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_delete_missing_summary_404():
    r = client.delete("/api/v1/summary/99999999")
    assert r.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_summary_routes.py -v`
Expected: FAIL — routes return 404 (not registered yet).

- [ ] **Step 3: Create the routes file**

Create `backend/app/api/v1/routes/summary.py`:

```python
"""Summary generation routes (SSE generate + list + delete)."""
from __future__ import annotations

import json
import logging
from typing import AsyncGenerator, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import Summary
from app.services.ingestion_service import ingest
from app.services.summary_service import generate_summary

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/summary", tags=["summary"])

VALID_SOURCE_TYPES = {"text", "web", "youtube"}


class SummaryRequest(BaseModel):
    source_type: str
    value: str


class SummaryOut(BaseModel):
    id: int
    source_type: str
    source_url: Optional[str]
    title: str
    tldr: str
    key_points: List[str]
    takeaways: List[str]
    char_count: int
    created_at: str


def _to_out(s: Summary) -> dict:
    return {
        "id": s.id,
        "source_type": s.source_type,
        "source_url": s.source_url,
        "title": s.title,
        "tldr": s.tldr,
        "key_points": s.key_points or [],
        "takeaways": s.takeaways or [],
        "char_count": s.char_count,
        "created_at": s.created_at.isoformat(),
    }


@router.post("/generate")
async def generate(payload: SummaryRequest, db: Session = Depends(get_db)):
    if payload.source_type not in VALID_SOURCE_TYPES:
        raise HTTPException(status_code=422, detail="Invalid source_type")
    if not payload.value or not payload.value.strip():
        raise HTTPException(status_code=422, detail="value is required")

    settings = get_settings()

    async def event_stream() -> AsyncGenerator[dict, None]:
        try:
            yield {"data": json.dumps({"status": "fetching", "message": "Fetching content..."})}
            title, text = ingest(payload.source_type, payload.value)

            yield {"data": json.dumps({"status": "summarizing", "message": "Summarizing with Claude..."})}
            result = generate_summary(text, settings.anthropic_api_key, settings.ai_model)

            final_title = title or result["title"] or "未命名摘要"
            source_url = payload.value if payload.source_type in ("web", "youtube") else None

            summary = Summary(
                source_type=payload.source_type,
                source_url=source_url,
                title=final_title,
                tldr=result["tldr"],
                key_points=result["key_points"],
                takeaways=result["takeaways"],
                char_count=len(text),
            )
            db.add(summary)
            db.commit()
            db.refresh(summary)

            yield {"data": json.dumps({"status": "done", "summary": _to_out(summary)})}

        except ValueError as exc:
            db.rollback()
            logger.warning("Summary error: %s", exc)
            yield {"data": json.dumps({"status": "error", "message": str(exc)})}
        except Exception:
            db.rollback()
            logger.exception("Unexpected summary error")
            yield {"data": json.dumps({"status": "error", "message": "Could not generate summary — please try again."})}

    return EventSourceResponse(event_stream())


@router.get("/list", response_model=List[SummaryOut])
def list_summaries(db: Session = Depends(get_db)):
    rows = db.scalars(select(Summary).order_by(Summary.created_at.desc())).all()
    return [SummaryOut(**_to_out(s)) for s in rows]


@router.delete("/{summary_id}", status_code=204)
def delete_summary(summary_id: int, db: Session = Depends(get_db)):
    s = db.get(Summary, summary_id)
    if not s:
        raise HTTPException(status_code=404, detail="Summary not found")
    db.delete(s)
    db.commit()
```

- [ ] **Step 4: Register the router**

In `backend/app/api/v1/api.py`, add `summary` to the routes import line (alphabetically near `streaks`) and register it. The import line currently ends `... resume, streaks`; change to `... resume, streaks, summary`. Then add after `api_router.include_router(podcast.router)`:

```python
api_router.include_router(summary.router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_summary_routes.py -v`
Expected: PASS (4 tests).

- [ ] **Step 6: Run the full backend suite**

Run: `cd backend && python -m pytest -q`
Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/v1/routes/summary.py backend/app/api/v1/api.py backend/tests/test_summary_routes.py
git commit -m "feat: summary API routes (SSE generate, list, delete)"
```

---

## Task 6: Frontend — summary view component

**Files:**
- Create: `frontend/src/components/toolkits/summary-view.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/toolkits/summary-view.tsx`:

```tsx
"use client";

export interface Summary {
  id: number;
  source_type: string;
  source_url: string | null;
  title: string;
  tldr: string;
  key_points: string[];
  takeaways: string[];
  char_count: number;
  created_at: string;
}

export function SummaryView({ summary }: { summary: Summary }) {
  return (
    <div className="space-y-4">
      {/* TL;DR — most prominent (3-second scan) */}
      <div className="rounded-2xl border border-ember/20 bg-ember/5 p-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-ember/70 mb-1">
          TL;DR
        </p>
        <p className="text-base font-medium text-ink leading-relaxed">{summary.tldr}</p>
      </div>

      {/* Key points */}
      {summary.key_points.length > 0 && (
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-ink/40 mb-2">
            关键要点 Key Points
          </p>
          <ul className="space-y-1.5">
            {summary.key_points.map((p, i) => (
              <li key={i} className="flex gap-2 text-sm text-ink/80 leading-relaxed">
                <span className="text-ember flex-shrink-0">•</span>
                <span>{p}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Takeaways */}
      {summary.takeaways.length > 0 && (
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-ink/40 mb-2">
            核心收获 Takeaways
          </p>
          <ul className="space-y-1.5">
            {summary.takeaways.map((t, i) => (
              <li key={i} className="flex gap-2 text-sm text-ink/80 leading-relaxed">
                <span className="text-pine flex-shrink-0">✓</span>
                <span>{t}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Source link */}
      {summary.source_url && (
        <a
          href={summary.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block text-[11px] text-ink/40 hover:text-ember transition-colors break-all"
        >
          🔗 {summary.source_url}
        </a>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc --noEmit -p tsconfig.json`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/toolkits/summary-view.tsx
git commit -m "feat: summary-view component (TL;DR/points/takeaways hierarchy)"
```

---

## Task 7: Frontend — summary list component

**Files:**
- Create: `frontend/src/components/toolkits/summary-list.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/toolkits/summary-list.tsx`:

```tsx
"use client";

import { useState } from "react";
import { API_BASE } from "@/lib/api";
import { SummaryView, type Summary } from "./summary-view";

interface SummaryListProps {
  summaries: Summary[];
  loadError?: boolean;
  onDelete: (id: number) => void;
}

const SOURCE_LABEL: Record<string, string> = {
  text: "文本",
  web: "网页",
  youtube: "YouTube",
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  if (diff < 86400000) return "Today";
  if (diff < 172800000) return "Yesterday";
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function SummaryCard({ s, onDelete }: { s: Summary; onDelete: (id: number) => void }) {
  const [open, setOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function handleDelete(e: React.MouseEvent) {
    e.stopPropagation();
    if (!confirm("Delete this summary?")) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      const res = await fetch(`${API_BASE}/summary/${s.id}`, { method: "DELETE" });
      if (!res.ok) throw new Error(`Server error ${res.status}`);
      onDelete(s.id);
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "Delete failed");
      setDeleting(false);
    }
  }

  return (
    <div className="rounded-2xl border border-ink/10 bg-white p-4 hover:border-ember/30 hover:shadow-sm transition-all">
      <div className="flex items-start gap-3 cursor-pointer" onClick={() => setOpen((o) => !o)}>
        <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-ember/10 flex items-center justify-center text-base">
          📝
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-ink truncate">{s.title}</p>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <span className="text-[11px] px-2 py-0.5 rounded-full font-medium bg-ink/8 text-ink/50">
              {SOURCE_LABEL[s.source_type] ?? s.source_type}
            </span>
            <span className="text-[11px] text-ink/20">·</span>
            <span className="text-[11px] text-ink/40">{formatDate(s.created_at)}</span>
          </div>
        </div>
        <button
          onClick={handleDelete}
          disabled={deleting}
          aria-label="Delete summary"
          title="Delete summary"
          className="flex items-center justify-center w-10 h-10 rounded-full text-ink/40 hover:text-red-400 hover:bg-red-50 active:bg-red-100 transition-colors text-xl leading-none disabled:opacity-40"
        >
          {deleting ? "…" : "×"}
        </button>
      </div>

      {!open && <p className="text-xs text-ink/50 mt-2 line-clamp-2">{s.tldr}</p>}
      {open && (
        <div className="mt-4 pt-4 border-t border-ink/10">
          <SummaryView summary={s} />
        </div>
      )}
      {deleteError && <p className="mt-2 text-[11px] text-red-400">{deleteError}</p>}
    </div>
  );
}

export function SummaryList({ summaries, loadError, onDelete }: SummaryListProps) {
  if (loadError) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3">
        <p className="text-sm text-red-600">Failed to load summaries — is the backend running?</p>
      </div>
    );
  }

  if (summaries.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="text-5xl mb-4 opacity-20">📝</div>
        <p className="text-sm font-medium text-ink/40">No summaries yet</p>
        <p className="text-xs text-ink/30 mt-1">用生成器创建第一篇摘要</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {summaries.map((s) => (
        <SummaryCard key={s.id} s={s} onDelete={onDelete} />
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc --noEmit -p tsconfig.json`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/toolkits/summary-list.tsx
git commit -m "feat: summary-list component with expand + delete"
```

---

## Task 8: Frontend — summary generator (SSE)

**Files:**
- Create: `frontend/src/components/toolkits/summary-generator.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/toolkits/summary-generator.tsx`:

```tsx
"use client";

import { useEffect, useRef, useState } from "react";
import { API_BASE } from "@/lib/api";
import type { Summary } from "./summary-view";

interface Props {
  onSummaryReady: (summary: Summary) => void;
}

type Status = "idle" | "fetching" | "summarizing" | "done" | "error";

const STATUS_LABELS: Record<Status, string> = {
  idle: "",
  fetching: "Fetching content...",
  summarizing: "Summarizing with Claude...",
  done: "Done!",
  error: "Failed",
};

const VALID_STATUSES = new Set<string>(Object.keys(STATUS_LABELS));
type SourceType = "text" | "web" | "youtube";

export function SummaryGenerator({ onSummaryReady }: Props) {
  const [sourceType, setSourceType] = useState<SourceType>("text");
  const [value, setValue] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => () => abortRef.current?.abort(), []);

  const isBusy = status === "fetching" || status === "summarizing";
  const valid = value.trim().length > 0;

  async function handleGenerate() {
    if (!valid || isBusy) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setStatus("fetching");
    setErrorMsg("");

    try {
      const response = await fetch(`${API_BASE}/summary/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source_type: sourceType, value }),
        signal: controller.signal,
      });
      if (!response.ok || !response.body) throw new Error("Failed to start");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value: chunk } = await reader.read();
        if (done || controller.signal.aborted) break;
        buffer += decoder.decode(chunk, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data:")) continue;
          try {
            const payload = JSON.parse(line.slice(5).trim());
            if (payload.status && VALID_STATUSES.has(payload.status)) {
              setStatus(payload.status as Status);
            }
            if (payload.status === "done" && payload.summary) {
              onSummaryReady(payload.summary as Summary);
              setValue("");
            }
            if (payload.status === "error") {
              setErrorMsg(payload.message ?? "Unknown error");
            }
          } catch {
            // ignore malformed SSE line
          }
        }
      }
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") return;
      setStatus("error");
      setErrorMsg("Connection failed — is the backend running?");
    }
  }

  return (
    <div className="space-y-5">
      <span className="text-xs font-semibold uppercase tracking-[0.28em] text-ink/40">
        Generate Summary
      </span>

      {/* Source type tabs */}
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-ink/60">Source</label>
        <div className="flex gap-2">
          {(["text", "web", "youtube"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setSourceType(t)}
              disabled={isBusy}
              className={`flex-1 rounded-xl py-2 text-sm font-medium transition-colors disabled:opacity-40 ${
                sourceType === t
                  ? "bg-ember/15 text-ember border border-ember/40"
                  : "bg-white text-ink/50 border border-ink/15 hover:border-ink/30"
              }`}
            >
              {t === "text" ? "文本" : t === "web" ? "网页" : "YouTube"}
            </button>
          ))}
        </div>
      </div>

      {/* Input */}
      <div className="space-y-1.5">
        {sourceType === "text" ? (
          <textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="粘贴要总结的文本..."
            disabled={isBusy}
            rows={8}
            className="w-full rounded-xl border border-ink/15 bg-white px-3 py-2.5 text-sm text-ink placeholder:text-ink/30 outline-none transition-colors focus:border-ember disabled:opacity-40 resize-none"
          />
        ) : (
          <input
            type="url"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={sourceType === "web" ? "https://example.com/article" : "https://youtube.com/watch?v=..."}
            disabled={isBusy}
            className="w-full rounded-xl border border-ink/15 bg-white px-3 py-2.5 text-sm text-ink placeholder:text-ink/30 outline-none transition-colors focus:border-ember disabled:opacity-40"
          />
        )}
      </div>

      {/* Progress / button */}
      {isBusy ? (
        <div className="rounded-xl border border-ember/20 bg-ember/5 px-4 py-3 flex items-center gap-2">
          <svg className="animate-spin h-4 w-4 text-ember flex-shrink-0" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
          </svg>
          <span className="text-sm text-ember">{STATUS_LABELS[status]}</span>
        </div>
      ) : (
        <button
          onClick={handleGenerate}
          disabled={!valid}
          className="w-full rounded-xl bg-ember py-3 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-30"
        >
          <span aria-hidden="true">📝</span> Generate Summary
        </button>
      )}

      {status === "done" && (
        <div className="rounded-xl border border-pine/20 bg-mint/30 px-4 py-3 text-sm text-pine font-medium">
          ✓ Summary ready — see the list on the right!
        </div>
      )}
      {status === "error" && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3">
          <p className="text-sm text-red-600">{errorMsg}</p>
          <button
            onClick={() => setStatus("idle")}
            className="text-xs text-red-400 hover:text-red-600 mt-1 underline"
          >
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
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/toolkits/summary-generator.tsx
git commit -m "feat: summary-generator with source tabs + SSE progress"
```

---

## Task 9: Frontend — summarize page (mobile-collapse)

**Files:**
- Create: `frontend/src/app/toolkits/summarize/page.tsx`

- [ ] **Step 1: Create the page**

Create `frontend/src/app/toolkits/summarize/page.tsx`:

```tsx
"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { SummaryGenerator } from "@/components/toolkits/summary-generator";
import { SummaryList } from "@/components/toolkits/summary-list";
import type { Summary } from "@/components/toolkits/summary-view";
import { API_BASE } from "@/lib/api";

export default function SummarizePage() {
  const [summaries, setSummaries] = useState<Summary[]>([]);
  const [loadError, setLoadError] = useState(false);
  const [genOpen, setGenOpen] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/summary/list`)
      .then((r) => r.json())
      .then((data: Summary[]) => {
        setSummaries(data);
        if (data.length === 0) setGenOpen(true);
      })
      .catch(() => setLoadError(true));
  }, []);

  const handleNew = useCallback((s: Summary) => {
    setSummaries((prev) => [s, ...prev]);
  }, []);

  const handleDelete = useCallback((id: number) => {
    setSummaries((prev) => prev.filter((s) => s.id !== id));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <Link
          href="/toolkits"
          className="text-xs text-ink/40 hover:text-ember transition-colors mb-2 inline-flex items-center gap-1"
        >
          ← Toolkits
        </Link>
        <div className="flex items-center gap-3 mt-1">
          <span className="text-3xl">📝</span>
          <div>
            <span className="text-xs font-semibold uppercase tracking-[0.28em] text-ember">
              Toolkits
            </span>
            <h1 className="font-display text-2xl text-ink leading-tight">内容摘要 Summarize</h1>
          </div>
        </div>
        <p className="text-ink/50 text-sm mt-1 ml-12">
          粘贴文本、网页或 YouTube 链接 — 获得结构化中文摘要。
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[2fr_3fr] rounded-[28px] border border-ink/10 bg-white/85 shadow-panel overflow-hidden lg:min-h-[600px]">
        {/* Generator — collapsible on mobile */}
        <div className="border-b lg:border-b-0 lg:border-r border-ink/10 bg-sand/20">
          <button
            type="button"
            onClick={() => setGenOpen((o) => !o)}
            aria-expanded={genOpen}
            className="lg:hidden w-full flex items-center justify-between gap-2 px-5 py-4 text-left active:bg-sand/40 transition-colors"
          >
            <span className="flex items-center gap-2 text-sm font-semibold text-ink">
              <span aria-hidden="true">📝</span> 生成新摘要 · New Summary
            </span>
            <svg
              className={`h-4 w-4 flex-shrink-0 text-ink/40 transition-transform ${genOpen ? "rotate-180" : ""}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          <div className={`${genOpen ? "block" : "hidden"} lg:block px-5 pb-5 lg:p-6`}>
            <SummaryGenerator onSummaryReady={handleNew} />
          </div>
        </div>

        {/* History — primary on mobile */}
        <div className="p-5 lg:p-6">
          <div className="flex items-baseline gap-2 mb-4 lg:mb-5">
            <span className="text-xs font-semibold uppercase tracking-[0.28em] text-ink/40">
              My Summaries
            </span>
            {summaries.length > 0 && (
              <span className="text-[10px] text-ink/30">
                {summaries.length} {summaries.length === 1 ? "summary" : "summaries"}
              </span>
            )}
          </div>
          <SummaryList summaries={summaries} loadError={loadError} onDelete={handleDelete} />
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc --noEmit -p tsconfig.json`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/toolkits/summarize/page.tsx
git commit -m "feat: summarize page with mobile-collapse layout"
```

---

## Task 10: Toolkit index card + fix stale dark-theme header

**Files:**
- Modify: `frontend/src/app/toolkits/page.tsx`

- [ ] **Step 1: Fix the stale dark-theme header**

In `frontend/src/app/toolkits/page.tsx`, the header still uses `text-cream` (a dark-theme leftover, invisible on the light background). Change:

```tsx
        <h1 className="font-display text-3xl text-cream mt-1">Your toolkit.</h1>
        <p className="text-cream/50 text-sm mt-1">
```

to:

```tsx
        <h1 className="font-display text-3xl text-ink mt-1">Your toolkit.</h1>
        <p className="text-ink/50 text-sm mt-1">
```

- [ ] **Step 2: Add the Summarize card**

In the same file, replace the "Doc Builder" coming-soon card with the real Summarize card (insert immediately after the YouTube Podcast `<ToolkitCard ... />` block):

```tsx
        <ToolkitCard
          icon="📝"
          name="内容摘要 Summarize"
          description="粘贴文本、网页或 YouTube 链接，获得结构化中文摘要 — TL;DR、关键要点与核心收获。"
          href="/toolkits/summarize"
          tags={[
            { label: "AI summary", variant: "default" },
            { label: "Web · YouTube", variant: "default" },
            { label: "Ready", variant: "ready" },
          ]}
        />
```

(Leave the Job Scanner and "Request a tool" cards as-is.)

- [ ] **Step 3: Typecheck**

Run: `cd frontend && npx tsc --noEmit -p tsconfig.json`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/toolkits/page.tsx
git commit -m "feat: add Summarize toolkit card; fix stale text-cream header"
```

---

## Task 11: Deploy

**Files:** none (CI/CD pipeline per CLAUDE.md)

- [ ] **Step 1: Run full backend test suite**

Run: `cd backend && python -m pytest -q`
Expected: all green.

- [ ] **Step 2: Final frontend typecheck**

Run: `cd frontend && npx tsc --noEmit -p tsconfig.json`
Expected: no errors.

- [ ] **Step 3: Push and tag (triggers GitHub Actions)**

```bash
git push origin main
git tag v0.28.0
git push origin v0.28.0
```

(If git/push hits the local SSL interception, use `git -c http.sslVerify=false push ...`.)

- [ ] **Step 4: Watch the deploy**

Run: `gh run watch $(gh run list --limit 2 --json databaseId,name --jq '.[] | select(.name == "Build & Deploy Portal") | .databaseId' | head -1)`
Expected: build + deploy succeed.

- [ ] **Step 5: Verify on the live server**

```bash
ssh root@146.190.124.162 "curl -s http://172.18.0.4:8000/api/v1/summary/list"
```
Expected: `[]` (or existing summaries) — confirms the route + table exist.

Then in the browser: open `/toolkits`, confirm the Summarize card appears and links to `/toolkits/summarize`; generate a summary from a pasted paragraph and from a web URL.

---

## Notes for the implementer
- **DB table:** created automatically by `Base.metadata.create_all()` on backend startup — no migration step.
- **No new secrets:** reuses `ANTHROPIC_API_KEY` already on the VPS.
- **Local test deps:** `youtube-transcript-api`, `pydub`, and now `trafilatura` must be pip-installed locally to run backend tests (lazy imports mean `anthropic`/network aren't needed since tests mock them).
- **Deferred (Phase 1b):** the "生成播客" hand-off (generalize podcast `/generate` to accept `source_text`) is a separate spec — do not build it here.

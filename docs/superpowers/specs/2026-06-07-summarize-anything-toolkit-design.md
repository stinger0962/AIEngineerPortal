# 内容摘要 / Summarize Anything Toolkit — Design Spec

**Date:** 2026-06-07
**Status:** Approved (Phase 1a) — reviewed via gstack plan-eng-review + plan-design-review
**Author:** AI Engineer Portal

---

## Overview

A second Toolkit: **内容摘要 / Summarize Anything**. The user provides a source —
pasted text, a web article URL, or a YouTube URL — and receives a structured
Chinese summary (TL;DR, key points, takeaways). Generated summaries are saved to
a history list the user can revisit, mirroring the podcast tool's UX.

This is the first slice of a larger "anything → study outputs" vision. The
architecture is a **pluggable ingestion layer** (`source → clean text`) feeding
Claude. Future phases add more ingestion adapters (WeChat, Bilibili, audio via
Whisper) and more outputs — without changing the core.

### Why not wrap NotebookLM

The referenced project (`qiaomu-anything-to-notebooklm`) drives NotebookLM via
Playwright browser automation against a logged-in Google account. NotebookLM has
no public API. Running that server-side risks the Google account being flagged
(same datacenter-IP bot detection we hit with YouTube) and is fragile against UI
changes. We replicate the *outcome* with APIs we control (Claude + our existing
pipeline) instead.

---

## Scope

### Phase 1a (this spec — build now)
- Inputs: **paste text**, **web article URL**, **YouTube URL**
- Output: **structured Chinese summary** (`tldr`, `key_points[]`, `takeaways[]`)
- History: saved summaries list, view, delete
- Real-time progress via **SSE** (fetching → summarizing → done)

### Phase 1b (fast-follow, separate spec)
- "生成播客" hand-off: when a summary's source text is long enough, a button
  sends the extracted text to the podcast pipeline. Requires generalizing the
  podcast `/generate` endpoint to accept `source_text`. **Not in this spec.**

### Out of scope (later phases)
- WeChat / Bilibili / X ingestion adapters
- Audio sources (Ximalaya, podcasts) + Whisper ASR layer
- Mind maps, quizzes, flashcards, slides
- Summary language selection (Phase 1a is Chinese-only, consistent with portal)

---

## Architecture

```
            ┌─────────── source ───────────┐
  paste txt │  web url  │  youtube url      │
            └──────┬────────┬─────────┬─────┘
                   ▼        ▼         ▼
        ingestion_service.ingest(source_type, value)
          text → passthrough
          web  → trafilatura (fetch + article extraction)
          yt   → extract_transcript()   [reused from podcast]
                   └────────┬────────┘
                            ▼  (title, clean_text)
                   len(text) < MIN_CHARS ?  ── yes ──► 422 "content too short"
                            ▼ no
        summary_service.generate(text, key, model)
          → Claude → structured JSON {tldr, key_points[], takeaways[]}
                            ▼
                   save → summaries table
                            ▼
                   SSE "done" {summary}  ──► frontend renders + prepends to history
```

**Design principle:** ingestion adapters are independent units with one signature
(`value → (title, text)`). Adding a source later = registering one adapter; the
summary half never changes.

---

## Backend

### New files
```
backend/app/
  services/
    ingestion_service.py     # ingest(source_type, value) -> (title, text)
    summary_service.py       # generate_summary(text, key, model) -> dict
  api/v1/routes/
    summary.py               # POST /summary/generate (SSE), GET /summary/list, DELETE /summary/{id}
  models/entities.py         # + Summary model (edit) — table auto-created by
                             #   Base.metadata.create_all() on startup (no migration;
                             #   matches how PodcastEpisode was added)
```

### `ingestion_service.py`

```python
MIN_CONTENT_CHARS = 200

SourceType = Literal["text", "web", "youtube"]

def ingest(source_type: str, value: str) -> Tuple[str, str]:
    """Return (title, clean_text). Raises ValueError on failure / too-short."""
    if source_type == "text":
        title, text = _ingest_text(value)
    elif source_type == "web":
        title, text = _ingest_web(value)
    elif source_type == "youtube":
        title, text = _ingest_youtube(value)   # reuse extract_transcript
    else:
        raise ValueError(f"Unknown source type: {source_type}")
    if len(text.strip()) < MIN_CONTENT_CHARS:
        raise ValueError("Content too short to summarize (need ~200+ characters).")
    return title, text
```

- `_ingest_text(value)` → `("", value)` (title inferred later by Claude / first line)
- `_ingest_web(url)` → `trafilatura.fetch_url` + `trafilatura.extract`; title from
  trafilatura metadata; raise `ValueError("Could not extract article text")` if empty
- `_ingest_youtube(url)` → reuse `extract_transcript(url)` from `podcast_service`

### `summary_service.py`

```python
def generate_summary(text: str, anthropic_api_key: str, model: str) -> dict:
    """Return {"tldr": str, "key_points": [str], "takeaways": [str], "title": str}.
    Uses Claude tool/JSON output. Raises ValueError on parse failure."""
```

- Prompt instructs Claude to return **strict JSON** (Chinese content): a one-sentence
  `tldr`, 3–7 `key_points`, 2–4 `takeaways`, and a concise `title` (≤ 20 chars).
- Parse defensively: extract JSON from the response, validate keys/types; on failure
  raise `ValueError("Could not parse summary")`.
- If `ingest` returned a non-empty title (web/youtube), prefer it over Claude's; for
  pasted text, use Claude's inferred title.

### Routes — `summary.py`

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/summary/generate` | SSE: ingest → summarize → save → done |
| `GET` | `/api/v1/summary/list` | All summaries, newest first |
| `DELETE` | `/api/v1/summary/{id}` | Delete a summary row |

**SSE events** (reuse podcast pattern):
```
{"status": "fetching",    "message": "Fetching content..."}
{"status": "summarizing", "message": "Summarizing with Claude..."}
{"status": "done",        "summary": {...}}
{"status": "error",       "message": "..."}
```

Request body:
```json
{ "source_type": "text|web|youtube", "value": "<text or url>" }
```

Validation: `source_type` in the allowed set (422 otherwise); `value` non-empty.
For `web`/`youtube`, basic URL sanity check.

### Data model — `summaries` table

```sql
CREATE TABLE summaries (
    id           SERIAL PRIMARY KEY,
    source_type  TEXT NOT NULL,             -- 'text' | 'web' | 'youtube'
    source_url   TEXT,                       -- null for pasted text
    title        TEXT NOT NULL,
    tldr         TEXT NOT NULL,
    key_points   JSON NOT NULL,              -- list[str]
    takeaways    JSON NOT NULL,              -- list[str]
    char_count   INTEGER NOT NULL,           -- length of source text
    created_at   TIMESTAMP DEFAULT now()
);
```

`char_count` is stored so Phase 1b can decide whether to offer the podcast hand-off.

### Dependencies
- Add `trafilatura` to `backend/requirements.txt`. Nothing else (reuses Claude +
  `extract_transcript`). `httpx` already present; trafilatura bundles its own fetch.

### Error handling

| Scenario | Handling |
|----------|----------|
| Unknown source_type | 422 before stream |
| Empty `value` | 422 before stream |
| Web fetch fails / no article text | SSE error: "Could not extract article text from that URL." |
| YouTube no captions | SSE error (reuse existing transcript message) |
| Content < 200 chars | SSE error: "Content too short to summarize." |
| Claude call fails / unparseable | SSE error: "Could not generate summary — please try again." |

---

## Frontend

### New files (mirror podcast tool, same design system)
```
frontend/src/
  app/toolkits/summarize/page.tsx          # split panel, mobile-collapsible
  components/toolkits/
    summary-generator.tsx                  # source tabs + input + SSE progress
    summary-list.tsx                       # history list
    summary-view.tsx                       # render one structured summary
  lib/api.ts                               # (existing) API_BASE
```
Edit: `app/toolkits/page.tsx` (toolkit index) — add the second card, mark "ready".

### `summary-generator.tsx`
- **Source-type tabs:** `文本` / `网页` / `YouTube` (segmented control, same styling
  as podcast format toggle). Keyboard-navigable.
- Input adapts per tab: `<textarea>` for 文本, `<input type="url">` for 网页/YouTube.
- Generate button (disabled until input valid).
- **SSE progress** via `fetch` + `ReadableStream` reader (copy the podcast generator's
  AbortController + VALID_STATUSES pattern).
- Success → prepend new summary to list. Inline error box on failure.

### `summary-view.tsx` (hierarchy — gstack 3-second scan)
- **TL;DR** rendered largest/most prominent
- **关键要点 Key points** — bulleted list
- **核心收获 Takeaways** — bulleted list
- Source link (for web/youtube) + date

### `summary-list.tsx`
- History cards (title, source-type badge 文本/网页/YouTube, date) + delete `×`
  (40px touch target, confirm dialog, reuse podcast-episode-list pattern).
- Click a card → expand/show `summary-view`.
- **Empty state:** warmth + "用左边的生成器创建第一篇摘要" CTA (neutral copy that
  works on mobile too).

### `page.tsx` (reuse mobile pattern we just shipped)
- Desktop: split panel `lg:grid-cols-[2fr_3fr]` — generator left, history right.
- Mobile: generator collapses into a `📝 生成新摘要` tap-to-expand bar; history is
  primary; auto-expand on first run (no summaries yet).

### Design system (AI-slop guard)
- Use existing tokens only: `ink`, `ember`, `sand`, `pine`, `mint`, `Panel`
  (`rounded-[28px] border border-ink/10 bg-white/85 shadow-panel`). No new aesthetic.

### Dependencies
- None. Structured JSON → plain JSX (no markdown library).

---

## Testing

Backend unit tests (no live network — mock all I/O):
- `ingest`: each adapter dispatch; too-short guard raises; unknown type raises
- `_ingest_web`: mock `trafilatura` → returns (title, text); empty extraction raises
- `_ingest_youtube`: monkeypatch `extract_transcript`
- `summary_service.generate_summary`: mock `anthropic.Anthropic`; valid JSON parsed;
  malformed JSON raises `ValueError`; title preference logic
- Route validation: bad `source_type` → 422; empty `value` → 422

Frontend: TypeScript typecheck (tsc) must pass; manual mobile/desktop check post-deploy.

---

## Toolkit index card

Add to `app/toolkits/page.tsx`:
- Title: **内容摘要** / Summarize Anything
- Icon/emoji: 📝
- Description: "粘贴文本、网页或 YouTube 链接 → 获得结构化中文摘要"
- Tags: 文本 · 网页 · YouTube
- Status: ready → links to `/toolkits/summarize`

---

## Deployment

Standard pipeline (per CLAUDE.md): commit → push → tag → GitHub Actions builds
images → GHCR → VPS pulls & restarts. New backend dep (`trafilatura`) ships in the
backend image. The `summaries` table is created automatically by
`Base.metadata.create_all()` on backend startup (no migration step). No new secrets
required (reuses `ANTHROPIC_API_KEY`).

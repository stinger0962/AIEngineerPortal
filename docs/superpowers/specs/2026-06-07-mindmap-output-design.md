# 思维导图 / Mind Map Output — Design Spec

**Date:** 2026-06-07
**Status:** Approved
**Tool:** 织 Loom (蒸馏所 Distill)

---

## Overview

Add a second output type to **织 Loom**: **思维导图 / Mind Map**. After pasting a
source (text / web / YouTube / WeChat), the user chooses an output — **摘要
(Summary)** or **思维导图 (Mind Map)** — and Loom generates it on demand. Both
outputs live in one unified library, each badged by type.

A mind map is a separately-generated, richer artifact: Claude produces a
hierarchical Chinese markdown outline (3–4 levels), rendered as an interactive,
zoomable diagram with **markmap**.

### Why this model
Mirrors NotebookLM's on-demand artifact model (load source once, generate the
output you want when you want it). Keeps all of a user's distilled content in one
place. Reuses Loom's existing ingestion, table, list, delete, and SSE — the only
genuinely new pieces are the mind-map prompt and the markmap renderer.

---

## Scope

### In scope
- Output-type selector (摘要 / 思维导图) in Loom's generator
- `mindmap_service` — Claude → hierarchical markdown outline
- Persisted mind-map items in the existing table (`output_type`, `mindmap_md`)
- `MindMapView` — interactive markmap rendering, themed, mobile-friendly
- Unified library: both output types listed, badged, expand to the right view

### Out of scope (later)
- Other outputs (study guide, quiz, flashcards) — same pattern, future specs
- The full NotebookLM "one stored source → many artifacts" notebook model
- Citation grounding / multi-source Q&A
- Export (PNG/OPML) of mind maps

---

## Architecture

```
paste / url
   → ingest(source_type, value)            [shared, unchanged]
   → clean text
   → output_type == "summary"  → summary_service.generate_summary  → sections JSON
     output_type == "mindmap"  → mindmap_service.generate_mindmap  → markdown outline
   → save row to `summaries` table (output_type discriminator)
   → unified library
       → output_type == "summary"  → SummaryView
       → output_type == "mindmap"  → MindMapView (markmap)
```

The `summaries` table is now a generic "Loom outputs" store (name kept to avoid a
rename migration).

---

## Backend

### Data model — extend `Summary` (`backend/app/models/entities.py`)
Add two columns:
```python
    output_type: Mapped[str] = mapped_column(String(20), nullable=False, default="summary")  # summary | mindmap
    mindmap_md: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
```
- Summary rows: `output_type="summary"`, `sections` populated, `mindmap_md` null.
- Mindmap rows: `output_type="mindmap"`, `mindmap_md` populated, `sections=[]`, `tldr` a short one-line gist.

### Auto-migration (`backend/app/main.py` lifespan)
Extend the idempotent additive migration (same try/except pattern already added
for `sections`) with two more statements:
```python
    for ddl in (
        "ALTER TABLE summaries ADD COLUMN sections JSON",
        "ALTER TABLE summaries ADD COLUMN output_type VARCHAR(20) DEFAULT 'summary'",
        "ALTER TABLE summaries ADD COLUMN mindmap_md TEXT",
    ):
        try:
            with engine.begin() as conn:
                conn.execute(text(ddl))
        except Exception:
            pass
```
(Each in its own transaction so one "already exists" error doesn't abort the rest.)

### `mindmap_service.py` (new)
```python
def generate_mindmap(text: str, anthropic_api_key: str, model: str) -> dict:
    """Return {"title": str, "markdown": str} — a hierarchical Chinese markdown
    outline suitable for markmap. Raises ValueError on unusable output."""
```
- Prompt: produce a markdown outline — one `#` root (the central topic), `##`
  main branches, `###` sub-branches, `-` leaf points; 3–4 levels; concise Chinese
  labels (not full sentences); 4–7 main branches.
- Parse: strip code fences; require a single `#` root line and at least 2 `##`
  branches, else `ValueError("Mind map has no usable structure")`.
- Title = the `#` root text (fallback "思维导图").
- Cap input at the same `_MAX_INPUT_CHARS` as summaries.

### Routes (`backend/app/api/v1/routes/summary.py`)
- `GenerateRequest` gains `output_type: str = "summary"`; validate it's in
  `{"summary", "mindmap"}` (422 otherwise).
- In the SSE generate stream, after ingest, branch:
  - summary → existing path (sections)
  - mindmap → `generate_mindmap`; build row with `output_type="mindmap"`,
    `mindmap_md=result["markdown"]`, `tldr=""` (or a short gist), `sections=[]`,
    `title=result["title"]`.
- Item output schema gains `output_type: str` and `mindmap_md: Optional[str]`.
  `_to_out` includes both. `_sections_for` backward-compat unchanged.
- `list` and `delete` unchanged.
- SSE progress for mindmap: `fetching → mapping ("Building mind map...") → done`.

### Dependencies
Backend: none new.

---

## Frontend

### `summary-generator.tsx`
- Add an **output-type toggle** at the top (above Source): `摘要` / `思维导图`
  (segmented control, teal active — Loom's accent).
- Include `output_type` in the POST body.
- Adapt the button label: "Generate Summary" / "Generate Mind Map" (or 生成摘要 /
  生成思维导图).
- SSE statuses extend with `mapping`.

### `MindMapView` (new component)
- Props: `markdown: string`.
- Renders with **markmap** (`markmap-lib` Transformer + `markmap-view` Markmap)
  inside a `useEffect` on a ref'd `<svg>`. Fixed-height container (~`h-[360px]`
  mobile, taller on desktop), teal-leaning color options, interactive
  zoom/pan/collapse. Clean up the Markmap instance on unmount.

### Item type + list (`summary-view.tsx`, `summary-list.tsx`)
- The `Summary` (Loom item) type gains `output_type: "summary" | "mindmap"` and
  `mindmap_md: string | null`.
- List card: badge shows `摘要` or `思维导图`; the collapsed preview uses `tldr`
  for summaries and the root/"思维导图" label for maps.
- Expand: `output_type === "mindmap"` → `MindMapView`; else `SummaryView`.

### Dependencies
Frontend: add `markmap-lib` and `markmap-view` (npm, bundled — no CDN).

---

## Error handling

| Scenario | Handling |
|----------|----------|
| Invalid `output_type` | 422 before stream |
| Mind-map output unparseable / no structure | SSE error: "Could not build a mind map — please try again." |
| Ingestion / Claude failures | Same as summary path (clear SSE error) |
| markmap render error (frontend) | Catch in the effect; show a small "无法渲染思维导图" fallback message |

---

## Testing

Backend (mock Claude, no network):
- `mindmap_service.generate_mindmap`: valid markdown parsed → `{title, markdown}`;
  code-fence stripping; missing root/branches raises; title falls back.
- Route: `output_type` not in set → 422; (existing summary tests stay green).
- Model: `output_type` and `mindmap_md` columns present.

Frontend: `tsc --noEmit` passes; manual check that a generated map renders and
zoom/pan/collapse work on desktop and mobile.

---

## Deployment

Standard pipeline (commit → tag → GitHub Actions → GHCR → VPS). The two new
columns are added by the startup auto-migration. Frontend gains two bundled npm
deps. No new secrets (reuses `ANTHROPIC_API_KEY`).

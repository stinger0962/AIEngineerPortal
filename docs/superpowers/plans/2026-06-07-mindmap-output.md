# 思维导图 / Mind Map Output Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a second output type to 织 Loom — 思维导图 / Mind Map — generated on demand and rendered as an interactive markmap, living in the same unified library as summaries.

**Architecture:** A new `output_type` discriminator on the existing `summaries` table. The generate endpoint branches to `summary_service` (sections) or `mindmap_service` (markdown outline). The frontend gains an output toggle and a `MindMapView` rendering the outline with bundled markmap.

**Tech Stack:** FastAPI, SQLAlchemy (`create_all` + `apply_runtime_schema_patches`), Anthropic SDK, Next.js/React/Tailwind, `markmap-lib` + `markmap-view`.

**Spec:** `docs/superpowers/specs/2026-06-07-mindmap-output-design.md`

---

## File Structure

**Backend**
- Modify `backend/app/models/entities.py` — add `output_type`, `mindmap_md` to `Summary`
- Modify `backend/app/db/bootstrap.py` — add `SUMMARIES_COLUMN_PATCHES` (sections + output_type + mindmap_md), merge into patch set
- Modify `backend/app/main.py` — remove the now-redundant inline `sections` ALTER (handled by bootstrap)
- Create `backend/app/services/mindmap_service.py`
- Modify `backend/app/api/v1/routes/summary.py` — `output_type` param, branch, item schema
- Tests: `test_summary_model.py`, `test_mindmap_service.py` (new), `test_summary_routes.py`

**Frontend**
- `package.json` — add `markmap-lib`, `markmap-view`
- Create `frontend/src/components/toolkits/mindmap-view.tsx`
- Modify `summary-view.tsx` (item type), `summary-list.tsx` (badge + expand branch), `summary-generator.tsx` (output toggle)

---

## Task 1: Model columns

**Files:** Modify `backend/app/models/entities.py`; Test `backend/tests/test_summary_model.py`

- [ ] **Step 1: Update the model test**

In `backend/tests/test_summary_model.py`, change the expected columns set to include the two new columns:
```python
def test_summary_model_table_and_columns():
    from app.models.entities import Summary
    assert Summary.__tablename__ == "summaries"
    cols = set(Summary.__table__.columns.keys())
    assert {
        "id", "source_type", "source_url", "title", "tldr",
        "key_points", "takeaways", "sections",
        "output_type", "mindmap_md", "char_count", "created_at",
    }.issubset(cols)
```

- [ ] **Step 2: Run it, confirm it fails**

Run: `cd backend && python -m pytest tests/test_summary_model.py -v`
Expected: FAIL (output_type/mindmap_md not in columns).

- [ ] **Step 3: Add the columns**

In `backend/app/models/entities.py`, in the `Summary` class, add after the `sections` line:
```python
    output_type: Mapped[str] = mapped_column(String(20), nullable=False, default="summary")  # summary | mindmap
    mindmap_md: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
```

- [ ] **Step 4: Run it, confirm pass**

Run: `cd backend && python -m pytest tests/test_summary_model.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/app/models/entities.py backend/tests/test_summary_model.py
git commit -m "feat: add output_type and mindmap_md columns to Summary"
```

---

## Task 2: Runtime migration via bootstrap

**Files:** Modify `backend/app/db/bootstrap.py`, `backend/app/main.py`

- [ ] **Step 1: Add the summaries patch set in bootstrap.py**

In `backend/app/db/bootstrap.py`, after the `PHASE_TWO_COLUMN_PATCHES = {...}` block, add:
```python
SUMMARIES_COLUMN_PATCHES = {
    "summaries": [
        ("sections", "ALTER TABLE summaries ADD COLUMN sections JSON"),
        ("output_type", "ALTER TABLE summaries ADD COLUMN output_type VARCHAR(20) DEFAULT 'summary'"),
        ("mindmap_md", "ALTER TABLE summaries ADD COLUMN mindmap_md TEXT"),
    ],
}
```

- [ ] **Step 2: Merge it into the applied patches**

In `apply_runtime_schema_patches`, change the `all_patches` line from:
```python
        all_patches = {**PHASE_TWO_COLUMN_PATCHES, **PHASE_FIVE_COLUMN_PATCHES}
```
to:
```python
        all_patches = {**PHASE_TWO_COLUMN_PATCHES, **PHASE_FIVE_COLUMN_PATCHES, **SUMMARIES_COLUMN_PATCHES}
```
(The existing loop checks `inspector.get_columns` and only ALTERs missing columns — idempotent. The `summaries` table is skipped automatically if it doesn't exist yet, since create_all builds it with all columns from the model first.)

- [ ] **Step 3: Remove the now-redundant inline ALTER in main.py**

In `backend/app/main.py` lifespan, delete this block (the `sections` column is now handled by bootstrap's patch set):
```python
    from sqlalchemy import text
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE summaries ADD COLUMN sections JSON"))
        except Exception:
            pass
```
Leave the `Base.metadata.create_all(bind=engine)` and `apply_runtime_schema_patches(engine)` calls intact (apply runs right after create_all).

- [ ] **Step 4: Smoke-test the app boots + patches run**

Run: `cd backend && python -c "from app.main import app; print('ok')"`
Expected: prints `ok` with no import/migration errors.

- [ ] **Step 5: Commit**
```bash
git add backend/app/db/bootstrap.py backend/app/main.py
git commit -m "feat: add summaries column patches to bootstrap; drop inline ALTER"
```

---

## Task 3: Mind map service

**Files:** Create `backend/app/services/mindmap_service.py`; Test `backend/tests/test_mindmap_service.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_mindmap_service.py`:
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


def test_generate_mindmap_valid(monkeypatch):
    from app.services.mindmap_service import generate_mindmap
    md = "# 中心主题\n## 分支一\n- 要点1\n## 分支二\n- 要点2"
    _mock_claude(monkeypatch, md)
    out = generate_mindmap("正文内容", "k", "m")
    assert out["title"] == "中心主题"
    assert "## 分支一" in out["markdown"]


def test_generate_mindmap_strips_fences(monkeypatch):
    from app.services.mindmap_service import generate_mindmap
    _mock_claude(monkeypatch, "```markdown\n# 主题\n## A\n- x\n## B\n- y\n```")
    out = generate_mindmap("正文", "k", "m")
    assert out["title"] == "主题"
    assert out["markdown"].startswith("# 主题")


def test_generate_mindmap_no_structure_raises(monkeypatch):
    from app.services.mindmap_service import generate_mindmap
    _mock_claude(monkeypatch, "就是一段没有任何标题的普通文字")
    with pytest.raises(ValueError, match="structure"):
        generate_mindmap("正文", "k", "m")


def test_generate_mindmap_single_branch_raises(monkeypatch):
    from app.services.mindmap_service import generate_mindmap
    _mock_claude(monkeypatch, "# 主题\n## 只有一个分支\n- x")
    with pytest.raises(ValueError, match="structure"):
        generate_mindmap("正文", "k", "m")
```

- [ ] **Step 2: Run, confirm fail**

Run: `cd backend && python -m pytest tests/test_mindmap_service.py -v`
Expected: FAIL (ModuleNotFoundError).

- [ ] **Step 3: Implement the service**

Create `backend/app/services/mindmap_service.py`:
```python
"""Mind map generation via Claude — hierarchical Markdown outline for markmap."""
from __future__ import annotations

import re
from typing import Dict

_MAX_INPUT_CHARS = 20000

_MINDMAP_PROMPT = """你是一位专业的中文知识整理专家。请阅读以下内容，输出一份用于绘制思维导图的 Markdown 大纲。

要求：
1. 用 Markdown 标题层级表示结构：
   - 一个 `#` 一级标题作为中心主题（整张图的根节点）
   - 4-7 个 `##` 二级标题作为主要分支
   - `###` 三级标题作为子分支（按需）
   - `-` 列表项作为最末端的要点
2. 整体 3-4 层，结构清晰，覆盖核心内容
3. 节点文字简洁（短语或关键词，不要整句），全部使用中文
4. 直接输出 Markdown，不要代码块标记、不要任何解释或前言

内容：
{content}"""


def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw).strip()
    return raw


def generate_mindmap(text: str, anthropic_api_key: str, model: str) -> Dict:
    """Return {"title": str, "markdown": str} — a hierarchical Markdown outline.

    Raises ValueError if the output lacks a usable structure (a single `#` root and
    at least two `##` branches).
    """
    import anthropic

    client = anthropic.Anthropic(api_key=anthropic_api_key)
    prompt = _MINDMAP_PROMPT.format(content=text[:_MAX_INPUT_CHARS])
    message = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    md = _strip_fences(message.content[0].text)

    lines = md.splitlines()
    roots = [ln for ln in lines if ln.strip().startswith("# ")]
    branches = [ln for ln in lines if ln.strip().startswith("## ")]
    if not roots or len(branches) < 2:
        raise ValueError("Mind map has no usable structure")

    title = roots[0].strip().lstrip("#").strip() or "思维导图"
    return {"title": title, "markdown": md}
```

- [ ] **Step 4: Run, confirm pass (4 tests)**

Run: `cd backend && python -m pytest tests/test_mindmap_service.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/app/services/mindmap_service.py backend/tests/test_mindmap_service.py
git commit -m "feat: mindmap service (Claude hierarchical markdown outline)"
```

---

## Task 4: Routes — output_type branching

**Files:** Modify `backend/app/api/v1/routes/summary.py`; Test `backend/tests/test_summary_routes.py`

- [ ] **Step 1: Add a failing route test**

Append to `backend/tests/test_summary_routes.py`:
```python
def test_generate_rejects_bad_output_type():
    r = client.post("/api/v1/summary/generate", json={"source_type": "text", "value": "x", "output_type": "podcast"})
    assert r.status_code == 422
```

- [ ] **Step 2: Run, confirm fail**

Run: `cd backend && python -m pytest tests/test_summary_routes.py::test_generate_rejects_bad_output_type -v`
Expected: FAIL (currently 200/ignored, not 422).

- [ ] **Step 3: Update the routes**

In `backend/app/api/v1/routes/summary.py`:

(a) Add the import alongside the existing service imports:
```python
from app.services.mindmap_service import generate_mindmap
```

(b) Add `output_type` to the request model:
```python
class SummaryRequest(BaseModel):
    source_type: str
    value: str
    output_type: str = "summary"  # summary | mindmap
```

(c) Add a constant near `VALID_SOURCE_TYPES`:
```python
VALID_OUTPUT_TYPES = {"summary", "mindmap"}
```

(d) Add `output_type`/`mindmap_md` to `SummaryOut` (after `tldr`/`sections`):
```python
class SummaryOut(BaseModel):
    id: int
    source_type: str
    source_url: Optional[str]
    title: str
    tldr: str
    sections: List[Section]
    output_type: str
    mindmap_md: Optional[str]
    char_count: int
    created_at: str
```

(e) In `_to_out`, add the two fields:
```python
        "output_type": s.output_type,
        "mindmap_md": s.mindmap_md,
```

(f) In `generate`, add output_type validation after the source_type check:
```python
    if payload.output_type not in VALID_OUTPUT_TYPES:
        raise HTTPException(status_code=422, detail="Invalid output_type")
```

(g) Replace the body of `event_stream` between the ingest and the `db.add` with the branching logic:
```python
        try:
            yield {"data": json.dumps({"status": "fetching", "message": "Fetching content..."})}
            title, text = ingest(payload.source_type, payload.value)
            source_url = payload.value if payload.source_type in ("web", "youtube") else None

            if payload.output_type == "mindmap":
                yield {"data": json.dumps({"status": "mapping", "message": "Building mind map..."})}
                mm = generate_mindmap(text, settings.anthropic_api_key, settings.ai_model)
                item = Summary(
                    source_type=payload.source_type,
                    source_url=source_url,
                    title=(title or mm["title"] or "思维导图"),
                    tldr="",
                    key_points=[],
                    takeaways=[],
                    sections=[],
                    output_type="mindmap",
                    mindmap_md=mm["markdown"],
                    char_count=len(text),
                )
            else:
                yield {"data": json.dumps({"status": "summarizing", "message": "Summarizing with Claude..."})}
                result = generate_summary(text, settings.anthropic_api_key, settings.ai_model)
                item = Summary(
                    source_type=payload.source_type,
                    source_url=source_url,
                    title=(title or result["title"] or "未命名摘要"),
                    tldr=result["tldr"],
                    key_points=[],
                    takeaways=[],
                    sections=result["sections"],
                    output_type="summary",
                    mindmap_md=None,
                    char_count=len(text),
                )

            db.add(item)
            db.commit()
            db.refresh(item)

            yield {"data": json.dumps({"status": "done", "summary": _to_out(item)})}

        except ValueError as exc:
            db.rollback()
            logger.warning("Loom generation error: %s", exc)
            yield {"data": json.dumps({"status": "error", "message": str(exc)})}
        except Exception:
            db.rollback()
            logger.exception("Unexpected Loom generation error")
            yield {"data": json.dumps({"status": "error", "message": "Generation failed — please try again."})}
```
(Read the current `event_stream` first and replace its inner try/except accordingly; keep the `EventSourceResponse(event_stream())` return.)

- [ ] **Step 4: Run the route + full Loom suite**

Run: `cd backend && python -m pytest tests/test_summary_routes.py tests/test_summary_service.py tests/test_mindmap_service.py tests/test_summary_model.py tests/test_ingestion_service.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**
```bash
git add backend/app/api/v1/routes/summary.py backend/tests/test_summary_routes.py
git commit -m "feat: summary route branches on output_type (summary | mindmap)"
```

---

## Task 5: Frontend — markmap deps + MindMapView

**Files:** `frontend/package.json`; Create `frontend/src/components/toolkits/mindmap-view.tsx`

- [ ] **Step 1: Install markmap**

Run: `cd frontend && npm install markmap-lib markmap-view`
(If npm hits the SSL "unable to verify" error, use `npm install markmap-lib markmap-view --strict-ssl=false`.)
Expected: both added to `package.json` dependencies.

- [ ] **Step 2: Create the component**

Create `frontend/src/components/toolkits/mindmap-view.tsx`:
```tsx
"use client";

import { useEffect, useRef } from "react";
import { Transformer } from "markmap-lib";
import { Markmap } from "markmap-view";

const transformer = new Transformer();

export function MindMapView({ markdown }: { markdown: string }) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const mmRef = useRef<Markmap | null>(null);

  useEffect(() => {
    if (!svgRef.current) return;
    try {
      const { root } = transformer.transform(markdown || "# ");
      if (!mmRef.current) {
        mmRef.current = Markmap.create(svgRef.current, { duration: 300, paddingX: 16 }, root);
      } else {
        mmRef.current.setData(root);
      }
      mmRef.current.fit();
    } catch {
      // swallow render errors; fallback handled below by empty svg
    }
    return () => {
      mmRef.current?.destroy();
      mmRef.current = null;
    };
  }, [markdown]);

  if (!markdown) {
    return (
      <div className="rounded-xl border border-ink/10 bg-white p-4 text-sm text-ink/40">
        无法渲染思维导图
      </div>
    );
  }

  return (
    <div className="w-full h-[360px] lg:h-[460px] rounded-xl border border-ink/10 bg-white overflow-hidden">
      <svg ref={svgRef} className="w-full h-full" />
    </div>
  );
}
```

- [ ] **Step 3: Typecheck**

Run: `cd frontend && npx tsc --noEmit -p tsconfig.json`
Expected: no errors. (If markmap ships its own types this passes; if a type is missing, add `// @ts-expect-error` only on the specific failing import line — do not suppress globally.)

- [ ] **Step 4: Commit**
```bash
git add frontend/package.json frontend/package-lock.json frontend/src/components/toolkits/mindmap-view.tsx
git commit -m "feat: MindMapView component rendering markmap (bundled)"
```

---

## Task 6: Frontend — item type, output toggle, list rendering

**Files:** Modify `summary-view.tsx`, `summary-generator.tsx`, `summary-list.tsx`

- [ ] **Step 1: Extend the `Summary` type**

In `frontend/src/components/toolkits/summary-view.tsx`, update the `Summary` interface to add two fields (leave `SummaryView` rendering unchanged):
```tsx
export interface Summary {
  id: number;
  source_type: string;
  source_url: string | null;
  title: string;
  tldr: string;
  sections: Section[];
  output_type: "summary" | "mindmap";
  mindmap_md: string | null;
  char_count: number;
  created_at: string;
}
```

- [ ] **Step 2: Add the output toggle to the generator**

In `frontend/src/components/toolkits/summary-generator.tsx`:

(a) Extend the status union + labels to include `mapping`:
```tsx
type Status = "idle" | "fetching" | "summarizing" | "mapping" | "done" | "error";

const STATUS_LABELS: Record<Status, string> = {
  idle: "",
  fetching: "Fetching content...",
  summarizing: "Summarizing with Claude...",
  mapping: "Building mind map...",
  done: "Done!",
  error: "Failed",
};
```
(b) Update the `isBusy` check to include mapping:
```tsx
  const isBusy = status === "fetching" || status === "summarizing" || status === "mapping";
```
(c) Add an output-type state near the other useState calls:
```tsx
  const [outputType, setOutputType] = useState<"summary" | "mindmap">("summary");
```
(d) Include it in the POST body:
```tsx
        body: JSON.stringify({ source_type: sourceType, value, output_type: outputType }),
```
(e) Add the output toggle UI as the FIRST control inside the form (just under the `Generate Summary` heading span, before the Source block):
```tsx
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-ink/60">Output 输出</label>
        <div className="flex gap-2">
          {([["summary", "摘要"], ["mindmap", "思维导图"]] as const).map(([val, label]) => (
            <button
              key={val}
              onClick={() => setOutputType(val)}
              disabled={isBusy}
              className={`flex-1 rounded-xl py-2 text-sm font-medium transition-colors disabled:opacity-40 ${
                outputType === val
                  ? "bg-teal/15 text-teal border border-teal/40"
                  : "bg-white text-ink/50 border border-ink/15 hover:border-ink/30"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
```
(f) Make the Generate button label adapt:
```tsx
          <span aria-hidden="true">📝</span> {outputType === "mindmap" ? "Generate Mind Map" : "Generate Summary"}
```

- [ ] **Step 3: Render mind maps in the list**

In `frontend/src/components/toolkits/summary-list.tsx`:

(a) Import MindMapView:
```tsx
import { MindMapView } from "./mindmap-view";
```
(b) In the card, add an output-type badge next to the source badge. Find the source-type badge span and add before/after it:
```tsx
            <span className="text-[11px] px-2 py-0.5 rounded-full font-medium bg-teal/10 text-teal">
              {s.output_type === "mindmap" ? "思维导图" : "摘要"}
            </span>
```
(c) The collapsed preview currently shows `s.tldr`. Guard it for mind maps (no tldr):
```tsx
      {!open && s.output_type !== "mindmap" && <p className="text-xs text-ink/50 mt-2 line-clamp-2">{s.tldr}</p>}
```
(d) The expanded section currently renders `<SummaryView summary={s} />`. Branch it:
```tsx
      {open && (
        <div className="mt-4 pt-4 border-t border-ink/10">
          {s.output_type === "mindmap" ? (
            <MindMapView markdown={s.mindmap_md ?? ""} />
          ) : (
            <SummaryView summary={s} />
          )}
        </div>
      )}
```

- [ ] **Step 4: Typecheck**

Run: `cd frontend && npx tsc --noEmit -p tsconfig.json`
Expected: no errors.

- [ ] **Step 5: Commit**
```bash
git add frontend/src/components/toolkits/summary-view.tsx frontend/src/components/toolkits/summary-generator.tsx frontend/src/components/toolkits/summary-list.tsx
git commit -m "feat: Loom output toggle (摘要/思维导图) + mind map rendering in library"
```

---

## Task 7: Deploy

**Files:** none

- [ ] **Step 1: Full backend suite**

Run: `cd backend && python -m pytest tests/test_summary_routes.py tests/test_summary_service.py tests/test_mindmap_service.py tests/test_summary_model.py tests/test_ingestion_service.py tests/test_podcast_service.py -q`
Expected: all green.

- [ ] **Step 2: Frontend typecheck**

Run: `cd frontend && npx tsc --noEmit -p tsconfig.json`
Expected: no errors.

- [ ] **Step 3: Push + tag**
```bash
git push origin main
git tag v0.31.0
git push origin v0.31.0
```
(Use `git -c http.sslVerify=false push ...` if the local SSL interception blocks the push.)

- [ ] **Step 4: Watch deploy**

Run: `gh run watch $(gh run list --limit 2 --json databaseId,name --jq '.[] | select(.name == "Build & Deploy Portal") | .databaseId' | head -1)`
Expected: build + deploy succeed.

- [ ] **Step 5: Verify on live server**

Generate a mind map end to end (confirms branch + columns + render data):
```bash
ssh root@146.190.124.162 "docker exec infra-backend-1 python3 -c \"
import json, httpx
body={'source_type':'text','output_type':'mindmap','value':'人工智能正在改变软件开发。它能写代码、审查PR、调试问题，但需要清晰的规范、良好的上下文和人工监督才能避免幻觉和安全错误。最有效的团队把AI当作需要明确指令的初级工程师，而不是万能的预言机。测试、代码审查和渐进式发布在AI时代依然不可或缺。'}
with httpx.Client(timeout=120) as c:
    with c.stream('POST','http://172.18.0.4:8000/api/v1/summary/generate',json=body) as r:
        for line in r.iter_lines():
            if line.startswith('data:'):
                p=json.loads(line[5:].strip())
                if p['status']=='done':
                    s=p['summary']; print('output_type:',s['output_type']); print('title:',s['title']); print('md head:', (s['mindmap_md'] or '')[:80])
                elif p['status']=='error': print('ERROR',p['message'])
\""
```
Expected: `output_type: mindmap`, a title, and markdown starting with `#`.

Then in the browser: open 织 Loom, pick **思维导图**, generate from a URL, confirm the interactive map renders and zoom/pan/collapse work (desktop + mobile).

---

## Notes for the implementer
- **DB:** the two columns are added to fresh DBs by `create_all` (from the model) and to the existing prod table by `apply_runtime_schema_patches` (Task 2). No manual migration.
- **No new secrets** (reuses `ANTHROPIC_API_KEY`).
- **markmap is bundled** (npm), not loaded from a CDN — the earlier mockup's CDN failure does not apply.
- **Local test deps**: backend tests mock anthropic; `markmap-*` only needed for the frontend build/typecheck.

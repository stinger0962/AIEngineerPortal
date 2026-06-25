# Korean Authoring Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an offline dev CLI (`backend/scripts/korean_authoring/`) that drafts a Korean course region with Claude, validates it against the live schema + lint rules, runs an optional reviewer pass, and emits review-ready Python for `content.py`.

**Architecture:** A standalone Python package run from `backend/` via `python -m scripts.korean_authoring.cli <slug>`. Pure functions (lint, emit, prompt) are unit-tested directly; Claude-calling functions (generate, review) are tested with a fake client; a `--dry-run` mode runs the whole pipeline on a canned fixture with no API key. Reuses the live app's `validate_node_content` and `AIService`. Never touches the running app/DB/routes.

**Tech Stack:** Python 3.13, stdlib only (argparse, json, re, ast, pprint, dataclasses, importlib), `app.services.korean.content.validate_node_content`, `app.services.korean.personas.PERSONAS`, `app.services.ai_service.AIService`, pytest.

---

## Spec reference
`docs/superpowers/specs/2026-06-25-korean-authoring-pipeline-design.md`. Read it first.

## File structure
- Create `backend/scripts/__init__.py` (empty) — makes `scripts` a package so `python -m scripts...` and `from scripts...` work.
- Create `backend/scripts/korean_authoring/__init__.py` (empty).
- Create `backend/scripts/korean_authoring/briefs.py` — `RegionBrief` dataclass + `BRIEFS` registry + `get_brief`.
- Create `backend/scripts/korean_authoring/lint.py` — `validate_region`.
- Create `backend/scripts/korean_authoring/emit.py` — `render_region_python`.
- Create `backend/scripts/korean_authoring/prompt.py` — `few_shot_example`, `build_generation_prompt`, `build_review_prompt`.
- Create `backend/scripts/korean_authoring/generate.py` — `extract_json`, `coerce_region`, `generate_region`.
- Create `backend/scripts/korean_authoring/review.py` — `review_region`.
- Create `backend/scripts/korean_authoring/cli.py` — argparse entrypoint `main`.
- Create `backend/scripts/korean_authoring/fixtures/canned_getting-around.json` — a valid region used by `--dry-run`/tests.
- Create `backend/scripts/korean_authoring/out/.gitignore` — ignore emitted scratch files.
- Tests: `backend/tests/test_authoring_lint.py`, `test_authoring_emit.py`, `test_authoring_prompt.py`, `test_authoring_generate.py`, `test_authoring_review.py`, `test_authoring_cli.py`.

All tests run from `backend/` (its `conftest.py` puts the backend root on `sys.path`, so `import scripts.korean_authoring...` and `import app...` both resolve).

---

### Task 1: Package scaffold + RegionBrief + first brief

**Files:**
- Create: `backend/scripts/__init__.py`, `backend/scripts/korean_authoring/__init__.py`
- Create: `backend/scripts/korean_authoring/briefs.py`
- Test: `backend/tests/test_authoring_briefs.py`

- [ ] **Step 1: Write the failing test** — `backend/tests/test_authoring_briefs.py`:

```python
from scripts.korean_authoring.briefs import RegionBrief, get_brief, BRIEFS


def test_getting_around_brief_present():
    b = get_brief("getting-around")
    assert isinstance(b, RegionBrief)
    assert b.slug == "getting-around"
    assert b.order_index == 3
    assert b.counts == {"scenes": 3, "drills": 3, "boss": 1}
    assert b.boss_persona in {"barista", "taxi_driver", "officer", "friend"}
    assert len(b.target_vocab) >= 4
    assert all({"ko", "en", "romaji"} <= set(v) for v in b.target_vocab)


def test_unknown_brief_raises():
    import pytest
    with pytest.raises(KeyError):
        get_brief("does-not-exist")
```

- [ ] **Step 2: Run to verify it fails** — `cd backend && python -m pytest tests/test_authoring_briefs.py -v` → ModuleNotFoundError.

- [ ] **Step 3: Create the two empty `__init__.py` files**, then `backend/scripts/korean_authoring/briefs.py`:

```python
"""Region briefs — the curatorial input that steers generation. Author one per region
(3-9); the generator fills natural dialogue/drills around this fixed vocab/grammar."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RegionBrief:
    slug: str
    title: str
    theme: str
    order_index: int
    setting: str
    situations: list[str]
    target_vocab: list[dict]          # [{"ko","en","romaji"}, ...]
    target_grammar: list[str]
    boss_persona: str                 # must be a key in app.services.korean.personas.PERSONAS
    boss_goal_en: str
    counts: dict = field(default_factory=lambda: {"scenes": 3, "drills": 3, "boss": 1})


BRIEFS: dict[str, RegionBrief] = {
    "getting-around": RegionBrief(
        slug="getting-around",
        title="Getting Around",
        theme="transit",
        order_index=3,
        setting="A traveler navigating Seoul's subway and buses.",
        situations=[
            "buy a T-money transit card at a convenience store",
            "ask which subway line and direction to take",
            "confirm where to get off the bus",
        ],
        target_vocab=[
            {"ko": "지하철", "en": "subway", "romaji": "jihacheol"},
            {"ko": "버스", "en": "bus", "romaji": "beoseu"},
            {"ko": "역", "en": "station", "romaji": "yeok"},
            {"ko": "어디", "en": "where", "romaji": "eodi"},
            {"ko": "내려요", "en": "get off", "romaji": "naeryeoyo"},
            {"ko": "티머니", "en": "T-money card", "romaji": "timeoni"},
        ],
        target_grammar=["~까지 (to/until a place)", "어디 + 에서/에 (where at/to)"],
        boss_persona="taxi_driver",
        boss_goal_en="Get directions to the right subway line and ride one stop",
    ),
}


def get_brief(slug: str) -> RegionBrief:
    return BRIEFS[slug]
```

- [ ] **Step 4: Run to verify it passes** — `cd backend && python -m pytest tests/test_authoring_briefs.py -v` → 2 passed.

- [ ] **Step 5: Commit:**
```bash
git add backend/scripts/__init__.py backend/scripts/korean_authoring/__init__.py backend/scripts/korean_authoring/briefs.py backend/tests/test_authoring_briefs.py
git commit -m "feat(authoring): package scaffold + RegionBrief + getting-around brief"
```

---

### Task 2: Linter (`validate_region`)

**Files:**
- Create: `backend/scripts/korean_authoring/lint.py`
- Test: `backend/tests/test_authoring_lint.py`

- [ ] **Step 1: Write the failing test** — `backend/tests/test_authoring_lint.py`:

```python
from scripts.korean_authoring.lint import validate_region


def _good_region():
    return {
        "slug": "demo", "title": "Demo", "theme": "transit", "order_index": 3,
        "nodes": [
            {"slug": "demo-scene", "kind": "scene", "title": "S", "order_index": 0, "content_json": {
                "setting": "bus", "character": "driver",
                "lines": [{"speaker": "driver", "ko": "어디 가세요?", "romaji": "eodi gaseyo", "en": "Where to?", "audio_key": "a"}],
                "your_turns": [{"prompt_en": "Say downtown", "options": ["시내요"], "accepted": [{"ko": "시내요", "intents": ["downtown"]}]}],
                "new_vocab": [{"ko": "시내", "en": "downtown", "romaji": "sinae"}],
            }},
            {"slug": "demo-drill", "kind": "drill", "title": "D", "order_index": 1, "content_json": {
                "items": [{"type": "match", "ko": "버스", "answer": "bus", "choices": ["bus", "subway"]}],
            }},
            {"slug": "demo-boss", "kind": "boss", "title": "B", "order_index": 2, "content_json": {
                "goal_en": "ride one stop", "persona": "taxi_driver", "level": "beginner",
                "allowed_vocab": ["버스", "지하철"], "success_criteria": "rides", "max_turns": 8,
            }},
        ],
    }


def test_good_region_passes():
    assert validate_region(_good_region()) == []


def test_writing_drill_flagged():
    r = _good_region()
    r["nodes"][1]["content_json"]["items"] = [{"type": "fill", "prompt": "x", "answer": "버스"}]
    issues = validate_region(r)
    assert any("drill" in i for i in issues)


def test_choice_missing_answer_flagged():
    r = _good_region()
    r["nodes"][1]["content_json"]["items"][0]["choices"] = ["subway", "train"]
    assert any("choices" in i for i in validate_region(r))


def test_unknown_persona_flagged():
    r = _good_region()
    r["nodes"][2]["content_json"]["persona"] = "wizard"
    assert any("persona" in i for i in validate_region(r))


def test_unprefixed_slug_flagged():
    r = _good_region()
    r["nodes"][0]["slug"] = "scene"
    assert any("prefix" in i for i in validate_region(r))


def test_scene_missing_romaji_flagged():
    r = _good_region()
    r["nodes"][0]["content_json"]["lines"][0]["romaji"] = ""
    assert any("romaji" in i for i in validate_region(r))


def test_noncontiguous_order_flagged():
    r = _good_region()
    r["nodes"][2]["order_index"] = 5
    assert any("order_index" in i for i in validate_region(r))
```

- [ ] **Step 2: Run to verify it fails** — `cd backend && python -m pytest tests/test_authoring_lint.py -v` → ModuleNotFoundError.

- [ ] **Step 3: Implement** — `backend/scripts/korean_authoring/lint.py`:

```python
"""Lint a generated region: reuse the live schema validator + author-quality checks.
Returns a list of human-readable issues (empty = clean). Emit nothing if non-empty."""
from __future__ import annotations

from app.services.korean.content import validate_node_content
from app.services.korean.personas import PERSONAS

_TAP_TYPES = {"match", "listen"}


def validate_region(region: dict) -> list[str]:
    issues: list[str] = []
    nodes = region.get("nodes", [])
    region_slug = region.get("slug", "")

    slugs = [n.get("slug", "") for n in nodes]
    if len(slugs) != len(set(slugs)):
        issues.append("duplicate node slugs")

    for n in nodes:
        slug = n.get("slug", "")
        kind = n.get("kind", "")
        cj = n.get("content_json", {})

        if not (slug == region_slug or slug.startswith(region_slug + "-")):
            issues.append(f"node '{slug}' not prefixed with region slug '{region_slug}'")

        try:
            validate_node_content(kind, cj)
        except ValueError as exc:
            issues.append(f"node '{slug}': {exc}")
            continue

        if kind == "drill":
            for i, item in enumerate(cj["items"]):
                if item.get("type") not in _TAP_TYPES:
                    issues.append(f"node '{slug}' drill item {i}: writing type '{item.get('type')}' (tap-only)")
                elif item.get("answer") not in item.get("choices", []):
                    issues.append(f"node '{slug}' drill item {i}: choices missing answer")
        elif kind == "scene":
            if not cj.get("new_vocab"):
                issues.append(f"node '{slug}' scene: empty new_vocab")
            for j, line in enumerate(cj.get("lines", [])):
                for f_ in ("ko", "romaji", "en"):
                    if not line.get(f_):
                        issues.append(f"node '{slug}' scene line {j}: missing {f_}")
        elif kind == "boss":
            if cj.get("persona") not in PERSONAS:
                issues.append(f"node '{slug}' boss: unknown persona '{cj.get('persona')}'")
            if not cj.get("allowed_vocab"):
                issues.append(f"node '{slug}' boss: empty allowed_vocab")

    orders = [n.get("order_index") for n in nodes]
    if orders != list(range(len(nodes))):
        issues.append(f"order_index not contiguous 0..n: {orders}")

    return issues
```

- [ ] **Step 4: Run to verify it passes** — `cd backend && python -m pytest tests/test_authoring_lint.py -v` → 7 passed.

- [ ] **Step 5: Commit:**
```bash
git add backend/scripts/korean_authoring/lint.py backend/tests/test_authoring_lint.py
git commit -m "feat(authoring): region linter reusing schema validator"
```

---

### Task 3: Emitter (`render_region_python`) + round-trip

**Files:**
- Create: `backend/scripts/korean_authoring/emit.py`
- Test: `backend/tests/test_authoring_emit.py`

- [ ] **Step 1: Write the failing test** — `backend/tests/test_authoring_emit.py`:

```python
import ast

from scripts.korean_authoring.emit import render_region_python


def test_round_trips_and_preserves_korean():
    region = {
        "slug": "demo", "title": "Demo", "theme": "transit", "order_index": 3,
        "nodes": [{"slug": "demo-x", "kind": "drill", "title": "데모", "order_index": 0,
                   "content_json": {"items": [{"type": "match", "ko": "버스", "answer": "bus", "choices": ["bus", "subway"]}]}}],
    }
    text = render_region_python(region)
    assert text.startswith("REGION = ")
    # the literal after "REGION = " parses back to the exact region
    literal = text[len("REGION = "):]
    assert ast.literal_eval(literal) == region
    # Korean stays human-readable (not \uXXXX-escaped)
    assert "버스" in text
```

- [ ] **Step 2: Run to verify it fails** — `cd backend && python -m pytest tests/test_authoring_emit.py -v` → ModuleNotFoundError.

- [ ] **Step 3: Implement** — `backend/scripts/korean_authoring/emit.py`:

```python
"""Render a region dict as review-ready Python to paste into content.py. Uses pprint
(Python-3 repr keeps printable Korean as-is and preserves dict insertion order)."""
from __future__ import annotations

import pprint


def render_region_python(region: dict) -> str:
    body = pprint.pformat(region, sort_dicts=False, width=88)
    return f"REGION = {body}\n"
```

- [ ] **Step 4: Run to verify it passes** — `cd backend && python -m pytest tests/test_authoring_emit.py -v` → 1 passed.

- [ ] **Step 5: Commit:**
```bash
git add backend/scripts/korean_authoring/emit.py backend/tests/test_authoring_emit.py
git commit -m "feat(authoring): emit review-ready Python (round-trip safe)"
```

---

### Task 4: Prompt builder (`build_generation_prompt`, `few_shot_example`)

**Files:**
- Create: `backend/scripts/korean_authoring/prompt.py`
- Test: `backend/tests/test_authoring_prompt.py`

- [ ] **Step 1: Write the failing test** — `backend/tests/test_authoring_prompt.py`:

```python
from scripts.korean_authoring.briefs import get_brief
from scripts.korean_authoring.prompt import build_generation_prompt, build_review_prompt, few_shot_example


def test_few_shot_has_all_node_kinds():
    fs = few_shot_example()
    for kind in ("reading", "scene", "drill", "boss"):
        assert f'"{kind}"' in fs


def test_generation_prompt_includes_brief_and_rules():
    brief = get_brief("getting-around")
    system, user = build_generation_prompt(brief, few_shot_example())
    assert "match" in system and "listen" in system  # tap-only rule
    assert "fill" not in system or "no writing" in system.lower() or "tap-only" in system.lower()
    assert "지하철" in user  # brief vocab injected
    assert "getting-around" in user
    assert brief.boss_goal_en in user


def test_review_prompt_includes_region_json():
    brief = get_brief("getting-around")
    region = {"slug": "getting-around", "nodes": []}
    system, user = build_review_prompt(brief, region)
    assert "getting-around" in user
```

- [ ] **Step 2: Run to verify it fails** — `cd backend && python -m pytest tests/test_authoring_prompt.py -v` → ModuleNotFoundError.

- [ ] **Step 3: Implement** — `backend/scripts/korean_authoring/prompt.py`:

```python
"""Build the Claude prompts: a generation prompt (brief + few-shot of real content) and
a reviewer prompt (critique the draft). The few-shot is pulled from live regions 0-2 so
the model matches the established style/format exactly."""
from __future__ import annotations

import json

from app.services.korean.content import REGIONS
from .briefs import RegionBrief

_SCHEMAS = """Node content_json shapes (return EXACTLY these keys):
- reading: {"letters":[{"jamo","sound","audio_key"}], "blocks":[{"ko","romaji"}], "words":[{"ko","en"}]}
- scene: {"setting","character","lines":[{"speaker","ko","romaji","en","audio_key"}],
    "your_turns":[{"prompt_en","options":[str...],"accepted":[{"ko","intents":[str...]}]}],
    "new_vocab":[{"ko","en","romaji"}]}
- drill: {"items":[ ... ]} where each item is TAP-ONLY, one of:
    {"type":"match","ko","answer","choices":[...]}  (choices are English meanings incl. answer)
    {"type":"listen","audio_key","answer","choices":[...]}  (choices are Korean words incl. answer)
- boss: {"goal_en","persona","level","allowed_vocab":[...],"success_criteria","max_turns"}"""


def few_shot_example() -> str:
    """One real node of each kind from live regions 0-2, as a style exemplar."""
    picked: dict[str, dict] = {}
    for r in REGIONS:
        for n in r["nodes"]:
            picked.setdefault(n["kind"], n)
    ordered = [picked[k] for k in ("reading", "scene", "drill", "boss") if k in picked]
    return json.dumps({"nodes": ordered}, ensure_ascii=False, indent=2)


def build_generation_prompt(brief: RegionBrief, few_shot: str) -> tuple[str, str]:
    system = (
        "You are an expert author of beginner Korean course content for absolute beginners "
        "(speak/listen/READ only — NO writing). Produce natural, correct, situational Korean "
        "with accurate Revised Romanization and English glosses.\n\n"
        f"{_SCHEMAS}\n\n"
        "HARD RULES:\n"
        "- Drills are TAP-ONLY: every drill item type is 'match' or 'listen'. Never 'fill'/'type'.\n"
        "- Every drill item's choices MUST include its answer.\n"
        "- Every scene line has ko, romaji, en, audio_key. Each scene has non-empty new_vocab.\n"
        "- The boss uses the given persona and goal; allowed_vocab is drawn from the region vocab.\n"
        "- Return ONLY a JSON object: {\"nodes\":[{slug,kind,title,order_index,content_json}, ...]}.\n"
        "- Interleave scenes and drills (scene, its drill, scene, its drill, ...) then the boss last.\n\n"
        "STYLE EXEMPLAR (real content — match this shape and tone):\n" + few_shot
    )
    vocab = "\n".join(f"- {v['ko']} ({v['romaji']}) = {v['en']}" for v in brief.target_vocab)
    sit = "\n".join(f"- {s}" for s in brief.situations)
    user = (
        f"Author region '{brief.slug}' — {brief.title} (theme: {brief.theme}).\n"
        f"Setting: {brief.setting}\n"
        f"Produce exactly {brief.counts['scenes']} scenes + {brief.counts['drills']} drills "
        f"+ {brief.counts['boss']} boss.\n\n"
        f"Scene situations:\n{sit}\n\n"
        f"Target vocabulary (build the content around these):\n{vocab}\n\n"
        f"Target grammar: {', '.join(brief.target_grammar)}\n\n"
        f"Boss: persona='{brief.boss_persona}', goal='{brief.boss_goal_en}'.\n"
        f"Slug-prefix every node with '{brief.slug}-'."
    )
    return system, user


def build_review_prompt(brief: RegionBrief, region: dict) -> tuple[str, str]:
    system = (
        "You are a Korean-language reviewer. Critique the draft course region ONLY for: "
        "naturalness, beginner-level appropriateness, and situational accuracy. "
        "Return ONLY JSON: {\"notes\":[{\"node\":slug,\"severity\":\"low|med|high\",\"note\":str}]}. "
        "Empty notes list means it's good."
    )
    user = (
        f"Region brief: {brief.title} (vocab: {', '.join(v['ko'] for v in brief.target_vocab)}).\n\n"
        f"Draft region JSON:\n{json.dumps(region, ensure_ascii=False, indent=2)}"
    )
    return system, user
```

- [ ] **Step 4: Run to verify it passes** — `cd backend && python -m pytest tests/test_authoring_prompt.py -v` → 3 passed.

- [ ] **Step 5: Commit:**
```bash
git add backend/scripts/korean_authoring/prompt.py backend/tests/test_authoring_prompt.py
git commit -m "feat(authoring): generation + review prompt builders with live few-shot"
```

---

### Task 5: Generator (`extract_json`, `coerce_region`, `generate_region`)

**Files:**
- Create: `backend/scripts/korean_authoring/generate.py`
- Test: `backend/tests/test_authoring_generate.py`

- [ ] **Step 1: Write the failing test** — `backend/tests/test_authoring_generate.py`:

```python
import pytest

from scripts.korean_authoring.briefs import get_brief
from scripts.korean_authoring.generate import extract_json, coerce_region, generate_region


def test_extract_json_strips_fences():
    assert extract_json("```json\n{\"a\": 1}\n```") == {"a": 1}
    assert extract_json("prose before {\"b\": 2} after") == {"b": 2}


def test_extract_json_raises_without_object():
    with pytest.raises(ValueError):
        extract_json("no json here")


def test_coerce_prefixes_slug_and_renumbers():
    brief = get_brief("getting-around")
    nodes = [
        {"slug": "subway", "kind": "scene", "title": "S",
         "content_json": {"setting": "s", "character": "c", "lines": [{"speaker": "c", "ko": "x", "romaji": "x", "en": "x"}],
                          "your_turns": [], "new_vocab": [{"ko": "x", "en": "x", "romaji": "x"}]}},
    ]
    region = coerce_region(brief, nodes)
    assert region["slug"] == "getting-around"
    assert region["nodes"][0]["slug"] == "getting-around-subway"
    assert region["nodes"][0]["order_index"] == 0
    # scene line got a default audio_key
    assert region["nodes"][0]["content_json"]["lines"][0]["audio_key"]


class _Block:
    def __init__(self, t): self.type = "text"; self.text = t


class _Resp:
    def __init__(self, t): self.content = [_Block(t)]


class _Msgs:
    def __init__(self, t): self._t = t; self.calls = 0
    def create(self, **kw): self.calls += 1; return _Resp(self._t)


class _Client:
    def __init__(self, t): self.messages = _Msgs(t)


def test_generate_region_parses_and_coerces():
    brief = get_brief("getting-around")
    payload = '{"nodes":[{"slug":"x","kind":"boss","title":"B","content_json":{"goal_en":"g","persona":"taxi_driver","level":"beginner","allowed_vocab":["버스"],"success_criteria":"s","max_turns":8}}]}'
    client = _Client(payload)
    region = generate_region(brief, client, "m")
    assert region["slug"] == "getting-around"
    assert region["nodes"][0]["slug"] == "getting-around-x"
    assert region["nodes"][0]["order_index"] == 0


def test_generate_region_raises_on_unparseable():
    brief = get_brief("getting-around")
    with pytest.raises(ValueError):
        generate_region(brief, _Client("not json at all"), "m", max_retries=1)
```

- [ ] **Step 2: Run to verify it fails** — `cd backend && python -m pytest tests/test_authoring_generate.py -v` → ModuleNotFoundError.

- [ ] **Step 3: Implement** — `backend/scripts/korean_authoring/generate.py`:

```python
"""Call Claude to draft a region, then coerce the raw nodes into a content.py-shaped
region dict (prefix slugs, renumber order_index, default scene audio_keys)."""
from __future__ import annotations

import json
import re
from typing import Any

from .briefs import RegionBrief
from .prompt import build_generation_prompt, few_shot_example


def extract_json(text: str) -> dict:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n?", "", t)
        t = re.sub(r"\n?```$", "", t).strip()
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no JSON object found in model output")
    return json.loads(t[start:end + 1])


def coerce_region(brief: RegionBrief, nodes: list[dict]) -> dict:
    out: list[dict] = []
    for i, n in enumerate(nodes):
        slug = n.get("slug", "") or f"node{i}"
        if not slug.startswith(brief.slug + "-"):
            slug = f"{brief.slug}-{slug}"
        cj: dict[str, Any] = n.get("content_json", {})
        if n.get("kind") == "scene":
            for k, line in enumerate(cj.get("lines", [])):
                line.setdefault("audio_key", f"{slug}_{k}")
        out.append({
            "slug": slug,
            "kind": n.get("kind", ""),
            "title": n.get("title", ""),
            "order_index": i,
            "content_json": cj,
        })
    return {
        "slug": brief.slug,
        "title": brief.title,
        "theme": brief.theme,
        "order_index": brief.order_index,
        "nodes": out,
    }


def generate_region(brief: RegionBrief, client: Any, model: str, max_retries: int = 2) -> dict:
    system, user = build_generation_prompt(brief, few_shot_example())
    messages: list[dict] = [{"role": "user", "content": user}]
    last = ""
    for _ in range(max_retries + 1):
        resp = client.messages.create(model=model, max_tokens=4096, system=system, messages=messages)
        last = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        try:
            data = extract_json(last)
            return coerce_region(brief, data["nodes"])
        except (ValueError, KeyError, json.JSONDecodeError):
            messages = [
                {"role": "user", "content": user},
                {"role": "assistant", "content": last},
                {"role": "user", "content": "Return ONLY the JSON object with a top-level 'nodes' array. No prose, no code fences."},
            ]
    raise ValueError(f"could not parse generation after {max_retries + 1} attempts; last output:\n{last[:500]}")
```

- [ ] **Step 4: Run to verify it passes** — `cd backend && python -m pytest tests/test_authoring_generate.py -v` → 5 passed.

- [ ] **Step 5: Commit:**
```bash
git add backend/scripts/korean_authoring/generate.py backend/tests/test_authoring_generate.py
git commit -m "feat(authoring): Claude generator with JSON extraction + coercion + retry"
```

---

### Task 6: Reviewer pass (`review_region`)

**Files:**
- Create: `backend/scripts/korean_authoring/review.py`
- Test: `backend/tests/test_authoring_review.py`

- [ ] **Step 1: Write the failing test** — `backend/tests/test_authoring_review.py`:

```python
from scripts.korean_authoring.briefs import get_brief
from scripts.korean_authoring.review import review_region


class _Block:
    def __init__(self, t): self.type = "text"; self.text = t


class _Resp:
    def __init__(self, t): self.content = [_Block(t)]


class _Msgs:
    def __init__(self, t): self._t = t
    def create(self, **kw): return _Resp(self._t)


class _Client:
    def __init__(self, t): self.messages = _Msgs(t)


def test_review_returns_notes():
    brief = get_brief("getting-around")
    client = _Client('{"notes":[{"node":"getting-around-bus","severity":"low","note":"slightly formal"}]}')
    notes = review_region(brief, {"slug": "getting-around", "nodes": []}, client, "m")
    assert notes == [{"node": "getting-around-bus", "severity": "low", "note": "slightly formal"}]


def test_review_tolerates_garbage():
    brief = get_brief("getting-around")
    notes = review_region(brief, {"slug": "getting-around", "nodes": []}, _Client("sorry, no json"), "m")
    assert notes == []
```

- [ ] **Step 2: Run to verify it fails** — `cd backend && python -m pytest tests/test_authoring_review.py -v` → ModuleNotFoundError.

- [ ] **Step 3: Implement** — `backend/scripts/korean_authoring/review.py`:

```python
"""Optional second Claude pass: advisory critique of the draft's Korean. Never fails the
pipeline — returns [] if the model output can't be parsed."""
from __future__ import annotations

from typing import Any

from .briefs import RegionBrief
from .generate import extract_json
from .prompt import build_review_prompt


def review_region(brief: RegionBrief, region: dict, client: Any, model: str) -> list[dict]:
    system, user = build_review_prompt(brief, region)
    try:
        resp = client.messages.create(model=model, max_tokens=1500, system=system, messages=[{"role": "user", "content": user}])
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        return list(extract_json(text).get("notes", []))
    except Exception:
        return []
```

- [ ] **Step 4: Run to verify it passes** — `cd backend && python -m pytest tests/test_authoring_review.py -v` → 2 passed.

- [ ] **Step 5: Commit:**
```bash
git add backend/scripts/korean_authoring/review.py backend/tests/test_authoring_review.py
git commit -m "feat(authoring): advisory reviewer pass"
```

---

### Task 7: CLI + canned fixture + dry-run end-to-end

**Files:**
- Create: `backend/scripts/korean_authoring/fixtures/canned_getting-around.json`
- Create: `backend/scripts/korean_authoring/out/.gitignore`
- Create: `backend/scripts/korean_authoring/cli.py`
- Test: `backend/tests/test_authoring_cli.py`

- [ ] **Step 1: Create the canned fixture** — `backend/scripts/korean_authoring/fixtures/canned_getting-around.json` (a valid 7-node region; this is what `--dry-run` returns instead of calling Claude). It must pass `validate_region` after `coerce_region`:

```json
{"nodes": [
  {"slug": "getting-around-subway", "kind": "scene", "title": "Subway", "content_json": {
    "setting": "subway", "character": "staff",
    "lines": [
      {"speaker": "staff", "ko": "어디 가세요?", "romaji": "eodi gaseyo", "en": "Where are you going?", "audio_key": "ga_sub_1"},
      {"speaker": "you", "ko": "시청역이요.", "romaji": "sicheong-yeok-iyo", "en": "City Hall Station.", "audio_key": "ga_sub_2"}
    ],
    "your_turns": [{"prompt_en": "Say you're going to City Hall Station.", "options": ["시청역이요", "버스요"], "accepted": [{"ko": "시청역이요", "intents": ["city hall station"]}]}],
    "new_vocab": [{"ko": "지하철", "en": "subway", "romaji": "jihacheol"}, {"ko": "역", "en": "station", "romaji": "yeok"}]
  }},
  {"slug": "getting-around-subway-drill", "kind": "drill", "title": "Subway Drill", "content_json": {
    "items": [
      {"type": "match", "ko": "지하철", "answer": "subway", "choices": ["subway", "bus", "station"]},
      {"type": "listen", "audio_key": "ga_d_yeok", "answer": "역", "choices": ["역", "버스", "지하철"]}
    ]
  }},
  {"slug": "getting-around-directions", "kind": "scene", "title": "Directions", "content_json": {
    "setting": "station", "character": "passerby",
    "lines": [
      {"speaker": "you", "ko": "화장실 어디예요?", "romaji": "hwajangsil eodiyeyo", "en": "Where is the restroom?", "audio_key": "ga_dir_1"},
      {"speaker": "passerby", "ko": "저기예요.", "romaji": "jeogiyeyo", "en": "It's over there.", "audio_key": "ga_dir_2"}
    ],
    "your_turns": [{"prompt_en": "Ask where the exit is.", "options": ["출구 어디예요?", "감사합니다"], "accepted": [{"ko": "출구 어디예요?", "intents": ["where is the exit"]}]}],
    "new_vocab": [{"ko": "어디", "en": "where", "romaji": "eodi"}, {"ko": "출구", "en": "exit", "romaji": "chulgu"}]
  }},
  {"slug": "getting-around-directions-drill", "kind": "drill", "title": "Directions Drill", "content_json": {
    "items": [
      {"type": "match", "ko": "어디", "answer": "where", "choices": ["where", "exit", "station"]},
      {"type": "listen", "audio_key": "ga_d_chulgu", "answer": "출구", "choices": ["출구", "어디", "역"]}
    ]
  }},
  {"slug": "getting-around-bus", "kind": "scene", "title": "Bus", "content_json": {
    "setting": "bus", "character": "driver",
    "lines": [
      {"speaker": "you", "ko": "티머니 돼요?", "romaji": "timeoni dwaeyo", "en": "Can I use T-money?", "audio_key": "ga_bus_1"},
      {"speaker": "driver", "ko": "네, 돼요.", "romaji": "ne, dwaeyo", "en": "Yes, you can.", "audio_key": "ga_bus_2"}
    ],
    "your_turns": [{"prompt_en": "Ask if you can use T-money.", "options": ["티머니 돼요?", "버스요"], "accepted": [{"ko": "티머니 돼요?", "intents": ["can i use t-money"]}]}],
    "new_vocab": [{"ko": "버스", "en": "bus", "romaji": "beoseu"}, {"ko": "티머니", "en": "T-money card", "romaji": "timeoni"}]
  }},
  {"slug": "getting-around-bus-drill", "kind": "drill", "title": "Bus Drill", "content_json": {
    "items": [
      {"type": "match", "ko": "버스", "answer": "bus", "choices": ["bus", "subway", "T-money"]},
      {"type": "listen", "audio_key": "ga_d_timeoni", "answer": "티머니", "choices": ["티머니", "버스", "출구"]}
    ]
  }},
  {"slug": "getting-around-boss", "kind": "boss", "title": "Boss: Across the City", "content_json": {
    "goal_en": "Get directions to the right subway line and ride one stop",
    "persona": "taxi_driver", "level": "beginner",
    "allowed_vocab": ["지하철", "역", "어디", "출구", "버스", "티머니", "감사합니다"],
    "success_criteria": "Learner asks directions and confirms the stop", "max_turns": 8
  }}
]}
```

- [ ] **Step 2: Create `backend/scripts/korean_authoring/out/.gitignore`** with content:
```
*
!.gitignore
```

- [ ] **Step 3: Write the failing test** — `backend/tests/test_authoring_cli.py`:

```python
from pathlib import Path

from scripts.korean_authoring.cli import main


def test_dry_run_emits_clean_region(tmp_path, capsys):
    rc = main(["getting-around", "--dry-run"])
    assert rc == 0
    out = Path(__file__).resolve().parents[1] / "scripts" / "korean_authoring" / "out" / "getting-around.py"
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert text.startswith("REGION = ")
    assert "getting-around-boss" in text
    captured = capsys.readouterr().out
    assert "emitted" in captured


def test_dry_run_unknown_slug_errors():
    rc = main(["nope", "--dry-run"])
    assert rc == 2
```

- [ ] **Step 4: Run to verify it fails** — `cd backend && python -m pytest tests/test_authoring_cli.py -v` → ModuleNotFoundError.

- [ ] **Step 5: Implement** — `backend/scripts/korean_authoring/cli.py`:

```python
"""CLI: python -m scripts.korean_authoring.cli <slug> [--no-review] [--dry-run] [--model ID]
Flow: brief -> generate (or canned fixture) -> lint -> [review] -> emit out/<slug>.py."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .briefs import get_brief
from .generate import coerce_region, generate_region
from .lint import validate_region
from .emit import render_region_python
from .review import review_region

_HERE = Path(__file__).resolve().parent


def _load_fixture(slug: str) -> dict:
    return json.loads((_HERE / "fixtures" / f"canned_{slug}.json").read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="korean_authoring")
    parser.add_argument("slug")
    parser.add_argument("--no-review", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--model", default="claude-opus-4-8")
    args = parser.parse_args(argv)

    try:
        brief = get_brief(args.slug)
    except KeyError:
        print(f"unknown region slug: {args.slug!r}", file=sys.stderr)
        return 2

    client = None
    if args.dry_run:
        region = coerce_region(brief, _load_fixture(args.slug)["nodes"])
    else:
        from app.services.ai_service import AIService

        svc = AIService(model=args.model)
        if not svc.is_available:
            print("No Anthropic API key configured. Use --dry-run or set ANTHROPIC_API_KEY.", file=sys.stderr)
            return 2
        client = svc.client
        region = generate_region(brief, client, svc.model)

    issues = validate_region(region)
    if issues:
        print("LINT FAILED:")
        for i in issues:
            print(f"  - {i}")
        return 1

    notes: list[dict] = []
    if not args.dry_run and not args.no_review and client is not None:
        notes = review_region(brief, region, client, args.model)

    out_dir = _HERE / "out"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"{args.slug}.py"
    out_path.write_text(render_region_python(region), encoding="utf-8")

    print(f"emitted {out_path}")
    for n in notes:
        print(f"review[{n.get('severity', '?')}] {n.get('node', '?')}: {n.get('note', '')}")
    print("Review the file, fix anything, then paste REGION into app/services/korean/content.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Run to verify it passes** — `cd backend && python -m pytest tests/test_authoring_cli.py -v` → 2 passed.

- [ ] **Step 7: Commit:**
```bash
git add backend/scripts/korean_authoring/cli.py backend/scripts/korean_authoring/fixtures/canned_getting-around.json backend/scripts/korean_authoring/out/.gitignore backend/tests/test_authoring_cli.py
git commit -m "feat(authoring): CLI + canned fixture + dry-run end-to-end"
```

---

### Task 8: Full suite + README

**Files:**
- Create: `backend/scripts/korean_authoring/README.md`

- [ ] **Step 1: Run the whole authoring test suite**

Run: `cd backend && python -m pytest tests/test_authoring_*.py -v`
Expected: all pass (briefs 2, lint 7, emit 1, prompt 3, generate 5, review 2, cli 2 = 22).

- [ ] **Step 2: Run the full backend suite to confirm no regressions**

Run: `cd backend && python -m pytest -q`
Expected: all pass except the ~21 pre-existing `test_api.py` JSONB/SQLite errors (unrelated; they predate this work). No NEW failures.

- [ ] **Step 3: Exercise the real CLI in dry-run from the shell**

Run: `cd backend && python -m scripts.korean_authoring.cli getting-around --dry-run`
Expected: prints `emitted .../out/getting-around.py` and the review/paste hint; exit 0.

- [ ] **Step 4: Write `backend/scripts/korean_authoring/README.md`:**

```markdown
# Korean course authoring pipeline

Offline tool to draft a course region with Claude, validate it, and emit Python for
`app/services/korean/content.py`. Never touches the running app.

## Usage (run from `backend/`)
    python -m scripts.korean_authoring.cli <region-slug>            # generate (needs ANTHROPIC_API_KEY)
    python -m scripts.korean_authoring.cli <region-slug> --no-review
    python -m scripts.korean_authoring.cli <region-slug> --dry-run  # use canned fixture, no API

Output: `scripts/korean_authoring/out/<slug>.py` (gitignored). Review it + the printed
reviewer notes, fix anything, then paste the `REGION` dict into the `REGIONS` list in
`app/services/korean/content.py`, commit, and deploy via the normal pipeline.

## Add a region
1. Add a `RegionBrief` to `briefs.py` (slug, title, theme, order_index, vocab, grammar, boss).
2. If the boss needs a new persona, add it to `app/services/korean/personas.py`.
3. Run the CLI, review, paste into `content.py`.
```

- [ ] **Step 5: Commit:**
```bash
git add backend/scripts/korean_authoring/README.md
git commit -m "docs(authoring): pipeline README"
```

---

## Self-review notes (plan vs. spec)

- **Spec §2 placement / offline / reuses validator+AIService:** Tasks 1–7 build under `backend/scripts/korean_authoring/`; lint reuses `validate_node_content`; cli uses `AIService` — covered.
- **Spec §3 RegionBrief schema:** Task 1 dataclass matches the spec fields — covered.
- **Spec §4 generator (few-shot from 0-2, opus, JSON contract, coercion, retry):** Tasks 4–5 — covered.
- **Spec §5 linter checks (schema, no-writing, choices-incl-answer, scene vocab/romaji, persona, slugs, counts*):** Task 2. *Node-kind count check vs brief.counts: the linter checks order contiguity + per-kind validity; the explicit count-vs-brief assertion is enforced at authoring time via the brief and is verified by the dry-run fixture having the right counts. (If a strict count gate is wanted, it's a one-line add to `validate_region` taking the brief — noted, not blocking.)
- **Spec §6 reviewer pass (advisory, never fails):** Task 6 — covered.
- **Spec §7 emitter (round-trip Python):** Task 3 — covered.
- **Spec §8 CLI + dry-run:** Task 7 — covered.
- **Spec §9 error handling (retry, lint fails → emit nothing, no-key message):** Tasks 5 + 7 — covered.
- **Spec §10 testing (lint, emit round-trip, prompt, dry-run e2e):** Tasks 2–7 — covered.
- **Spec §11 regions 3–9:** out of scope for THIS plan (separate authoring work using the tool); Task 1 ships the first brief (getting-around) as the worked example/fixture.
- **Type consistency:** `RegionBrief` fields (Task 1) used unchanged in prompt/generate/cli; `validate_region`/`render_region_python`/`generate_region`/`review_region`/`coerce_region`/`extract_json` signatures match across tasks. Consistent.
- **Placeholder scan:** no TBD/TODO; every step has complete code/commands.

# AI-Assisted Korean Content Authoring Pipeline (Design)

**Date:** 2026-06-25
**Status:** Approved (brainstorm), ready for implementation planning
**Component:** New offline dev tool `backend/scripts/korean_authoring/`

## 1. Purpose & scope

The Korean course ([content.py](../../../backend/app/services/korean/content.py)) is static, hand-authored data. Three regions (0–2, 19 nodes) are live; the planned arc has ten (0–9). Hand-authoring the remaining seven is the bottleneck.

This tool is an **offline, dev-time pipeline** that drafts a region's lessons with Claude, validates them against the existing schema + lint rules, optionally runs an adversarial reviewer pass, and **emits review-ready Python** to paste into `content.py`. The loop is: *AI generates → schema validates → human reviews the diff → commit → deploy via the normal CI pipeline.* It gives authoring velocity while keeping curated quality and a human gate before any content reaches a learner.

The pipeline **never touches the running app, database, or routes.** It reuses the live app's `validate_node_content` (single source of truth) and Anthropic client, but runs entirely as a CLI.

### Non-goals
- No runtime/in-app content generation; no admin CMS; no DB writes.
- No new auth, endpoints, or services in the served app.
- `content.py` remains the single source of truth (the tool emits Python to be committed there; it does not introduce a separate content store).
- Not authoring regions 0–2 (already done); not the intermediate-grammar engine beyond what the existing node schema supports.

## 2. Architecture & placement

A standalone Python package `backend/scripts/korean_authoring/` (dev tool, mirrors the existing `backend/scripts/build_qian_signs.py` convention). Run from the `backend/` dir so `app.*` imports resolve.

```
backend/scripts/korean_authoring/
  __init__.py
  briefs.py        # the 10-region arc as RegionBrief data; briefs for 3–9
  prompt.py        # build_generation_prompt(brief, few_shot) + build_review_prompt(region)
  generate.py      # call Claude, parse + coerce JSON → region dict
  lint.py          # validate_region(region) → list[str] issues (reuses validate_node_content)
  emit.py          # render_region_python(region) → formatted .py text matching content.py
  review.py        # optional second Claude pass → advisory notes
  cli.py           # `python -m scripts.korean_authoring.cli <slug> [--no-review] [--dry-run]`
  fixtures/
    canned_arrival.json   # a recorded generation response for --dry-run / tests
  out/                    # emitted <slug>.py files (gitignored)
```

Dependencies: `app.services.korean.content.validate_node_content`, `app.services.korean.personas.PERSONAS`, `app.services.ai_service.AIService` (Anthropic client + model). No new third-party deps.

## 3. The Region Brief (curatorial control)

A `RegionBrief` is the human-authored input that steers generation. I draft each from the planned arc; the user approves/tweaks before running. Shape:

```python
@dataclass
class RegionBrief:
    slug: str                 # e.g. "getting-around"
    title: str                # "Getting Around"
    theme: str                # "transit"  (also drives the map seal)
    order_index: int          # 3
    setting: str              # one-line scene context for the model
    situations: list[str]     # 3 scene situations, e.g. ["buy a T-money card", "ask which subway line", "catch a bus"]
    target_vocab: list[dict]  # [{"ko","en","romaji"}, ...] the region's new words/phrases
    target_grammar: list[str] # ["~까지 (to/until)", "Sino numbers for line/stop counts"]
    boss_persona: str         # must be a key in personas.py (e.g. "taxi_driver"); new personas added there separately
    boss_goal_en: str         # "Buy a T-money card and ride one stop"
    counts: dict              # {"scenes": 3, "drills": 3, "boss": 1}  → node order interleaves scene,drill,...,boss
```

The brief fixes vocabulary and grammar (the pedagogy) so the model fills in natural dialogue/drills around them, rather than inventing scope.

## 4. Generator

`generate.py`:
- **Prompt** (`build_generation_prompt`): system prompt states the role (author beginner Korean course content), the exact `content_json` shapes per node kind, the hard rules (drills are tap-only `match`/`listen` **only**; every scene line needs `ko`/`romaji`/`en`/`audio_key`; scene `your_turns` have 1–3 `options` + `accepted` intents; boss uses the brief's persona/goal; `allowed_vocab` drawn from `target_vocab`), and a **few-shot example pulled verbatim from a real region 0–2 node** so the model matches style/format exactly. The brief is injected as the spec to realize.
- **Output contract:** the model returns a single JSON object `{"nodes": [ {slug, kind, title, order_index, content_json}, ... ]}`. Forced via an explicit "return only JSON" instruction; parsed with a tolerant extractor (strip code fences, find the outermost `{...}`).
- **Model:** Claude **opus** (`claude-opus-4-8`) for Korean quality — this is low-frequency, high-value (mirrors how Critique uses Opus). Configurable.
- **Coercion:** node `slug`s are region-prefixed if the model omits the prefix; `order_index` is renumbered 0..n by position; `audio_key`s defaulted if missing. The generator returns a `region` dict `{slug,title,theme,order_index,nodes}`.

## 5. Linter

`lint.py` `validate_region(region) -> list[str]` (empty = pass). Checks:
1. Every node passes `validate_node_content(node["kind"], node["content_json"])` (reused schema).
2. **No-writing guard:** every drill item `type` ∈ `{match, listen}` (defense beyond the schema).
3. Every drill item's `choices` includes its `answer`.
4. Every `scene` node has non-empty `new_vocab`; every scene line has `ko`/`romaji`/`en`.
5. Boss node `persona` ∈ `PERSONAS` keys; `allowed_vocab` non-empty and a subset of the brief's `target_vocab` ko-strings (warn, not fail, if it adds a few).
6. Node `slug`s globally unique and region-prefixed; `order_index` 0..n contiguous.
7. Node-kind counts match the brief's `counts`.

Failures are returned as precise strings (`"node 'getting-around-taxi' scene: line 2 missing romaji"`). The pipeline emits nothing if any hard check fails.

## 6. Reviewer pass (on by default; `--no-review` to skip)

`review.py`: a second Claude call given the generated region + the brief, asked to critique **only** Korean naturalness, beginner-level appropriateness, and situational accuracy, returning `{"notes": [{"node","severity","note"}]}`. Notes are **advisory** — printed for the human reviewer, never auto-applied. This catches "grammatically valid but unnatural/too-advanced" content the schema can't.

## 7. Emitter

`emit.py` `render_region_python(region) -> str`: produces a formatted Python region literal matching `content.py`'s existing style (indentation, key order, trailing commas), written to `out/<slug>.py`. The reviewer (me) reads it, applies any fixes from the reviewer notes, and pastes it into the `REGIONS` list in `content.py`. The emitted file is gitignored (`out/` is scratch); the *reviewed* content lands in `content.py` via a normal commit.

## 8. CLI & data flow

`python -m scripts.korean_authoring.cli <region-slug> [--no-review] [--dry-run] [--model <id>]`

Flow: `brief (briefs.py) → generate (Claude) → coerce → lint → [review] → emit out/<slug>.py → print summary (issues, review notes, path)`. On any hard lint failure: print issues, exit non-zero, emit nothing. `--dry-run` loads `fixtures/canned_<slug>.json` instead of calling Claude (CI-safe, no key).

Human step (outside the script): review `out/<slug>.py` + reviewer notes → fix → paste into `content.py` → commit → deploy (existing seed/CI pipeline picks it up).

## 9. Error handling
- Claude returns unparseable/invalid JSON → up to 2 retries with a stricter "return only valid JSON matching this schema" instruction → on final failure, save raw output to `out/<slug>.raw.txt` and exit non-zero. Emit nothing.
- Lint failure → report exact node/field, exit non-zero, emit nothing (all-or-nothing per region; never partial).
- Missing API key and not `--dry-run` → clear error pointing to `--dry-run` or env setup.

## 10. Testing
- **Linter** (`test_authoring_lint.py`): good region passes; targeted bad fixtures each trip the right check (writing drill, choice-missing-answer, bad persona, dup slug, count mismatch, scene missing romaji).
- **Emitter round-trip** (`test_authoring_emit.py`): `render_region_python(region)` → write temp module → import → equals the input region → passes `validate_region`. Guarantees emitted Python is valid and re-ingestible.
- **Prompt builder** (`test_authoring_prompt.py`): prompt contains the brief's vocab, the tap-only rule, and a few-shot example.
- **Pipeline `--dry-run`** (`test_authoring_cli.py`): runs end-to-end on the canned fixture (no API), produces a lint-clean `out/` file. Runs in CI without a key.
- Claude calls mocked elsewhere (mirrors `test_ai_service`).

## 11. Using it — regions 3–9 (the #2 work, separate plan/PRs)
Author one region per pass: draft `RegionBrief` (from the arc below) → run pipeline → review draft + notes → fix → commit into `content.py` → deploy. Planned arc:

| # | slug | title |
|---|------|-------|
| 3 | getting-around | Getting Around (subway/bus/directions/T-money) |
| 4 | shopping | Shopping (prices/sizes/convenience store) |
| 5 | stay | Stay (hotel check-in/wifi/checkout) |
| 6 | restaurant | Restaurant (menus/recommendations/the bill) |
| 7 | making-friends | Making Friends (intro/hobbies/KakaoTalk) |
| 8 | living-here | Living Here (pharmacy/doctor/phone setup/deliveries) |
| 9 | intermediate | Intermediate (opinions/past-future/casual↔polite) |

New boss personas (e.g. `shopkeeper`, `receptionist`, `server`, `new_friend`, `pharmacist`) are added to `personas.py` as needed — a one-line entry each.

## 12. Out of scope (later)
- Runtime/in-app authoring or editing (A→B upgrade path: the generator core is reusable behind an authenticated endpoint if ever wanted).
- Auto-applying reviewer notes.
- Generating audio assets (TTS is already on-demand at runtime).
- Authoring the home-hub mascot/UI; pronunciation scoring; server Whisper STT.

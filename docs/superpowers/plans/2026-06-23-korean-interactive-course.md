# 한국어 Korean Interactive Course — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable, beginner-oriented Korean course module (`/korean`) inside the 方寸 platform: a journey-map of regions whose nodes run a Reading/Scene/Drill/Boss loop, with tap/type + browser-mic speaking, MiniMax TTS, and a Claude roleplay boss — shipping the engine plus regions 0–2 (한글 Island, Arrival, Café).

**Architecture:** Mirror the existing `ziwei`/`qian` modules. Content lives in two seeded tables (`KoreanRegion`, `KoreanNode` with a flexible `content_json`); per-user state lives in `KoreanProgress`, the existing `MemoryCard` table (`category="korean"`), and `KoreanConversation`/`KoreanMessage`. A `KoreanOracle` service (mirror of `ZiweiOracle`) drives the boss over SSE. The frontend is a Next.js route under `frontend/src/app/korean/` with a typed API client mirroring `lib/ziwei/api.ts`.

**Tech Stack:** FastAPI + SQLAlchemy (JSON columns, `Base.metadata.create_all` + `apply_runtime_schema_patches`), Anthropic Claude (`AIService`), MiniMax TTS (`_tts_bytes`), Next.js 15 / React 19 / TanStack Query / Tailwind, browser Web Speech API (`SpeechRecognition`, `lang="ko-KR"`). Tests: pytest with the SQLite `TestClient` harness in `backend/tests/test_api.py`.

---

## Spec reference

Design doc: `docs/superpowers/specs/2026-06-23-korean-interactive-course-design.md`. Read it before starting.

## File structure

**Backend — create:**
- `backend/app/services/korean/__init__.py` — package marker.
- `backend/app/services/korean/personas.py` — Korean tutor persona prompt fragments.
- `backend/app/services/korean/oracle.py` — `KoreanOracle` (boss roleplay + verdict).
- `backend/app/services/korean/content.py` — authored regions/nodes data + `validate_node_content`.
- `backend/app/services/korean/service.py` — query/progress/reset logic + MemoryCard seeding.
- `backend/app/api/v1/routes/korean.py` — HTTP routes.
- `backend/tests/test_korean_content.py`, `test_korean_service.py`, `test_korean_routes.py`, `test_korean_oracle.py`.

**Backend — modify:**
- `backend/app/models/entities.py` — add `KoreanRegion`, `KoreanNode`, `KoreanProgress`, `KoreanConversation`, `KoreanMessage`.
- `backend/app/models/__init__.py` — export the five new models.
- `backend/app/db/bootstrap.py` — add Korean index patches (tables themselves come from `create_all`).
- `backend/app/services/seed_service.py` — call `sync_korean_content`.
- `backend/app/api/v1/api.py` — register `korean.router`.
- `backend/app/core/config.py` — add `korean_model`, `minimax_korean_voice_id`.

**Frontend — create:**
- `frontend/src/lib/korean/types.ts` — shared TS types for content/state.
- `frontend/src/lib/korean/api.ts` — typed API client + SSE boss stream.
- `frontend/src/lib/korean/use-speech.ts` — Web Speech API hook (mic STT).
- `frontend/src/lib/korean/use-tts.ts` — TTS playback hook (fetch + cache + play).
- `frontend/src/app/korean/page.tsx` — the journey map page.
- `frontend/src/app/korean/node/[nodeSlug]/page.tsx` — node player route.
- `frontend/src/components/korean/journey-map.tsx` — region/node map UI + reset control.
- `frontend/src/components/korean/node-player.tsx` — dispatches by node kind.
- `frontend/src/components/korean/reading-node.tsx`, `scene-node.tsx`, `drill-node.tsx`, `boss-node.tsx`.
- `frontend/src/components/korean/romanization-toggle.tsx`.

**Frontend — modify:**
- `frontend/src/components/home/folding-screen-hub.tsx` — add a 한국어 tile (follow existing tile pattern).

---

## PHASE A — Backend data foundation

### Task A1: Add Korean ORM models

**Files:**
- Modify: `backend/app/models/entities.py` (append at end of file)
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_korean_models.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_korean_models.py`:

```python
from app.models import (
    KoreanConversation,
    KoreanMessage,
    KoreanNode,
    KoreanProgress,
    KoreanRegion,
)


def test_korean_models_have_expected_tables():
    assert KoreanRegion.__tablename__ == "korean_regions"
    assert KoreanNode.__tablename__ == "korean_nodes"
    assert KoreanProgress.__tablename__ == "korean_progress"
    assert KoreanConversation.__tablename__ == "korean_conversations"
    assert KoreanMessage.__tablename__ == "korean_messages"


def test_korean_node_has_content_json_and_kind():
    cols = {c.name for c in KoreanNode.__table__.columns}
    assert {"region_id", "slug", "kind", "order_index", "title", "content_json"} <= cols


def test_korean_progress_is_user_scoped():
    cols = {c.name for c in KoreanProgress.__table__.columns}
    assert {"user_id", "node_id", "status", "score", "stars", "completed_at"} <= cols
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_korean_models.py -v`
Expected: FAIL with `ImportError: cannot import name 'KoreanRegion'`.

- [ ] **Step 3: Add models to `entities.py`**

Append to `backend/app/models/entities.py`:

```python
class KoreanRegion(Base):
    __tablename__ = "korean_regions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    theme: Mapped[str] = mapped_column(String(120), default="")
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class KoreanNode(Base):
    __tablename__ = "korean_nodes"
    __table_args__ = (
        Index("ix_korean_nodes_slug", "slug", unique=True),
        Index("ix_korean_nodes_region", "region_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("korean_regions.id"))
    slug: Mapped[str] = mapped_column(String(160), unique=True)
    kind: Mapped[str] = mapped_column(String(20))  # reading | scene | drill | boss
    title: Mapped[str] = mapped_column(String(200))
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    content_json: Mapped[Dict] = mapped_column(JSON, default=dict)


class KoreanProgress(Base):
    __tablename__ = "korean_progress"
    __table_args__ = (
        Index("ix_korean_progress_user_node", "user_id", "node_id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    node_id: Mapped[int] = mapped_column(ForeignKey("korean_nodes.id"))
    status: Mapped[str] = mapped_column(String(20), default="locked")  # locked|unlocked|completed
    score: Mapped[float] = mapped_column(Float, default=0.0)
    stars: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class KoreanConversation(Base):
    __tablename__ = "korean_conversations"
    __table_args__ = (Index("ix_korean_conv_user_node", "user_id", "node_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    node_id: Mapped[int] = mapped_column(ForeignKey("korean_nodes.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class KoreanMessage(Base):
    __tablename__ = "korean_messages"
    __table_args__ = (Index("ix_korean_msg_conv", "conversation_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 4: Export from `models/__init__.py`**

Add the five names to both the `from app.models.entities import (...)` block and `__all__` in `backend/app/models/__init__.py`:

```python
    KoreanConversation,
    KoreanMessage,
    KoreanNode,
    KoreanProgress,
    KoreanRegion,
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_korean_models.py -v`
Expected: PASS (3 passed).

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/entities.py backend/app/models/__init__.py backend/tests/test_korean_models.py
git commit -m "feat(korean): add Korean course ORM models"
```

### Task A2: Add Korean index patches to bootstrap

**Files:**
- Modify: `backend/app/db/bootstrap.py:79-93` (the `INDEX_PATCHES` list)

- [ ] **Step 1: Append Korean indexes to `INDEX_PATCHES`**

In `backend/app/db/bootstrap.py`, add these entries to the `INDEX_PATCHES` list (before the closing `]`):

```python
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_korean_nodes_slug ON korean_nodes (slug)",
    "CREATE INDEX IF NOT EXISTS ix_korean_nodes_region ON korean_nodes (region_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_korean_progress_user_node ON korean_progress (user_id, node_id)",
    "CREATE INDEX IF NOT EXISTS ix_korean_conv_user_node ON korean_conversations (user_id, node_id)",
    "CREATE INDEX IF NOT EXISTS ix_korean_msg_conv ON korean_messages (conversation_id)",
```

> Note: tables are created by `Base.metadata.create_all` in `main.py:29`; these patches only ensure indexes exist on already-deployed DBs, matching the existing pattern.

- [ ] **Step 2: Verify import still loads**

Run: `cd backend && python -c "from app.db.bootstrap import INDEX_PATCHES; assert any('korean_nodes' in p for p in INDEX_PATCHES); print('ok')"`
Expected: prints `ok`.

- [ ] **Step 3: Commit**

```bash
git add backend/app/db/bootstrap.py
git commit -m "feat(korean): add Korean index patches to bootstrap"
```

---

## PHASE B — Content (regions 0–2)

Content is authored as Python data validated against a per-kind schema. Author **all** nodes for regions 0–2. The tasks below define the schema + validator, give one fully-worked node per kind as the authoring template, and list the exact vocabulary/goals per region so the remaining nodes are mechanical to fill in.

### Task B1: Content schema validator

**Files:**
- Create: `backend/app/services/korean/__init__.py` (empty)
- Create: `backend/app/services/korean/content.py`
- Test: `backend/tests/test_korean_content.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_korean_content.py`:

```python
import pytest

from app.services.korean.content import REGIONS, validate_node_content


def test_validate_reading_node_ok():
    validate_node_content("reading", {
        "letters": [{"jamo": "ㅏ", "sound": "a", "audio_key": "jamo_a"}],
        "blocks": [{"ko": "가", "romaji": "ga"}],
        "words": [{"ko": "가구", "en": "furniture"}],
    })


def test_validate_scene_node_ok():
    validate_node_content("scene", {
        "setting": "airport",
        "character": "officer",
        "lines": [{"speaker": "officer", "ko": "여권이요", "romaji": "yeogwonieyo", "en": "Passport, please", "audio_key": "k1"}],
        "your_turns": [{"prompt_en": "Hand over passport", "options": ["네, 여기요"], "accepted": [{"ko": "여기요", "intents": ["here you go"]}]}],
        "new_vocab": [{"ko": "여권", "en": "passport", "romaji": "yeogwon"}],
    })


def test_validate_rejects_unknown_kind():
    with pytest.raises(ValueError):
        validate_node_content("mystery", {})


def test_validate_rejects_missing_field():
    with pytest.raises(ValueError):
        validate_node_content("boss", {"goal_en": "order coffee"})  # missing persona/level/...


def test_all_seeded_content_is_valid():
    for region in REGIONS:
        for node in region["nodes"]:
            validate_node_content(node["kind"], node["content_json"])


def test_regions_cover_0_through_2():
    slugs = {r["slug"] for r in REGIONS}
    assert {"hangul-island", "arrival", "cafe-food"} <= slugs
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_korean_content.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.korean.content'`.

- [ ] **Step 3: Implement the validator skeleton + empty REGIONS**

Create `backend/app/services/korean/__init__.py` (empty file).

Create `backend/app/services/korean/content.py` with the validator and an empty `REGIONS = []` for now (B2 fills content):

```python
"""Authored Korean course content (regions 0-2) + per-kind content_json validation."""
from __future__ import annotations

from typing import Any

_REQUIRED_FIELDS: dict[str, set[str]] = {
    "reading": {"letters", "blocks", "words"},
    "scene": {"setting", "character", "lines", "your_turns", "new_vocab"},
    "drill": {"items"},
    "boss": {"goal_en", "persona", "level", "allowed_vocab", "success_criteria", "max_turns"},
}

VALID_KINDS = set(_REQUIRED_FIELDS)


def validate_node_content(kind: str, content: dict[str, Any]) -> None:
    if kind not in _REQUIRED_FIELDS:
        raise ValueError(f"unknown node kind: {kind!r}")
    missing = _REQUIRED_FIELDS[kind] - set(content or {})
    if missing:
        raise ValueError(f"{kind} node missing fields: {sorted(missing)}")
    if kind == "drill":
        for item in content["items"]:
            if item.get("type") not in {"match", "listen", "fill", "type"}:
                raise ValueError(f"drill item has invalid type: {item.get('type')!r}")


REGIONS: list[dict[str, Any]] = []  # populated in content_data below
```

- [ ] **Step 4: Run test to verify partial pass**

Run: `cd backend && python -m pytest tests/test_korean_content.py -v`
Expected: validator tests PASS; `test_all_seeded_content_is_valid` PASS (empty loop); `test_regions_cover_0_through_2` FAIL (REGIONS empty). This confirms the validator works before authoring.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/korean/__init__.py backend/app/services/korean/content.py backend/tests/test_korean_content.py
git commit -m "feat(korean): content_json schema validator"
```

### Task B2: Author regions 0–2 content

**Files:**
- Modify: `backend/app/services/korean/content.py` (replace `REGIONS = []` with authored data)

Author the data below. Each region is `{"slug","title","theme","order_index","nodes":[...]}`; each node is `{"slug","kind","title","order_index","content_json":{...}}`. Node slugs must be globally unique — prefix with the region slug (e.g. `arrival-greetings`).

**Authoring templates (one per kind — copy the shape, fill real Korean):**

```python
# READING node content_json
{
    "letters": [{"jamo": "ㅏ", "sound": "a", "audio_key": "jamo_a"}],
    "blocks": [{"ko": "가", "romaji": "ga"}],
    "words": [{"ko": "아기", "en": "baby"}],
}

# SCENE node content_json
{
    "setting": "cafe",
    "character": "barista",
    "lines": [
        {"speaker": "barista", "ko": "어서 오세요!", "romaji": "eoseo oseyo", "en": "Welcome!", "audio_key": "cafe1"},
    ],
    "your_turns": [
        {
            "prompt_en": "Greet back",
            "options": ["안녕하세요", "감사합니다"],
            "accepted": [{"ko": "안녕하세요", "intents": ["hello", "hi"]}],
        },
    ],
    "new_vocab": [{"ko": "안녕하세요", "en": "hello", "romaji": "annyeonghaseyo"}],
}

# DRILL node content_json
{
    "items": [
        {"type": "match", "ko": "주세요", "answer": "please give", "choices": ["please give", "thank you"]},
        {"type": "listen", "audio_key": "num_dul", "answer": "둘", "choices": ["하나", "둘"]},
        {"type": "fill", "prompt": "아메리카노 ___", "answer": "주세요"},
        {"type": "type", "prompt_en": "Say hello", "answer": "안녕하세요"},
    ],
}

# BOSS node content_json
{
    "goal_en": "Order a coffee and pay for it",
    "persona": "barista",
    "level": "beginner",
    "allowed_vocab": ["아메리카노", "주세요", "한 잔", "얼마예요", "카드", "감사합니다"],
    "success_criteria": "Learner orders a drink and responds to the price",
    "max_turns": 8,
}
```

**Region 0 · `hangul-island`** (theme `"reading"`, order 0) — 5 reading nodes:
- `hangul-vowels` — basic vowels ㅏ ㅓ ㅗ ㅜ ㅡ ㅣ ㅑ ㅕ ㅛ ㅠ (letters + 2-3 blocks + 2 words).
- `hangul-consonants-1` — ㄱ ㄴ ㄷ ㄹ ㅁ ㅂ ㅅ (+ blocks like 가 나 다, words 가구/나무).
- `hangul-consonants-2` — ㅇ ㅈ ㅊ ㅋ ㅌ ㅍ ㅎ + double ㄲㄸㅃㅆㅉ (+ blocks, words 아기/우유).
- `hangul-blocks-batchim` — syllable assembly + 받침 (final consonant): 한, 글, 밥, 물 (blocks + words 한국/사람).
- `hangul-read-signs` — reading real signs/words: 출구 (exit), 화장실 (restroom), 카페, 지하철 (words only; this is the reading mini-boss).

**Region 1 · `arrival`** (theme `"arrival"`, order 1) — 3 scenes + 3 drills + 1 boss (8 nodes), interleave scene→drill:
- `arrival-greetings` (scene): 안녕하세요 / 감사합니다 / 네 / 아니요 / 죄송합니다. new_vocab those 5.
- `arrival-greetings-drill` (drill): 4 items over the greetings vocab.
- `arrival-immigration` (scene): officer asks 여권이요 (passport), 무슨 일로 오셨어요? (purpose) → 여행이요 (travel). new_vocab 여권/여행/관광.
- `arrival-immigration-drill` (drill): 4 items.
- `arrival-taxi` (scene): 어디 가세요? (where to) → 시내요 / 호텔이요; 얼마예요? (how much). new_vocab 시내/호텔/얼마예요.
- `arrival-taxi-drill` (drill): 4 items.
- `arrival-boss` (boss): goal "Take a taxi from the airport to your hotel", persona `taxi_driver`, level beginner, allowed_vocab from this region, max_turns 8.

**Region 2 · `cafe-food`** (theme `"cafe"`, order 2) — 3 scenes + 3 drills + 1 boss (8 nodes):
- `cafe-ordering` (scene): 어서 오세요 / 뭐 드릴까요? → 아메리카노 주세요. new_vocab 아메리카노/주세요/뭐.
- `cafe-ordering-drill` (drill): 4 items.
- `cafe-numbers` (scene): native numbers 하나~다섯 + counter 잔 (한 잔/두 잔). new_vocab 하나/둘/잔/한 잔.
- `cafe-numbers-drill` (drill): 4 items.
- `cafe-paying` (scene): 얼마예요? → 4500원이요; 카드요 / 현금이요. new_vocab 얼마예요/원/카드/현금.
- `cafe-paying-drill` (drill): 4 items.
- `cafe-boss` (boss): goal "Order a drink and pay", persona `barista`, level beginner, allowed_vocab from this region, max_turns 8.

- [ ] **Step 1: Author the data**

Replace `REGIONS = []` in `content.py` with the full authored list following the structure and vocab above. Every node's `content_json` must satisfy `validate_node_content`.

- [ ] **Step 2: Run the content validation test**

Run: `cd backend && python -m pytest tests/test_korean_content.py -v`
Expected: PASS — including `test_all_seeded_content_is_valid` and `test_regions_cover_0_through_2`.

- [ ] **Step 3: Assert node counts (guard against accidental omissions)**

Add to `backend/tests/test_korean_content.py`:

```python
def test_region_node_counts():
    by_slug = {r["slug"]: r for r in REGIONS}
    assert len(by_slug["hangul-island"]["nodes"]) == 5
    assert len(by_slug["arrival"]["nodes"]) == 7
    assert len(by_slug["cafe-food"]["nodes"]) == 7


def test_node_slugs_globally_unique():
    slugs = [n["slug"] for r in REGIONS for n in r["nodes"]]
    assert len(slugs) == len(set(slugs))
```

Run: `cd backend && python -m pytest tests/test_korean_content.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/korean/content.py backend/tests/test_korean_content.py
git commit -m "feat(korean): author regions 0-2 (hangul island, arrival, cafe)"
```

### Task B3: Seed content into the DB

**Files:**
- Modify: `backend/app/services/seed_service.py`
- Test: `backend/tests/test_korean_seed.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_korean_seed.py`:

```python
from pathlib import Path
from tempfile import mkdtemp

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models import KoreanNode, KoreanRegion
from app.services.seed_service import seed_database

DB = Path(mkdtemp(prefix="korean-seed-")) / "t.db"
engine = create_engine(f"sqlite:///{DB.as_posix()}", connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_seed_creates_regions_and_nodes_idempotently():
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        seed_database(db)
        seed_database(db)  # second run must not duplicate
        regions = db.scalars(select(KoreanRegion)).all()
        nodes = db.scalars(select(KoreanNode)).all()
        assert len(regions) == 3
        assert len(nodes) == 19  # 5 + 7 + 7
    finally:
        db.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_korean_seed.py -v`
Expected: FAIL — `regions` is empty (no sync yet).

- [ ] **Step 3: Add `sync_korean_content` and call it**

In `backend/app/services/seed_service.py`, add the import and function, and call it inside `seed_database`:

```python
from app.models import KoreanNode, KoreanRegion  # add to existing model imports
from app.services.korean.content import REGIONS as KOREAN_REGIONS  # add near other seed imports


def sync_korean_content(db: Session) -> None:
    for r in KOREAN_REGIONS:
        region = db.scalar(select(KoreanRegion).where(KoreanRegion.slug == r["slug"]))
        if not region:
            region = KoreanRegion(
                slug=r["slug"], title=r["title"], theme=r.get("theme", ""),
                order_index=r["order_index"], is_active=True,
            )
            db.add(region)
            db.flush()
        for n in r["nodes"]:
            node = db.scalar(select(KoreanNode).where(KoreanNode.slug == n["slug"]))
            if not node:
                node = KoreanNode(region_id=region.id, slug=n["slug"])
                db.add(node)
            node.region_id = region.id
            node.kind = n["kind"]
            node.title = n["title"]
            node.order_index = n["order_index"]
            node.content_json = n["content_json"]
    db.commit()
```

Add the call inside `seed_database`, right after `seed_memory_cards(db)`:

```python
    sync_korean_content(db)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_korean_seed.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/seed_service.py backend/tests/test_korean_seed.py
git commit -m "feat(korean): seed regions/nodes idempotently"
```

---

## PHASE C — Backend service & routes

### Task C1: Map + progress query service

**Files:**
- Create: `backend/app/services/korean/service.py`
- Test: `backend/tests/test_korean_service.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_korean_service.py`:

```python
from pathlib import Path
from tempfile import mkdtemp

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models import KoreanProgress, MemoryCard, User
from app.services.korean import service as ksvc
from app.services.seed_service import seed_database

DB = Path(mkdtemp(prefix="korean-svc-")) / "t.db"
engine = create_engine(f"sqlite:///{DB.as_posix()}", connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _setup():
    Base.metadata.create_all(bind=engine)
    db = Session()
    seed_database(db)
    return db


def test_get_map_first_node_unlocked_rest_locked():
    db = _setup()
    try:
        uid = db.scalar(select(User.id))
        m = ksvc.get_map(db, uid)
        first_region = m[0]
        assert first_region["nodes"][0]["status"] == "unlocked"
        assert first_region["nodes"][1]["status"] == "locked"
    finally:
        db.close()


def test_complete_node_unlocks_next_and_seeds_cards():
    db = _setup()
    try:
        uid = db.scalar(select(User.id))
        m = ksvc.get_map(db, uid)
        first_slug = m[0]["nodes"][0]["slug"]
        ksvc.complete_node(db, uid, first_slug, score=1.0, stars=3)
        m2 = ksvc.get_map(db, uid)
        assert m2[0]["nodes"][0]["status"] == "completed"
        assert m2[0]["nodes"][1]["status"] == "unlocked"
    finally:
        db.close()


def test_reset_progress_clears_only_this_user():
    db = _setup()
    try:
        uid = db.scalar(select(User.id))
        first_slug = ksvc.get_map(db, uid)[0]["nodes"][0]["slug"]
        ksvc.complete_node(db, uid, first_slug, score=1.0, stars=3)
        ksvc.reset_progress(db, uid)
        assert db.scalars(select(KoreanProgress).where(KoreanProgress.user_id == uid)).all() == []
        assert db.scalars(select(MemoryCard).where(MemoryCard.category == "korean")).all() == []
        # map back to start
        assert ksvc.get_map(db, uid)[0]["nodes"][0]["status"] == "unlocked"
    finally:
        db.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_korean_service.py -v`
Expected: FAIL — `ModuleNotFoundError` / `AttributeError: module ... has no attribute 'get_map'`.

- [ ] **Step 3: Implement the service**

Create `backend/app/services/korean/service.py`:

```python
"""Korean course query/progress logic. State is user-scoped; content is shared."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    KoreanConversation,
    KoreanMessage,
    KoreanNode,
    KoreanProgress,
    KoreanRegion,
    MemoryCard,
)


def _ordered_nodes(db: Session, region_id: int) -> list[KoreanNode]:
    return db.scalars(
        select(KoreanNode).where(KoreanNode.region_id == region_id).order_by(KoreanNode.order_index.asc())
    ).all()


def _flat_node_order(db: Session) -> list[KoreanNode]:
    regions = db.scalars(select(KoreanRegion).order_by(KoreanRegion.order_index.asc())).all()
    out: list[KoreanNode] = []
    for r in regions:
        out.extend(_ordered_nodes(db, r.id))
    return out


def _progress_map(db: Session, user_id: int) -> dict[int, KoreanProgress]:
    rows = db.scalars(select(KoreanProgress).where(KoreanProgress.user_id == user_id)).all()
    return {p.node_id: p for p in rows}


def get_map(db: Session, user_id: int) -> list[dict[str, Any]]:
    """Regions with per-node status. The first node overall is unlocked by default;
    a node is unlocked once the node before it (in flat order) is completed."""
    flat = _flat_node_order(db)
    prog = _progress_map(db, user_id)
    completed_ids = {nid for nid, p in prog.items() if p.status == "completed"}

    status_by_node: dict[int, str] = {}
    for idx, node in enumerate(flat):
        if node.id in completed_ids:
            status_by_node[node.id] = "completed"
        elif idx == 0 or flat[idx - 1].id in completed_ids:
            status_by_node[node.id] = "unlocked"
        else:
            status_by_node[node.id] = "locked"

    regions = db.scalars(select(KoreanRegion).order_by(KoreanRegion.order_index.asc())).all()
    result: list[dict[str, Any]] = []
    for r in regions:
        nodes = _ordered_nodes(db, r.id)
        result.append({
            "slug": r.slug, "title": r.title, "theme": r.theme, "order_index": r.order_index,
            "nodes": [
                {
                    "slug": n.slug, "kind": n.kind, "title": n.title, "order_index": n.order_index,
                    "status": status_by_node[n.id],
                    "stars": prog[n.id].stars if n.id in prog else 0,
                }
                for n in nodes
            ],
        })
    return result


def get_node(db: Session, slug: str) -> KoreanNode | None:
    return db.scalar(select(KoreanNode).where(KoreanNode.slug == slug))


def complete_node(db: Session, user_id: int, slug: str, score: float, stars: int) -> dict[str, Any]:
    node = get_node(db, slug)
    if node is None:
        raise ValueError("unknown node")
    row = db.scalar(
        select(KoreanProgress).where(
            KoreanProgress.user_id == user_id, KoreanProgress.node_id == node.id
        )
    )
    if row is None:
        row = KoreanProgress(user_id=user_id, node_id=node.id)
        db.add(row)
    row.status = "completed"
    row.score = score
    row.stars = max(row.stars, stars)
    row.completed_at = datetime.utcnow()
    _seed_cards_for_node(db, node)
    db.commit()
    return {"slug": slug, "status": "completed", "stars": row.stars}


def _seed_cards_for_node(db: Session, node: KoreanNode) -> None:
    """Turn a scene node's new_vocab into spaced-repetition MemoryCards (category=korean)."""
    if node.kind != "scene":
        return
    for v in node.content_json.get("new_vocab", []):
        front, back = v.get("ko", ""), v.get("en", "")
        if not front:
            continue
        exists = db.scalar(
            select(MemoryCard).where(MemoryCard.category == "korean", MemoryCard.front_md == front)
        )
        if exists:
            continue
        db.add(MemoryCard(
            front_md=front, back_md=back, category="korean", source_kind="lesson",
            source_title=node.title, difficulty="beginner", tags_json=["korean"],
        ))


def reset_progress(db: Session, user_id: int) -> dict[str, int]:
    node_ids = db.scalars(select(KoreanNode.id)).all()
    conv_ids = db.scalars(
        select(KoreanConversation.id).where(KoreanConversation.user_id == user_id)
    ).all()
    deleted_progress = 0
    for p in db.scalars(select(KoreanProgress).where(KoreanProgress.user_id == user_id)).all():
        db.delete(p); deleted_progress += 1
    for m in db.scalars(select(MemoryCard).where(MemoryCard.category == "korean")).all():
        db.delete(m)
    if conv_ids:
        for msg in db.scalars(select(KoreanMessage).where(KoreanMessage.conversation_id.in_(conv_ids))).all():
            db.delete(msg)
    for c in db.scalars(select(KoreanConversation).where(KoreanConversation.user_id == user_id)).all():
        db.delete(c)
    db.commit()
    return {"deleted_progress": deleted_progress}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_korean_service.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/korean/service.py backend/tests/test_korean_service.py
git commit -m "feat(korean): map/progress/reset service with MemoryCard seeding"
```

### Task C2: Korean persona + KoreanOracle (boss roleplay)

**Files:**
- Create: `backend/app/services/korean/personas.py`
- Create: `backend/app/services/korean/oracle.py`
- Test: `backend/tests/test_korean_oracle.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_korean_oracle.py`:

```python
from app.services.korean.oracle import KoreanOracle


class _FakeBlock:
    def __init__(self, text): self.type = "text"; self.text = text


class _FakeUsage:
    input_tokens = 10; output_tokens = 5


class _FakeResp:
    def __init__(self, text):
        self.content = [_FakeBlock(text)]; self.usage = _FakeUsage()


class _FakeMessages:
    def __init__(self, text): self._text = text
    def create(self, **kwargs):
        self._kwargs = kwargs
        return _FakeResp(self._text)


class _FakeClient:
    def __init__(self, text): self.messages = _FakeMessages(text)


def test_oracle_system_prompt_constrains_vocab():
    client = _FakeClient("네, 아메리카노 한 잔이요. [[goal_met]]")
    oracle = KoreanOracle(client=client, model="x")
    boss = {"goal_en": "Order coffee", "persona": "barista", "level": "beginner",
            "allowed_vocab": ["아메리카노", "주세요"], "success_criteria": "orders a drink", "max_turns": 8}
    result = oracle.run(boss=boss, messages=[{"role": "user", "content": "아메리카노 주세요"}])
    assert result is not None
    assert result["goal_met"] is True
    assert "아메리카노" in client.messages._kwargs["system"]  # allowed vocab injected


def test_oracle_detects_goal_not_met():
    client = _FakeClient("안녕하세요! 뭐 드릴까요?")
    oracle = KoreanOracle(client=client, model="x")
    boss = {"goal_en": "Order coffee", "persona": "barista", "level": "beginner",
            "allowed_vocab": ["아메리카노"], "success_criteria": "orders a drink", "max_turns": 8}
    result = oracle.run(boss=boss, messages=[{"role": "user", "content": "안녕하세요"}])
    assert result["goal_met"] is False
    assert "[[goal_met]]" not in result["response"]  # marker stripped from display text


def test_oracle_returns_none_on_api_failure():
    class _Boom:
        class messages:
            @staticmethod
            def create(**kwargs): raise RuntimeError("down")
    oracle = KoreanOracle(client=_Boom(), model="x")
    boss = {"goal_en": "x", "persona": "barista", "level": "beginner",
            "allowed_vocab": [], "success_criteria": "x", "max_turns": 8}
    assert oracle.run(boss=boss, messages=[{"role": "user", "content": "hi"}]) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_korean_oracle.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.korean.oracle'`.

- [ ] **Step 3: Implement personas**

Create `backend/app/services/korean/personas.py`:

```python
"""Korean roleplay personas. KoreanNode boss content_json.persona selects one."""

PERSONAS: dict[str, str] = {
    "barista": "You are a friendly Korean café barista. Speak natural but simple Korean.",
    "taxi_driver": "You are a patient Korean taxi driver. Speak short, clear Korean.",
    "officer": "You are a polite Korean immigration officer. Speak formal, simple Korean.",
    "friend": "You are a warm Korean friend the learner just met. Speak casual, simple Korean.",
}

DEFAULT_PERSONA = "friend"


def persona_prompt(persona: str) -> str:
    return PERSONAS.get(persona, PERSONAS[DEFAULT_PERSONA])
```

- [ ] **Step 4: Implement KoreanOracle**

Create `backend/app/services/korean/oracle.py`:

```python
"""Korean roleplay boss: one Claude call per turn, constrained to the learner's level
and the node's allowed vocabulary. A trailing [[goal_met]] marker signals success."""
from __future__ import annotations

import time
from typing import Any, Optional

from .personas import persona_prompt

_GOAL_MARKER = "[[goal_met]]"


class KoreanOracle:
    def __init__(self, client: Any, model: str):
        self.client = client
        self.model = model

    def _system_prompt(self, boss: dict) -> str:
        vocab = "、".join(boss.get("allowed_vocab", []))
        return (
            f"{persona_prompt(boss.get('persona', ''))}\n\n"
            "You are roleplaying with an absolute-beginner Korean learner inside a language game.\n"
            f"The learner's level is: {boss.get('level', 'beginner')}.\n"
            f"Scene goal (in English, for you only): {boss.get('goal_en', '')}.\n"
            f"Success means: {boss.get('success_criteria', '')}.\n\n"
            "RULES:\n"
            "- Reply ONLY in short, simple Korean (1-2 sentences). No English, no romanization.\n"
            f"- Stay within this vocabulary plus tiny obvious additions: {vocab}.\n"
            "- Stay in character; gently steer the learner toward the goal.\n"
            f"- When the learner has clearly achieved the goal, append the literal marker {_GOAL_MARKER} "
            "at the very end of your reply (it is stripped before display)."
        )

    def run(self, boss: dict, messages: list[dict]) -> Optional[dict]:
        start = time.time()
        try:
            response = self.client.messages.create(
                model=self.model, max_tokens=300,
                system=self._system_prompt(boss),
                messages=messages[-12:], timeout=60.0,
            )
        except Exception:
            return None
        text = "".join(
            b.text for b in response.content if getattr(b, "type", None) == "text"
        ).strip()
        if not text:
            return None
        goal_met = _GOAL_MARKER in text
        clean = text.replace(_GOAL_MARKER, "").strip()
        return {
            "response": clean,
            "goal_met": goal_met,
            "_meta": {
                "model": self.model,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "latency_ms": int((time.time() - start) * 1000),
            },
        }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_korean_oracle.py -v`
Expected: PASS (3 passed).

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/korean/personas.py backend/app/services/korean/oracle.py backend/tests/test_korean_oracle.py
git commit -m "feat(korean): KoreanOracle boss roleplay + personas"
```

### Task C3: Config additions (Korean model + voice)

**Files:**
- Modify: `backend/app/core/config.py`

- [ ] **Step 1: Add settings**

In `backend/app/core/config.py`, inside the `Settings` class (near `critique_model`), add:

```python
    # Korean course: cheap conversational model for the roleplay boss + a Korean TTS voice.
    korean_model: str = "claude-sonnet-4-6"
    minimax_korean_voice_id: str = "Korean_SweetGirl"  # override via env MINIMAX_KOREAN_VOICE_ID
```

> The exact MiniMax Korean voice id must be confirmed against the account's voice catalog before deploy; the default is a placeholder-safe string and is overridable by env. TTS failure degrades gracefully (Task C4), so a wrong id never blocks learning.

- [ ] **Step 2: Verify settings load**

Run: `cd backend && python -c "from app.core.config import get_settings; s=get_settings(); print(s.korean_model, s.minimax_korean_voice_id)"`
Expected: prints `claude-sonnet-4-6 Korean_SweetGirl`.

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/config.py
git commit -m "feat(korean): config for Korean roleplay model + TTS voice"
```

### Task C4: Korean routes

**Files:**
- Create: `backend/app/api/v1/routes/korean.py`
- Modify: `backend/app/api/v1/api.py`
- Test: `backend/tests/test_korean_routes.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_korean_routes.py`:

```python
from pathlib import Path
from tempfile import mkdtemp

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.services.seed_service import seed_database

DB = Path(mkdtemp(prefix="korean-routes-")) / "t.db"
engine = create_engine(f"sqlite:///{DB.as_posix()}", connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def _override():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


def setup_module():
    Base.metadata.create_all(bind=engine)
    db = TestSession(); seed_database(db); db.close()
    app.dependency_overrides[get_db] = _override


def teardown_module():
    app.dependency_overrides.clear(); engine.dispose()


client = TestClient(app)


def test_get_map():
    r = client.get("/api/v1/korean/map")
    assert r.status_code == 200
    data = r.json()
    assert data[0]["slug"] == "hangul-island"
    assert data[0]["nodes"][0]["status"] == "unlocked"


def test_get_node_returns_content():
    slug = client.get("/api/v1/korean/map").json()[0]["nodes"][0]["slug"]
    r = client.get(f"/api/v1/korean/nodes/{slug}")
    assert r.status_code == 200
    assert r.json()["kind"] == "reading"
    assert "content_json" in r.json()


def test_get_unknown_node_404():
    assert client.get("/api/v1/korean/nodes/does-not-exist").status_code == 404


def test_complete_then_reset():
    slug = client.get("/api/v1/korean/map").json()[0]["nodes"][0]["slug"]
    r = client.post(f"/api/v1/korean/nodes/{slug}/complete", json={"score": 1.0, "stars": 3})
    assert r.status_code == 200
    assert r.json()["status"] == "completed"
    assert client.get("/api/v1/korean/map").json()[0]["nodes"][1]["status"] == "unlocked"
    assert client.delete("/api/v1/korean/progress").status_code == 200
    assert client.get("/api/v1/korean/map").json()[0]["nodes"][0]["status"] == "unlocked"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_korean_routes.py -v`
Expected: FAIL — 404s on `/korean/map` (router not registered).

- [ ] **Step 3: Implement the routes**

Create `backend/app/api/v1/routes/korean.py`:

```python
"""Korean course endpoints: map, node fetch, completion, reset, TTS, boss roleplay (SSE)."""
from __future__ import annotations

import json
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.core.config import get_settings
from app.db.session import SessionLocal, get_db
from app.models import KoreanConversation, KoreanMessage, User
from app.services.ai_service import AIService
from app.services.korean import service as ksvc
from app.services.korean.oracle import KoreanOracle
from app.services.podcast_service import _tts_bytes

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/korean", tags=["korean"])


def get_user_id(db: Session) -> int:
    return db.scalar(select(User.id).limit(1))


class CompleteRequest(BaseModel):
    score: float = 1.0
    stars: int = 1


class TtsRequest(BaseModel):
    text: str


class BossTurn(BaseModel):
    message: str
    conversation_id: int | None = None


@router.get("/map")
def get_map(db: Session = Depends(get_db)):
    return ksvc.get_map(db, get_user_id(db))


@router.get("/nodes/{slug}")
def get_node(slug: str, db: Session = Depends(get_db)):
    node = ksvc.get_node(db, slug)
    if node is None:
        raise HTTPException(404, "Unknown node")
    return {
        "slug": node.slug, "kind": node.kind, "title": node.title,
        "order_index": node.order_index, "content_json": node.content_json or {},
    }


@router.post("/nodes/{slug}/complete")
def complete_node(slug: str, payload: CompleteRequest, db: Session = Depends(get_db)):
    try:
        return ksvc.complete_node(db, get_user_id(db), slug, payload.score, payload.stars)
    except ValueError:
        raise HTTPException(404, "Unknown node")


@router.delete("/progress")
def reset_progress(db: Session = Depends(get_db)):
    return ksvc.reset_progress(db, get_user_id(db))


@router.post("/tts")
def korean_tts(payload: TtsRequest):
    settings = get_settings()
    if not settings.minimax_api_key or not settings.minimax_group_id:
        raise HTTPException(503, "TTS not configured")
    text = (payload.text or "").strip()[:400]
    if not text:
        raise HTTPException(400, "Empty text")
    try:
        mp3 = _tts_bytes(
            text, settings.minimax_korean_voice_id, settings.minimax_api_key,
            settings.minimax_group_id, settings.minimax_model, settings.minimax_api_base,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("korean tts failed")
        raise HTTPException(502, "TTS upstream error") from exc
    return Response(content=mp3, media_type="audio/mpeg", headers={"Cache-Control": "public, max-age=86400"})


@router.post("/nodes/{slug}/boss")
def boss_turn(slug: str, payload: BossTurn, db: Session = Depends(get_db)):
    """One roleplay turn. Streams the assistant reply, then a done event with goal_met."""
    node = ksvc.get_node(db, slug)
    if node is None or node.kind != "boss":
        raise HTTPException(404, "Unknown boss node")
    user_id = get_user_id(db)
    boss = node.content_json or {}

    conv_id = payload.conversation_id
    if conv_id is None:
        conv = KoreanConversation(user_id=user_id, node_id=node.id)
        db.add(conv); db.commit(); db.refresh(conv); conv_id = conv.id
    db.add(KoreanMessage(conversation_id=conv_id, role="user", content=payload.message))
    db.commit()

    history = [
        {"role": m.role, "content": m.content}
        for m in db.scalars(
            select(KoreanMessage).where(KoreanMessage.conversation_id == conv_id).order_by(KoreanMessage.id.asc())
        ).all()
    ]

    svc = AIService(model=get_settings().korean_model)

    def event_stream():
        if not svc.is_available:
            # Graceful fallback: scripted reply so a flaky/absent API never traps a learner.
            fallback = "네, 알겠습니다."
            db2 = SessionLocal()
            try:
                db2.add(KoreanMessage(conversation_id=conv_id, role="assistant", content=fallback))
                db2.commit()
            finally:
                db2.close()
            yield {"data": json.dumps({"type": "text", "delta": fallback}, ensure_ascii=False)}
            yield {"data": json.dumps({"type": "done", "conversation_id": conv_id, "goal_met": False}, ensure_ascii=False)}
            return

        oracle = KoreanOracle(client=svc.client, model=svc.model)
        result = oracle.run(boss=boss, messages=history)
        if result is None:
            yield {"data": json.dumps({"type": "error"}, ensure_ascii=False)}
            return
        reply, goal_met = result["response"], result["goal_met"]
        db2 = SessionLocal()
        try:
            db2.add(KoreanMessage(conversation_id=conv_id, role="assistant", content=reply))
            db2.commit()
        finally:
            db2.close()
        yield {"data": json.dumps({"type": "text", "delta": reply}, ensure_ascii=False)}
        yield {"data": json.dumps({"type": "done", "conversation_id": conv_id, "goal_met": goal_met}, ensure_ascii=False)}

    return EventSourceResponse(event_stream())
```

- [ ] **Step 4: Register the router**

In `backend/app/api/v1/api.py`: add `korean` to the imports on line 5, and add `api_router.include_router(korean.router)` after the `qian` line.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_korean_routes.py -v`
Expected: PASS (4 passed).

- [ ] **Step 6: Run the full backend suite**

Run: `cd backend && python -m pytest -q`
Expected: all pass (existing + new Korean tests).

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/v1/routes/korean.py backend/app/api/v1/api.py backend/tests/test_korean_routes.py
git commit -m "feat(korean): map/node/complete/reset/tts/boss routes"
```

---

## PHASE D — Frontend

### Task D1: Types + API client

**Files:**
- Create: `frontend/src/lib/korean/types.ts`
- Create: `frontend/src/lib/korean/api.ts`

- [ ] **Step 1: Create types**

Create `frontend/src/lib/korean/types.ts`:

```typescript
export type NodeKind = "reading" | "scene" | "drill" | "boss";
export type NodeStatus = "locked" | "unlocked" | "completed";

export type MapNode = {
  slug: string;
  kind: NodeKind;
  title: string;
  order_index: number;
  status: NodeStatus;
  stars: number;
};

export type MapRegion = {
  slug: string;
  title: string;
  theme: string;
  order_index: number;
  nodes: MapNode[];
};

export type ReadingContent = {
  letters: { jamo: string; sound: string; audio_key: string }[];
  blocks: { ko: string; romaji: string }[];
  words: { ko: string; en: string }[];
};

export type SceneLine = { speaker: string; ko: string; romaji: string; en: string; audio_key: string };
export type SceneTurn = {
  prompt_en: string;
  options: string[];
  accepted: { ko: string; intents: string[] }[];
};
export type SceneContent = {
  setting: string;
  character: string;
  lines: SceneLine[];
  your_turns: SceneTurn[];
  new_vocab: { ko: string; en: string; romaji: string }[];
};

export type DrillItem =
  | { type: "match"; ko: string; answer: string; choices: string[] }
  | { type: "listen"; audio_key: string; answer: string; choices: string[] }
  | { type: "fill"; prompt: string; answer: string }
  | { type: "type"; prompt_en: string; answer: string };
export type DrillContent = { items: DrillItem[] };

export type BossContent = {
  goal_en: string;
  persona: string;
  level: string;
  allowed_vocab: string[];
  success_criteria: string;
  max_turns: number;
};

export type NodeDetail = {
  slug: string;
  kind: NodeKind;
  title: string;
  order_index: number;
  content_json: ReadingContent | SceneContent | DrillContent | BossContent;
};
```

- [ ] **Step 2: Create the API client**

Create `frontend/src/lib/korean/api.ts`:

```typescript
import { API_BASE } from "@/lib/api";
import type { MapRegion, NodeDetail } from "./types";

export class KoreanApiError extends Error {
  constructor(public status: number, detail?: string) {
    super(detail ?? `Request failed: ${status}`);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const err = (await res.json().catch(() => null)) as { detail?: unknown } | null;
    throw new KoreanApiError(res.status, typeof err?.detail === "string" ? err.detail : undefined);
  }
  return (await res.json()) as T;
}

export type BossStreamHandlers = {
  onText: (delta: string) => void;
  onDone: (conversationId: number, goalMet: boolean) => void;
  onError: () => void;
};

async function streamBoss(
  slug: string,
  body: { message: string; conversation_id?: number },
  handlers: BossStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_BASE}/korean/nodes/${slug}/boss`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
    signal,
  });
  if (!res.ok || !res.body) {
    handlers.onError();
    return;
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done || signal?.aborted) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data:")) continue;
      const raw = trimmed.slice(5).trim();
      if (!raw) continue;
      let ev: { type: string; delta?: string; conversation_id?: number; goal_met?: boolean };
      try {
        ev = JSON.parse(raw);
      } catch {
        continue;
      }
      if (ev.type === "text" && ev.delta) handlers.onText(ev.delta);
      else if (ev.type === "done") handlers.onDone(ev.conversation_id ?? 0, Boolean(ev.goal_met));
      else if (ev.type === "error") handlers.onError();
    }
  }
}

export const koreanApi = {
  getMap: () => request<MapRegion[]>("/korean/map"),
  getNode: (slug: string) => request<NodeDetail>(`/korean/nodes/${slug}`),
  completeNode: (slug: string, score: number, stars: number) =>
    request<{ slug: string; status: string; stars: number }>(
      `/korean/nodes/${slug}/complete`,
      { method: "POST", body: JSON.stringify({ score, stars }) },
    ),
  resetProgress: () => request<{ deleted_progress: number }>("/korean/progress", { method: "DELETE" }),
  ttsUrl: () => `${API_BASE}/korean/tts`,
  streamBoss,
};
```

- [ ] **Step 3: Verify it type-checks**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors in `lib/korean/*`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/korean/types.ts frontend/src/lib/korean/api.ts
git commit -m "feat(korean): frontend types + API client"
```

### Task D2: Speech (mic STT) + TTS hooks

**Files:**
- Create: `frontend/src/lib/korean/use-speech.ts`
- Create: `frontend/src/lib/korean/use-tts.ts`

- [ ] **Step 1: Create the speech hook**

Create `frontend/src/lib/korean/use-speech.ts`:

```typescript
"use client";
import { useCallback, useRef, useState } from "react";

type SpeechRecognitionLike = {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  start: () => void;
  stop: () => void;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
};

function getRecognition(): SpeechRecognitionLike | null {
  if (typeof window === "undefined") return null;
  const Ctor =
    (window as unknown as { SpeechRecognition?: new () => SpeechRecognitionLike }).SpeechRecognition ??
    (window as unknown as { webkitSpeechRecognition?: new () => SpeechRecognitionLike }).webkitSpeechRecognition;
  return Ctor ? new Ctor() : null;
}

/** Browser Web Speech API (ko-KR). `supported` is false on Safari/Firefox — callers hide the mic. */
export function useSpeech() {
  const [supported] = useState<boolean>(() => getRecognition() !== null);
  const [listening, setListening] = useState(false);
  const recRef = useRef<SpeechRecognitionLike | null>(null);

  const listen = useCallback((): Promise<string> => {
    return new Promise((resolve) => {
      const rec = getRecognition();
      if (!rec) {
        resolve("");
        return;
      }
      recRef.current = rec;
      rec.lang = "ko-KR";
      rec.interimResults = false;
      rec.maxAlternatives = 1;
      let result = "";
      rec.onresult = (e) => {
        result = e.results?.[0]?.[0]?.transcript ?? "";
      };
      rec.onerror = () => {
        setListening(false);
        resolve("");
      };
      rec.onend = () => {
        setListening(false);
        resolve(result);
      };
      setListening(true);
      rec.start();
    });
  }, []);

  const stop = useCallback(() => recRef.current?.stop(), []);

  return { supported, listening, listen, stop };
}

/** Normalize + fuzzy-compare for scene-line "judges meaning" check (no AI call). */
export function matchesIntent(transcript: string, accepted: { ko: string }[]): boolean {
  const norm = (s: string) => s.replace(/\s+/g, "").replace(/[.,!?]/g, "");
  const t = norm(transcript);
  if (!t) return false;
  return accepted.some((a) => {
    const target = norm(a.ko);
    return t.includes(target) || target.includes(t);
  });
}
```

- [ ] **Step 2: Create the TTS hook**

Create `frontend/src/lib/korean/use-tts.ts`:

```typescript
"use client";
import { useCallback, useRef } from "react";
import { koreanApi } from "./api";

/** Fetches Korean TTS audio, caches blob URLs by text, plays it. Silent no-op on failure
 * (TTS is an enhancement, never a gate). */
export function useTts() {
  const cache = useRef<Map<string, string>>(new Map());

  const speak = useCallback(async (text: string) => {
    if (!text) return;
    try {
      let url = cache.current.get(text);
      if (!url) {
        const res = await fetch(koreanApi.ttsUrl(), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
        });
        if (!res.ok) return;
        const blob = await res.blob();
        url = URL.createObjectURL(blob);
        cache.current.set(text, url);
      }
      await new Audio(url).play();
    } catch {
      // swallow — audio is optional
    }
  }, []);

  return { speak };
}
```

- [ ] **Step 3: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/korean/use-speech.ts frontend/src/lib/korean/use-tts.ts
git commit -m "feat(korean): mic STT + TTS hooks with graceful fallback"
```

### Task D3: Journey map page + reset

**Files:**
- Create: `frontend/src/app/korean/page.tsx`
- Create: `frontend/src/components/korean/journey-map.tsx`

- [ ] **Step 1: Create the map component**

Create `frontend/src/components/korean/journey-map.tsx`:

```tsx
"use client";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { koreanApi } from "@/lib/korean/api";
import type { MapNode } from "@/lib/korean/types";

const KIND_ICON: Record<string, string> = { reading: "🔤", scene: "💬", drill: "✍️", boss: "🎯" };

function NodeChip({ node }: { node: MapNode }) {
  const locked = node.status === "locked";
  const body = (
    <div
      className={`rounded-xl border p-3 transition ${
        locked
          ? "border-white/10 bg-white/5 opacity-50"
          : node.status === "completed"
            ? "border-emerald-400/60 bg-emerald-400/10"
            : "border-violet-400/60 bg-violet-400/10 hover:bg-violet-400/20"
      }`}
    >
      <div className="text-xl">{locked ? "🔒" : KIND_ICON[node.kind]}</div>
      <div className="mt-1 text-sm font-medium">{node.title}</div>
      <div className="text-xs opacity-60">{"★".repeat(node.stars) || "—"}</div>
    </div>
  );
  return locked ? body : <Link href={`/korean/node/${node.slug}`}>{body}</Link>;
}

export function JourneyMap() {
  const qc = useQueryClient();
  const { data: regions, isLoading } = useQuery({ queryKey: ["korean-map"], queryFn: koreanApi.getMap });
  const reset = useMutation({
    mutationFn: koreanApi.resetProgress,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["korean-map"] }),
  });

  if (isLoading) return <div className="p-8 opacity-60">Loading…</div>;

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">한국어 — Journey</h1>
        <button
          className="rounded-lg border border-white/15 px-3 py-1.5 text-sm opacity-80 hover:bg-white/10"
          onClick={() => {
            if (confirm("Reset all Korean progress? This cannot be undone.")) reset.mutate();
          }}
        >
          Reset progress
        </button>
      </div>
      <div className="space-y-8">
        {regions?.map((r) => (
          <section key={r.slug}>
            <h2 className="mb-3 text-lg font-medium opacity-90">{r.title}</h2>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {r.nodes.map((n) => (
                <NodeChip key={n.slug} node={n} />
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create the page**

Create `frontend/src/app/korean/page.tsx`:

```tsx
import { JourneyMap } from "@/components/korean/journey-map";

export default function KoreanPage() {
  return <JourneyMap />;
}
```

- [ ] **Step 3: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/korean/page.tsx frontend/src/components/korean/journey-map.tsx
git commit -m "feat(korean): journey map page + reset control"
```

### Task D4: Node player + romanization toggle

**Files:**
- Create: `frontend/src/components/korean/romanization-toggle.tsx`
- Create: `frontend/src/components/korean/node-player.tsx`
- Create: `frontend/src/app/korean/node/[nodeSlug]/page.tsx`

- [ ] **Step 1: Romanization toggle (localStorage-backed context-free hook)**

Create `frontend/src/components/korean/romanization-toggle.tsx`:

```tsx
"use client";
import { useEffect, useState } from "react";

const KEY = "korean.romaji";

export function useRomaji(): [boolean, (v: boolean) => void] {
  const [on, setOn] = useState(true);
  useEffect(() => {
    const saved = localStorage.getItem(KEY);
    if (saved !== null) setOn(saved === "1");
  }, []);
  const set = (v: boolean) => {
    setOn(v);
    localStorage.setItem(KEY, v ? "1" : "0");
  };
  return [on, set];
}

export function RomanizationToggle({ on, onChange }: { on: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center gap-2 text-xs opacity-70">
      <input type="checkbox" checked={on} onChange={(e) => onChange(e.target.checked)} />
      Show romanization
    </label>
  );
}
```

- [ ] **Step 2: Node player dispatcher (renders by kind; per-kind sub-components in D5)**

Create `frontend/src/components/korean/node-player.tsx`:

```tsx
"use client";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { koreanApi } from "@/lib/korean/api";
import type {
  BossContent,
  DrillContent,
  NodeDetail,
  ReadingContent,
  SceneContent,
} from "@/lib/korean/types";
import { ReadingNode } from "./reading-node";
import { SceneNode } from "./scene-node";
import { DrillNode } from "./drill-node";
import { BossNode } from "./boss-node";

export function NodePlayer({ slug }: { slug: string }) {
  const router = useRouter();
  const qc = useQueryClient();
  const { data: node, isLoading } = useQuery<NodeDetail>({
    queryKey: ["korean-node", slug],
    queryFn: () => koreanApi.getNode(slug),
  });
  const complete = useMutation({
    mutationFn: (stars: number) => koreanApi.completeNode(slug, 1.0, stars),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["korean-map"] });
      router.push("/korean");
    },
  });

  if (isLoading || !node) return <div className="p-8 opacity-60">Loading…</div>;

  const onDone = (stars: number) => complete.mutate(stars);

  return (
    <div className="mx-auto max-w-2xl p-6">
      <button className="mb-4 text-sm opacity-60 hover:opacity-100" onClick={() => router.push("/korean")}>
        ← Map
      </button>
      <h1 className="mb-4 text-xl font-semibold">{node.title}</h1>
      {node.kind === "reading" && <ReadingNode content={node.content_json as ReadingContent} onDone={onDone} />}
      {node.kind === "scene" && <SceneNode content={node.content_json as SceneContent} onDone={onDone} />}
      {node.kind === "drill" && <DrillNode content={node.content_json as DrillContent} onDone={onDone} />}
      {node.kind === "boss" && <BossNode slug={slug} content={node.content_json as BossContent} onDone={onDone} />}
    </div>
  );
}
```

- [ ] **Step 3: Create the route page**

Create `frontend/src/app/korean/node/[nodeSlug]/page.tsx`:

```tsx
import { NodePlayer } from "@/components/korean/node-player";

export default async function KoreanNodePage({
  params,
}: {
  params: Promise<{ nodeSlug: string }>;
}) {
  const { nodeSlug } = await params;
  return <NodePlayer slug={nodeSlug} />;
}
```

> Note: Next.js 15 passes `params` as a Promise in async server components — matches the existing `courses/[courseSlug]` and `learn/lesson/[lessonSlug]` routes.

- [ ] **Step 4: Commit (will not type-check until D5 adds the four sub-components — commit together after D5).**

Proceed directly to D5; commit at the end of D5.

### Task D5: The four node sub-components

**Files:**
- Create: `frontend/src/components/korean/reading-node.tsx`
- Create: `frontend/src/components/korean/scene-node.tsx`
- Create: `frontend/src/components/korean/drill-node.tsx`
- Create: `frontend/src/components/korean/boss-node.tsx`

- [ ] **Step 1: Reading node**

Create `frontend/src/components/korean/reading-node.tsx`:

```tsx
"use client";
import { useTts } from "@/lib/korean/use-tts";
import type { ReadingContent } from "@/lib/korean/types";

export function ReadingNode({ content, onDone }: { content: ReadingContent; onDone: (stars: number) => void }) {
  const { speak } = useTts();
  return (
    <div className="space-y-6">
      <section>
        <h3 className="mb-2 text-sm uppercase opacity-60">Letters — tap to hear</h3>
        <div className="flex flex-wrap gap-2">
          {content.letters.map((l) => (
            <button
              key={l.jamo}
              onClick={() => speak(l.jamo)}
              className="rounded-lg border border-white/15 px-4 py-3 text-2xl hover:bg-white/10"
            >
              {l.jamo}
              <span className="ml-1 text-xs opacity-50">{l.sound}</span>
            </button>
          ))}
        </div>
      </section>
      <section>
        <h3 className="mb-2 text-sm uppercase opacity-60">Read these words</h3>
        <div className="flex flex-wrap gap-3">
          {content.words.map((w) => (
            <button key={w.ko} onClick={() => speak(w.ko)} className="rounded-lg bg-white/5 px-4 py-2 hover:bg-white/10">
              <span className="text-lg">{w.ko}</span>
              <span className="ml-2 text-xs opacity-60">{w.en}</span>
            </button>
          ))}
        </div>
      </section>
      <button onClick={() => onDone(3)} className="rounded-lg bg-emerald-500/80 px-5 py-2 font-medium hover:bg-emerald-500">
        I can read these ✓
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Scene node (tap or mic, romanization toggle, TTS)**

Create `frontend/src/components/korean/scene-node.tsx`:

```tsx
"use client";
import { useState } from "react";
import { useTts } from "@/lib/korean/use-tts";
import { useSpeech, matchesIntent } from "@/lib/korean/use-speech";
import { useRomaji, RomanizationToggle } from "./romanization-toggle";
import type { SceneContent } from "@/lib/korean/types";

export function SceneNode({ content, onDone }: { content: SceneContent; onDone: (stars: number) => void }) {
  const { speak } = useTts();
  const { supported, listening, listen } = useSpeech();
  const [romaji, setRomaji] = useState(true);
  const [romajiHook, setRomajiHook] = useRomaji();
  const [turnIdx, setTurnIdx] = useState(0);
  const [feedback, setFeedback] = useState<string>("");

  const showRomaji = romajiHook ?? romaji;
  const turn = content.your_turns[turnIdx];
  const done = turnIdx >= content.your_turns.length;

  const advance = () => {
    setFeedback("");
    if (turnIdx + 1 >= content.your_turns.length) {
      setTurnIdx(content.your_turns.length);
    } else {
      setTurnIdx(turnIdx + 1);
    }
  };

  const tryAnswer = (text: string) => {
    if (matchesIntent(text, turn.accepted) || turn.options.includes(text)) {
      setFeedback("좋아요! ✓");
      setTimeout(advance, 600);
    } else {
      setFeedback("Not quite — try again or tap an option.");
    }
  };

  const onMic = async () => {
    const heard = await listen();
    if (heard) tryAnswer(heard);
  };

  return (
    <div className="space-y-5">
      <RomanizationToggle on={showRomaji} onChange={(v) => { setRomaji(v); setRomajiHook(v); }} />
      <div className="space-y-3">
        {content.lines.map((line, i) => (
          <div key={i} className="rounded-xl bg-white/5 p-3">
            <div className="text-xs opacity-50">{line.speaker}</div>
            <div className="flex items-center gap-2">
              <span className="text-lg">{line.ko}</span>
              <button onClick={() => speak(line.ko)} className="text-sm opacity-60 hover:opacity-100">🔊</button>
            </div>
            {showRomaji && <div className="text-xs italic opacity-50">{line.romaji} — {line.en}</div>}
          </div>
        ))}
      </div>

      {!done ? (
        <div className="space-y-3 rounded-xl border border-violet-400/40 p-4">
          <div className="text-xs uppercase opacity-60">Your line — {turn.prompt_en}</div>
          <div className="flex flex-wrap gap-2">
            {turn.options.map((o) => (
              <button key={o} onClick={() => tryAnswer(o)} className="rounded-lg bg-violet-400/20 px-4 py-2 hover:bg-violet-400/30">
                {o}
              </button>
            ))}
          </div>
          {supported && (
            <button
              onClick={onMic}
              className={`rounded-lg px-4 py-2 ${listening ? "bg-amber-500/40" : "bg-amber-500/20 hover:bg-amber-500/30"}`}
            >
              🎤 {listening ? "Listening…" : "Say it"}
            </button>
          )}
          {feedback && <div className="text-sm opacity-80">{feedback}</div>}
        </div>
      ) : (
        <button onClick={() => onDone(3)} className="rounded-lg bg-emerald-500/80 px-5 py-2 font-medium hover:bg-emerald-500">
          Scene complete ✓
        </button>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Drill node**

Create `frontend/src/components/korean/drill-node.tsx`:

```tsx
"use client";
import { useState } from "react";
import { useTts } from "@/lib/korean/use-tts";
import type { DrillContent, DrillItem } from "@/lib/korean/types";

function choicesFor(item: DrillItem): string[] {
  if (item.type === "match" || item.type === "listen") return item.choices;
  return [];
}
function answerFor(item: DrillItem): string {
  return item.answer;
}

export function DrillNode({ content, onDone }: { content: DrillContent; onDone: (stars: number) => void }) {
  const { speak } = useTts();
  const [idx, setIdx] = useState(0);
  const [typed, setTyped] = useState("");
  const [wrong, setWrong] = useState(0);
  const item = content.items[idx];
  const finished = idx >= content.items.length;

  const submit = (value: string) => {
    if (value.replace(/\s+/g, "") === answerFor(item).replace(/\s+/g, "")) {
      setTyped("");
      setIdx(idx + 1);
    } else {
      setWrong(wrong + 1);
    }
  };

  if (finished) {
    const stars = wrong === 0 ? 3 : wrong <= 2 ? 2 : 1;
    return (
      <button onClick={() => onDone(stars)} className="rounded-lg bg-emerald-500/80 px-5 py-2 font-medium hover:bg-emerald-500">
        Drill complete — {"★".repeat(stars)} ✓
      </button>
    );
  }

  return (
    <div className="space-y-4 rounded-xl border border-sky-400/40 p-4">
      <div className="text-xs uppercase opacity-60">
        {idx + 1} / {content.items.length}
      </div>
      {item.type === "match" && <div className="text-2xl">{item.ko}</div>}
      {item.type === "listen" && (
        <button onClick={() => speak(item.answer)} className="rounded-lg bg-white/10 px-4 py-2">🔊 Listen</button>
      )}
      {item.type === "fill" && <div className="text-lg">{item.prompt}</div>}
      {item.type === "type" && <div className="text-lg">{item.prompt_en}</div>}

      {choicesFor(item).length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {choicesFor(item).map((c) => (
            <button key={c} onClick={() => submit(c)} className="rounded-lg bg-sky-400/20 px-4 py-2 hover:bg-sky-400/30">
              {c}
            </button>
          ))}
        </div>
      ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            submit(typed);
          }}
          className="flex gap-2"
        >
          <input
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            className="flex-1 rounded-lg border border-white/15 bg-transparent px-3 py-2"
            placeholder="Type 한글…"
          />
          <button className="rounded-lg bg-sky-400/30 px-4 py-2">Check</button>
        </form>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Boss node (SSE roleplay)**

Create `frontend/src/components/korean/boss-node.tsx`:

```tsx
"use client";
import { useRef, useState } from "react";
import { koreanApi } from "@/lib/korean/api";
import { useSpeech } from "@/lib/korean/use-speech";
import { useTts } from "@/lib/korean/use-tts";
import type { BossContent } from "@/lib/korean/types";

type Msg = { role: "user" | "assistant"; content: string };

export function BossNode({
  slug,
  content,
  onDone,
}: {
  slug: string;
  content: BossContent;
  onDone: (stars: number) => void;
}) {
  const { speak } = useTts();
  const { supported, listening, listen } = useSpeech();
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [won, setWon] = useState(false);
  const convId = useRef<number | undefined>(undefined);

  const send = async (text: string) => {
    if (!text || busy) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    setBusy(true);
    let reply = "";
    await koreanApi.streamBoss(
      slug,
      { message: text, conversation_id: convId.current },
      {
        onText: (delta) => {
          reply += delta;
        },
        onDone: (cid, goalMet) => {
          convId.current = cid;
          if (reply) {
            setMessages((m) => [...m, { role: "assistant", content: reply }]);
            speak(reply);
          }
          if (goalMet) setWon(true);
          setBusy(false);
        },
        onError: () => {
          setMessages((m) => [...m, { role: "assistant", content: "(연결 오류 — 다시 시도하세요)" }]);
          setBusy(false);
        },
      },
    );
  };

  const onMic = async () => {
    const heard = await listen();
    if (heard) send(heard);
  };

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-emerald-400/40 bg-emerald-400/5 p-3 text-sm">
        🎯 Goal: {content.goal_en}
      </div>
      <div className="min-h-[180px] space-y-2 rounded-xl bg-white/5 p-3">
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
            <span
              className={`inline-block rounded-xl px-3 py-1.5 text-sm ${
                m.role === "user" ? "bg-emerald-400/20" : "bg-white/10"
              }`}
            >
              {m.content}
            </span>
          </div>
        ))}
        {busy && <div className="text-xs opacity-50">…</div>}
      </div>

      {won ? (
        <button onClick={() => onDone(3)} className="rounded-lg bg-emerald-500/80 px-5 py-2 font-medium hover:bg-emerald-500">
          Goal cleared — claim ★★★
        </button>
      ) : (
        <div className="flex gap-2">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
            className="flex flex-1 gap-2"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={busy}
              className="flex-1 rounded-lg border border-white/15 bg-transparent px-3 py-2"
              placeholder="한국어로 말해보세요…"
            />
            <button disabled={busy} className="rounded-lg bg-emerald-400/30 px-4 py-2">
              Send
            </button>
          </form>
          {supported && (
            <button
              onClick={onMic}
              disabled={busy}
              className={`rounded-lg px-4 py-2 ${listening ? "bg-amber-500/40" : "bg-amber-500/20 hover:bg-amber-500/30"}`}
            >
              🎤
            </button>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Type-check the whole frontend**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors. (If `useRomaji` returns a possibly-undefined value flagged by TS, the `showRomaji = romajiHook ?? romaji` in scene-node already guards it.)

- [ ] **Step 6: Lint**

Run: `cd frontend && npm run lint`
Expected: no errors in `components/korean/*` or `lib/korean/*`.

- [ ] **Step 7: Commit (D4 + D5 together)**

```bash
git add frontend/src/app/korean frontend/src/components/korean
git commit -m "feat(korean): node player + reading/scene/drill/boss components"
```

### Task D6: Add 한국어 tile to the home hub

**Files:**
- Modify: `frontend/src/components/home/folding-screen-hub.tsx`

- [ ] **Step 1: Read the existing tile pattern**

Read `frontend/src/components/home/folding-screen-hub.tsx` and locate the array/list of module tiles (e.g. entries linking to `/ziwei`, `/qian`, `/learn`). Note the exact shape (label, href, icon/emoji, description fields).

- [ ] **Step 2: Add a Korean tile**

Add an entry following that exact shape, e.g.:

```tsx
{ label: "한국어", href: "/korean", icon: "🇰🇷", description: "Learn Korean — travel & live" }
```

Match the surrounding entries' field names and placement (likely under the 学 / learn grouping).

- [ ] **Step 3: Verify in the browser**

Run the verification workflow (preview_start, navigate to `/`, snapshot) to confirm the tile renders and links to `/korean`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/home/folding-screen-hub.tsx
git commit -m "feat(korean): add 한국어 tile to home hub"
```

---

## PHASE E — Integration, verification & deploy

### Task E1: End-to-end browser verification

**Files:** none (verification only)

- [ ] **Step 1: Start backend + frontend**

Use the project's dev setup (`run` skill or existing dev scripts). Ensure backend is on `:8000` and frontend on `:3000`.

- [ ] **Step 2: Verify the map**

Navigate to `/korean`. Confirm: 3 regions render; first node `unlocked`, rest `locked`; "Reset progress" button present.

- [ ] **Step 3: Verify reading node**

Open the first reading node. Tap a letter and a word — TTS plays (or fails silently if MiniMax not configured locally — check `preview_console_logs` for a clean failure, not a crash). Click "I can read these" → returns to map → next node now `unlocked`.

- [ ] **Step 4: Verify scene + drill**

Open a scene node: NPC lines render with 🔊 and romanization toggle works; tapping the correct option advances; completing returns to map. Open the following drill: items advance on correct answers; finishing awards stars.

- [ ] **Step 5: Verify boss (if Claude key present locally)**

Open a boss node; send a Korean message; confirm an assistant reply streams in. If no key, confirm the scripted fallback reply appears (never a crash).

- [ ] **Step 6: Verify reset**

Click "Reset progress", confirm; map returns to only the first node unlocked.

- [ ] **Step 7: Capture proof**

`preview_screenshot` the map and one node player; note results.

### Task E2: Review-integration sanity + full suite

**Files:** none (verification only) — confirms Korean `MemoryCard`s flow into existing review.

- [ ] **Step 1: Confirm cards seed on scene completion**

After completing a scene node locally, query the DB (or hit the existing memory/review endpoint) and confirm `MemoryCard` rows with `category="korean"` exist. The existing review flow (`/review`) surfaces cards by due date irrespective of category, so no review-side code change is required.

- [ ] **Step 2: Run the full backend test suite**

Run: `cd backend && python -m pytest -q`
Expected: all pass.

- [ ] **Step 3: Frontend build**

Run: `cd frontend && npm run build`
Expected: build succeeds (per `deploy_discipline`, a failing *local* build is not a deploy blocker, but a clean build here is the goal; if it fails for environmental reasons, note it and rely on CI).

### Task E3: Deploy via GitHub Actions (STRICT — never SSH/build on VPS)

**Files:** none

- [ ] **Step 1: Push to main**

```bash
git checkout main
git merge --no-ff claude/keen-wing-8fab30
git push origin main
```

- [ ] **Step 2: Tag a release**

```bash
git tag v0.54.0
git push origin v0.54.0
```

- [ ] **Step 3: Watch the pipeline**

Run: `gh run watch` (or `gh run list --limit 1`).
Expected: workflow builds images in CI, pushes to GHCR, SSHes into the VPS to pull & restart. A change is done only when the pipeline is green.

- [ ] **Step 4: Smoke-test prod**

Hit the prod `/korean` route and `/api/v1/korean/map`. Confirm the map loads. Confirm a Korean TTS line plays (validates `MINIMAX_KOREAN_VOICE_ID` is set correctly in prod env — fix the env var and redeploy if not).

---

## Self-review notes (verification of this plan against the spec)

- **Spec §2 experience model (map + scene + boss):** Tasks B2 (content), D3 (map), D5 (scene/boss) — covered.
- **Spec §2 node loop (reading/scene/drill/boss):** B1 validator + D5 four components — covered.
- **Spec §2 romanization toggle:** D4 `romanization-toggle.tsx`, used in D5 scene — covered.
- **Spec §3 TTS (MiniMax, cached):** C4 `/korean/tts` + D2 `use-tts` (blob cache) — covered.
- **Spec §3 STT (browser, graceful fallback):** D2 `use-speech` (`supported` gate) — covered.
- **Spec §3 scene fuzzy-match (no AI):** D2 `matchesIntent` — covered.
- **Spec §3 boss (Claude, level/vocab-constrained, SSE):** C2 oracle + C4 boss route + D5 boss — covered.
- **Spec §3 cost posture (Claude only on boss):** only the boss route calls `AIService` — covered.
- **Spec §4 architecture / content-state split:** A1 models, B seed, C1 service — covered.
- **Spec §5 v1 content regions 0–2:** B2 + B3 (node counts asserted: 5/7/7) — covered.
- **Spec §6 reset + user scoping:** C1 `reset_progress` (user-scoped), C4 `DELETE /progress`, D3 button — covered.
- **Spec §7 error handling (mic/TTS/Claude/STT all degrade):** D2 silent TTS, `supported` gate, C4 scripted fallback + `error` event — covered.
- **Spec §8 testing:** A1, B1–B3, C1–C2, C4 tests; E1 browser verification — covered.
- **Spec §9 build order:** Phases A→E follow it — covered.
- **Type consistency check:** `NodeKind`/`NodeStatus`/`MapNode`/`NodeDetail` defined in D1 and consumed unchanged in D3–D5; `streamBoss`/`completeNode`/`getMap`/`resetProgress` names match between `api.ts` (D1) and callers (D3–D5); backend `get_map`/`get_node`/`complete_node`/`reset_progress` names match between `service.py` (C1) and `korean.py` (C4). Consistent.
- **Out-of-scope (pronunciation scoring, Whisper, regions 3–9, real auth):** correctly absent.

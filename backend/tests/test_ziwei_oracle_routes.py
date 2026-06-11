"""Tests for the ziwei oracle endpoint (conversation persistence + budget guard).

AIService mocking: we monkeypatch ``app.api.v1.routes.ziwei.AIService`` so ``AIService()``
returns a fake with ``is_available=True``, ``model="test-model"`` and a fake Anthropic
client. The *real* ``ZiweiOracle`` runs against that fake client, which returns a canned
``end_turn`` response (one text block + usage), so persistence/budget logic is exercised end-to-end.

AIFeedback/SQLite: ``AIFeedback.response_json`` is a JSONB column which SQLite cannot compile
via ``Base.metadata``. The route both reads (budget sum) and writes AIFeedback rows, so the
table must exist. We create it via raw DDL with TEXT columns (SQLite-compatible) instead of
``AIFeedback.__table__.create``. JSON-mapped tables (User/ZiweiProfile/ZiweiConversation/
ZiweiMessage) are created normally per-table.
"""
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

import app.api.v1.routes.ziwei as ziwei_routes
from app.db.session import get_db
from app.main import app
from app.models.entities import (
    User,
    ZiweiConversation,
    ZiweiMessage,
    ZiweiProfile,
)

TEST_DB_DIR = Path(mkdtemp(prefix="ai-engineer-ziwei-oracle-tests-"))
TEST_DB_PATH = TEST_DB_DIR / "test_ziwei_oracle.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH.as_posix()}"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

# What the model emits (with inline camera marker) vs. the clean prose the parser returns.
from app.services.ziwei.oracle_tools import parse_markers as _parse_markers

CANNED_RAW = "命宫紫微，主尊贵。[[focus:命宫]] 福泽深厚。"
CANNED_TEXT = _parse_markers(CANNED_RAW)[0]  # markers stripped from response/persisted prose


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---- canned Anthropic response -------------------------------------------------
class _FakeMessages:
    def create(self, *args, **kwargs):
        return SimpleNamespace(
            stop_reason="end_turn",
            content=[SimpleNamespace(type="text", text=CANNED_RAW)],
            usage=SimpleNamespace(input_tokens=120, output_tokens=80),
        )


class _FakeClient:
    def __init__(self):
        self.messages = _FakeMessages()


class _FakeAIService:
    """Stand-in for AIService injected at the route module path."""

    is_available = True
    model = "test-model"

    def __init__(self, *args, **kwargs):
        self.client = _FakeClient()


# ---- chart fixture (copied from test_ziwei_patterns_batch1._mk) ------------------
def _mk(palaces_spec, ming="子", shen="午"):
    order = ["命宫", "兄弟", "夫妻", "子女", "财帛", "疾厄", "迁移", "交友", "官禄", "田宅", "福德", "父母"]
    branches = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    start = branches.index(ming)
    rot = branches[start:] + branches[:start]
    palaces = []
    for i, name in enumerate(order):
        br = rot[i]
        majors, minors = palaces_spec.get(br, ([], []))
        palaces.append({
            "name": name, "earthlyBranch": br, "heavenlyStem": "甲",
            "majorStars": [{"name": n, "type": "major", "mutagen": m, "brightness": b} for (n, m, b) in majors],
            "minorStars": [{"name": n, "type": "soft"} for n in minors],
            "adjectiveStars": [], "isBodyPalace": False, "isOriginalPalace": False,
            "changsheng12": "长生", "decadal": {"range": [1, 10], "heavenlyStem": "甲", "earthlyBranch": br}, "ages": [],
        })
    return {"earthlyBranchOfSoulPalace": ming, "earthlyBranchOfBodyPalace": shen, "palaces": palaces}


def _valid_chart():
    return _mk({"子": ([("紫微", "", "庙")], [])})


def setup_module():
    # JSON-mapped tables compile under SQLite; create each individually.
    User.__table__.create(bind=engine, checkfirst=True)
    ZiweiProfile.__table__.create(bind=engine, checkfirst=True)
    ZiweiConversation.__table__.create(bind=engine, checkfirst=True)
    ZiweiMessage.__table__.create(bind=engine, checkfirst=True)
    # AIFeedback.response_json is JSONB which SQLite cannot compile via metadata;
    # create a SQLite-compatible table via raw DDL (TEXT in place of JSONB/timestamps).
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS ai_feedback ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "user_id INTEGER NOT NULL, "
            "feature VARCHAR(30) NOT NULL, "
            "reference_id INTEGER NOT NULL, "
            "user_input_hash TEXT NOT NULL, "
            "prompt_template TEXT, "
            "response_json TEXT, "
            "model VARCHAR(100), "
            "input_tokens INTEGER, "
            "output_tokens INTEGER, "
            "latency_ms INTEGER, "
            "created_at TIMESTAMP"
            ")"
        ))
    app.dependency_overrides[get_db] = override_get_db


def teardown_module():
    app.dependency_overrides.clear()
    engine.dispose()
    if TEST_DB_DIR.exists():
        rmtree(TEST_DB_DIR, ignore_errors=True)


client = TestClient(app)


@pytest.fixture(autouse=True)
def _patch_ai_service(monkeypatch):
    monkeypatch.setattr(ziwei_routes, "AIService", _FakeAIService)


@pytest.fixture(autouse=True)
def _clean_db():
    """Reset all tables before each test for isolation."""
    with engine.begin() as conn:
        for tbl in ("ai_feedback", "ziwei_messages", "ziwei_conversations", "ziwei_profiles", "users"):
            conn.execute(text(f"DELETE FROM {tbl}"))
    yield


def _seed_profile(chart=None, persona="sage"):
    db = TestingSessionLocal()
    try:
        db.add(User(id=1, name="Tester", email="t@example.com", target_role="x"))
        profile = ZiweiProfile(
            name="命主", relation="self", gender="male",
            birth_date="1990-01-01", birth_time_index=0,
            chart_json=_valid_chart() if chart is None else chart, persona=persona,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile.id
    finally:
        db.close()


def test_ask_oracle_creates_conversation_and_persists():
    pid = _seed_profile()
    r = client.post(f"/api/v1/ziwei/profiles/{pid}/oracle", json={"scenario": "natal", "message": "事业如何？"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "conversation_id" in body
    assert body["response"] == CANNED_TEXT
    assert isinstance(body["camera_commands"], list)
    # inline marker parsed into a focus_palace camera command
    assert any(c["type"] == "focus_palace" for c in body["camera_commands"])
    assert isinstance(body["meta"], dict)
    # segments: the marker splits prose into segments; the first carries the focus command
    assert isinstance(body["segments"], list)
    assert len(body["segments"]) >= 1
    assert body["segments"][0]["commands"][0]["type"] == "focus_palace"
    conv_id = body["conversation_id"]

    rc = client.get(f"/api/v1/ziwei/profiles/{pid}/conversations")
    assert rc.status_code == 200
    convs = rc.json()
    assert len(convs) == 1
    assert convs[0]["id"] == conv_id

    rm = client.get(f"/api/v1/ziwei/conversations/{conv_id}/messages")
    assert rm.status_code == 200
    msgs = rm.json()
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"
    assert msgs[1]["content"] == CANNED_TEXT
    # segments persisted in chart_context_json of assistant message
    ctx = msgs[1]["chart_context_json"]
    assert "segments" in ctx
    assert isinstance(ctx["segments"], list)
    assert len(ctx["segments"]) >= 1
    assert ctx["segments"][0]["commands"][0]["type"] == "focus_palace"


def test_ask_oracle_404_unknown_profile():
    r = client.post("/api/v1/ziwei/profiles/999999/oracle", json={"scenario": "natal", "message": "x"})
    assert r.status_code == 404


def test_ask_oracle_400_no_chart():
    pid = _seed_profile(chart={})
    r = client.post(f"/api/v1/ziwei/profiles/{pid}/oracle", json={"scenario": "natal", "message": "x"})
    assert r.status_code == 400


def test_ask_oracle_continues_conversation():
    pid = _seed_profile()
    r1 = client.post(f"/api/v1/ziwei/profiles/{pid}/oracle", json={"scenario": "natal", "message": "事业如何？"})
    assert r1.status_code == 200
    conv_id = r1.json()["conversation_id"]

    r2 = client.post(
        f"/api/v1/ziwei/profiles/{pid}/oracle",
        json={"scenario": "natal", "message": "感情呢？", "conversation_id": conv_id},
    )
    assert r2.status_code == 200
    assert r2.json()["conversation_id"] == conv_id

    rm = client.get(f"/api/v1/ziwei/conversations/{conv_id}/messages")
    assert len(rm.json()) == 4


def test_budget_exceeded_429():
    from app.core.config import get_settings
    pid = _seed_profile()
    budget = get_settings().ai_daily_token_budget
    # Pre-insert AIFeedback rows summing tokens >= today's budget.
    db = TestingSessionLocal()
    try:
        db.execute(text(
            "INSERT INTO ai_feedback (user_id, feature, reference_id, user_input_hash, "
            "input_tokens, output_tokens, created_at) "
            "VALUES (1, 'ziwei_oracle', :ref, '', :inp, :out, CURRENT_TIMESTAMP)"
        ), {"ref": pid, "inp": budget, "out": 1})
        db.commit()
    finally:
        db.close()
    r = client.post(f"/api/v1/ziwei/profiles/{pid}/oracle", json={"scenario": "natal", "message": "x"})
    assert r.status_code == 429


def test_ask_oracle_rejects_cross_profile_conversation():
    """POSTing with a conversation_id that belongs to a different profile must return 404."""
    pid_a = _seed_profile()
    # Create a second profile (profile B) with a valid chart.
    db = TestingSessionLocal()
    try:
        profile_b = ZiweiProfile(
            name="乙命主", relation="friend", gender="female",
            birth_date="1992-03-15", birth_time_index=2,
            chart_json=_valid_chart(), persona="sage",
        )
        db.add(profile_b)
        db.commit()
        db.refresh(profile_b)
        pid_b = profile_b.id
    finally:
        db.close()

    # Create a conversation under profile A via a normal oracle call.
    r1 = client.post(f"/api/v1/ziwei/profiles/{pid_a}/oracle", json={"scenario": "natal", "message": "命运如何？"})
    assert r1.status_code == 200
    conv_id_a = r1.json()["conversation_id"]

    # Now POST to profile B's oracle endpoint with profile A's conversation_id → 404.
    r2 = client.post(
        f"/api/v1/ziwei/profiles/{pid_b}/oracle",
        json={"scenario": "natal", "message": "感情呢？", "conversation_id": conv_id_a},
    )
    assert r2.status_code == 404


def test_ask_oracle_502_leaves_no_orphan_message(monkeypatch):
    """On oracle failure (502), neither a user message nor the new conversation persists."""
    pid = _seed_profile()

    # Monkeypatch ZiweiOracle.run to return None (simulates backend LLM failure).
    monkeypatch.setattr(ziwei_routes.ZiweiOracle, "run", lambda *args, **kwargs: None)

    r = client.post(f"/api/v1/ziwei/profiles/{pid}/oracle", json={"scenario": "natal", "message": "大运如何？"})
    assert r.status_code == 502

    # No conversation should have been committed.
    rc = client.get(f"/api/v1/ziwei/profiles/{pid}/conversations")
    assert rc.status_code == 200
    assert len(rc.json()) == 0, "Orphan conversation persisted after 502"

    # Confirm no messages exist under any conversation for this profile.
    db = TestingSessionLocal()
    try:
        convs = db.scalars(
            select(ZiweiConversation).where(ZiweiConversation.profile_id == pid)
        ).all()
        assert len(convs) == 0, "Orphan conversation found in DB after 502"
        for conv in convs:
            msgs = db.scalars(
                select(ZiweiMessage).where(ZiweiMessage.conversation_id == conv.id)
            ).all()
            assert len(msgs) == 0, f"Orphan messages found in conv {conv.id} after 502"
    finally:
        db.close()

"""Tests for the streaming ziwei oracle endpoint + StreamMarkerParser.

StreamMarkerParser unit tests cover the crux: markers split across deltas, alias
normalization, invalid-marker drop, consecutive-command dedup, and no-marker passthrough.

Endpoint integration test mirrors test_ziwei_oracle_routes.py: monkeypatch
``app.api.v1.routes.ziwei.AIService`` with a fake whose ``client.messages.stream(...)``
returns a context manager yielding deltas via ``.text_stream`` and usage via
``.get_final_message()``. The route's generator persists via ``app.db.session.SessionLocal``
directly (not the get_db override), so we also monkeypatch ``ziwei_routes.SessionLocal`` to
the test session. Tables are built via per-table create (JSON-mapped) + raw DDL (AIFeedback).
"""
import json
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
from app.services.ziwei.oracle_tools import StreamMarkerParser


# ============================ StreamMarkerParser unit tests ============================
def _drain(parser, deltas):
    events = []
    for d in deltas:
        events.extend(parser.feed(d))
    trailing, clean, segs, cams = parser.finish()
    if trailing:
        events.append(("text", trailing))
    return events, clean, segs, cams


def test_stream_parser_marker_split_across_deltas():
    # 标记 [[focus:命宫]] 被切成多个 delta
    events, clean, segs, cams = _drain(StreamMarkerParser(), ["你命宫紫微。[[fo", "cus:命", "宫]] 宜走高位。"])
    text = "".join(v for k, v in events if k == "text")
    assert "[[" not in text and "命宫紫微" in text and "宜走高位" in text
    assert cams == [{"type": "focus_palace", "palace": "命宫"}]
    assert ("camera", {"type": "focus_palace", "palace": "命宫"}) in events


def test_stream_parser_overview_term_and_alias():
    events, clean, segs, cams = _drain(StreamMarkerParser(), ["[[overview]]看交友[[focus:交友]]这是机月同梁格[[term:机月同梁格|稳健之格]]。"])
    assert cams == [
        {"type": "overview"},
        {"type": "focus_palace", "palace": "仆役"},  # 交友→仆役
        {"type": "explain_term", "term": "机月同梁格", "explanation": "稳健之格"},
    ]
    assert "[[" not in clean and "机月同梁格" in clean


def test_stream_parser_invalid_and_dedup():
    events, clean, segs, cams = _drain(StreamMarkerParser(), ["甲[[focus:火星宫]]乙[[focus:命宫]]丙[[focus:命宫]]丁"])
    # 火星宫非法丢弃；命宫连续两次去重
    assert cams == [{"type": "focus_palace", "palace": "命宫"}]
    assert clean == "甲乙丙丁"


def test_stream_parser_no_markers():
    events, clean, segs, cams = _drain(StreamMarkerParser(), ["纯文字", "没有标记。"])
    assert clean == "纯文字没有标记。"
    assert cams == []
    assert segs == [{"text": "纯文字没有标记。", "commands": []}]


# ============================ Endpoint integration test ============================
TEST_DB_DIR = Path(mkdtemp(prefix="ai-engineer-ziwei-stream-tests-"))
TEST_DB_PATH = TEST_DB_DIR / "test_ziwei_stream.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH.as_posix()}"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

from app.services.ziwei.oracle_tools import parse_markers as _parse_markers

CANNED_RAW = "命宫紫微，主尊贵。[[focus:命宫]] 福泽深厚。"
CANNED_TEXT = _parse_markers(CANNED_RAW)[0]
# Split the raw text into deltas, slicing through the marker to exercise cross-delta parsing.
_split = CANNED_RAW.index("focus:") + 3  # mid-marker cut
CANNED_DELTAS = [CANNED_RAW[:_split], CANNED_RAW[_split:]]


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---- fake streaming Anthropic client ----
class _FakeStream:
    def __init__(self, deltas):
        self._deltas = deltas

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    @property
    def text_stream(self):
        for d in self._deltas:
            yield d

    def get_final_message(self):
        return SimpleNamespace(usage=SimpleNamespace(input_tokens=120, output_tokens=80))


class _FakeMessages:
    def stream(self, *args, **kwargs):
        return _FakeStream(CANNED_DELTAS)


class _FakeClient:
    def __init__(self):
        self.messages = _FakeMessages()


class _FakeAIService:
    is_available = True
    model = "test-model"

    def __init__(self, *args, **kwargs):
        self.client = _FakeClient()


# ---- chart fixture ----
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
    User.__table__.create(bind=engine, checkfirst=True)
    ZiweiProfile.__table__.create(bind=engine, checkfirst=True)
    ZiweiConversation.__table__.create(bind=engine, checkfirst=True)
    ZiweiMessage.__table__.create(bind=engine, checkfirst=True)
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
    # The generator persists via app.db.session.SessionLocal directly; point it at the test DB.
    monkeypatch.setattr(ziwei_routes, "SessionLocal", TestingSessionLocal)


@pytest.fixture(autouse=True)
def _clean_db():
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


def _parse_sse(body: str):
    """Extract JSON payloads from `data:` lines of an SSE response body."""
    events = []
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            payload = line[len("data:"):].strip()
            if payload:
                events.append(json.loads(payload))
    return events


def test_oracle_stream_emits_events_and_persists():
    pid = _seed_profile()
    r = client.post(f"/api/v1/ziwei/profiles/{pid}/oracle/stream", json={"scenario": "natal", "message": "事业如何？"})
    assert r.status_code == 200, r.text

    events = _parse_sse(r.text)
    by_type = {}
    for e in events:
        by_type.setdefault(e["type"], []).append(e)

    # text events reconstruct the clean reading
    reconstructed = "".join(e["delta"] for e in by_type.get("text", [])).strip()
    assert reconstructed == CANNED_TEXT
    assert "[[" not in reconstructed

    # a camera event for the inline marker
    assert by_type.get("camera"), "no camera event emitted"
    assert by_type["camera"][0]["command"] == {"type": "focus_palace", "palace": "命宫"}

    # a done event with conversation_id
    assert by_type.get("done"), "no done event emitted"
    done = by_type["done"][0]
    conv_id = done["conversation_id"]
    assert conv_id
    assert done["meta"]["total_tokens"] == 200

    assert "error" not in by_type

    # assistant ZiweiMessage persisted with clean content + segments in chart_context_json
    db = TestingSessionLocal()
    try:
        msgs = db.scalars(
            select(ZiweiMessage).where(ZiweiMessage.conversation_id == conv_id).order_by(ZiweiMessage.id.asc())
        ).all()
        assert len(msgs) == 2
        assert msgs[0].role == "user"
        assert msgs[1].role == "assistant"
        assert msgs[1].content == CANNED_TEXT
        ctx = msgs[1].chart_context_json
        assert "segments" in ctx and isinstance(ctx["segments"], list) and len(ctx["segments"]) >= 1
        assert ctx["camera_commands"][0] == {"type": "focus_palace", "palace": "命宫"}
    finally:
        db.close()


class _RaisingStream(_FakeStream):
    @property
    def text_stream(self):
        yield "命宫紫微，主尊贵。"  # 半截文本已发给客户端
        raise RuntimeError("upstream boom")  # 流中途炸


class _RaisingMessages:
    def stream(self, *args, **kwargs):
        return _RaisingStream([])


class _RaisingAIService(_FakeAIService):
    def __init__(self, *args, **kwargs):
        self.client = SimpleNamespace(messages=_RaisingMessages())


def test_oracle_stream_emits_error_and_salvages_partial(monkeypatch):
    monkeypatch.setattr(ziwei_routes, "AIService", _RaisingAIService)
    pid = _seed_profile()
    r = client.post(f"/api/v1/ziwei/profiles/{pid}/oracle/stream", json={"scenario": "natal", "message": "事业如何？"})
    assert r.status_code == 200, r.text
    events = _parse_sse(r.text)
    types = [e["type"] for e in events]
    # 中途失败：先有已发的文字，最后是 error，且没有 done
    assert "error" in types and "done" not in types
    assert any(e["type"] == "text" and "命宫紫微" in e["delta"] for e in events)
    # 已生成的半截被尽力保住（salvage-persist）
    db = TestingSessionLocal()
    try:
        msgs = db.scalars(select(ZiweiMessage).order_by(ZiweiMessage.id.asc())).all()
        assert any(m.role == "assistant" and "命宫紫微" in m.content for m in msgs)
    finally:
        db.close()


def test_oracle_stream_404_unknown_profile():
    r = client.post("/api/v1/ziwei/profiles/999999/oracle/stream", json={"scenario": "natal", "message": "x"})
    assert r.status_code == 404


def test_oracle_stream_400_no_chart():
    pid = _seed_profile(chart={})
    r = client.post(f"/api/v1/ziwei/profiles/{pid}/oracle/stream", json={"scenario": "natal", "message": "x"})
    assert r.status_code == 400

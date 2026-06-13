import json
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

import app.api.v1.routes.qian as qian_routes
from app.db.session import get_db
from app.main import app
from app.models.entities import QianReading, User

TEST_DIR = Path(mkdtemp(prefix="qian-tests-"))
engine = create_engine(f"sqlite:///{(TEST_DIR/'t.db').as_posix()}", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class _FakeStream:
    def __init__(self, deltas): self._d = deltas
    def __enter__(self): return self
    def __exit__(self, *a): return False
    @property
    def text_stream(self):
        for d in self._d: yield d
    def get_final_message(self): return SimpleNamespace(usage=SimpleNamespace(input_tokens=120, output_tokens=80))


class _FakeMessages:
    def stream(self, *a, **k): return _FakeStream(["此乃上签。", "[[term:辰宫|地支]] 凡事可成。"])


class _FakeClient:
    def __init__(self): self.messages = _FakeMessages()


class _FakeAIService:
    is_available = True
    model = "test-model"
    def __init__(self, *a, **k): self.client = _FakeClient()


def override_get_db():
    db = TestingSessionLocal()
    try: yield db
    finally: db.close()


def setup_module():
    User.__table__.create(bind=engine, checkfirst=True)
    QianReading.__table__.create(bind=engine, checkfirst=True)
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS ai_feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,"
            " feature VARCHAR(30) NOT NULL, reference_id INTEGER NOT NULL, user_input_hash TEXT NOT NULL,"
            " prompt_template TEXT, response_json TEXT, model VARCHAR(100), input_tokens INTEGER,"
            " output_tokens INTEGER, latency_ms INTEGER, created_at TIMESTAMP)"
        ))
    app.dependency_overrides[get_db] = override_get_db


def teardown_module():
    app.dependency_overrides.clear()
    engine.dispose()
    rmtree(TEST_DIR, ignore_errors=True)


client = TestClient(app)


def _patch(monkeypatch):
    monkeypatch.setattr(qian_routes, "AIService", _FakeAIService)
    monkeypatch.setattr(qian_routes, "SessionLocal", TestingSessionLocal)


def _events(body: str):
    out = []
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            p = line[5:].strip()
            if p: out.append(json.loads(p))
    return out


def test_stream_draws_sign_text_camera_done_and_persists(monkeypatch):
    _patch(monkeypatch)
    r = client.post("/api/v1/qian/oracle/stream", json={"question": "今年事业？"})
    assert r.status_code == 200, r.text
    evs = _events(r.text)
    by = {}
    for e in evs: by.setdefault(e["type"], []).append(e)
    assert by["sign"][0]["sign"]["id"] and 1 <= by["sign"][0]["sign"]["id"] <= 100
    assert "".join(e["delta"] for e in by.get("text", [])).strip()
    assert by.get("camera") and by["camera"][0]["command"]["type"] == "explain_term"
    assert by.get("done")
    db = TestingSessionLocal()
    try:
        rows = db.scalars(select(QianReading)).all()
        assert len(rows) == 1 and rows[0].question == "今年事业？" and rows[0].response
    finally:
        db.close()


def test_stream_with_fixed_sign_id(monkeypatch):
    _patch(monkeypatch)
    r = client.post("/api/v1/qian/oracle/stream", json={"question": "问", "sign_id": 7})
    evs = _events(r.text)
    sign = next(e for e in evs if e["type"] == "sign")["sign"]
    assert sign["id"] == 7


def test_stream_400_empty_question(monkeypatch):
    _patch(monkeypatch)
    r = client.post("/api/v1/qian/oracle/stream", json={"question": "   "})
    assert r.status_code == 400


def test_readings_list(monkeypatch):
    _patch(monkeypatch)
    client.post("/api/v1/qian/oracle/stream", json={"question": "甲"})
    r = client.get("/api/v1/qian/readings")
    assert r.status_code == 200 and isinstance(r.json(), list) and len(r.json()) >= 1

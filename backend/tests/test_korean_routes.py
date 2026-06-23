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
    Base.metadata.create_all(
        bind=engine,
        tables=[t for t in Base.metadata.sorted_tables if t.name != "ai_feedback"],
    )
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

from pathlib import Path
from tempfile import mkdtemp
from shutil import rmtree

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import get_db
from app.main import app
from app.models.entities import Summary

TEST_DB_DIR = Path(mkdtemp(prefix="ai-engineer-summary-tests-"))
TEST_DB_PATH = TEST_DB_DIR / "test_summary.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH.as_posix()}"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def setup_module():
    # Only create the summaries table — other tables use JSONB which SQLite cannot compile.
    Summary.__table__.create(bind=engine, checkfirst=True)
    app.dependency_overrides[get_db] = override_get_db


def teardown_module():
    app.dependency_overrides.clear()
    engine.dispose()
    if TEST_DB_DIR.exists():
        rmtree(TEST_DB_DIR, ignore_errors=True)


client = TestClient(app)


def test_generate_rejects_bad_source_type():
    r = client.post("/api/v1/summary/generate", json={"source_type": "pdf", "value": "x"})
    assert r.status_code == 422


def test_generate_rejects_empty_value():
    r = client.post("/api/v1/summary/generate", json={"source_type": "text", "value": "  "})
    assert r.status_code == 422


def test_list_summaries_returns_list():
    r = client.get("/api/v1/summary/list")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_delete_missing_summary_404():
    r = client.delete("/api/v1/summary/99999999")
    assert r.status_code == 404


def test_generate_rejects_bad_output_type():
    r = client.post("/api/v1/summary/generate", json={"source_type": "text", "value": "x", "output_type": "podcast"})
    assert r.status_code == 422

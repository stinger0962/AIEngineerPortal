from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import get_db
from app.main import app
from app.models.entities import ScribeTranscript

TEST_DB_DIR = Path(mkdtemp(prefix="ai-engineer-scribe-tests-"))
TEST_DB_PATH = TEST_DB_DIR / "test_scribe.db"
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
    ScribeTranscript.__table__.create(bind=engine, checkfirst=True)
    app.dependency_overrides[get_db] = override_get_db


def teardown_module():
    app.dependency_overrides.clear()
    engine.dispose()
    if TEST_DB_DIR.exists():
        rmtree(TEST_DB_DIR, ignore_errors=True)


client = TestClient(app)


def test_scribe_generate_rejects_bad_url():
    r = client.post("/api/v1/scribe/generate", json={"youtube_url": "https://vimeo.com/1"})
    assert r.status_code == 422


def test_scribe_list_returns_list():
    r = client.get("/api/v1/scribe/list")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_scribe_delete_missing_404():
    r = client.delete("/api/v1/scribe/99999999")
    assert r.status_code == 404

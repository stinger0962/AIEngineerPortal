from pathlib import Path
from tempfile import mkdtemp
from shutil import rmtree

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import get_db
from app.main import app
from app.models.entities import DubVideo

TEST_DB_DIR = Path(mkdtemp(prefix="ai-engineer-dub-tests-"))
TEST_DB_PATH = TEST_DB_DIR / "test_dub.db"
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
    # Only create the dub_videos table — other tables use JSONB which SQLite cannot compile.
    DubVideo.__table__.create(bind=engine, checkfirst=True)
    app.dependency_overrides[get_db] = override_get_db


def teardown_module():
    app.dependency_overrides.clear()
    engine.dispose()
    if TEST_DB_DIR.exists():
        rmtree(TEST_DB_DIR, ignore_errors=True)


client = TestClient(app)


def test_dub_generate_rejects_bad_url():
    r = client.post("/api/v1/dub/generate", json={"youtube_url": "https://vimeo.com/1", "voice_id": "random"})
    assert r.status_code == 422


def test_dub_list_returns_list():
    r = client.get("/api/v1/dub/list")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_dub_delete_missing_404():
    r = client.delete("/api/v1/dub/99999999")
    assert r.status_code == 404

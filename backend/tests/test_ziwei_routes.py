from pathlib import Path
from tempfile import mkdtemp
from shutil import rmtree

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import get_db
from app.main import app
from app.models.entities import ZiweiProfile

TEST_DB_DIR = Path(mkdtemp(prefix="ziwei-route-tests-"))
TEST_DATABASE_URL = f"sqlite:///{(TEST_DB_DIR / 'test.db').as_posix()}"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def setup_module():
    # 只建 ziwei_profiles 表——其他表含 SQLite 不支持的列类型
    ZiweiProfile.__table__.create(bind=engine, checkfirst=True)
    app.dependency_overrides[get_db] = override_get_db


def teardown_module():
    app.dependency_overrides.clear()
    engine.dispose()
    if TEST_DB_DIR.exists():
        rmtree(TEST_DB_DIR, ignore_errors=True)


client = TestClient(app)

VALID_PAYLOAD = {
    "name": "妈妈",
    "relation": "family",
    "gender": "female",
    "birth_date": "1965-03-12",
    "birth_time_index": 4,
    "is_lunar_input": False,
    "is_leap_month": False,
    "chart_json": {"palaces": [{"name": "命宫", "earthlyBranch": "子"}], "fiveElementsClass": "水二局"},
}


def test_list_profiles_empty():
    response = client.get("/api/v1/ziwei/profiles")
    assert response.status_code == 200
    assert response.json() == []


def test_create_profile():
    response = client.post("/api/v1/ziwei/profiles", json=VALID_PAYLOAD)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] > 0
    assert body["name"] == "妈妈"
    assert body["persona"] == "sage"
    assert body["chart_json"]["fiveElementsClass"] == "水二局"


def test_create_profile_rejects_bad_time_index():
    response = client.post("/api/v1/ziwei/profiles", json={**VALID_PAYLOAD, "birth_time_index": 13})
    assert response.status_code == 400


def test_create_profile_rejects_bad_gender():
    response = client.post("/api/v1/ziwei/profiles", json={**VALID_PAYLOAD, "gender": "other"})
    assert response.status_code == 400


def test_create_profile_rejects_bad_birth_date():
    response = client.post("/api/v1/ziwei/profiles", json={**VALID_PAYLOAD, "birth_date": "not-a-date"})
    assert response.status_code == 400


def test_get_update_delete_profile():
    created = client.post("/api/v1/ziwei/profiles", json=VALID_PAYLOAD).json()
    pid = created["id"]

    got = client.get(f"/api/v1/ziwei/profiles/{pid}")
    assert got.status_code == 200
    assert got.json()["name"] == "妈妈"

    updated = client.put(f"/api/v1/ziwei/profiles/{pid}", json={"persona": "taoist", "name": "母亲"})
    assert updated.status_code == 200
    assert updated.json()["persona"] == "taoist"
    assert updated.json()["name"] == "母亲"

    bad_persona = client.put(f"/api/v1/ziwei/profiles/{pid}", json={"persona": "wizard"})
    assert bad_persona.status_code == 400

    deleted = client.delete(f"/api/v1/ziwei/profiles/{pid}")
    assert deleted.status_code == 200
    assert client.get(f"/api/v1/ziwei/profiles/{pid}").status_code == 404

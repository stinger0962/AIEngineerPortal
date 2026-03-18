from pathlib import Path
from tempfile import mkdtemp
from shutil import rmtree

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Exercise, InterviewQuestion, KnowledgeArticle, LearningPath, Lesson, User
from app.services.seed_service import seed_database

TEST_DB_DIR = Path(mkdtemp(prefix="ai-engineer-portal-tests-"))
TEST_DB_PATH = TEST_DB_DIR / "test.db"
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
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    app.dependency_overrides[get_db] = override_get_db


def teardown_module():
    app.dependency_overrides.clear()
    engine.dispose()
    if TEST_DB_DIR.exists():
        rmtree(TEST_DB_DIR, ignore_errors=True)


client = TestClient(app)


def test_dashboard_summary():
    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200
    assert response.json()["user_name"] == "Alex Builder"
    assert response.json()["stats"][0]["value"] == "0.0%"


def test_complete_lesson_updates_progress():
    paths = client.get("/api/v1/learning/paths").json()
    lesson_id = paths[0]["lessons"][1]["id"]
    response = client.post(f"/api/v1/learning/lessons/{lesson_id}/complete")
    assert response.status_code == 200
    assert response.json()["completed"] is True


def test_exercise_attempt_roundtrip():
    recommended = client.get("/api/v1/exercises/recommended").json()
    exercise_id = recommended[0]["id"]
    response = client.post(
        f"/api/v1/exercises/{exercise_id}/attempt",
        json={"submitted_code": "def solve(payload):\n    return payload\n", "notes": "Tested solution"},
    )
    assert response.status_code == 200
    assert response.json()["score"] >= 80


def test_knowledge_search():
    response = client.get("/api/v1/knowledge/search", params={"query": "rag"})
    assert response.status_code == 200
    assert len(response.json()) > 0


def test_project_create_and_update():
    create_response = client.post(
        "/api/v1/projects",
        json={
            "title": "Prompt QA Studio",
            "summary": "A focused QA workflow for prompts.",
            "status": "active",
            "category": "evaluation",
            "stack_json": ["Next.js", "FastAPI"],
            "architecture_md": "Structured evaluations with reviewer checkpoints.",
            "repo_url": None,
            "demo_url": None,
            "lessons_learned_md": "",
            "portfolio_score": 80,
        },
    )
    assert create_response.status_code == 200
    project_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/projects/{project_id}",
        json={
            "title": "Prompt QA Studio",
            "summary": "Updated summary",
            "status": "complete",
            "category": "evaluation",
            "stack_json": ["Next.js", "FastAPI"],
            "architecture_md": "Structured evaluations with reviewer checkpoints.",
            "repo_url": None,
            "demo_url": None,
            "lessons_learned_md": "Need stronger benchmark coverage.",
            "portfolio_score": 86,
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "complete"


def test_seed_sync_is_idempotent_and_keeps_reference_content_populated():
    db = TestingSessionLocal()
    try:
        seed_database(db)
        assert db.query(User).count() == 1
        assert db.query(LearningPath).count() == 7
        assert db.query(Lesson).count() == 35
        assert db.query(Exercise).count() >= 40
        assert db.query(KnowledgeArticle).count() >= 30
        assert db.query(InterviewQuestion).count() >= 24
    finally:
        db.close()

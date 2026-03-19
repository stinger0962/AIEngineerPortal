from pathlib import Path
from tempfile import mkdtemp
from shutil import rmtree

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Exercise, InterviewQuestion, JobPosting, KnowledgeArticle, LearningPath, Lesson, NewsItem, User
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
        assert db.query(NewsItem).count() >= 4
        assert db.query(JobPosting).count() >= 3
    finally:
        db.close()


def test_news_and_jobs_phase_two_routes():
    news_response = client.get("/api/v1/news")
    assert news_response.status_code == 200
    assert len(news_response.json()) >= 1
    assert "is_seeded" in news_response.json()[0]
    assert "focus_area" in news_response.json()[0]
    assert "recommended_path_slug" in news_response.json()[0]
    assert "recommended_exercise_category" in news_response.json()[0]

    news_meta = client.get("/api/v1/news/meta")
    assert news_meta.status_code == 200
    assert news_meta.json()["item_count"] >= 1

    jobs_response = client.get("/api/v1/jobs")
    assert jobs_response.status_code == 200
    jobs = jobs_response.json()
    assert len(jobs) >= 1
    assert "is_seeded" in jobs[0]
    assert "focus_area" in jobs[0]
    assert "primary_gap" in jobs[0]
    assert "recommended_exercise_category" in jobs[0]

    jobs_meta = client.get("/api/v1/jobs/meta")
    assert jobs_meta.status_code == 200
    assert jobs_meta.json()["item_count"] >= 1

    job_id = jobs[0]["id"]
    fit_response = client.post(f"/api/v1/jobs/{job_id}/analyze-fit")
    assert fit_response.status_code == 200
    assert fit_response.json()["fit_score"] >= 45


def test_recommendations_include_signal_specific_actions():
    response = client.get("/api/v1/recommendations/next-actions")
    assert response.status_code == 200
    payload = response.json()
    assert any(item["source_kind"] == "news" and item["action_path"].startswith("/learn/") for item in payload)
    assert any(
        item["source_kind"] == "jobs"
        and (
            item["action_path"] in {
                "/projects",
                "/interview",
                "/learn",
                "/learn/ai-deployment-and-mlops",
                "/learn/ai-agents-and-tools",
                "/learn/python-for-ai-engineers",
            }
            or item["action_path"].startswith("/learn/lesson/")
        )
        for item in payload
    )


def test_saved_signals_drive_recommendations_and_today_view():
    news_items = client.get("/api/v1/news").json()
    saved_news = next(item for item in news_items if item["category"] == "agents")
    save_news_response = client.post(f"/api/v1/news/{saved_news['id']}/save")
    assert save_news_response.status_code == 200

    jobs = client.get("/api/v1/jobs").json()
    saved_job = jobs[0]
    save_job_response = client.post(f"/api/v1/jobs/{saved_job['id']}/save")
    assert save_job_response.status_code == 200

    recommendations = client.get("/api/v1/recommendations/next-actions").json()
    news_recommendation = next(item for item in recommendations if item["source_kind"] == "news")
    job_recommendation = next(item for item in recommendations if item["source_kind"] == "jobs")
    assert news_recommendation["title"] == "Act on a saved AI signal"
    assert news_recommendation["action_path"].startswith("/learn/lesson/ai-agents-and-tools")
    assert job_recommendation["title"] in {
        "Turn your saved target role into portfolio proof",
        "Close the top gap for your saved role",
        "Use your saved role to tighten interview positioning",
    }

    today = client.get("/api/v1/dashboard/today").json()
    assert any("saved signal" in item.lower() for item in today["focus"])
    assert any("saved 1 news items and 1 roles" in item.lower() for item in today["highlights"])


def test_dashboard_summary_adapts_to_completed_lessons_and_practice_history():
    agent_news = next(item for item in client.get("/api/v1/news").json() if item["category"] == "agents")
    assert client.post(f"/api/v1/news/{agent_news['id']}/save").status_code == 200

    paths = client.get("/api/v1/learning/paths").json()
    agents_path = next(path for path in paths if path["slug"] == "ai-agents-and-tools")
    first_agent_lesson_id = agents_path["lessons"][0]["id"]
    assert client.post(f"/api/v1/learning/lessons/{first_agent_lesson_id}/complete").status_code == 200

    summary = client.get("/api/v1/dashboard/summary").json()
    assert summary["next_lesson"]["slug"] == "ai-agents-and-tools-2"
    assert summary["recommended_exercise"]["category"] in {"prompt-formatting", "api-async"}
    first_recommended_id = summary["recommended_exercise"]["id"]

    attempt_response = client.post(
        f"/api/v1/exercises/{first_recommended_id}/attempt",
        json={"submitted_code": "def solve(payload):\n    return payload\n", "notes": "Rotate to next drill"},
    )
    assert attempt_response.status_code == 200

    next_summary = client.get("/api/v1/dashboard/summary").json()
    assert next_summary["recommended_exercise"]["id"] != first_recommended_id


def test_recommendations_prefer_interview_when_project_proof_exists():
    updated = client.get("/api/v1/recommendations/next-actions").json()
    internal = next(item for item in updated if item["source_kind"] in {"projects", "interview"})
    assert internal["source_kind"] == "interview"
    assert internal["action_path"] == "/interview"
    assert "completed project proof point" in internal["reason"].lower()

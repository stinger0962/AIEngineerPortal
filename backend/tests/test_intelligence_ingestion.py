from datetime import datetime, timedelta

from app.services.jobs_service import _dedupe_and_rank_jobs, _looks_like_relevant_role, _score_job_relevance
from app.services.news_service import _dedupe_and_rank_news, _normalize_url


def test_normalize_url_strips_tracking_params_and_trailing_slash():
    normalized = _normalize_url("https://Example.com/path/to/article/?utm_source=test&utm_medium=email&id=7")
    assert normalized == "https://example.com/path/to/article?id=7"


def test_news_dedupe_prefers_higher_ranked_item_and_limits_per_source():
    now = datetime.utcnow()
    items = [
        {
            "source_name": "OpenAI",
            "title": "Agents launch",
            "slug": "agents-launch",
            "summary": "Agent updates",
            "source_url": "https://openai.com/news/agents",
            "category": "agents",
            "published_at": now,
            "signal_score": 95,
            "tags_json": ["agents", "tooling"],
        },
        {
            "source_name": "OpenAI",
            "title": "Agents launch",
            "slug": "agents-launch-duplicate",
            "summary": "Duplicate entry",
            "source_url": "https://openai.com/news/agents/",
            "category": "agents",
            "published_at": now - timedelta(hours=1),
            "signal_score": 70,
            "tags_json": ["agents"],
        },
    ]

    deduped = _dedupe_and_rank_news(items)

    assert len(deduped) == 1
    assert deduped[0]["signal_score"] == 95


def test_job_dedupe_prefers_highest_relevance_for_same_role():
    now = datetime.utcnow()
    items = [
        {
            "source_name": "Remotive",
            "title": "AI Engineer",
            "slug": "job-1",
            "company_name": "Example AI",
            "location": "Remote",
            "employment_type": "full-time",
            "summary": "Relevant role",
            "source_url": "https://jobs.example.com/roles/1",
            "description_md": "RAG evaluation role",
            "published_at": now,
            "tags_json": ["rag", "evaluation"],
            "relevance_score": 92,
        },
        {
            "source_name": "Arbeitnow",
            "title": "AI Engineer",
            "slug": "job-2",
            "company_name": "Example AI",
            "location": "Remote",
            "employment_type": "full-time",
            "summary": "Lower ranked duplicate",
            "source_url": "https://jobs.example.com/roles/1?utm_source=test",
            "description_md": "AI role",
            "published_at": now - timedelta(days=1),
            "tags_json": ["ai-engineer"],
            "relevance_score": 64,
        },
    ]

    deduped = _dedupe_and_rank_jobs(items)

    assert len(deduped) == 1
    assert deduped[0]["relevance_score"] == 92


def test_generic_fullstack_role_is_not_treated_as_ai_role():
    title = "Senior Full-stack React Developer"
    description = "Build product features with React, Python, and cloud tooling for startup clients."

    assert _looks_like_relevant_role(title, description) is False
    assert _score_job_relevance(title, description, ["react", "python"], 1.0) < 55


def test_platform_engineer_title_can_still_count_as_relevant_when_ai_signal_is_in_description():
    title = "LLM Platform Engineer"
    description = "Own evaluation runs, retrieval systems, deployment safety, and provider integrations."

    assert _looks_like_relevant_role(title, description) is True

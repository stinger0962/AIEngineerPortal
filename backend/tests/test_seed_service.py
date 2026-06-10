import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


@pytest.fixture()
def db_session():
    # Only the projects table: other tables use Postgres-only types (JSONB)
    # that SQLite cannot create.
    from app.models.entities import Project

    engine = create_engine("sqlite://")
    Project.__table__.create(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_projects_payload_keys_match_project_model():
    from app.models.entities import Project
    from app.seed.data import PROJECTS

    columns = set(Project.__table__.columns.keys())
    for payload in PROJECTS:
        unknown = set(payload) - columns
        assert not unknown, f"PROJECTS payload {payload.get('slug')!r} has keys not on Project: {sorted(unknown)}"


def test_seed_project_templates_on_fresh_database(db_session):
    from app.models.entities import Project
    from app.seed.data import PROJECTS
    from app.services.seed_service import seed_project_templates

    seed_project_templates(db_session)
    db_session.flush()

    slugs = set(db_session.scalars(select(Project.slug)).all())
    assert slugs == {payload["slug"] for payload in PROJECTS}


def test_knowledge_article_payload_keys_match_model():
    from app.models.entities import KnowledgeArticle
    from app.seed.data import build_articles

    columns = set(KnowledgeArticle.__table__.columns.keys())
    required = {"title", "slug", "category", "summary", "content_md", "source_links_json", "tags_json"}
    for payload in build_articles():
        unknown = set(payload) - columns
        assert not unknown, f"article payload {payload.get('slug')!r} has keys not on KnowledgeArticle: {sorted(unknown)}"
        missing = required - set(payload)
        assert not missing, f"article payload {payload.get('slug')!r} missing keys: {sorted(missing)}"

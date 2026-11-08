"""Fresh product boundaries: local SQLite only, no live services or migrations."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import QianReading, User
from app import paid_main
from app.api.v1.routes import qian


@pytest.fixture
def product(tmp_path, monkeypatch):
    settings = get_settings().model_copy(update={
        "database_url": f"sqlite:///{tmp_path / 'portal.db'}",
        "paid_database_url": f"sqlite:///{tmp_path / 'paid.db'}",
        "stripe_secret_key": "", "stripe_test_enabled": False,
        "ziwei_claim_code": "", "ziwei_auto_adopt": False,
        "paid_accounts_enabled": False,
    })
    monkeypatch.setattr(paid_main, "get_settings", lambda: settings)
    from app.services import paid_accounts as auth
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    return settings, paid_main.create_app()


def test_fresh_start_only_product_tables_and_no_seed(product, tmp_path):
    settings, app = product
    with TestClient(app) as client:
        assert client.get("/health").json()["payments"] == "test-only"
        assert set(inspect(app.state.paid_engine).get_table_names()) == {t.name for t in paid_main.PAID_TABLES}
        with Session(app.state.paid_engine) as db:
            assert db.scalars(select(User)).all() == []
        assert client.get("/api/v1/ziwei/profiles", headers={"X-Device-Id": "fresh"}).status_code == 503
        assert client.get("/api/v1/qian/readings", headers={"X-Device-Id": "fresh"}).status_code == 503
        assert client.post("/api/v1/billing/checkout", json={"pack": "p10"}).status_code == 503
        assert client.get("/api/v1/billing/balance", headers={"X-Device-Id": "fresh"}).status_code == 503
        for path in ("/dashboard", "/projects", "/learning/paths", "/copilot", "/memory"):
            assert client.get("/api/v1" + path).status_code == 404
        assert client.post("/api/v1/ziwei/claim", json={"code": "old"}).status_code == 404
    assert not (tmp_path / "portal.db").exists()
    # Restart reuses only its own fresh-product records.
    with TestClient(app) as client:
        assert client.get("/api/v1/billing/balance", headers={"X-Device-Id": "fresh"}).status_code == 503


@pytest.mark.parametrize("changes, message", [
    ({"paid_database_url": ""}, "PAID_DATABASE_URL"),
    ({"paid_database_url": "sqlite:///same.db", "database_url": "sqlite:///same.db"}, "portal DATABASE_URL"),
    ({"stripe_secret_key": "sk_live_forbidden"}, "test keys only"),
    ({"stripe_secret_key": "rk_live_forbidden"}, "test keys only"),
    ({"ziwei_claim_code": "legacy"}, "Legacy claim"),
    ({"ziwei_auto_adopt": True}, "Legacy claim"),
])
def test_unsafe_configuration_fails_before_connect(product, monkeypatch, changes, message):
    settings, app = product
    for field, value in changes.items():
        setattr(settings, field, value)
    monkeypatch.setattr(paid_main, "create_engine", lambda *a, **k: pytest.fail("must validate before opening storage"))
    with pytest.raises(RuntimeError, match=message):
        with TestClient(app):
            pass


def test_unrelated_database_is_not_modified(product):
    settings, app = product
    engine = create_engine(settings.paid_database_url)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE personal_notes (body TEXT)"))
        conn.execute(text("INSERT INTO personal_notes VALUES ('keep me')"))
    with pytest.raises(RuntimeError, match="unrelated tables"):
        with TestClient(app):
            pass
    assert inspect(engine).get_table_names() == ["personal_notes"]
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT body FROM personal_notes")) == "keep me"
    engine.dispose()


def test_private_generation_closed_without_accounts(product):
    _, app = product
    with TestClient(app) as client:
        for path, payload in (("/qian/oracle/stream", {"question": "test"}),
                              ("/ziwei/tts", {"text": "test"})):
            assert client.post("/api/v1" + path, json=payload).status_code == 503


def test_shared_ziwei_router_is_unchanged():
    from app.api.v1.routes import ziwei
    assert "/ziwei/claim" in {r.path for r in ziwei.router.routes}

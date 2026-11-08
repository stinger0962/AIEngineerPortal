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


@pytest.mark.parametrize("alias", ["relative", "symlink", "hardlink", "missing-parent-alias"])
def test_database_file_alias_rejected_before_connect(product, tmp_path, monkeypatch, alias):
    settings, app = product
    target = tmp_path / "same.db"
    if alias != "missing-parent-alias":
        target.touch()
    if alias == "relative":
        monkeypatch.chdir(tmp_path)
        paid_url = "sqlite:///./same.db"
    elif alias == "symlink":
        (tmp_path / "alias.db").symlink_to(target)
        paid_url = f"sqlite:///{tmp_path / 'alias.db'}"
    elif alias == "hardlink":
        import os
        os.link(target, tmp_path / "alias.db")
        paid_url = f"sqlite:///{tmp_path / 'alias.db'}"
    else:
        (tmp_path / "alias-dir").symlink_to(tmp_path, target_is_directory=True)
        paid_url = f"sqlite:///{tmp_path / 'alias-dir' / 'same.db'}"
    settings.database_url = f"sqlite:///{target}"
    settings.paid_database_url = paid_url
    before = target.read_bytes() if target.exists() else None
    monkeypatch.setattr(paid_main, "create_engine", lambda *a, **k: pytest.fail("alias must fail before opening storage"))
    with pytest.raises(RuntimeError, match="portal DATABASE_URL"):
        with TestClient(app):
            pass
    assert (target.read_bytes() if target.exists() else None) == before


@pytest.mark.parametrize("paid,portal", [
    ("postgresql://alice:secret@LOCALHOST/paid", "postgresql+psycopg://bob:other@localhost:5432/paid"),
    ("postgresql://alice:secret@db.example./paid", "postgresql://bob:other@db.example:5432/paid"),
    ("postgresql://alice:secret@[0:0:0:0:0:0:0:1]/paid", "postgresql://bob:other@[::1]:5432/paid"),
])
def test_postgres_login_driver_and_host_alias_rejected_before_connect(product, monkeypatch, paid, portal):
    settings, app = product
    settings.paid_database_url, settings.database_url = paid, portal
    monkeypatch.setattr(paid_main, "create_engine", lambda *a, **k: pytest.fail("alias must fail before connect"))
    with pytest.raises(RuntimeError, match="portal DATABASE_URL"):
        with TestClient(app):
            pass


@pytest.mark.parametrize("url", [
    "sqlite:///file:paid.db?uri=true", "sqlite:///paid.db?mode=ro", "sqlite:///:memory:",
    "postgresql://user:secret@host/paid?host=other", "postgresql:///paid",
    "postgresql://user:secret@host:bad/paid",
])
def test_ambiguous_database_url_rejected_before_connect(product, monkeypatch, url):
    settings, app = product
    settings.paid_database_url = url
    monkeypatch.setattr(paid_main, "create_engine", lambda *a, **k: pytest.fail("unsafe URL must fail before connect"))
    with pytest.raises(RuntimeError) as error:
        with TestClient(app):
            pass
    assert "secret" not in str(error.value)


def test_portal_sqlite_uri_cannot_hide_alias(product, monkeypatch):
    settings, app = product
    settings.database_url = settings.paid_database_url + "?uri=true"
    monkeypatch.setattr(paid_main, "create_engine", lambda *a, **k: pytest.fail("unsafe URL must fail before connect"))
    with pytest.raises(RuntimeError, match="plain dedicated SQLite"):
        with TestClient(app):
            pass


@pytest.mark.parametrize("paid,portal", [
    ("postgresql://one:secret@localhost/paid", "postgresql://two:other@localhost/portal"),
    ("postgresql://one:secret@localhost:5433/db", "postgresql://two:other@localhost:5432/db"),
    ("postgresql://one:secret@localhost/Paid", "postgresql://two:other@localhost/paid"),
])
def test_distinct_postgres_targets_validate_without_network(paid, portal):
    paid_main.validate_database_isolation(paid, portal)


def test_safe_postgres_schema_option_does_not_change_database_identity():
    from app.db.paid_isolation import validate_database_isolation
    validate_database_isolation(
        "postgresql://user:secret@127.0.0.1:55432/ziwei_qa?options=-csearch_path%3Dpaid_qa_fixture",
        "sqlite:////tmp/unused-portal-isolation-test.db")
    with pytest.raises(RuntimeError, match="portal DATABASE_URL"):
        validate_database_isolation(
            "postgresql://user:secret@LOCALHOST/paid?options=-csearch_path%3Dpaid_qa_fixture",
            "postgresql://other:other@localhost:5432/paid?options=-csearch_path%3Dpublic")


@pytest.mark.parametrize("query", [
    "options=-csearch_path%3Dpaid%20-cport%3D5433", "options=-csearch_path%3Dpaid,public",
    "options=-csearch_path%3Dpaid&host=other", "host=other", "port=5433", "dbname=portal",
    "options=-csearch_path%3Dpaid&options=-csearch_path%3Dother", "options=-csearch_path%3D%22paid%22",
])
def test_postgres_connection_options_cannot_bypass_isolation(query):
    from app.db.paid_isolation import validate_database_isolation
    with pytest.raises(RuntimeError):
        validate_database_isolation(f"postgresql://user:secret@localhost/paid?{query}", "sqlite:////tmp/portal-options-test.db")

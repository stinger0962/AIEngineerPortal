from datetime import datetime, timedelta
import os
from uuid import uuid4
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateSchema, DropSchema

import pytest
from fastapi import FastAPI, Request, Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.api.v1.routes import account_recovery, billing, ziwei, qian
from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import (Account, AccountChallenge, AccountDevice, AccountSession,
    CreditLedger, VerifiedAccountEmail, ZiweiProfile, ZiweiProfileOwner, ZiweiConversation,
    ZiweiMessage, QianReading)
from app.services import account_recovery as auth, credits


@pytest.fixture
def harness(tmp_path, monkeypatch):
    settings = get_settings().model_copy(update={"account_recovery_enabled": True,
        "account_session_secure": False, "stripe_test_enabled": False, "stripe_secret_key": "",
        "ziwei_free_credits": 3})
    for module in (auth, account_recovery, credits, billing, ziwei):
        monkeypatch.setattr(module, "get_settings", lambda: settings)
    postgres_url = os.environ.get("ZIWEI_QA_POSTGRES_URL")
    admin = None
    schema = None
    if postgres_url:
        target = make_url(postgres_url)
        if target.host != "127.0.0.1" or target.port != 55432 or target.database != "ziwei_qa":
            raise ValueError("Recovery tests require isolated localhost QA PostgreSQL")
        schema = "recovery_" + uuid4().hex
        admin = create_engine(postgres_url)
        with admin.begin() as connection:
            connection.execute(CreateSchema(schema))
        engine = create_engine(postgres_url, connect_args={"options": f"-csearch_path={schema}"})
    else:
        engine = create_engine(f"sqlite:///{tmp_path / 'recovery.db'}", connect_args={"check_same_thread": False})
    from app.models.entities import AccountRateLimit, PaymentOrder, User
    for model in (User, Account, AccountDevice, CreditLedger, PaymentOrder, VerifiedAccountEmail,
                  AccountSession, AccountChallenge, AccountRateLimit, ZiweiProfile,
                  ZiweiConversation, ZiweiMessage, ZiweiProfileOwner, QianReading):
        model.__table__.create(engine)
    app = FastAPI()
    for router in (account_recovery.router, billing.router, ziwei.router, qian.router):
        app.include_router(router, prefix="/api/v1")
    def database():
        with Session(engine, autoflush=False, expire_on_commit=False) as db:
            yield db
    outbox = []
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[auth.get_sender] = lambda: lambda email, code: outbox.append((email, code))
    client = TestClient(app, headers={"X-Recovery-Client": "1", "X-Device-Id": "device-a"})
    yield client, engine, outbox, settings, app
    client.close()
    engine.dispose()
    if admin is not None:
        with admin.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        admin.dispose()


def profile(client, name="A"):
    r = client.post("/api/v1/ziwei/profiles", json={"name": name, "gender": "male", "birth_date": "2000-1-1", "birth_time_index": 1})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def challenge(client, outbox, purpose="bind", email="a@example.test"):
    r = client.post("/api/v1/account/challenges", json={"email": email, "purpose": purpose})
    assert r.status_code == 200, r.text
    return {"challenge_id": r.json()["challenge_id"], "code": outbox[-1][1]}


def verify(client, data):
    return client.post("/api/v1/account/verify", json=data)


def test_recovery_restores_balance_profiles_and_messages_without_merging(harness):
    c, engine, outbox, _, app = harness
    pid = profile(c)
    with Session(engine) as db:
        acct = credits.resolve_account(db, "device-a")
        aid = acct.id
        credits.grant(db, aid, 40, "purchase")
        conv = ZiweiConversation(profile_id=pid, title="saved", scenario="natal")
        db.add(conv); db.flush()
        cid = conv.id
        db.add(ZiweiMessage(conversation_id=cid, role="assistant", content="saved reading")); db.commit()
    data = challenge(c, outbox)
    assert verify(c, data).status_code == 200
    old_cookie = c.cookies.get(auth.cookie_name())
    assert c.get("/api/v1/billing/balance").json()["balance"] == 43
    second = TestClient(app, headers={"X-Recovery-Client": "1", "X-Device-Id": "device-b"})
    unrelated = profile(second, "B")
    assert second.get(f"/api/v1/ziwei/profiles/{pid}").status_code == 404
    recovered = challenge(second, outbox, "recover")
    assert verify(second, recovered).status_code == 200
    assert second.get("/api/v1/billing/balance").json()["balance"] == 43
    assert [p["id"] for p in second.get("/api/v1/ziwei/profiles").json()] == [pid]
    assert second.get(f"/api/v1/ziwei/conversations/{cid}/messages").json()[0]["content"] == "saved reading"
    assert second.get(f"/api/v1/ziwei/profiles/{unrelated}").status_code == 404
    assert c.get("/api/v1/billing/balance").status_code == 401
    c.cookies.clear()
    assert c.get("/api/v1/ziwei/profiles").status_code == 401
    c.cookies.set(auth.cookie_name(), old_cookie)
    assert c.get("/api/v1/ziwei/profiles").status_code == 401
    with Session(engine) as db:
        assert credits.balance(db, aid) == 43
        assert len(db.scalars(select(Account)).all()) == 2
        assert credits.balance(db, credits.resolve_account(db, "device-b").id) == 3


def test_wrong_expired_replay_and_hashed_secrets(harness):
    c, engine, outbox, _, _ = harness
    profile(c)
    data = challenge(c, outbox)
    with Session(engine) as db:
        row = db.get(AccountChallenge, data["challenge_id"])
        assert row.code_hash != data["code"] and len(row.code_hash) == 64
    assert verify(c, {**data, "code": "wrong"}).status_code == 400
    assert verify(c, data).status_code == 200
    assert verify(c, data).status_code == 400
    with Session(engine) as db:
        session = db.scalar(select(AccountSession))
        assert session.token_hash != c.cookies.get(auth.cookie_name())
        session.expires_at = datetime.utcnow() - timedelta(seconds=1); db.commit()
    assert c.get("/api/v1/ziwei/profiles").status_code == 401
    c.cookies.clear()
    data = challenge(c, outbox, "recover")
    with Session(engine) as db:
        db.get(AccountChallenge, data["challenge_id"]).expires_at = datetime.utcnow() - timedelta(seconds=1); db.commit()
    assert verify(c, data).status_code == 400


def test_bind_conflicts_and_no_checkout_email_proof(harness):
    c, engine, outbox, _, app = harness
    profile(c)
    with Session(engine) as db:
        a = credits.resolve_account(db, "legacy")
        a.email = "a@example.test"; db.commit()
    # A historical email cannot be recovered until explicitly verified.
    data = challenge(c, outbox, "recover")
    assert verify(c, data).status_code == 400
    assert verify(c, challenge(c, outbox)).status_code == 200
    b = TestClient(app, headers={"X-Recovery-Client": "1", "X-Device-Id": "device-b"})
    pid = profile(b)
    data = challenge(b, outbox)
    assert verify(b, data).status_code == 409
    assert verify(b, data).status_code == 409
    assert b.get(f"/api/v1/ziwei/profiles/{pid}").status_code == 200
    with Session(engine) as db:
        assert db.get(ZiweiProfileOwner, pid) is None
        assert len(db.scalars(select(Account)).all()) == 3


def test_bind_requires_original_device_and_preserves_ambiguous_records(harness):
    c, engine, outbox, _, _ = harness
    pid = profile(c)
    with Session(engine) as db:
        db.add(ZiweiProfile(name="legacy", gender="male", birth_date="2000-1-1", birth_time_index=1))
        db.add(AccountDevice(account_id=credits.resolve_account(db, "device-a").id, device_id="other-linked"))
        db.add(ZiweiProfile(name="other", device_id="other-linked", gender="male", birth_date="2000-1-1", birth_time_index=1))
        db.commit()
    data = challenge(c, outbox)
    assert c.post("/api/v1/account/verify", headers={"X-Device-Id": "wrong"}, json=data).status_code == 400
    assert verify(c, data).status_code == 200
    assert [p["id"] for p in c.get("/api/v1/ziwei/profiles").json()] == [pid]
    with Session(engine) as db:
        assert len(db.scalars(select(ZiweiProfile)).all()) == 3
        assert len(db.scalars(select(ZiweiProfileOwner)).all()) == 1


def test_rate_limits_and_email_normalization(harness):
    c, _, outbox, _, _ = harness
    data = challenge(c, outbox, email=" A@EXAMPLE.TEST ")
    assert outbox[-1][0] == "a@example.test"
    for _ in range(5):
        assert verify(c, {**data, "code": "wrong"}).status_code == 400
    assert verify(c, data).status_code == 429
    for _ in range(4):
        challenge(c, outbox, email="a@example.test")
    assert c.post("/api/v1/account/challenges", json={"email": "A@example.test", "purpose": "recover"}).status_code == 429


def test_logout_and_missing_corrupt_stale_device_storage(harness):
    c, _, outbox, _, app = harness
    pid = profile(c)
    assert verify(c, challenge(c, outbox)).status_code == 200
    for device in ("", "{corrupt}", "stale-device", "x" * 1000):
        assert c.get(f"/api/v1/ziwei/profiles/{pid}", headers={"X-Device-Id": device}).status_code == 200
    assert c.post("/api/v1/account/logout").status_code == 200
    assert c.get(f"/api/v1/ziwei/profiles/{pid}").status_code == 401
    b = TestClient(app, headers={"X-Recovery-Client": "1"})
    assert verify(b, challenge(b, outbox, "recover")).status_code == 200
    new_pid = profile(b, "new")
    assert b.delete(f"/api/v1/ziwei/profiles/{new_pid}").status_code == 200
    token = b.cookies.get(auth.cookie_name())
    assert b.post("/api/v1/account/logout-all").status_code == 200
    b.cookies.set(auth.cookie_name(), token)
    assert b.get("/api/v1/billing/balance").status_code == 401


def test_csrf_and_delivery_failure_and_disabled_routes(harness):
    c, engine, outbox, settings, app = harness
    assert verify(c, challenge(c, outbox)).status_code == 200
    assert c.post("/api/v1/account/logout", headers={"Origin": "https://evil.example"}).status_code == 403
    assert c.get("/api/v1/account/session", headers={"X-Recovery-Client": ""}).status_code == 403
    c.cookies.clear()
    app.dependency_overrides.pop(auth.get_sender)
    assert c.post("/api/v1/account/challenges", json={"email": "b@example.test", "purpose": "recover"}).status_code == 503
    with Session(engine) as db:
        assert db.scalar(select(AccountChallenge).where(AccountChallenge.email == "b@example.test")).consumed
    settings.account_recovery_enabled = False
    assert c.post("/api/v1/account/challenges", json={"email": "b@example.test", "purpose": "recover"}).status_code == 404


def test_recovery_csrf_is_rejected_before_consuming_code(harness):
    c, _, outbox, _, _ = harness
    data = challenge(c, outbox)
    for headers in ({"X-Recovery-Client": ""}, {"Origin": "https://untrusted.example.test"}):
        assert c.post("/api/v1/account/verify", json=data, headers=headers).status_code == 403
        assert c.post("/api/v1/account/challenges", json={"email": "a@example.test", "purpose": "recover"}, headers=headers).status_code == 403
    assert verify(c, data).status_code == 200


def test_disabled_enrollment_keeps_verified_ownership_closed(harness):
    c, engine, outbox, settings, _ = harness
    pid = profile(c)
    assert verify(c, challenge(c, outbox)).status_code == 200
    settings.account_recovery_enabled = False
    assert c.get(f"/api/v1/ziwei/profiles/{pid}").status_code == 200
    c.cookies.clear()
    assert c.get(f"/api/v1/ziwei/profiles/{pid}").status_code == 401
    assert c.get("/api/v1/billing/balance").status_code == 401
    with Session(engine) as db:
        with pytest.raises(Exception) as error:
            credits.resolve_account(db, "device-a")
        assert error.value.status_code == 401


def test_qian_stays_device_scoped_after_ziwei_recovery(harness):
    c, engine, outbox, _, app = harness
    with Session(engine) as db:
        row = QianReading(device_id="device-a", question="test", sign_id=1, response="private")
        db.add(row); db.commit(); rid = row.id
    before = c.get(f"/api/v1/qian/readings/{rid}")
    assert before.status_code == 200
    assert verify(c, challenge(c, outbox)).status_code == 200
    assert c.get(f"/api/v1/qian/readings/{rid}").json() == before.json()
    b = TestClient(app, headers={"X-Recovery-Client": "1", "X-Device-Id": "device-b"})
    assert verify(b, challenge(b, outbox, "recover")).status_code == 200
    assert b.get(f"/api/v1/qian/readings/{rid}").status_code == 404
    assert c.get(f"/api/v1/qian/readings/{rid}").status_code == 200
    with Session(engine) as db:
        assert db.get(QianReading, rid).device_id == "device-a"


def test_interrupted_migration_rolls_back_and_retry_preserves_balance(harness, monkeypatch):
    c, engine, outbox, _, _ = harness
    pid = profile(c)
    data = challenge(c, outbox)
    original = auth.issue_session
    def interrupted(*args):
        raise RuntimeError("simulated interruption before commit")
    monkeypatch.setattr(auth, "issue_session", interrupted)
    with pytest.raises(RuntimeError):
        verify(c, data)
    with Session(engine) as db:
        assert not db.get(AccountChallenge, data["challenge_id"]).consumed
        assert db.get(ZiweiProfileOwner, pid) is None
        assert db.scalar(select(VerifiedAccountEmail)) is None
        assert credits.balance(db, credits.resolve_account(db, "device-a").id) == 3
    monkeypatch.setattr(auth, "issue_session", original)
    assert verify(c, data).status_code == 200
    # Lost response: same code is not reusable. A new email challenge safely recovers.
    c.cookies.clear()
    assert verify(c, data).status_code == 400
    assert verify(c, challenge(c, outbox, "recover")).status_code == 200
    with Session(engine) as db:
        assert len(db.scalars(select(ZiweiProfileOwner)).all()) == 1
        assert len(db.scalars(select(CreditLedger)).all()) == 1


def test_concurrent_code_consumption_issues_one_session(harness):
    from concurrent.futures import ThreadPoolExecutor
    c, engine, outbox, _, app = harness
    data = challenge(c, outbox)
    def attempt(_):
        with TestClient(app, headers={"X-Recovery-Client": "1", "X-Device-Id": "device-a"}) as browser:
            return verify(browser, data).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(attempt, range(2)))
    assert sorted(statuses) == [200, 400]
    with Session(engine) as db:
        assert len(db.scalars(select(AccountSession)).all()) == 1


def test_secure_cookie_and_cross_account_order_isolation(harness):
    from app.models.entities import PaymentOrder
    c, engine, outbox, settings, app = harness
    profile(c)
    with Session(engine) as db:
        aid = credits.resolve_account(db, "device-a").id
        order = PaymentOrder(account_id=aid, pack="p10", credits=10, amount_cents=990,
                             stripe_session_id="cs_test_local", status="paid")
        db.add(order); db.commit(); oid = order.id
    settings.account_session_secure = True
    response = verify(c, challenge(c, outbox))
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=strict" in cookie
    c.cookies.clear(); settings.account_session_secure = False
    assert verify(c, challenge(c, outbox, "recover")).status_code == 200
    assert c.get(f"/api/v1/billing/orders/{oid}").status_code == 200
    b = TestClient(app, headers={"X-Recovery-Client": "1", "X-Device-Id": "device-b"})
    assert verify(b, challenge(b, outbox, email="b@example.test")).status_code == 200
    assert b.get(f"/api/v1/billing/orders/{oid}").status_code == 404
    assert b.get("/api/v1/ziwei/profiles").json() == []


def test_logout_remains_available_with_enrollment_disabled(harness):
    c, _, outbox, settings, _ = harness
    assert verify(c, challenge(c, outbox)).status_code == 200
    pending = challenge(c, outbox, "recover")
    settings.account_recovery_enabled = False
    assert c.get("/api/v1/account/session").json()["authenticated"]
    assert c.post("/api/v1/account/logout-all").status_code == 200
    settings.account_recovery_enabled = True
    assert verify(c, pending).status_code == 200  # logout revokes sessions, not mailbox access


def test_postgres_additive_migration_repeatability(harness):
    from pathlib import Path
    from app.models.entities import AccountRateLimit
    c, engine, outbox, _, _ = harness
    if engine.dialect.name != "postgresql":
        pytest.skip("DDL requires isolated PostgreSQL")
    pid = profile(c)
    with Session(engine) as db:
        aid = credits.resolve_account(db, "device-a").id
        credits.grant(db, aid, 10, "purchase")
    for model in (ZiweiProfileOwner, AccountChallenge, AccountSession, VerifiedAccountEmail, AccountRateLimit):
        model.__table__.drop(engine)
    sql = (Path(__file__).resolve().parents[1] / "scripts/migrations/20261106_account_recovery.sql").read_text()
    for _ in range(2):
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.exec_driver_sql(sql)
    assert verify(c, challenge(c, outbox)).status_code == 200
    assert c.get("/api/v1/billing/balance").json()["balance"] == 13
    assert c.get(f"/api/v1/ziwei/profiles/{pid}").status_code == 200


def test_logout_all_serializes_after_concurrent_recovery(harness):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    c, engine, outbox, _, app = harness
    assert verify(c, challenge(c, outbox)).status_code == 200
    data = challenge(c, outbox, "recover")
    original_identity = auth.identity
    logout_authorized = Event()
    release_logout = Event()
    # Pause logout after authentication, before its account lock. This explicitly
    # models an already authorized request overlapping a recovery commit.
    def paused_identity(request: Request, db: Session = Depends(get_db)):
        principal = original_identity(request, request.headers.get("x-device-id", ""), db)
        if request.url.path.endswith("logout-all"):
            # End the read transaction so SQLite can allow the recovery writer.
            db.rollback()
            logout_authorized.set()
            assert release_logout.wait(5)
        return principal
    app.dependency_overrides[auth.identity] = paused_identity
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(lambda: c.post("/api/v1/account/logout-all"))
        assert logout_authorized.wait(5)
        b = TestClient(app, headers={"X-Recovery-Client": "1"})
        try:
            assert verify(b, data).status_code == 200
        finally:
            release_logout.set()
        assert future.result(timeout=5).status_code == 200
    assert b.get("/api/v1/account/session").status_code == 401
    with Session(engine) as db:
        assert not db.scalars(select(AccountSession)).all()


def test_saved_legacy_bearer_can_restore_then_bind_but_not_reopen_verified_account(harness):
    c, _, outbox, _, app = harness
    pid = profile(c)
    b = TestClient(app, headers={"X-Recovery-Client": "1", "X-Device-Id": "new-browser"})
    assert b.get(f"/api/v1/ziwei/profiles/{pid}").status_code == 404
    b.headers["X-Device-Id"] = "device-a"  # explicit saved legacy-code restore
    assert b.get(f"/api/v1/ziwei/profiles/{pid}").status_code == 200
    assert verify(b, challenge(b, outbox)).status_code == 200
    assert b.get(f"/api/v1/ziwei/profiles/{pid}").status_code == 200
    b.cookies.clear()
    assert b.get(f"/api/v1/ziwei/profiles/{pid}").status_code == 401
    assert verify(b, challenge(b, outbox, "recover")).status_code == 200


@pytest.mark.parametrize("cookie_state", ["expired", "revoked", "unknown"])
@pytest.mark.parametrize("enrollment_enabled", [True, False])
def test_logout_clears_stale_cookie_idempotently(harness, cookie_state, enrollment_enabled):
    c, engine, outbox, settings, _ = harness
    assert verify(c, challenge(c, outbox)).status_code == 200
    with Session(engine) as db:
        row = db.scalar(select(AccountSession))
        if cookie_state == "expired":
            row.expires_at = datetime.utcnow() - timedelta(seconds=1)
        else:
            db.delete(row)
        db.commit()
    if cookie_state == "unknown":
        c.cookies.clear(); c.cookies.set(auth.cookie_name(), "unrecognized-token", domain="testserver.local", path="/")
    assert c.get("/api/v1/account/session").status_code == 401
    settings.account_recovery_enabled = enrollment_enabled
    for _ in range(2):
        response = c.post("/api/v1/account/logout")
        assert response.status_code == 200
        assert not c.cookies.get(auth.cookie_name())
        assert c.get("/api/v1/account/session").json() == {"authenticated": False}
    with Session(engine) as db:
        assert not db.scalars(select(AccountSession)).all()


def test_production_host_cookie_and_untrusted_cookie_names(harness):
    c, engine, outbox, settings, app = harness
    settings.account_session_secure = True
    settings.app_env = "production"
    secure = TestClient(app, base_url="https://testserver", headers={"X-Recovery-Client": "1", "X-Device-Id": "secure-device"})
    response = verify(secure, challenge(secure, outbox))
    cookie = response.headers["set-cookie"]
    assert cookie.startswith("__Host-oracle_session=")
    assert "Path=/;" in cookie and "Secure" in cookie and "HttpOnly" in cookie and "SameSite=strict" in cookie
    assert "Domain=" not in cookie
    token = secure.cookies.get(auth.COOKIE)
    assert secure.get("/api/v1/account/session").json()["authenticated"]
    for wrong_name in (auth.LOCAL_COOKIE, "oracle_session"):
        attacker = TestClient(app, base_url="https://testserver", headers={"X-Recovery-Client": "1"})
        attacker.cookies.set(wrong_name, token, domain="testserver.local", path="/")
        assert attacker.get("/api/v1/account/session").json() == {"authenticated": False}
        cleared = attacker.post("/api/v1/account/logout")
        assert cleared.status_code == 200
        assert attacker.get("/api/v1/account/session").json() == {"authenticated": False}
    logout = secure.post("/api/v1/account/logout")
    secure_deletion = next(h for h in logout.headers.get_list("set-cookie") if h.startswith(auth.COOKIE + "="))
    assert "Path=/;" in secure_deletion and "Secure" in secure_deletion and "Max-Age=0" in secure_deletion
    assert "Domain=" not in secure_deletion
    settings.account_session_secure = False
    assert c.post("/api/v1/account/challenges", json={"email":"new@example.test", "purpose":"recover"}).status_code == 503


@pytest.mark.parametrize("wrong_name", ["oracle_session", auth.LOCAL_COOKIE])
def test_parent_domain_cookie_cannot_authenticate_or_trap_browser(harness, wrong_name):
    _, _, outbox, settings, app = harness
    settings.account_session_secure = True
    settings.app_env = "production"
    owner = TestClient(app, base_url="https://portal.leipan.cc", headers={"X-Recovery-Client": "1", "X-Device-Id": "owner-device"})
    pid = profile(owner)
    assert verify(owner, challenge(owner, outbox)).status_code == 200
    token = owner.cookies.get(auth.COOKIE)
    visitor = TestClient(app, base_url="https://portal.leipan.cc", headers={"X-Recovery-Client": "1", "X-Device-Id": "visitor-device"})
    # A real cookie-jar parent-domain cookie is sent to the portal subdomain and
    # survives a host-only deletion. Even a valid token under this name is ignored.
    visitor.cookies.set(wrong_name, token, domain=".leipan.cc", path="/")
    response = visitor.get("/api/v1/account/session")
    assert wrong_name in response.request.headers["cookie"]
    assert response.json() == {"authenticated": False}
    assert visitor.get(f"/api/v1/ziwei/profiles/{pid}").status_code == 404
    own_pid = profile(visitor)
    assert visitor.post("/api/v1/account/logout").status_code == 200
    assert visitor.cookies.get(wrong_name, domain=".leipan.cc", path="/") == token
    assert visitor.get("/api/v1/account/session").json() == {"authenticated": False}
    assert visitor.get(f"/api/v1/ziwei/profiles/{own_pid}").status_code == 200
    visitor.headers["X-Device-Id"] = "owner-device"
    assert visitor.get(f"/api/v1/ziwei/profiles/{pid}").status_code == 401
    assert visitor.get("/api/v1/billing/balance").status_code == 401
    # Invalid current-mode cookies still fail closed; wrong names cannot mask them.
    visitor.cookies.set(auth.COOKIE, "invalid", domain="portal.leipan.cc", path="/")
    assert visitor.get("/api/v1/account/session").status_code == 401
    assert visitor.post("/api/v1/account/logout").status_code == 200
    assert visitor.get("/api/v1/account/session").json() == {"authenticated": False}
    assert verify(visitor, challenge(visitor, outbox, "recover")).status_code == 200
    assert visitor.get(f"/api/v1/ziwei/profiles/{pid}").status_code == 200

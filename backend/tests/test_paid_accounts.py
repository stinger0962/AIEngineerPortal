"""Fresh accounts: fake email and model output only; no external communication."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateSchema, DropSchema
from uuid import uuid4
import os
import socket
from sqlalchemy.orm import Session

from app import paid_main
from app.api.v1.routes import paid_accounts, qian
from app.core.config import get_settings
from app.models.entities import (Account, AccountDevice, CreditLedger, QianReading,
                                ZiweiProfile, ZiweiConversation, ZiweiMessage)
from app.models.paid_accounts import (PaidChallenge, PaidQianOwner, PaidRateLimit,
                                      PaidSession, PaidVerifiedEmail, PaidZiweiOwner)
from app.services import paid_accounts as auth, credits

HEADERS = {"X-Paid-Client": "1", "Origin": "https://paid.test"}
PROFILE = {"name": "测试", "gender": "female", "birth_date": "1990-1-1", "birth_time_index": 1}


@pytest.fixture
def product(tmp_path, monkeypatch):
    settings = get_settings()
    admin, schema = None, None
    paid_url = f"sqlite:///{tmp_path / 'paid.db'}"
    postgres_url = os.environ.get("ZIWEI_QA_POSTGRES_URL")
    if postgres_url:
        target = make_url(postgres_url)
        if target.host != "127.0.0.1" or target.port != 55432 or target.database != "ziwei_qa":
            raise ValueError("Paid QA PostgreSQL must be isolated 127.0.0.1:55432/ziwei_qa")
        schema = "paid_qa_" + uuid4().hex
        admin = create_engine(postgres_url)
        with admin.begin() as connection:
            connection.execute(CreateSchema(schema))
        paid_url = target.update_query_dict({"options": f"-csearch_path={schema}"}).render_as_string(hide_password=False)
    for field, value in {
        "database_url": f"sqlite:///{tmp_path / 'portal.db'}",
        "paid_database_url": paid_url,
        "paid_accounts_enabled": True, "paid_session_secure": True,
        "cors_origins": "https://paid.test", "app_env": "test",
        "stripe_secret_key": "", "stripe_test_enabled": False,
        "anthropic_api_key": "", "openai_api_key": "", "minimax_api_key": "",
        "ziwei_claim_code": "", "ziwei_auto_adopt": False,
    }.items():
        monkeypatch.setattr(settings, field, value)
    app = paid_main.create_app()
    outbox = []
    app.dependency_overrides[auth.get_sender] = lambda: lambda email, code: outbox.append((email, code))
    def no_external_connections(*args, **kwargs):
        raise AssertionError("Paid account QA forbids external network calls")
    monkeypatch.setattr(socket.socket, "connect", no_external_connections)
    monkeypatch.setattr(socket.socket, "connect_ex", no_external_connections)
    # psycopg uses C-level libpq sockets; its only permitted URL was validated above.
    try:
        with TestClient(app, base_url="https://paid.test", headers=HEADERS) as client:
            yield SimpleNamespace(app=app, client=client, outbox=outbox, settings=settings, engine=app.state.paid_engine)
    finally:
        if admin is not None:
            with admin.begin() as connection:
                connection.execute(DropSchema(schema, cascade=True))
            admin.dispose()


def fresh_client(product):
    return TestClient(product.app, base_url="https://paid.test", headers=HEADERS)


def challenge(product, client=None, email="user@example.com"):
    client = client or product.client
    response = client.post("/api/v1/account/challenges", json={"email": email})
    assert response.status_code == 200, response.text
    assert set(response.json()) == {"challenge_id", "expires_in"}
    assert response.json()["expires_in"] == 900
    return {"challenge_id": response.json()["challenge_id"], "code": product.outbox[-1][1]}


def login(product, client=None, email="user@example.com"):
    client = client or product.client
    payload = challenge(product, client, email)
    response = client.post("/api/v1/account/verify", json=payload)
    assert response.status_code == 200, response.text
    assert response.json() == {"authenticated": True}
    return response, payload


def count(product, model):
    with Session(product.engine) as db:
        return db.scalar(select(func.count()).select_from(model))


def test_first_verification_creates_one_fresh_account_and_credit_grant(product):
    response, payload = login(product, email=" User@Example.COM ")
    assert product.outbox[-1][0] == "user@example.com"
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(auth.COOKIE + "=")
    assert all(part in cookie for part in ("HttpOnly", "Secure", "SameSite=strict", "Path=/", "Max-Age=2592000"))
    assert "Domain=" not in cookie
    token = product.client.cookies.get(auth.COOKIE)
    assert len(token) >= 43 and token not in response.text
    with Session(product.engine) as db:
        row = db.get(PaidChallenge, payload["challenge_id"])
        assert row.code_hash == auth.digest(payload["code"]) and row.code_hash != payload["code"] and row.consumed
        assert db.get(PaidSession, auth.digest(token)) is not None
        assert db.get(PaidVerifiedEmail, "user@example.com").account_id == db.scalar(select(Account.id))
        assert db.scalar(select(func.sum(CreditLedger.delta))) == product.settings.ziwei_free_credits
    assert count(product, AccountDevice) == 0
    assert product.client.get("/api/v1/account/session").json() == {"authenticated": True, "enabled": True, "account_id": 1}
    assert product.client.get("/api/v1/billing/balance").json()["balance"] == product.settings.ziwei_free_credits


def test_login_on_another_browser_restores_ziwei_qian_and_shared_credits(product):
    login(product)
    old = product.client
    profile = old.post("/api/v1/ziwei/profiles", json=PROFILE).json()
    with Session(product.engine) as db:
        account_id = db.get(PaidVerifiedEmail, "user@example.com").account_id
        reading = QianReading(question="private", sign_id=1, response="saved answer")
        db.add(reading)
        db.flush()
        db.add(PaidQianOwner(reading_id=reading.id, account_id=account_id))
        conv = ZiweiConversation(profile_id=profile["id"], title="saved chat")
        db.add(conv)
        db.flush()
        db.add(ZiweiMessage(conversation_id=conv.id, role="assistant", content="private chat"))
        db.add(CreditLedger(account_id=account_id, delta=7, reason="test"))
        db.commit()
        reading_id, conv_id = reading.id, conv.id
        assert db.get(ZiweiProfile, profile["id"]).device_id is None
    newer = fresh_client(product)
    login(product, newer)
    assert newer.get("/api/v1/billing/balance").json()["balance"] == product.settings.ziwei_free_credits + 7
    assert [p["id"] for p in newer.get("/api/v1/ziwei/profiles").json()] == [profile["id"]]
    assert newer.get(f"/api/v1/ziwei/conversations/{conv_id}/messages").json()[0]["content"] == "private chat"
    assert newer.get(f"/api/v1/qian/readings/{reading_id}").json()["response"] == "saved answer"
    assert old.get("/api/v1/account/session").status_code == 401
    assert count(product, Account) == 1
    assert count(product, PaidSession) == 1
    assert count(product, CreditLedger) == 2


def test_accounts_and_device_ids_cannot_cross_access(product):
    login(product)
    profile = product.client.post("/api/v1/ziwei/profiles", json=PROFILE).json()
    with Session(product.engine) as db:
        account_id = db.get(PaidVerifiedEmail, "user@example.com").account_id
        reading = QianReading(question="private", sign_id=1)
        db.add(reading); db.flush()
        db.add(PaidQianOwner(reading_id=reading.id, account_id=account_id))
        conv = ZiweiConversation(profile_id=profile["id"])
        db.add(conv); db.flush()
        db.commit()
        rid, cid = reading.id, conv.id
    other = fresh_client(product)
    login(product, other, "other@example.com")
    for route in (f"/ziwei/profiles/{profile['id']}", f"/ziwei/profiles/{profile['id']}/conversations",
                  f"/ziwei/conversations/{cid}/messages", f"/qian/readings/{rid}"):
        assert other.get("/api/v1" + route, headers={"X-Device-Id": f"paid-account:{account_id}"}).status_code == 404
    assert other.get("/api/v1/ziwei/profiles").json() == []
    assert other.get("/api/v1/qian/readings").json() == []
    assert other.put(f"/api/v1/ziwei/profiles/{profile['id']}", json={"name": "stolen"}).status_code == 404
    assert other.delete(f"/api/v1/ziwei/profiles/{profile['id']}").status_code == 404
    anon = fresh_client(product)
    assert anon.get("/api/v1/ziwei/profiles", headers={"X-Device-Id": f"paid-account:{account_id}"}).status_code == 401
    assert anon.get("/api/v1/billing/balance", headers={"X-Device-Id": "old-device"}).status_code == 401
    assert anon.post("/api/v1/ziwei/tts", json={"text": "test"}).status_code == 401


def test_existing_contact_email_and_device_data_are_never_adopted(product):
    with Session(product.engine) as db:
        account = Account(email="user@example.com")
        db.add(account); db.flush()
        old_id = account.id
        db.add(AccountDevice(account_id=old_id, device_id="old-device"))
        db.add(CreditLedger(account_id=old_id, delta=99, reason="test"))
        profile = ZiweiProfile(device_id="old-device", **PROFILE)
        db.add(profile)
        db.add(QianReading(device_id="old-device", question="old", sign_id=1))
        db.commit()
    login(product)
    assert product.client.get("/api/v1/billing/balance", headers={"X-Device-Id": "old-device"}).json()["balance"] == product.settings.ziwei_free_credits
    assert product.client.get("/api/v1/ziwei/profiles").json() == []
    assert product.client.get("/api/v1/qian/readings").json() == []
    with Session(product.engine) as db:
        assert db.get(PaidVerifiedEmail, "user@example.com").account_id != old_id
        assert credits.balance(db, old_id) == 99
    assert product.client.post("/api/v1/ziwei/claim", json={"code": "old"}).status_code == 404
    assert product.client.post("/api/v1/account/challenges", json={"email": "new@example.com", "purpose": "bind"}).status_code == 422


def test_wrong_expired_replayed_and_mismatched_codes(product):
    payload = challenge(product)
    wrong = dict(payload, code="wrong")
    assert product.client.post("/api/v1/account/verify", json=wrong).status_code == 400
    assert product.client.post("/api/v1/account/verify", json=payload).status_code == 200
    assert product.client.post("/api/v1/account/verify", json=payload).status_code == 400
    expired = challenge(product, email="expired@example.com")
    with Session(product.engine) as db:
        db.get(PaidChallenge, expired["challenge_id"]).expires_at = datetime.utcnow() - timedelta(seconds=1)
        db.commit()
    assert product.client.post("/api/v1/account/verify", json=expired).status_code == 400
    other = challenge(product, email="other@example.com")
    assert product.client.post("/api/v1/account/verify", json=dict(other, code=payload["code"])).status_code == 400
    assert count(product, Account) == 1


def test_email_failure_consumes_challenge_and_never_returns_code(product):
    product.app.dependency_overrides.pop(auth.get_sender)
    response = product.client.post("/api/v1/account/challenges", json={"email": "user@example.com"})
    assert response.status_code == 503 and response.json() == {"detail": "Email delivery unavailable"}
    with Session(product.engine) as db:
        rows = db.scalars(select(PaidChallenge)).all()
        assert len(rows) == 1 and rows[0].consumed
    assert count(product, Account) == 0


def test_storage_failure_rolls_back_all_issuance_and_allows_retry(product, monkeypatch):
    payload = challenge(product)
    real_issue = auth.issue_session
    monkeypatch.setattr(auth, "issue_session", lambda *a: (_ for _ in ()).throw(ValueError("injected failure")))
    client = TestClient(product.app, base_url="https://paid.test", headers=HEADERS, raise_server_exceptions=False)
    assert client.post("/api/v1/account/verify", json=payload).status_code == 500
    assert count(product, Account) == 0
    assert count(product, PaidVerifiedEmail) == 0
    assert count(product, CreditLedger) == 0
    with Session(product.engine) as db:
        assert not db.get(PaidChallenge, payload["challenge_id"]).consumed
    monkeypatch.setattr(auth, "issue_session", real_issue)
    assert client.post("/api/v1/account/verify", json=payload).status_code == 200
    assert count(product, Account) == 1


@pytest.mark.parametrize("endpoint, method, body", [
    ("/account/challenges", "post", {"email": "a@example.com"}),
    ("/account/verify", "post", {"challenge_id": "fake", "code": "fake"}),
    ("/account/session", "get", None),
    ("/account/logout", "post", None),
    ("/account/logout-all", "post", None),
    ("/ziwei/profiles", "get", None),
    ("/qian/readings", "get", None),
    ("/billing/balance", "get", None),
])
def test_csrf_and_foreign_origin_rejected(product, endpoint, method, body):
    for headers in ({"Origin": "https://paid.test"}, {"X-Paid-Client": "1", "Origin": "https://evil.test"},
                    {"X-Paid-Client": "1", "Origin": "null"}):
        client = TestClient(product.app, base_url="https://paid.test", headers=headers)
        response = client.request(method, "/api/v1" + endpoint, json=body)
        assert response.status_code == 403
        assert response.headers["cache-control"] == "no-store"


def test_logout_revokes_current_and_clears_stale_cookie(product):
    login(product)
    token = product.client.cookies.get(auth.COOKIE)
    assert product.client.post("/api/v1/account/logout").status_code == 200
    assert product.client.get("/api/v1/account/session").json()["authenticated"] is False
    replay = fresh_client(product)
    replay.cookies.set(auth.COOKIE, token)
    assert replay.get("/api/v1/billing/balance").status_code == 401
    assert replay.post("/api/v1/account/logout").status_code == 200
    assert count(product, PaidSession) == 0


def test_logout_all_revokes_all_tokens_even_if_signin_disabled(product):
    login(product)
    with Session(product.engine) as db:
        account_id = db.get(PaidVerifiedEmail, "user@example.com").account_id
        token = auth.issue_session(db, account_id)
        db.commit()
    product.settings.paid_accounts_enabled = False
    assert product.client.post("/api/v1/account/logout-all").status_code == 200
    assert count(product, PaidSession) == 0
    product.settings.paid_accounts_enabled = True
    replay = fresh_client(product)
    replay.cookies.set(auth.COOKIE, token)
    assert replay.get("/api/v1/qian/readings").status_code == 401


def test_expired_session_and_wrong_cookie_names(product):
    login(product)
    with Session(product.engine) as db:
        db.scalars(select(PaidSession)).first().expires_at = datetime.utcnow() - timedelta(seconds=1)
        db.commit()
    assert product.client.get("/api/v1/account/session").status_code == 401
    assert product.client.post("/api/v1/account/logout").status_code == 200
    for name in (auth.LOCAL_COOKIE, "oracle_session", "__Host-oracle_session"):
        product.client.cookies.set(name, "untrusted")
    assert product.client.get("/api/v1/account/session").json()["authenticated"] is False
    assert product.client.get("/api/v1/billing/balance").status_code == 401


def test_disabled_accounts_never_fall_back_to_device_identity(product):
    login(product)
    product.settings.paid_accounts_enabled = False
    assert product.client.get("/api/v1/account/session").json() == {"authenticated": True, "enabled": False, "account_id": 1}
    assert product.client.post("/api/v1/account/challenges", json={"email": "a@example.com"}).status_code == 503
    assert product.client.post("/api/v1/account/verify", json={"challenge_id": "fake", "code": "fake"}).status_code == 503
    for path in ("/ziwei/profiles", "/qian/readings", "/billing/balance"):
        assert product.client.get("/api/v1" + path, headers={"X-Device-Id": "old-device"}).status_code == 503
    assert product.client.post("/api/v1/account/logout").status_code == 200


def test_rate_limits_persist_failed_attempts_and_ignore_forwarded_ip(product):
    payload = challenge(product)
    for _ in range(5):
        assert product.client.post("/api/v1/account/verify", json=dict(payload, code="wrong")).status_code == 400
    assert product.client.post("/api/v1/account/verify", json=payload).status_code == 429
    # New challenge, but normalized same mailbox remains subject to its own limit.
    for _ in range(4):
        challenge(product, email="USER@example.com")
    response = product.client.post("/api/v1/account/challenges", json={"email": "user@example.com"}, headers={"X-Forwarded-For": "203.0.113.99"})
    assert response.status_code == 429 and response.headers["retry-after"] == "3600"
    with Session(product.engine) as db:
        assert all("@" not in row.key for row in db.scalars(select(PaidRateLimit)))


def test_ip_start_limit_across_mailboxes(product):
    for index in range(20):
        response = product.client.post("/api/v1/account/challenges", json={"email": f"user{index}@example.com"},
                                      headers={"X-Forwarded-For": f"203.0.113.{index}"})
        assert response.status_code == 200
    assert product.client.post("/api/v1/account/challenges", json={"email": "extra@example.com"}).status_code == 429


def test_simultaneous_consumption_is_single_use(product):
    payload = challenge(product)
    def verify():
        return fresh_client(product).post("/api/v1/account/verify", json=payload).status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(lambda _: verify(), range(2)))
    assert sorted(statuses) == [200, 400]
    assert count(product, Account) == count(product, PaidVerifiedEmail) == count(product, CreditLedger) == count(product, PaidSession) == 1


def test_concurrent_new_challenges_do_not_duplicate_accounts_or_credits(product):
    payloads = [challenge(product), challenge(product)]
    def verify(payload):
        client = fresh_client(product)
        response = client.post("/api/v1/account/verify", json=payload)
        if response.status_code == 409:
            response = client.post("/api/v1/account/verify", json=payload)
        return response.status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(verify, payloads))
    assert statuses == [200, 200]
    assert count(product, Account) == count(product, CreditLedger) == count(product, PaidSession) == 1


def test_qian_stream_saves_account_owner_without_device_and_can_recover(product, monkeypatch):
    class FakeStream:
        text_stream = ["一切顺利。"]
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def get_final_message(self):
            return SimpleNamespace(usage=SimpleNamespace(input_tokens=4, output_tokens=5))
    fake_client = SimpleNamespace(messages=SimpleNamespace(stream=lambda **kw: FakeStream()))
    monkeypatch.setattr(qian, "AIService", lambda: SimpleNamespace(is_available=True, client=fake_client))
    login(product)
    response = product.client.post("/api/v1/qian/oracle/stream", json={"question": "测试", "sign_id": 7})
    assert response.status_code == 200 and '"type": "done"' in response.text
    with Session(product.engine) as db:
        reading = db.scalar(select(QianReading))
        assert reading.device_id is None
        assert db.get(PaidQianOwner, reading.id).account_id == db.get(PaidVerifiedEmail, "user@example.com").account_id
    assert len(product.client.get("/api/v1/qian/readings").json()) == 1


def test_profile_delete_removes_owner_without_affecting_account(product):
    login(product)
    profile_id = product.client.post("/api/v1/ziwei/profiles", json=PROFILE).json()["id"]
    assert product.client.delete(f"/api/v1/ziwei/profiles/{profile_id}").status_code == 200
    assert count(product, PaidZiweiOwner) == 0
    assert count(product, Account) == 1


def test_retention_removes_only_expired_auth_records(product):
    login(product)
    with Session(product.engine) as db:
        now = datetime.utcnow()
        db.add(PaidSession(token_hash="expired", account_id=db.scalar(select(Account.id)), expires_at=now - timedelta(seconds=1)))
        db.add(PaidChallenge(id="expired", code_hash="hash", email="old@example.com", expires_at=now-timedelta(days=2)))
        db.add(PaidRateLimit(key="expired", count=1, expires_at=now-timedelta(seconds=1)))
        db.commit()
        auth.purge_expired_auth_records(db, now=now)
        db.commit()
        assert db.get(PaidSession, "expired") is None
        assert db.get(PaidChallenge, "expired") is None
        assert db.get(PaidRateLimit, "expired") is None
    assert count(product, Account) == count(product, CreditLedger) == count(product, PaidSession) == 1


def test_portal_import_does_not_register_paid_tables():
    import os
    import subprocess
    import sys
    from pathlib import Path
    result = subprocess.run([sys.executable, "-c", "from app.main import app; from app.db.base import Base; "
                             "assert not any(name.startswith('paid_') for name in Base.metadata.tables)"],
                            env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])},
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_local_cookie_and_insecure_production_configuration(product):
    product.settings.paid_session_secure = False
    product.settings.app_env = "test"
    response, _ = login(product)
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(auth.LOCAL_COOKIE + "=") and "Secure" not in cookie
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie
    product.settings.app_env = "production"
    with pytest.raises(RuntimeError, match="Insecure paid session"):
        paid_main.validate_configuration(product.settings)
    assert product.client.post("/api/v1/account/challenges", json={"email": "other@example.com"}).status_code == 503


def test_missing_or_fake_identity_cannot_read_orders(product):
    from app.models.entities import PaymentOrder
    login(product)
    with Session(product.engine) as db:
        aid = db.get(PaidVerifiedEmail, "user@example.com").account_id
        order = PaymentOrder(account_id=aid, pack="p10", credits=10, amount_cents=990, stripe_session_id="cs_test_mock")
        db.add(order); db.commit()
        oid = order.id
    assert product.client.get(f"/api/v1/billing/orders/{oid}").status_code == 200
    other = fresh_client(product)
    login(product, other, "other@example.com")
    assert other.get(f"/api/v1/billing/orders/{oid}", headers={"X-Device-Id": str(aid)}).status_code == 404
    assert fresh_client(product).get(f"/api/v1/billing/orders/{oid}").status_code == 401


@pytest.mark.parametrize("email", ["not-an-email", "a@@example.com", "@example.com", "a@", "a\r\nBcc:b@example.com", "a b@example.com", "<a>@example.com"])
def test_invalid_email_never_calls_sender(product, email):
    assert product.client.post("/api/v1/account/challenges", json={"email": email}).status_code == 422
    assert product.outbox == []


def test_failed_login_does_not_revoke_current_session(product):
    login(product)
    token = product.client.cookies.get(auth.COOKIE)
    payload = challenge(product)
    assert product.client.post("/api/v1/account/verify", json=dict(payload, code="wrong")).status_code == 400
    assert product.client.cookies.get(auth.COOKIE) == token
    assert product.client.get("/api/v1/account/session").json()["authenticated"] is True


def test_tampered_session_and_header_do_not_authenticate(product):
    client = fresh_client(product)
    client.cookies.set(auth.COOKIE, "paid-account:1")
    assert client.get("/api/v1/ziwei/profiles", headers={"X-Device-Id": "paid-account:1"}).status_code == 401


def test_verify_ip_limit_counts_unknown_challenges(product):
    for index in range(40):
        response = product.client.post("/api/v1/account/verify", json={"challenge_id": f"unknown{index}", "code": "wrong"})
        assert response.status_code == 400
    assert product.client.post("/api/v1/account/verify", json={"challenge_id": "unknown-final", "code": "wrong"}).status_code == 429


def test_session_exposes_nonsecret_identity_for_account_switch_detection(product):
    assert product.client.get("/api/v1/account/session").json() == {
        "authenticated": False, "enabled": True, "account_id": None}
    login(product)
    first = product.client.get("/api/v1/account/session").json()
    assert isinstance(first["account_id"], int)
    login(product, email="other@example.com")
    second = product.client.get("/api/v1/account/session").json()
    assert isinstance(second["account_id"], int) and second["account_id"] != first["account_id"]
    assert set(second) == {"authenticated", "enabled", "account_id"}
    assert product.client.post("/api/v1/account/logout").status_code == 200
    assert product.client.get("/api/v1/account/session").json()["account_id"] is None

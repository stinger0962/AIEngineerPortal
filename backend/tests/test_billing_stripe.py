from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.entities import Account, AccountDevice, BillingRequest, CreditLedger, PaymentOrder
from app.services import credits as credits_svc
from app.services import stripe_billing


@pytest.fixture
def db(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'billing.db'}", connect_args={"timeout": 10})
    for m in (Account, AccountDevice, CreditLedger, PaymentOrder, BillingRequest):
        m.__table__.create(bind=engine)
    settings = SimpleNamespace(stripe_test_enabled=True, stripe_secret_key="sk_test_mock",
        stripe_webhook_secret="whsec_mock", stripe_test_base_url="http://localhost:3000",
        public_base_url="https://portal.leipan.cc")
    monkeypatch.setattr(stripe_billing, "get_settings", lambda: settings)
    with Session(engine) as session:
        yield session
    engine.dispose()


def checkout(db, monkeypatch):
    import stripe
    calls = []
    def create(**kw):
        calls.append(kw)
        return SimpleNamespace(id="cs_test_mock", url="https://checkout.stripe.com/mock", livemode=False)
    monkeypatch.setattr(stripe.checkout.Session, "create", create)
    acct = credits_svc.resolve_account(db, "device-a")
    result = stripe_billing.create_checkout_session(db, acct.id, "p10", "checkout-key")
    return acct, result, calls


def event(order, **changes):
    obj = dict(id=order.stripe_session_id, livemode=False, mode="payment", payment_status="paid",
               amount_total=order.amount_cents, currency=order.currency,
               metadata={"order_id": str(order.id), "account_id": str(order.account_id)})
    obj.update(changes)
    return {"type": "checkout.session.completed", "livemode": False, "data": {"object": obj}}


def test_checkout_retry_and_conflict(db, monkeypatch):
    acct, result, calls = checkout(db, monkeypatch)
    assert result["order_id"] and result["mode"] == "test"
    assert calls[0]["line_items"][0]["price_data"]["unit_amount"] == 990
    assert calls[0]["line_items"][0]["price_data"]["currency"] == "cny"
    assert calls[0]["success_url"].startswith("http://localhost:3000/")
    assert stripe_billing.create_checkout_session(db, acct.id, "p10", "checkout-key") == result
    assert len(calls) == 1
    with pytest.raises(ValueError, match="idempotency_conflict"):
        stripe_billing.create_checkout_session(db, acct.id, "p40", "checkout-key")


def test_timeout_retry_reuses_stripe_key(db, monkeypatch):
    import stripe
    acct = credits_svc.resolve_account(db, "device-a")
    keys = []
    def timeout(**kw):
        keys.append(kw["idempotency_key"])
        raise TimeoutError()
    monkeypatch.setattr(stripe.checkout.Session, "create", timeout)
    for _ in range(2):
        with pytest.raises(TimeoutError):
            stripe_billing.create_checkout_session(db, acct.id, "p10", "checkout-key")
    assert keys[0] == keys[1]
    assert len(db.scalars(select(PaymentOrder)).all()) == 1


@pytest.mark.parametrize("field,value", [("stripe_secret_key", "sk_live_mock"),
    ("stripe_test_enabled", False), ("stripe_test_base_url", "https://portal.leipan.cc"),
    ("stripe_test_base_url", "")])
def test_test_mode_guards(db, field, value):
    setattr(stripe_billing.get_settings(), field, value)
    assert not stripe_billing.is_configured()


@pytest.mark.parametrize("changes,status", [({"amount_total": 1}, "payment_mismatch"),
    ({"currency": "usd"}, "payment_mismatch"), ({"metadata": {}}, "payment_mismatch"),
    ({"livemode": True}, "live_or_unknown_mode_rejected"),
    ({"payment_status": "unpaid"}, "not_paid_yet")])
def test_invalid_event_never_grants(db, monkeypatch, changes, status):
    acct, result, _ = checkout(db, monkeypatch)
    before = credits_svc.balance(db, acct.id)
    assert stripe_billing.process_event(db, event(db.get(PaymentOrder, result["order_id"]), **changes)) == status
    assert credits_svc.balance(db, acct.id) == before


def test_concurrent_webhooks_grant_once(db, monkeypatch):
    acct, result, _ = checkout(db, monkeypatch)
    account_id = acct.id
    before = credits_svc.balance(db, account_id)
    payload = event(db.get(PaymentOrder, result["order_id"]))
    engine = db.get_bind()
    db.rollback()
    def deliver(_):
        with Session(engine) as session:
            return stripe_billing.process_event(session, payload)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(deliver, range(4)))
    assert results.count("credited") == 1
    assert credits_svc.balance(db, account_id) == before + 10
    assert len(db.scalars(select(CreditLedger).where(CreditLedger.reason == "purchase")).all()) == 1


def test_fulfillment_failure_rolls_back_status(db, monkeypatch):
    _, result, _ = checkout(db, monkeypatch)
    order_id = result["order_id"]
    payload = event(db.get(PaymentOrder, order_id))
    original = db.commit
    monkeypatch.setattr(db, "commit", lambda: (_ for _ in ()).throw(RuntimeError("database failure")))
    with pytest.raises(RuntimeError):
        stripe_billing.process_event(db, payload)
    db.rollback()
    monkeypatch.setattr(db, "commit", original)
    assert db.get(PaymentOrder, order_id).status == "pending"
    assert stripe_billing.process_event(db, payload) == "credited"


def test_concurrent_consumption_cannot_overdraw(db):
    acct = credits_svc.resolve_account(db, "device-a")
    account_id = acct.id
    initial = credits_svc.balance(db, account_id)
    engine = db.get_bind()
    db.rollback()
    def consume(_):
        with Session(engine) as session:
            return credits_svc.consume_one(session, account_id)
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(consume, range(initial + 5)))
    assert sum(results) == initial
    assert credits_svc.balance(db, account_id) == 0


def test_failed_generation_transaction_rolls_back(db):
    acct = credits_svc.resolve_account(db, "device-a")
    account_id = acct.id
    before = credits_svc.balance(db, account_id)
    assert credits_svc.consume_one(db, account_id, commit=False)
    db.rollback()
    assert credits_svc.balance(db, account_id) == before


def test_order_status_ownership_and_balance_contract(db, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.v1.routes.billing import router
    from app.db.session import get_db
    _, result, _ = checkout(db, monkeypatch)
    engine = db.get_bind()
    db.rollback()
    app = FastAPI()
    app.include_router(router)
    def isolated_db():
        with Session(engine) as session:
            yield session
    app.dependency_overrides[get_db] = isolated_db
    client = TestClient(app)
    path = f"/billing/orders/{result['order_id']}"
    assert client.get(path).status_code == 404
    assert client.get(path, headers={"X-Device-Id": "stranger"}).status_code == 404
    response = client.get(path, headers={"X-Device-Id": "device-a"})
    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert response.json()["amount_cents"] == 990
    balance = client.get("/billing/balance", headers={"X-Device-Id": "device-a"}).json()
    assert balance["mode"] == "test" and balance["currency"] == "cny"
    assert [p["amount_cents"] for p in balance["packs"]] == [990, 2990, 6800]
    assert client.post("/billing/checkout", headers={"X-Device-Id": "device-a"}, json={"pack": "p10"}).status_code == 400


def test_signature_verification_uses_raw_body(db):
    import hashlib
    import hmac
    import json
    import time
    payload = json.dumps({"id": "evt_mock", "object": "event", "type": "test", "livemode": False}).encode()
    timestamp = int(time.time())
    digest = hmac.new(b"whsec_mock", str(timestamp).encode() + b"." + payload, hashlib.sha256).hexdigest()
    signature = f"t={timestamp},v1={digest}"
    assert stripe_billing.verify_event(payload, signature)["id"] == "evt_mock"
    with pytest.raises(Exception):
        stripe_billing.verify_event(payload + b" ", signature)


def test_unknown_checkout_is_retryable(db):
    payload = {"type": "checkout.session.completed", "livemode": False,
               "data": {"object": {"id": "cs_unknown", "livemode": False}}}
    assert stripe_billing.process_event(db, payload) == "order_not_found"


def test_unresolved_old_checkout_is_not_recreated(db, monkeypatch):
    import stripe
    from datetime import datetime, timedelta
    acct = credits_svc.resolve_account(db, "device-a")
    monkeypatch.setattr(stripe.checkout.Session, "create", lambda **kw: (_ for _ in ()).throw(TimeoutError()))
    with pytest.raises(TimeoutError):
        stripe_billing.create_checkout_session(db, acct.id, "p10", "checkout-key")
    order = db.scalar(select(PaymentOrder))
    order.created_at = datetime.utcnow() - timedelta(hours=24)
    db.commit()
    with pytest.raises(ValueError, match="checkout_reconciliation_required"):
        stripe_billing.create_checkout_session(db, acct.id, "p10", "checkout-key")


def test_checkout_contention_is_bounded_and_retry_preserves_key(db, monkeypatch):
    from time import monotonic
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.v1.routes.billing import router
    from app.db.session import get_db
    from app.core.config import get_settings
    import stripe
    monkeypatch.setattr(get_settings(), "billing_lock_timeout_ms", 50)
    acct = credits_svc.resolve_account(db, "device-a")
    account_id = acct.id
    before = credits_svc.balance(db, account_id)
    engine = db.get_bind()
    db.rollback()
    app = FastAPI()
    app.include_router(router)
    def isolated_db():
        with Session(engine) as session:
            yield session
    app.dependency_overrides[get_db] = isolated_db
    calls = []
    def create(**kw):
        calls.append(kw)
        return SimpleNamespace(id="cs_test_contended", url="https://checkout.stripe.com/mock", livemode=False)
    monkeypatch.setattr(stripe.checkout.Session, "create", create)
    client = TestClient(app)
    headers = {"X-Device-Id": "device-a", "Idempotency-Key": "contention-key"}
    with Session(engine) as blocker:
        credits_svc.lock_account(blocker, account_id)
        start = monotonic()
        response = client.post("/billing/checkout", headers=headers, json={"pack": "p10"})
        assert monotonic() - start < 1.5  # does not use fixture's 10-second default
        assert response.status_code == 503
        assert response.headers["retry-after"] == "2"
        assert response.json()["detail"] == {"code": "billing_busy", "retryable": True, "retry_after_seconds": 2}
    assert calls == []
    assert credits_svc.balance(db, account_id) == before
    assert db.scalars(select(BillingRequest)).all() == []
    assert db.scalars(select(PaymentOrder)).all() == []
    db.rollback()
    first = client.post("/billing/checkout", headers=headers, json={"pack": "p10"})
    repeated = client.post("/billing/checkout", headers=headers, json={"pack": "p10"})
    assert first.status_code == repeated.status_code == 200
    assert first.json() == repeated.json() and len(calls) == 1


def test_busy_timeout_reapplied_after_commit(db, monkeypatch):
    from app.db.billing_contention import bound_lock_wait
    from app.core.config import get_settings
    from sqlalchemy import text
    monkeypatch.setattr(get_settings(), "billing_lock_timeout_ms", 75)
    bound_lock_wait(db)
    assert db.scalar(text("PRAGMA busy_timeout")) == 75
    db.execute(text("PRAGMA busy_timeout = 9000"))
    db.commit()
    assert db.scalar(text("PRAGMA busy_timeout")) == 75


def test_postgres_timeout_is_transaction_local_and_classification_is_precise():
    from app.db.billing_contention import _apply, is_lock_contention, _translate
    from fastapi import HTTPException
    from sqlalchemy.exc import OperationalError
    from unittest.mock import Mock
    connection = Mock(dialect=SimpleNamespace(name="postgresql"))
    _apply(connection, 2000)
    statement, parameters = connection.execute.call_args.args
    assert str(statement) == "SELECT set_config('lock_timeout', :timeout, true)"
    assert parameters == {"timeout": "2000ms"}
    for code in ("55P03", "40P01"):
        original = Exception("mock postgres lock failure")
        original.sqlstate = code
        error = OperationalError("UPDATE", {}, original)
        session = Mock()
        with pytest.raises(HTTPException) as result:
            _translate(session, error)
        assert result.value.status_code == 503
        session.rollback.assert_called_once()
    original = Exception("unrelated database outage")
    original.sqlstate = "08006"
    assert not is_lock_contention(OperationalError("SELECT", {}, original))


def test_post_provider_contention_keeps_checkout_intent_for_safe_retry(db, monkeypatch):
    import stripe
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.v1.routes.billing import router
    from app.db.session import get_db
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "billing_lock_timeout_ms", 50)
    account_id = credits_svc.resolve_account(db, "device-a").id
    engine = db.get_bind()
    db.rollback()
    app = FastAPI()
    app.include_router(router)
    def isolated_db():
        with Session(engine) as session:
            yield session
    app.dependency_overrides[get_db] = isolated_db
    keys = []
    blocker = Session(engine)
    def create(**kw):
        keys.append(kw["idempotency_key"])
        if len(keys) == 1:
            credits_svc.lock_account(blocker, account_id)
        return SimpleNamespace(id="cs_test_recovered", url="https://checkout.stripe.com/mock", livemode=False)
    monkeypatch.setattr(stripe.checkout.Session, "create", create)
    headers = {"X-Device-Id": "device-a", "Idempotency-Key": "post-provider-key"}
    client = TestClient(app)
    try:
        response = client.post("/billing/checkout", headers=headers, json={"pack": "p10"})
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "billing_busy"
    finally:
        blocker.close()
    orders = db.scalars(select(PaymentOrder)).all()
    assert len(orders) == 1 and orders[0].status == "pending"
    assert len(db.scalars(select(BillingRequest)).all()) == 1
    db.rollback()
    retried = client.post("/billing/checkout", headers=headers, json={"pack": "p10"})
    assert retried.status_code == 200
    assert keys[0] == keys[1]
    assert len(db.scalars(select(PaymentOrder)).all()) == 1
    assert len(db.scalars(select(BillingRequest)).all()) == 1

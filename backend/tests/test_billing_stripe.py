from types import SimpleNamespace

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.entities import Account, AccountDevice, CreditLedger, PaymentOrder
from app.services import credits as credits_svc
from app.services import stripe_billing

FREE = credits_svc.get_settings().ziwei_free_credits
FAKE_SETTINGS = SimpleNamespace(
    stripe_secret_key="sk_test_x", stripe_webhook_secret="whsec_x",
    public_base_url="https://portal.leipan.cc",
)


def _db() -> Session:
    engine = create_engine("sqlite://")
    for m in (Account, AccountDevice, CreditLedger, PaymentOrder):
        m.__table__.create(bind=engine)
    return Session(engine)


def _event(etype, sid, payment_status="paid", email="u@x.com"):
    return {"type": etype, "data": {"object": {
        "id": sid, "payment_status": payment_status, "customer_details": {"email": email}}}}


def test_create_checkout_session_records_pending_order(monkeypatch):
    import stripe
    db = _db()
    acct = credits_svc.resolve_account(db, "devA")
    monkeypatch.setattr(stripe_billing, "get_settings", lambda: FAKE_SETTINGS)
    monkeypatch.setattr(stripe.checkout.Session, "create",
                        lambda **kw: SimpleNamespace(id="cs_1", url="https://checkout/x", _kw=kw))

    url = stripe_billing.create_checkout_session(db, acct.id, "p10")
    assert url == "https://checkout/x"
    order = db.scalar(select(PaymentOrder).where(PaymentOrder.stripe_session_id == "cs_1"))
    assert order is not None
    assert order.credits == 10 and order.amount_cents == 990 and order.status == "pending"


def test_create_checkout_rejects_unknown_pack(monkeypatch):
    import pytest
    db = _db()
    acct = credits_svc.resolve_account(db, "devA")
    monkeypatch.setattr(stripe_billing, "get_settings", lambda: FAKE_SETTINGS)
    with pytest.raises(ValueError, match="unknown_pack"):
        stripe_billing.create_checkout_session(db, acct.id, "nope")


def test_process_event_credits_once_and_stores_email():
    db = _db()
    acct = credits_svc.resolve_account(db, "devA")  # balance = FREE
    db.add(PaymentOrder(account_id=acct.id, pack="p10", credits=10, amount_cents=990,
                        currency="cny", stripe_session_id="cs1", status="pending"))
    db.commit()

    assert stripe_billing.process_event(db, _event("checkout.session.completed", "cs1")) == "credited"
    assert credits_svc.balance(db, acct.id) == FREE + 10
    db.refresh(acct)
    assert acct.email == "u@x.com"

    # webhook re-delivery must not double-credit
    assert stripe_billing.process_event(db, _event("checkout.session.completed", "cs1")) == "already_paid"
    assert credits_svc.balance(db, acct.id) == FREE + 10


def test_process_event_waits_when_not_paid():
    db = _db()
    acct = credits_svc.resolve_account(db, "devA")
    db.add(PaymentOrder(account_id=acct.id, pack="p10", credits=10, amount_cents=990,
                        currency="cny", stripe_session_id="cs1", status="pending"))
    db.commit()
    assert stripe_billing.process_event(db, _event("checkout.session.completed", "cs1", payment_status="unpaid")) == "not_paid_yet"
    assert credits_svc.balance(db, acct.id) == FREE  # not credited


def test_process_event_unknown_order():
    db = _db()
    assert stripe_billing.process_event(db, _event("checkout.session.completed", "ghost")) == "order_not_found"


def test_process_event_async_failure_marks_order():
    db = _db()
    acct = credits_svc.resolve_account(db, "devA")
    db.add(PaymentOrder(account_id=acct.id, pack="p10", credits=10, amount_cents=990,
                        currency="cny", stripe_session_id="cs2", status="pending"))
    db.commit()
    assert stripe_billing.process_event(db, _event("checkout.session.async_payment_failed", "cs2")) == "failed"
    order = db.scalar(select(PaymentOrder).where(PaymentOrder.stripe_session_id == "cs2"))
    assert order.status == "failed"
    assert credits_svc.balance(db, acct.id) == FREE

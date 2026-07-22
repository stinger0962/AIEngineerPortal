from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import Account, AccountDevice, CreditLedger
from app.services import credits as credits_svc

FREE = get_settings().ziwei_free_credits


def _db() -> Session:
    engine = create_engine("sqlite://")
    for m in (Account, AccountDevice, CreditLedger):
        m.__table__.create(bind=engine)
    return Session(engine)


def test_resolve_account_creates_and_grants_free():
    db = _db()
    acct = credits_svc.resolve_account(db, "devA")
    assert acct is not None
    assert credits_svc.balance(db, acct.id) == FREE


def test_resolve_account_idempotent_same_device():
    db = _db()
    a1 = credits_svc.resolve_account(db, "devA")
    a2 = credits_svc.resolve_account(db, "devA")
    assert a1.id == a2.id
    assert credits_svc.balance(db, a1.id) == FREE  # free credits granted once, not per call


def test_two_devices_two_accounts():
    db = _db()
    a = credits_svc.resolve_account(db, "devA")
    b = credits_svc.resolve_account(db, "devB")
    assert a.id != b.id


def test_empty_device_returns_none():
    db = _db()
    assert credits_svc.resolve_account(db, "  ") is None


def test_consume_one_deducts_then_refuses_when_empty():
    db = _db()
    acct = credits_svc.resolve_account(db, "devA")
    for _ in range(FREE):
        assert credits_svc.consume_one(db, acct.id) is True
    assert credits_svc.balance(db, acct.id) == 0
    assert credits_svc.consume_one(db, acct.id) is False  # refuse when empty
    assert credits_svc.balance(db, acct.id) == 0  # not driven negative


def test_grant_adds_credits():
    db = _db()
    acct = credits_svc.resolve_account(db, "devA")
    credits_svc.grant(db, acct.id, 10, "purchase", order_id=1)
    assert credits_svc.balance(db, acct.id) == FREE + 10

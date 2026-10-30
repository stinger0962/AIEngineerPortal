"""Acceptance gates, intentionally fail where current implementation is unsafe.

Contract assumption: existing billing routes, pack p10, X-Device-Id identity.
All Stripe/AI effects are mocked; signature verification uses Stripe's local SDK.
"""
import hashlib
import hmac
import json
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import select
from app.models.entities import PaymentOrder, CreditLedger
from app.services import credits, stripe_billing


def pending(qa):
    with qa.sessions() as db:
        order = PaymentOrder(account_id=qa.owner, pack='p10', credits=10,
                             amount_cents=990, currency='cny', stripe_session_id='cs_test_qa', status='pending')
        db.add(order)
        db.commit()
        qa.order_id = order.id
        return order.id


def event(qa, **changes):
    obj = dict(id='cs_test_qa', object='checkout.session', livemode=False,
               payment_status='paid', mode='payment', amount_total=990, currency='cny',
               metadata={'account_id': str(qa.owner), 'order_id': str(qa.order_id)})
    obj.update(changes)
    return dict(id='evt_qa', object='event', livemode=False, type='checkout.session.completed', data={'object': obj})


def deliver(qa, payload, valid=True):
    raw = json.dumps(payload).encode()
    stamp = str(int(time.time()))
    signature = hmac.new(qa.settings.stripe_webhook_secret.encode(), stamp.encode() + b'.' + raw, hashlib.sha256).hexdigest()
    return qa.client.post('/api/v1/billing/webhook', content=raw,
                          headers={'stripe-signature': f't={stamp},v1={signature if valid else "00"}'})


def balance(qa, account=None):
    with qa.sessions() as db:
        return credits.balance(db, qa.owner if account is None else account)


def test_duplicate_and_distinct_success_notifications_credit_once(qa):
    oid = pending(qa)
    payload = event(qa)
    assert deliver(qa, payload).status_code == 200
    assert deliver(qa, payload).status_code == 200
    payload.update(id='evt_qa_async', type='checkout.session.async_payment_succeeded')
    assert deliver(qa, payload).status_code == 200
    assert balance(qa) == 10
    with qa.sessions() as db:
        assert len(db.scalars(select(CreditLedger).where(CreditLedger.order_id == oid)).all()) == 1


def test_invalid_signature_has_no_effect(qa):
    pending(qa)
    assert deliver(qa, event(qa), valid=False).status_code == 400
    assert balance(qa) == 0


@pytest.mark.parametrize('changes', [{'amount_total': 1}, {'currency': 'usd'}, {'livemode': True},
                                     {'metadata': {'account_id': '999999', 'pack': 'p10', 'credits': '10'}}])
def test_mismatched_payment_never_grants_credit(qa, changes):
    oid = pending(qa)
    deliver(qa, event(qa, **changes))
    assert balance(qa) == 0
    with qa.sessions() as db:
        assert db.get(PaymentOrder, oid).status != 'paid'


def test_live_envelope_never_grants_test_credit(qa):
    pending(qa)
    payload = event(qa)
    payload['livemode'] = True
    deliver(qa, payload)
    assert balance(qa) == 0


def test_live_key_cannot_enable_checkout(qa, monkeypatch):
    import stripe
    calls = []
    monkeypatch.setattr(stripe.checkout.Session, 'create', lambda **kw: calls.append(kw))
    qa.settings.stripe_secret_key = 'sk_live_nonfunctional_qa_placeholder'
    response = qa.client.post('/api/v1/billing/checkout', json={'pack': 'p10'}, headers={'X-Device-Id': 'qa-owner', 'Idempotency-Key': 'qa-live-key-reject'})
    assert response.status_code == 503
    assert calls == []


def test_other_account_cannot_redirect_order_credit(qa):
    pending(qa)
    assert deliver(qa, event(qa)).status_code == 200
    response = qa.client.get('/api/v1/billing/balance', headers={'X-Device-Id': 'qa-other'})
    assert response.json()['balance'] == 0
    assert balance(qa, qa.other) == 0


def test_concurrent_notifications_credit_once(qa):
    pending(qa)
    start = Barrier(2)
    def worker(_):
        start.wait(timeout=5)
        return deliver(qa, event(qa)).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(worker, range(2)))
    assert statuses == [200, 200]
    assert balance(qa) == 10


def test_concurrent_credit_consumption_cannot_overspend(qa, monkeypatch):
    with qa.sessions() as db:
        credits.grant(db, qa.owner, 1, 'qa')
    # Synchronize before acquiring the account lock: a barrier inside balance()
    # would deadlock a correct lock-before-read implementation.
    started = Barrier(2)
    def worker(_):
        started.wait(timeout=5)
        with qa.sessions() as db:
            return credits.consume_one(db, qa.owner)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(worker, range(2)))
    assert sorted(results) == [False, True]
    assert balance(qa) == 0


def test_overlapping_webhook_order_reads_credit_once(qa, monkeypatch):
    """Force the existing SELECT/status-check race; no Stripe network involved."""
    from sqlalchemy.orm import Session
    pending(qa)
    loaded = Barrier(2)
    original = Session.scalar
    def scalar(db, statement, *args, **kwargs):
        result = original(db, statement, *args, **kwargs)
        if isinstance(result, PaymentOrder):
            loaded.wait(timeout=5)
        return result
    monkeypatch.setattr(Session, 'scalar', scalar)
    def worker(_):
        with qa.sessions() as db:
            return stripe_billing.process_event(db, event(qa))
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(worker, range(2)))
    assert balance(qa) == 10


def test_delayed_async_success_waits_for_paid_and_grants_once(qa):
    oid = pending(qa)
    unpaid = event(qa, payment_status='unpaid')
    assert deliver(qa, unpaid).json()['status'] == 'not_paid_yet'
    assert balance(qa) == 0
    with qa.sessions() as db:
        assert db.get(PaymentOrder, oid).status == 'pending'
    success = event(qa)
    success.update(id='evt_delayed_success', type='checkout.session.async_payment_succeeded')
    assert deliver(qa, success).json()['status'] == 'credited'
    assert deliver(qa, success).json()['status'] == 'already_paid'
    assert deliver(qa, unpaid).json()['status'] == 'not_paid_yet'
    assert balance(qa) == 10
    with qa.sessions() as db:
        assert db.get(PaymentOrder, oid).status == 'paid'
        assert len(db.scalars(select(CreditLedger).where(CreditLedger.order_id == oid)).all()) == 1


@pytest.mark.parametrize('failure_first', [False, True])
def test_out_of_order_failure_and_paid_success_converge_to_one_grant(qa, failure_first):
    oid = pending(qa)
    failed = event(qa, payment_status='unpaid')
    failed.update(id='evt_failure', type='checkout.session.async_payment_failed')
    success = event(qa)
    success.update(id='evt_success', type='checkout.session.async_payment_succeeded')
    if failure_first:
        assert deliver(qa, failed).json()['status'] == 'failed'
        assert deliver(qa, failed).json()['status'] == 'already_failed'
        assert balance(qa) == 0
    assert deliver(qa, success).json()['status'] == 'credited'
    assert deliver(qa, failed).json()['status'] == 'already_paid'
    assert deliver(qa, success).json()['status'] == 'already_paid'
    assert balance(qa) == 10
    with qa.sessions() as db:
        assert db.get(PaymentOrder, oid).status == 'paid'
        assert len(db.scalars(select(CreditLedger).where(CreditLedger.order_id == oid)).all()) == 1


@pytest.mark.parametrize('changes', [
    {'amount_total': 1}, {'currency': 'usd'}, {'mode': 'subscription'},
    {'metadata': {}}, {'metadata': {'order_id': '999', 'account_id': '999'}},
])
def test_failure_metadata_mismatch_cannot_change_order_state(qa, changes):
    oid = pending(qa)
    failed = event(qa, **changes)
    failed['type'] = 'checkout.session.async_payment_failed'
    assert deliver(qa, failed).json()['status'] == 'payment_mismatch'
    with qa.sessions() as db:
        assert db.get(PaymentOrder, oid).status == 'pending'
    assert balance(qa) == 0


def test_other_session_success_never_fulfills_known_order(qa):
    oid = pending(qa)
    response = deliver(qa, event(qa, id='cs_test_other_session'))
    assert response.status_code == 503
    with qa.sessions() as db:
        assert db.get(PaymentOrder, oid).status == 'pending'
    assert balance(qa) == 0


def test_overlapping_failure_and_success_leave_paid_with_one_grant(qa):
    oid = pending(qa)
    failed = event(qa, payment_status='unpaid')
    failed['type'] = 'checkout.session.async_payment_failed'
    success = event(qa)
    success['type'] = 'checkout.session.async_payment_succeeded'
    start = Barrier(2)
    def worker(payload):
        start.wait(timeout=5)
        return deliver(qa, payload).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(worker, [failed, success])) == [200, 200]
    with qa.sessions() as db:
        assert db.get(PaymentOrder, oid).status == 'paid'
        assert len(db.scalars(select(CreditLedger).where(CreditLedger.order_id == oid)).all()) == 1
    assert balance(qa) == 10

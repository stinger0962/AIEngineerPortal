"""Adversarial/reordered events, no Stripe network communication."""
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Account, CreditLedger, PaymentOrder
from app.services import stripe_billing
from test_paid_accounts import product
from test_billing_stripe import event


@pytest.fixture
def order_db(product):
    with Session(product.engine) as db:
        acct = Account()
        db.add(acct)
        db.flush()
        order = PaymentOrder(account_id=acct.id, pack='p10', credits=10, amount_cents=990,
                             currency='cny', stripe_session_id='cs_test_fixture', status='pending')
        db.add(order)
        db.commit()
        yield db, order


class NoDatabase:
    def __getattr__(self, name):
        raise AssertionError('Invalid/unsupported payload must not touch database')


@pytest.mark.parametrize('payload', [None, [], '', 1, {}, {'type': []}, {'type': ''},
    {'type': 'checkout.session.completed'}, {'type': 'checkout.session.completed', 'data': []},
    {'type': 'checkout.session.completed', 'data': {'object': None}},
    {'type': 'checkout.session.completed', 'data': {'object': []}}])
def test_bad_envelope_no_database(payload):
    assert stripe_billing.process_event(NoDatabase(), payload) == 'invalid_event'


@pytest.mark.parametrize('field,value', [('id', []), ('id', ''), ('amount_total', True),
    ('amount_total', 990.0), ('amount_total', '990'), ('amount_total', -1),
    ('currency', []), ('mode', None), ('payment_status', {}), ('metadata', []),
    ('metadata', 'bad'), ('metadata', {'order_id': 1}), ('metadata', {'account_id': False})])
def test_invalid_checkout_types_no_database(order_db, field, value):
    _, order = order_db
    payload = event(order, **{field: value})
    assert stripe_billing.process_event(NoDatabase(), payload) == 'invalid_event'


@pytest.mark.parametrize('kind', ['charge.refunded', 'charge.refund.updated', 'refund.created',
                                 'refund.updated', 'refund.failed', 'charge.dispute.created',
                                 'charge.dispute.closed'])
def test_financial_events_explicitly_unsupported(kind):
    payload = {'type': kind, 'livemode': False, 'data': {'object': {'livemode': False}}}
    assert stripe_billing.process_event(NoDatabase(), payload) == 'unsupported_financial_event'


@pytest.mark.parametrize('sequence', [
    ['checkout.session.completed'] * 3,
    ['checkout.session.async_payment_failed', 'checkout.session.async_payment_succeeded', 'checkout.session.async_payment_failed'],
    ['checkout.session.async_payment_succeeded', 'checkout.session.completed', 'checkout.session.async_payment_failed'],
])
def test_reordered_duplicates_credit_once(order_db, sequence):
    db, order = order_db
    outcomes = []
    for kind in sequence:
        payload = event(order)
        payload['type'] = kind
        outcomes.append(stripe_billing.process_event(db, payload))
    assert outcomes.count('credited') == 1
    db.refresh(order)
    assert order.status == 'paid'
    grants = db.scalars(select(CreditLedger).where(CreditLedger.order_id == order.id)).all()
    assert len(grants) == 1 and grants[0].delta == 10


def test_pending_then_success_and_mismatch(order_db):
    db, order = order_db
    assert stripe_billing.process_event(db, event(order, payment_status='unpaid')) == 'not_paid_yet'
    assert stripe_billing.process_event(db, event(order, metadata={'order_id': str(order.id), 'account_id': '999'})) == 'payment_mismatch'
    assert stripe_billing.process_event(db, event(order, id='cs_unknown')) == 'order_not_found'
    assert stripe_billing.process_event(db, event(order)) == 'credited'
    assert stripe_billing.process_event(db, event(order)) == 'already_paid'


def test_stripe_sdk_event_mapping_supported(order_db):
    import stripe
    db, order = order_db
    payload = stripe.Event.construct_from(event(order), 'sk_test_fixture')
    assert stripe_billing.process_event(db, payload) == 'credited'


@pytest.mark.parametrize('value', [True, None, 0, 'false'])
def test_nonboolean_or_live_mode_rejected(order_db, value):
    _, order = order_db
    payload = event(order, livemode=value)
    assert stripe_billing.process_event(NoDatabase(), payload) == 'live_or_unknown_mode_rejected'
    payload = event(order)
    payload['livemode'] = value
    assert stripe_billing.process_event(NoDatabase(), payload) == 'live_or_unknown_mode_rejected'


def test_repeated_failure_and_financial_events_preserve_grants(order_db):
    db, order = order_db
    payload = event(order)
    payload['type'] = 'checkout.session.async_payment_failed'
    assert stripe_billing.process_event(db, payload) == 'failed'
    assert stripe_billing.process_event(db, payload) == 'already_failed'
    assert stripe_billing.process_event(db, event(order)) == 'credited'
    for kind in ('refund.created', 'charge.refunded', 'charge.dispute.created'):
        payload['type'] = kind
        assert stripe_billing.process_event(db, payload) == 'unsupported_financial_event'
    db.refresh(order)
    assert order.status == 'paid'
    assert len(db.scalars(select(CreditLedger).where(CreditLedger.order_id == order.id)).all()) == 1


@pytest.mark.parametrize('metadata', [{}, {'order_id': '1'}, {'order_id':'', 'account_id':'1'}])
def test_missing_identity_is_not_retryable_unknown_order(order_db, metadata):
    _, order = order_db
    payload = event(order, id='cs_test_unknown', metadata=metadata)
    assert stripe_billing.process_event(NoDatabase(), payload) == 'payment_mismatch'

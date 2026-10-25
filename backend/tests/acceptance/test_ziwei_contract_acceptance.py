"""Confirmed public contract gates; no assumptions about reservation model names."""
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest
import stripe
from app.api.v1.routes import ziwei
from test_ziwei_reading_acceptance import OWNER, REQUEST, RESULT, fund, remaining


@pytest.fixture
def checkout_calls(monkeypatch):
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        return stripe.StripeObject.construct_from({
            'id': 'cs_test_contract', 'url': 'https://checkout.stripe.com/c/pay/cs_test_contract',
            'livemode': False, 'payment_status': 'unpaid',
        }, 'sk_test_nonfunctional')
    monkeypatch.setattr(stripe.checkout.Session, 'create', create)
    return calls


def checkout(qa, key='qa-checkout-first', pack='p10'):
    headers = {'X-Device-Id': 'qa-owner'}
    if key is not None:
        headers['Idempotency-Key'] = key
    return qa.client.post('/api/v1/billing/checkout', headers=headers, json={'pack': pack})


def test_balance_declares_test_mode_and_currency(qa):
    response = qa.client.get('/api/v1/billing/balance', headers=OWNER)
    assert response.status_code == 200
    assert response.json()['mode'] == 'test'
    assert response.json()['currency'] == 'cny'


def test_checkout_retry_preserves_order_and_rejects_changed_pack(qa, checkout_calls):
    first = checkout(qa)
    assert first.status_code == 200
    body = first.json()
    assert body['mode'] == 'test'
    assert body['order_id']
    assert body['url']
    second = checkout(qa)
    assert second.status_code == 200
    assert second.json() == body
    assert checkout(qa, pack='p40').status_code == 409
    assert checkout_calls
    assert all(str(body['order_id']) in call['success_url'] for call in checkout_calls)
    assert remaining(qa) == 0, 'Checkout/redirect must never grant credits'


def test_order_details_require_owner_and_do_not_grant_credit(qa, checkout_calls):
    response = checkout(qa)
    assert response.status_code == 200
    oid = response.json()['order_id']
    path = f'/api/v1/billing/orders/{oid}'
    owned = qa.client.get(path, headers=OWNER)
    assert owned.status_code == 200
    assert owned.json() == {'order_id': oid, 'status': 'pending', 'pack': 'p10',
                            'credits': 10, 'amount_cents': 990, 'currency': 'cny', 'mode': 'test'}
    for headers in ({}, {'X-Device-Id': 'qa-other'}):
        assert qa.client.get(path, headers=headers).status_code == 404
    assert remaining(qa) == 0


def test_cancel_return_and_unpaid_notification_never_fulfill_checkout(qa, checkout_calls):
    """Simulated cancellation/resume flow; no actual Stripe delivery occurs."""
    from test_ziwei_payment_acceptance import deliver, event

    first = checkout(qa)
    assert first.status_code == 200
    body = first.json()
    qa.order_id = body['order_id']
    cancel = urlparse(checkout_calls[0]['cancel_url'])
    assert cancel.netloc == 'localhost:3000'
    assert cancel.path == '/ziwei'
    assert parse_qs(cancel.query) == {'canceled': ['1'], 'order_id': [str(qa.order_id)]}

    # A return flag cannot authorize payment; the owner still sees pending/zero.
    path = f'/api/v1/billing/orders/{qa.order_id}'
    status = qa.client.get(path + '?' + cancel.query, headers=OWNER)
    assert status.status_code == 200
    assert status.json()['status'] == 'pending'
    unpaid = event(qa, id='cs_test_contract', payment_status='unpaid')
    assert deliver(qa, unpaid).status_code == 200
    assert remaining(qa) == 0
    assert qa.client.get(path, headers=OWNER).json()['status'] == 'pending'

    # Resuming the same checkout must preserve the existing intent/session.
    assert checkout(qa).json() == body
    assert len(checkout_calls) == 1
    paid = event(qa, id='cs_test_contract')
    assert deliver(qa, paid).status_code == 200
    assert deliver(qa, paid).status_code == 200
    assert remaining(qa) == 10
    assert qa.client.get(path, headers=OWNER).json()['status'] == 'paid'


@pytest.mark.parametrize('key', [None, 'short', 'x' * 129])
def test_checkout_rejects_invalid_idempotency_key(qa, checkout_calls, key):
    response = checkout(qa, key=key)
    assert response.status_code == 400
    assert response.json()['detail']['code'] == 'invalid_idempotency_key'
    assert checkout_calls == []


@pytest.mark.parametrize('configuration', [
    {'stripe_test_enabled': False},
    {'stripe_test_base_url': ''},
    {'stripe_test_base_url': 'https://portal.leipan.cc'},
])
def test_checkout_fails_closed_for_disabled_or_unsafe_configuration(qa, checkout_calls, configuration):
    for key, value in configuration.items():
        # model_copy supplied these fields even on the old baseline Settings.
        qa.settings.__dict__[key] = value
    assert checkout(qa).status_code == 503
    assert checkout_calls == []


class CompleteStream:
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    @property
    def text_stream(self):
        yield 'Mock completed reading. '
    def get_final_message(self):
        return SimpleNamespace(usage=SimpleNamespace(input_tokens=1, output_tokens=1))


@pytest.fixture
def oracle_calls(monkeypatch):
    calls = []
    def run(*a, **kw):
        calls.append('sync')
        return RESULT
    def stream(**kw):
        calls.append('stream')
        return CompleteStream()
    monkeypatch.setattr(ziwei.ZiweiOracle, 'run', run)
    monkeypatch.setattr(ziwei.ZiweiOracle, '_system_prompt', lambda *a, **kw: 'QA')
    monkeypatch.setattr(ziwei, 'AIService', lambda: SimpleNamespace(
        is_available=True, client=SimpleNamespace(messages=SimpleNamespace(stream=stream))))
    return calls


@pytest.mark.parametrize('suffix', ['oracle', 'oracle/stream'])
@pytest.mark.parametrize('key', [None, 'short', 'x' * 129])
def test_reading_rejects_invalid_idempotency_key(qa, oracle_calls, suffix, key):
    fund(qa)
    headers = {'X-Device-Id': 'qa-owner'}
    if key is not None:
        headers['Idempotency-Key'] = key
    response = qa.client.post(f'/api/v1/ziwei/profiles/{qa.profile}/{suffix}', headers=headers, json=REQUEST)
    assert response.status_code == 400
    assert response.json()['detail']['code'] == 'invalid_idempotency_key'
    assert oracle_calls == []
    assert remaining(qa) == 1


@pytest.mark.parametrize('suffix', ['oracle', 'oracle/stream'])
def test_completed_reading_key_replay_and_changed_payload(qa, oracle_calls, suffix):
    fund(qa)
    path = f'/api/v1/ziwei/profiles/{qa.profile}/{suffix}'
    first = qa.client.post(path, headers=OWNER, json=REQUEST)
    assert first.status_code == 200
    if suffix.endswith('/stream'):
        assert '"done"' in first.text
        assert '"error"' not in first.text
    assert remaining(qa) == 0
    replay = qa.client.post(path, headers=OWNER, json=REQUEST)
    assert replay.status_code == 409
    assert replay.json()['detail']['code'] == 'request_already_completed'
    changed = qa.client.post(path, headers=OWNER, json={**REQUEST, 'message': 'Changed payload'})
    assert changed.status_code == 409
    assert changed.json()['detail']['code'] == 'idempotency_conflict'
    assert len(oracle_calls) == 1
    assert remaining(qa) == 0


@pytest.mark.parametrize('suffix', ['oracle', 'oracle/stream'])
def test_failed_reading_allows_same_key_retry(qa, oracle_calls, monkeypatch, suffix):
    from test_ziwei_reading_acceptance import InterruptedStream
    fund(qa)
    path = f'/api/v1/ziwei/profiles/{qa.profile}/{suffix}'
    if suffix == 'oracle':
        success = ziwei.ZiweiOracle.run
        monkeypatch.setattr(ziwei.ZiweiOracle, 'run', lambda *a, **kw: None)
    else:
        success = ziwei.AIService
        monkeypatch.setattr(ziwei, 'AIService', lambda: SimpleNamespace(is_available=True,
            client=SimpleNamespace(messages=SimpleNamespace(stream=lambda **kw: InterruptedStream()))))
    failed = qa.client.post(path, headers=OWNER, json=REQUEST)
    if suffix == 'oracle':
        assert failed.status_code == 502
        monkeypatch.setattr(ziwei.ZiweiOracle, 'run', success)
    else:
        assert failed.status_code == 200 and '"error"' in failed.text
        assert '"done"' not in failed.text
        monkeypatch.setattr(ziwei, 'AIService', success)
    assert remaining(qa) == 1
    retried = qa.client.post(path, headers=OWNER, json=REQUEST)
    assert retried.status_code == 200
    if suffix.endswith('/stream'):
        assert '"done"' in retried.text and '"error"' not in retried.text
    assert remaining(qa) == 0
    assert len(oracle_calls) == 1

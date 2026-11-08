"""Read-only order history against disposable storage; sockets forbidden by fixture."""
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session

from app.api.v1.routes import billing
from app.db.session import get_db
from app.models.entities import Account, AccountDevice, CreditLedger, PaymentOrder
from app.models.paid_accounts import PaidVerifiedEmail
from test_paid_accounts import product, login, fresh_client, count


def seed(product, email, count_orders=25):
    with Session(product.engine) as db:
        account_id = db.get(PaidVerifiedEmail, email).account_id
        ids = []
        for i in range(count_orders):
            order = PaymentOrder(account_id=account_id, pack='small', credits=10,
                                 amount_cents=100, currency='cny', status=['pending', 'paid', 'failed'][i % 3],
                                 stripe_session_id=f'never-expose-{account_id}-{i}',
                                 created_at=datetime(2026, 1, 1) + timedelta(days=i // 2))
            db.add(order)
            db.flush()
            ids.append(order.id)
        db.commit()
        return ids


def test_owner_bound_newest_history(product, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("History must never call checkout provider")
    monkeypatch.setattr(billing.stripe_billing, "create_checkout_session", forbidden)
    login(product, email='first@example.test')
    ids = seed(product, 'first@example.test')
    other = fresh_client(product)
    login(product, client=other, email='other@example.test')
    seed(product, 'other@example.test', 3)
    before = [count(product, model) for model in (Account, AccountDevice, CreditLedger, PaymentOrder)]
    response = product.client.get('/api/v1/billing/orders')
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    data = response.json()
    assert data['mode'] == 'test'
    assert [x['order_id'] for x in data['orders']] == ids[::-1][:10]
    assert set(data['orders'][0]) == {'order_id', 'status', 'pack', 'credits', 'amount_cents', 'currency', 'created_at'}
    assert data['orders'][0]['created_at'].endswith('Z')
    assert 'never-expose' not in response.text
    assert len(product.client.get('/api/v1/billing/orders?limit=20').json()['orders']) == 20
    assert [count(product, model) for model in (Account, AccountDevice, CreditLedger, PaymentOrder)] == before


@pytest.mark.parametrize('limit', ['0', '-1', '21', '99999999999', 'bad', '1.5', ''])
def test_malformed_limits(product, limit):
    login(product)
    assert product.client.get('/api/v1/billing/orders', params={'limit': limit}).status_code == 422
    assert count(product, PaymentOrder) == 0


def test_paid_requires_enabled_verified_session(product):
    assert product.client.get('/api/v1/billing/orders', headers={'X-Device-Id': 'fake'}).status_code == 401
    login(product)
    assert product.client.get('/api/v1/billing/orders').json() == {'mode': 'test', 'orders': []}
    product.settings.paid_accounts_enabled = False
    assert product.client.get('/api/v1/billing/orders').status_code == 503


def test_portal_unknown_device_does_not_create_account(product):
    app = FastAPI()
    app.include_router(billing.router)
    def db_session():
        with Session(product.engine) as db:
            yield db
    app.dependency_overrides[get_db] = db_session
    client = TestClient(app)
    for headers in ({}, {'X-Device-Id': 'unknown'}):
        response = client.get('/billing/orders', headers=headers)
        assert response.status_code == 200
        assert response.json() == {'mode': 'test', 'orders': []}
    assert count(product, Account) == count(product, AccountDevice) == count(product, CreditLedger) == 0


def test_portal_existing_device_remains_scoped(product):
    login(product, email='owner@example.test')
    ids = seed(product, 'owner@example.test', 1)
    with Session(product.engine) as db:
        owner = db.get(PaidVerifiedEmail, 'owner@example.test').account_id
        db.add(AccountDevice(account_id=owner, device_id='known'))
        db.commit()
    app = FastAPI()
    app.include_router(billing.router)
    def db_session():
        with Session(product.engine) as db:
            yield db
    app.dependency_overrides[get_db] = db_session
    client = TestClient(app)
    assert [x['order_id'] for x in client.get('/billing/orders', headers={'X-Device-Id': 'known'}).json()['orders']] == ids
    assert client.get('/billing/orders', headers={'X-Device-Id': 'other'}).json()['orders'] == []

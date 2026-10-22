"""Real local PostgreSQL gates; opt in only to disposable localhost QA database."""
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from sqlalchemy import select, text
from app.models.entities import BillingRequest, CreditLedger, PaymentOrder
from app.services import credits
from app.api.v1.routes import ziwei
from test_ziwei_reading_acceptance import OWNER, REQUEST, RESULT, fund, remaining

pytestmark = pytest.mark.skipif(not os.environ.get('ZIWEI_QA_POSTGRES_URL'),
                                reason='Requires disposable local PostgreSQL QA instance')
MIGRATION = Path(__file__).resolve().parents[2] / 'scripts/migrations/20261021_billing_requests.sql'


@pytest.mark.parametrize('existing_schema', [False, True], ids=['fresh-bootstrap', 'existing-baseline'])
def test_postgres_migration_is_repeatable_and_preserves_fixture_data(qa, existing_schema):
    engine = qa.sessions.kw['bind']
    with qa.sessions() as db:
        credits.grant(db, qa.owner, 7, 'qa-existing')
        order = PaymentOrder(account_id=qa.owner, pack='p10', credits=10, amount_cents=990,
                             currency='cny', stripe_session_id='cs_test_existing', status='pending')
        db.add(order)
        db.commit()
        oid = order.id
    if existing_schema:
        BillingRequest.__table__.drop(engine)
    script = MIGRATION.read_text()
    for _ in range(2):
        with engine.connect().execution_options(isolation_level='AUTOCOMMIT') as connection:
            connection.exec_driver_sql(script)
    with qa.sessions() as db:
        assert credits.balance(db, qa.owner) == 7
        assert db.get(PaymentOrder, oid).status == 'pending'
        assert len(db.scalars(select(CreditLedger)).all()) == 1
        db.add(BillingRequest(key='a' * 64, account_id=qa.owner,
                              fingerprint='b' * 64, response_json={'status': 'completed'}))
        db.commit()
        assert db.get(BillingRequest, 'a' * 64).response_json == {'status': 'completed'}


def test_postgres_account_lock_does_not_block_another_account(qa):
    fund(qa)
    with qa.sessions() as db:
        credits.grant(db, qa.other, 1, 'qa-other')
    with qa.sessions() as held:
        assert held.scalar(text('SHOW transaction_isolation')) == 'read committed'
        assert credits.consume_one(held, qa.owner, commit=False)
        def consume_other():
            with qa.sessions() as db:
                return credits.consume_one(db, qa.other)
        with ThreadPoolExecutor(max_workers=1) as pool:
            assert pool.submit(consume_other).result(timeout=1) is True
        held.rollback()
    assert remaining(qa) == 1
    with qa.sessions() as db:
        assert credits.balance(db, qa.other) == 0


def test_postgres_http_lock_timeout_rolls_back_and_same_key_retries(qa, monkeypatch):
    import app.db.billing_contention as contention
    fund(qa)
    qa.settings.billing_lock_timeout_ms = 100
    monkeypatch.setattr(contention, 'get_settings', lambda: qa.settings)
    calls = []
    def run(*args, **kwargs):
        calls.append(True)
        return RESULT
    monkeypatch.setattr(ziwei.ZiweiOracle, 'run', run)
    path = f'/api/v1/ziwei/profiles/{qa.profile}/oracle'
    with qa.sessions() as held:
        credits.lock_account(held, qa.owner)
        start = time.monotonic()
        response = qa.client.post(path, headers=OWNER, json=REQUEST)
        assert time.monotonic() - start < 1.5
        assert response.status_code == 503
        assert response.headers['retry-after'] == '2'
        assert response.json()['detail']['code'] == 'billing_busy'
        assert calls == []
        held.rollback()
    assert remaining(qa) == 1
    retried = qa.client.post(path, headers=OWNER, json=REQUEST)
    assert retried.status_code == 200
    assert remaining(qa) == 0
    assert calls == [True]

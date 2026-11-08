"""Offline aggregate audit on disposable databases only; no provider contacts."""
from datetime import datetime, timedelta
import json
import pytest
from sqlalchemy import insert, select
from app.cli import paid_billing_audit as audit
from app.models.entities import Account, CreditLedger, PaymentOrder
from test_paid_retention import fixture_db, snapshot


def add_order(engine, *, status='paid', grants=(10,), age=0, other_account=False):
    with engine.begin() as conn:
        result = conn.execute(insert(PaymentOrder).values(account_id=123, pack='p10', credits=10, amount_cents=990,
            currency='cny', stripe_session_id='pending:fixture', status=status, created_at=datetime.utcnow()-timedelta(hours=age)))
        oid = result.inserted_primary_key[0]
        if other_account:
            conn.execute(insert(Account).values(id=456))
        for delta in grants:
            conn.execute(insert(CreditLedger).values(account_id=456 if other_account else 123, delta=delta, reason='purchase', order_id=oid))
    return oid


def test_clean_local_ledger_does_not_claim_provider_reconciliation(fixture_db):
    env, engine = fixture_db
    add_order(engine)
    before = snapshot(engine)
    result = audit.run_audit(env)
    assert result['local_ledger_consistent'] and result['read_only']
    assert not result['provider_reconciled'] and not result['payment_refunds_supported']
    assert not any(result['anomalies'].values())
    assert snapshot(engine) == before
    assert 'private' not in json.dumps(result) and 'preserve@example' not in json.dumps(result)


@pytest.mark.parametrize('grants,other', [((),False), ((10,10),False), ((9,),False), ((10,),True)])
def test_paid_grant_mismatch_detected_without_repair(fixture_db, grants, other):
    env, engine = fixture_db
    add_order(engine, grants=grants, other_account=other)
    before = snapshot(engine)
    assert audit.run_audit(env)['anomalies']['paid_order_grant_mismatch'] == 1
    assert snapshot(engine) == before


@pytest.mark.parametrize('status', ['pending','failed','refunded'])
def test_unpaid_grant_and_unknown_status(fixture_db,status):
    env,engine=fixture_db
    add_order(engine,status=status)
    report=audit.run_audit(env)
    assert report['anomalies']['unpaid_order_has_purchase']==1
    assert report['anomalies']['unknown_order_state']==(1 if status=='refunded' else 0)


def test_old_pending_is_review_not_automatic_failure(fixture_db):
    env,engine=fixture_db
    add_order(engine,status='pending',grants=(),age=24)
    before=snapshot(engine)
    report=audit.run_audit(env)
    assert report['local_ledger_consistent']
    assert report['pending_review']==dict(older_than_safe_checkout_retry=1,without_saved_provider_session=1)
    assert snapshot(engine)==before


def test_orphan_negative_and_refund_categories(fixture_db):
    env,engine=fixture_db
    with engine.begin() as conn:
        conn.execute(insert(CreditLedger),[
            dict(account_id=123,delta=10,reason='purchase',order_id=999),
            dict(account_id=123,delta=-20,reason='ziwei_oracle',order_id=None),
            dict(account_id=123,delta=1,reason='refund',order_id=None),
            dict(account_id=123,delta=1,reason='refund',order_id=999),
            dict(account_id=999,delta=1,reason='purchase',order_id=None),
        ])
    findings=audit.run_audit(env)['anomalies']
    assert findings['orphan_purchase_entries']==2
    assert findings['orphan_ledger_accounts']==1
    assert findings['negative_account_balances']==1
    assert findings['unsupported_payment_refund_entries']==1


def test_no_portal_fallback_or_secret_output(tmp_path):
    with pytest.raises(RuntimeError,match='^Billing audit unavailable') as error:
        audit.run_audit({'DATABASE_URL':'postgresql://private:secret@invalid/db'})
    assert 'secret' not in str(error.value)
    assert not list(tmp_path.iterdir())

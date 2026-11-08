"""Maintenance runs only against disposable tmp_path databases."""
from datetime import datetime, timedelta
from pathlib import Path
import json
import os
import subprocess
import sys

import pytest
from sqlalchemy import create_engine, event, select, func, text

from app.cli import paid_retention as retention
from app.paid_main import PAID_TABLES
from app.db.base import Base
from app.models.paid_accounts import PaidSession, PaidChallenge, PaidRateLimit
from app.models.entities import Account, CreditLedger


@pytest.fixture
def fixture_db(tmp_path):
    env = {"PAID_DATABASE_URL": f"sqlite:///{tmp_path / 'paid.db'}", "DATABASE_URL": f"sqlite:///{tmp_path / 'portal.db'}"}
    engine = create_engine(env['PAID_DATABASE_URL'])
    Base.metadata.create_all(engine, tables=list(PAID_TABLES))
    now = datetime.utcnow()
    with engine.begin() as conn:
        conn.execute(Account.__table__.insert().values(id=123, email='preserve@example.test'))
        conn.execute(CreditLedger.__table__.insert().values(account_id=123, delta=3, reason='welcome'))
        for key, delta in [('expired', -2), ('future', 2)]:
            conn.execute(PaidSession.__table__.insert().values(token_hash=key, account_id=123, expires_at=now + timedelta(days=delta)))
            conn.execute(PaidRateLimit.__table__.insert().values(key=key, count=1, expires_at=now + timedelta(days=delta)))
            conn.execute(PaidChallenge.__table__.insert().values(id=key, code_hash='private-code', email='private@example.test', expires_at=now + timedelta(days=delta)))
        conn.execute(PaidChallenge.__table__.insert().values(id='grace', code_hash='secret', email='private@example.test', expires_at=now - timedelta(hours=12)))
    yield env, engine
    engine.dispose()


def snapshot(engine):
    with engine.connect() as conn:
        return {table.name: [tuple(row) for row in conn.execute(select(table))] for table in PAID_TABLES}


def test_dry_run_and_apply_only_expired(fixture_db):
    env, engine = fixture_db
    before = snapshot(engine)
    result = retention.run_retention(env)
    assert result['mode'] == 'dry-run'
    assert result['counts'] == dict(paid_sessions=1, paid_rate_limits=1, paid_challenges=1)
    assert snapshot(engine) == before
    result = retention.run_retention(env, apply=True, max_delete=3)
    after = snapshot(engine)
    for name in before.keys() - result['counts'].keys():
        assert after[name] == before[name]
    assert len(after['paid_challenges']) == 2
    assert sum(retention.run_retention(env, apply=True, max_delete=3)['counts'].values()) == 0
    assert 'private' not in json.dumps(result)


@pytest.mark.parametrize('budget', [None, 0, -1, 2])
def test_budget_rollback(fixture_db, budget):
    env, engine = fixture_db
    before = snapshot(engine)
    with pytest.raises(retention.RetentionError):
        retention.run_retention(env, apply=True, max_delete=budget)
    assert snapshot(engine) == before


def test_partial_failure_rolls_back(fixture_db, monkeypatch):
    env, engine = fixture_db
    before = snapshot(engine)
    real = retention._engine
    def wrapped(*args):
        target = real(*args)
        @event.listens_for(target, 'before_cursor_execute')
        def fail(conn, cursor, statement, parameters, context, executemany):
            if statement.startswith('DELETE FROM paid_rate_limits'):
                raise RuntimeError('password=secret-do-not-print')
        return target
    monkeypatch.setattr(retention, '_engine', wrapped)
    with pytest.raises(retention.RetentionError, match='Verify database state') as exc:
        retention.run_retention(env, apply=True, max_delete=3)
    assert 'secret' not in str(exc.value)
    assert snapshot(engine) == before


@pytest.mark.parametrize('kind', ['equal', 'alias', 'hardlink', 'symlink', 'missing', 'empty', 'unknown', 'table', 'view'])
def test_refuses_wrong_database(fixture_db, tmp_path, kind):
    env, engine = fixture_db
    if kind == 'equal':
        env['DATABASE_URL'] = env['PAID_DATABASE_URL']
    elif kind in {'alias', 'hardlink', 'symlink'}:
        portal = tmp_path / 'portal.db'
        if kind == 'hardlink':
            os.link(tmp_path / 'paid.db', portal)
        elif kind == 'symlink':
            portal.symlink_to(tmp_path / 'paid.db')
        else:
            env['DATABASE_URL'] = f'sqlite:///{tmp_path}/./paid.db'
    elif kind == 'missing':
        env['PAID_DATABASE_URL'] = f'sqlite:///{tmp_path}/missing.db'
    elif kind == 'empty':
        env['PAID_DATABASE_URL'] = ''
    elif kind == 'unknown':
        env['PAID_DATABASE_URL'] = 'mysql://user:private-secret@host/db'
    else:
        with engine.begin() as conn:
            conn.execute(text('CREATE TABLE unrelated (id INTEGER)' if kind == 'table' else 'CREATE VIEW unrelated AS SELECT 1'))
    with pytest.raises(retention.RetentionError) as exc:
        retention.run_retention(env, apply=True, max_delete=10)
    assert 'private-secret' not in str(exc.value)
    assert not (tmp_path / 'missing.db').exists()


def test_schema_allowlist_matches_app():
    assert retention.EXPECTED_TABLES == {table.name for table in PAID_TABLES}


def test_cli_no_app_config_import_or_env_file(tmp_path):
    result = subprocess.run([sys.executable, '-c', "from app.cli import paid_retention; import sys; assert 'app.core.config' not in sys.modules; assert 'app.db.session' not in sys.modules; raise SystemExit(paid_retention.main([]))"], env={**os.environ, 'PAID_DATABASE_URL': '', 'DATABASE_URL': '', 'PYTHONPATH': str(Path(__file__).resolve().parents[1])}, cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 1
    assert 'required' in result.stderr
    assert not result.stdout


def test_readonly_connection(fixture_db):
    env, _ = fixture_db
    engine = retention._engine(env, False)
    try:
        with engine.begin() as conn, pytest.raises(Exception, match='readonly'):
            conn.execute(text('DELETE FROM paid_sessions'))
    finally:
        engine.dispose()


def test_trigger_refused(fixture_db):
    env, engine = fixture_db
    with engine.begin() as conn:
        conn.execute(text("CREATE TRIGGER dangerous AFTER DELETE ON paid_sessions BEGIN DELETE FROM accounts; END"))
    before = snapshot(engine)
    with pytest.raises(retention.RetentionError, match='triggers'):
        retention.run_retention(env, apply=True, max_delete=3)
    assert snapshot(engine) == before


def test_exact_cutoff_boundaries(fixture_db, monkeypatch):
    env, engine = fixture_db
    cutoff = datetime(2026, 1, 1)
    class Clock:
        @staticmethod
        def utcnow():
            return cutoff
    monkeypatch.setattr(retention, 'datetime', Clock)
    with engine.begin() as conn:
        for table in (PaidSession.__table__, PaidChallenge.__table__, PaidRateLimit.__table__):
            conn.execute(table.delete())
        for name, delta in [('boundary', 0), ('after', 1)]:
            conn.execute(PaidSession.__table__.insert().values(token_hash=name, account_id=123, expires_at=cutoff + timedelta(microseconds=delta)))
            conn.execute(PaidChallenge.__table__.insert().values(id=name, code_hash='x', email='x@y.test', expires_at=cutoff - timedelta(days=1) + timedelta(microseconds=delta)))
    result = retention.run_retention(env, apply=True, max_delete=2)
    assert result['counts'] == dict(paid_sessions=1, paid_challenges=1, paid_rate_limits=0)


@pytest.mark.parametrize('paid,portal', [
    ('postgresql://one:secret@localhost/db', 'postgresql+psycopg://two:other@localhost:5432/db'),
    ('sqlite:///:memory:', 'sqlite:///portal.db'),
    ('postgresql://user:secret@host/db?options=-csearch_path=portal', 'sqlite:///portal.db'),
])
def test_unsafe_url_refused_without_connect(paid, portal):
    with pytest.raises(retention.RetentionError):
        retention.run_retention({'PAID_DATABASE_URL': paid, 'DATABASE_URL': portal}, apply=True, max_delete=5)


def test_inbound_cascade_refused(fixture_db):
    env, engine = fixture_db
    with engine.begin() as conn:
        # Existing paid table name, altered FK: table-name allowlist alone is unsafe.
        conn.execute(text("ALTER TABLE accounts ADD COLUMN auth_link TEXT REFERENCES paid_sessions(token_hash) ON DELETE CASCADE"))
        conn.execute(text("UPDATE accounts SET auth_link = 'expired'"))
    before = snapshot(engine)
    with pytest.raises(retention.RetentionError, match='references'):
        retention.run_retention(env, apply=True, max_delete=3)
    assert snapshot(engine) == before


def test_postgres_disposable_database():
    """CI-only unique database, never any existing database's records."""
    from sqlalchemy.engine import make_url
    from uuid import uuid4
    raw = os.environ.get('ZIWEI_QA_POSTGRES_URL')
    if not raw:
        pytest.skip('isolated PostgreSQL QA service not supplied')
    url = make_url(raw)
    assert url.host == '127.0.0.1' and url.port == 55432 and url.database == 'ziwei_qa' and not url.query
    name = 'paid_retention_qa_' + uuid4().hex
    admin = create_engine(url, isolation_level='AUTOCOMMIT')
    target = create_engine(url.set(database=name))
    created = False
    try:
        with admin.connect() as conn:
            conn.exec_driver_sql(f'CREATE DATABASE {name}')  # generated hex-only identifier
        created = True
        Base.metadata.create_all(target, tables=list(PAID_TABLES))
        with target.begin() as conn:
            conn.execute(Account.__table__.insert().values(id=123, email='preserved@example.test'))
            conn.execute(CreditLedger.__table__.insert().values(account_id=123, delta=3, reason='welcome'))
            conn.execute(PaidSession.__table__.insert().values(token_hash='expired', account_id=123, expires_at=datetime.utcnow() - timedelta(days=1)))
        env = {'PAID_DATABASE_URL': url.set(database=name).render_as_string(hide_password=False), 'DATABASE_URL': raw}
        before = snapshot(target)
        from app.cli.paid_billing_audit import run_audit
        report = run_audit(env)
        assert report['local_ledger_consistent'] is True and report['provider_reconciled'] is False
        assert snapshot(target) == before
        assert retention.run_retention(env)['counts']['paid_sessions'] == 1
        assert snapshot(target) == before
        assert retention.run_retention(env, apply=True, max_delete=1)['counts']['paid_sessions'] == 1
        assert retention.run_retention(env, apply=True, max_delete=1)['counts']['paid_sessions'] == 0
        after = snapshot(target)
        assert after['accounts'] == before['accounts'] and after['credit_ledger'] == before['credit_ledger']
        # Rewrite rules are also side effects, even without a trigger.
        with target.begin() as conn:
            conn.exec_driver_sql('CREATE RULE retention_test AS ON DELETE TO paid_sessions DO ALSO DELETE FROM credit_ledger')
        with pytest.raises(retention.RetentionError, match='rules'):
            retention.run_retention(env, apply=True, max_delete=1)
        with target.begin() as conn:
            conn.exec_driver_sql('DROP RULE retention_test ON paid_sessions')
            conn.exec_driver_sql('CREATE SCHEMA extra')
            conn.exec_driver_sql('CREATE TABLE extra.inbound (auth_link VARCHAR(64) REFERENCES public.paid_sessions(token_hash) ON DELETE CASCADE)')
        with pytest.raises(retention.RetentionError, match='references'):
            retention.run_retention(env, apply=True, max_delete=1)
    finally:
        target.dispose()
        if created:
            with admin.connect() as conn:
                conn.exec_driver_sql(f'DROP DATABASE {name}')
        admin.dispose()

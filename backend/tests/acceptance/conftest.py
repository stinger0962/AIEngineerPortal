"""Independent QA fixtures: temporary SQLite only; no external sockets or paid AI."""
import os
import socket
from types import SimpleNamespace

# Applied before application imports, regardless of developer .env configuration.
for name in ('ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'MINIMAX_API_KEY',
             'STRIPE_SECRET_KEY', 'STRIPE_WEBHOOK_SECRET'):
    os.environ[name] = ''
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['ZIWEI_REQUIRE_CREDITS'] = 'false'
os.environ['STRIPE_TEST_ENABLED'] = 'false'
os.environ['STRIPE_TEST_BASE_URL'] = ''

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateSchema, DropSchema
from uuid import uuid4
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB
from app.core.config import Settings
from app.db.session import get_db
from app.api.v1.routes import billing, ziwei
from app.models.entities import (Base, Account, AccountDevice, CreditLedger, PaymentOrder,
                                User, ZiweiProfile, ZiweiConversation, ZiweiMessage, AIFeedback)
from app.services import credits, stripe_billing


@compiles(JSONB, 'sqlite')
def _jsonb_sqlite(type_, compiler, **kw):
    return 'JSON'


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    postgres_url = os.environ.get('ZIWEI_QA_POSTGRES_URL')
    allowed = None
    if postgres_url:
        target = make_url(postgres_url)
        if target.host != '127.0.0.1' or target.port != 55432 or target.database != 'ziwei_qa':
            raise ValueError('QA PostgreSQL must be the isolated 127.0.0.1:55432/ziwei_qa instance')
        allowed = (target.host, target.port)
    for name in ('connect', 'connect_ex'):
        original = getattr(socket.socket, name)
        def guarded(sock, address, _original=original):
            if allowed and address == allowed:
                return _original(sock, address)
            raise AssertionError('QA suite forbids external network connections')
        monkeypatch.setattr(socket.socket, name, guarded)
    # psycopg/libpq sockets are implemented in C; the validated local URL above
    # is the database boundary. Python-level Stripe/AI sockets remain blocked.


@pytest.fixture
def qa(tmp_path, monkeypatch):
    settings = Settings(_env_file=None, database_url='sqlite://', app_env='test',
                        stripe_secret_key='sk_test_qa_placeholder',
                        stripe_webhook_secret='whsec_qa_placeholder',
                        public_base_url='https://portal.leipan.cc',
                        ziwei_require_credits=True, ziwei_free_credits=0,
                        ziwei_auto_adopt=False)
    # Explicit agreed configuration, also usable against the pre-contract baseline.
    settings = settings.model_copy(update={'stripe_test_enabled': True,
                                           'stripe_test_base_url': 'http://localhost:3000'})
    import app.core.config as config
    for module in (config, credits, stripe_billing, billing, ziwei):
        monkeypatch.setattr(module, 'get_settings', lambda: settings)
    postgres_url = os.environ.get('ZIWEI_QA_POSTGRES_URL')
    admin = None
    schema = None
    if postgres_url:
        schema = 'qa_' + uuid4().hex
        admin = create_engine(postgres_url)
        with admin.begin() as connection:
            connection.execute(CreateSchema(schema))
        engine = create_engine(postgres_url, connect_args={'options': f'-csearch_path={schema}'})
    else:
        engine = create_engine(f'sqlite:///{tmp_path / "qa.db"}',
                               connect_args={'check_same_thread': False, 'timeout': 5})
    # Include new billing/reservation tables without depending on their class names.
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    def db_override():
        with sessions() as db:
            yield db
    application = FastAPI()
    application.include_router(billing.router, prefix='/api/v1')
    application.include_router(ziwei.router, prefix='/api/v1')
    application.dependency_overrides[get_db] = db_override
    monkeypatch.setattr(ziwei, 'SessionLocal', sessions)
    monkeypatch.setattr(ziwei, 'AIService', lambda: SimpleNamespace(is_available=True, client=None))
    with sessions() as db:
        a = credits.resolve_account(db, 'qa-owner')
        b = credits.resolve_account(db, 'qa-other')
        db.add(User(id=1, name='QA', email='qa@example.invalid', target_role='test'))
        profile = ZiweiProfile(name='QA', relation='self', gender='male', birth_date='1990-01-01',
                               birth_time_index=0, device_id='qa-owner', chart_json={'palaces': [{}]})
        db.add(profile)
        db.commit()
        ids = (a.id, b.id, profile.id)
    yield SimpleNamespace(settings=settings, sessions=sessions,
                          client=TestClient(application), owner=ids[0], other=ids[1], profile=ids[2])
    engine.dispose()
    if admin is not None:
        with admin.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        admin.dispose()

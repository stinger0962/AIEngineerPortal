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
    def reject(*args, **kwargs):
        raise AssertionError('QA suite forbids external network connections')
    monkeypatch.setattr(socket.socket, 'connect', reject)
    monkeypatch.setattr(socket.socket, 'connect_ex', reject)
    monkeypatch.setattr(socket, 'create_connection', reject)


@pytest.fixture
def qa(tmp_path, monkeypatch):
    settings = Settings(_env_file=None, database_url='sqlite://', app_env='test',
                        stripe_secret_key='sk_test_qa_placeholder',
                        stripe_webhook_secret='whsec_qa_placeholder',
                        public_base_url='http://localhost:3000',
                        ziwei_require_credits=True, ziwei_free_credits=0,
                        ziwei_auto_adopt=False)
    # Explicit agreed configuration, also usable against the pre-contract baseline.
    settings = settings.model_copy(update={'stripe_test_enabled': True,
                                           'stripe_test_base_url': 'http://localhost:3000'})
    import app.core.config as config
    for module in (config, credits, stripe_billing, billing, ziwei):
        monkeypatch.setattr(module, 'get_settings', lambda: settings)
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

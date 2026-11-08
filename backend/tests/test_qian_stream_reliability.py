"""Mock-only Qian empty generation regression, isolated paid storage."""
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.api.v1.routes import qian
from app.models.entities import AIFeedback, QianReading
from test_paid_accounts import product, login


@pytest.mark.parametrize('chunks', [[], [''], ['  \n ']])
def test_empty_generation_is_error_not_done(product, monkeypatch, chunks):
    class Stream:
        text_stream = chunks
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def get_final_message(self):
            return SimpleNamespace(usage=SimpleNamespace(input_tokens=4, output_tokens=1))
    client = SimpleNamespace(messages=SimpleNamespace(stream=lambda **kw: Stream()))
    monkeypatch.setattr(qian, 'AIService', lambda: SimpleNamespace(is_available=True, client=client))
    login(product)
    response = product.client.post('/api/v1/qian/oracle/stream', json={'question':'synthetic','sign_id':7})
    assert response.status_code == 200
    assert '"type": "error"' in response.text
    assert '"type": "done"' not in response.text
    with Session(product.engine) as db:
        assert db.scalar(select(func.count()).select_from(QianReading)) == 0
        assert db.scalar(select(func.count()).select_from(AIFeedback)) == 1


@pytest.mark.parametrize('feature', ['qian', 'ziwei'])
@pytest.mark.parametrize('committed', [True, False])
def test_persistence_failure_never_blindly_retried(product, monkeypatch, feature, committed):
    from app.api.v1.routes import ziwei
    from app.models.entities import ZiweiProfile, ZiweiConversation, ZiweiMessage, CreditLedger
    from test_paid_accounts import PROFILE
    class Stream:
        text_stream = ['synthetic answer']
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def get_final_message(self):
            return SimpleNamespace(usage=SimpleNamespace(input_tokens=1, output_tokens=1))
    fake = SimpleNamespace(messages=SimpleNamespace(stream=lambda **kw: Stream()))
    route = qian if feature == 'qian' else ziwei
    monkeypatch.setattr(route, 'AIService', lambda: SimpleNamespace(is_available=True, client=fake))
    login(product)
    if feature == 'ziwei':
        monkeypatch.setattr(product.settings, 'ziwei_require_credits', True)
        monkeypatch.setattr(ziwei.ZiweiOracle, '_system_prompt', lambda *args: 'synthetic')
        pid = product.client.post('/api/v1/ziwei/profiles', json=PROFILE).json()['id']
        with Session(product.engine) as db:
            db.get(ZiweiProfile, pid).chart_json = {'palaces': [{}]}
            conv = ZiweiConversation(profile_id=pid, scenario='general', title='synthetic')
            db.add(conv)
            db.commit()
            cid = conv.id
        url = f'/api/v1/ziwei/profiles/{pid}/oracle/stream'
        payload = {'message':'synthetic', 'conversation_id':cid}
    else:
        url = '/api/v1/qian/oracle/stream'
        payload = {'question':'synthetic', 'sign_id':7}
    attempts = []
    class FailingCommit(Session):
        def commit(self):
            attempts.append(True)
            if committed:
                super().commit()
            raise RuntimeError('synthetic commit failure, outcome uncertain')
    monkeypatch.setattr(route, 'SessionLocal' if feature == 'qian' else 'Session', FailingCommit)
    response = product.client.post(url, json=payload, headers={'Idempotency-Key':'synthetic-commit'})
    assert '"type": "error"' in response.text and '"type": "done"' not in response.text
    assert len(attempts) == 1
    with Session(product.engine) as db:
        if feature == 'qian':
            assert db.scalar(select(func.count()).select_from(QianReading)) == int(committed)
        else:
            assert db.scalar(select(func.count()).select_from(ZiweiMessage)) == 2 * int(committed)
            assert db.scalar(select(func.count()).select_from(CreditLedger).where(CreditLedger.delta == -1)) == int(committed)
        assert db.scalar(select(func.count()).select_from(AIFeedback)) == int(committed)

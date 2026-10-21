"""Paid-reading acceptance tests using a fake oracle and disposable accounts."""
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace

import pytest
from app.api.v1.routes import ziwei
from app.models.entities import ZiweiConversation
from app.services import credits

OWNER = {'X-Device-Id': 'qa-owner'}
OTHER = {'X-Device-Id': 'qa-other'}
REQUEST = {'scenario': 'natal', 'message': 'QA reading'}
RESULT = {'response': 'Mock reading', 'camera_commands': [], 'segments': [],
          '_meta': {'model': 'fake', 'input_tokens': 1, 'output_tokens': 1, 'latency_ms': 0}}


def fund(qa):
    with qa.sessions() as db:
        credits.grant(db, qa.owner, 1, 'qa')


def remaining(qa):
    with qa.sessions() as db:
        return credits.balance(db, qa.owner)


def test_cross_account_reading_access_denied(qa, monkeypatch):
    monkeypatch.setattr(ziwei.ZiweiOracle, 'run', lambda *a, **kw: pytest.fail('Unauthorized generation'))
    with qa.sessions() as db:
        conv = ZiweiConversation(profile_id=qa.profile, scenario='natal', title='Private')
        db.add(conv)
        db.commit()
        cid = conv.id
    for path in (f'/ziwei/profiles/{qa.profile}', f'/ziwei/profiles/{qa.profile}/conversations',
                 f'/ziwei/conversations/{cid}/messages'):
        assert qa.client.get('/api/v1' + path, headers=OTHER).status_code in (403, 404)
    for suffix in ('oracle', 'oracle/stream'):
        response = qa.client.post(f'/api/v1/ziwei/profiles/{qa.profile}/{suffix}', headers=OTHER, json=REQUEST)
        assert response.status_code in (403, 404)


def test_failed_generation_preserves_credit(qa, monkeypatch):
    fund(qa)
    monkeypatch.setattr(ziwei.ZiweiOracle, 'run', lambda *a, **kw: None)
    response = qa.client.post(f'/api/v1/ziwei/profiles/{qa.profile}/oracle', headers=OWNER, json=REQUEST)
    assert response.status_code == 502
    assert remaining(qa) == 1


def test_success_then_exhaustion(qa, monkeypatch):
    fund(qa)
    calls = []
    def run(*a, **kw):
        calls.append(True)
        return RESULT
    monkeypatch.setattr(ziwei.ZiweiOracle, 'run', run)
    path = f'/api/v1/ziwei/profiles/{qa.profile}/oracle'
    assert qa.client.post(path, headers=OWNER, json=REQUEST).status_code == 200
    assert qa.client.post(path, headers=OWNER, json=REQUEST).status_code == 402
    assert len(calls) == 1
    assert remaining(qa) == 0


def test_simultaneous_reads_with_one_credit(qa, monkeypatch):
    fund(qa)
    # Pre-create distinct conversations to avoid SQLite's new-conversation write
    # serializing both requests before they reach the mocked upstream generation.
    with qa.sessions() as db:
        conversations = [ZiweiConversation(profile_id=qa.profile, scenario='natal', title='QA') for _ in range(2)]
        db.add_all(conversations)
        db.commit()
        ids = [c.id for c in conversations]
    entered = Barrier(2)
    calls = []
    def run(*a, **kw):
        calls.append(True)
        try:
            entered.wait(timeout=1)
        except Exception:
            pass  # correct implementations admit only one request
        return RESULT
    monkeypatch.setattr(ziwei.ZiweiOracle, 'run', run)
    def request(cid):
        return qa.client.post(f'/api/v1/ziwei/profiles/{qa.profile}/oracle', headers=OWNER,
                              json={**REQUEST, 'conversation_id': cid}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(request, ids))
    assert sorted(statuses) == [200, 402]
    assert len(calls) == 1
    assert remaining(qa) == 0


class InterruptedStream:
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    @property
    def text_stream(self):
        yield 'Partial mock reading. '
        raise RuntimeError('simulated upstream interruption')


def test_interrupted_stream_preserves_credit(qa, monkeypatch):
    fund(qa)
    fake_client = SimpleNamespace(messages=SimpleNamespace(stream=lambda **kw: InterruptedStream()))
    monkeypatch.setattr(ziwei, 'AIService', lambda: SimpleNamespace(is_available=True, client=fake_client))
    monkeypatch.setattr(ziwei.ZiweiOracle, '_system_prompt', lambda *a, **kw: 'QA')
    response = qa.client.post(f'/api/v1/ziwei/profiles/{qa.profile}/oracle/stream', headers=OWNER, json=REQUEST)
    assert response.status_code == 200
    events = [json.loads(line[5:].strip()) for line in response.text.splitlines() if line.startswith('data:')]
    assert any(e['type'] == 'error' for e in events)
    assert not any(e['type'] == 'done' for e in events)
    assert remaining(qa) == 1


def test_closed_stream_generator_preserves_credit(qa, monkeypatch):
    """Generator cancellation probe; not a real HTTP disconnect or process crash."""
    fund(qa)
    fake_client = SimpleNamespace(messages=SimpleNamespace(stream=lambda **kw: InterruptedStream()))
    monkeypatch.setattr(ziwei, 'AIService', lambda: SimpleNamespace(is_available=True, client=fake_client))
    monkeypatch.setattr(ziwei.ZiweiOracle, '_system_prompt', lambda *a, **kw: 'QA')
    monkeypatch.setattr(ziwei, 'EventSourceResponse', lambda generator: generator)
    with qa.sessions() as db:
        generator = ziwei.ask_oracle_stream(qa.profile, ziwei.OracleRequest(**REQUEST), db, 'qa-owner')
    next(generator)
    generator.close()
    assert remaining(qa) == 1

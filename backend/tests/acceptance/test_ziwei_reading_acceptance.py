"""Paid-reading acceptance tests using a fake oracle and disposable accounts."""
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, BrokenBarrierError
from types import SimpleNamespace

import pytest
from app.api.v1.routes import ziwei
from app.models.entities import ZiweiConversation
from app.services import credits

OWNER = {'X-Device-Id': 'qa-owner', 'Idempotency-Key': 'qa-reading-first'}
OTHER = {'X-Device-Id': 'qa-other', 'Idempotency-Key': 'qa-reading-other'}
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
    response = qa.client.post(path, headers={**OWNER, 'Idempotency-Key': 'qa-reading-second'}, json=REQUEST)
    assert response.status_code == 402
    assert response.json()['detail'] == {'code': 'insufficient_credits', 'balance': 0, 'required': 1}
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
        except BrokenBarrierError:
            pass  # correct implementations admit only one request
        return RESULT
    monkeypatch.setattr(ziwei.ZiweiOracle, 'run', run)
    def request(cid):
        return qa.client.post(f'/api/v1/ziwei/profiles/{qa.profile}/oracle', headers={**OWNER, 'Idempotency-Key': f'qa-parallel-{cid}'},
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
    """Close the route's stream after its first output, with HTTP dependencies active.

    This is a generator-close probe, not a real ASGI disconnect/process crash.
    """
    import inspect
    from starlette.responses import StreamingResponse
    fund(qa)
    fake_client = SimpleNamespace(messages=SimpleNamespace(stream=lambda **kw: InterruptedStream()))
    monkeypatch.setattr(ziwei, 'AIService', lambda: SimpleNamespace(is_available=True, client=fake_client))
    monkeypatch.setattr(ziwei.ZiweiOracle, '_system_prompt', lambda *a, **kw: 'QA')
    closed = []
    async def first_then_close(source):
        try:
            item = await anext(source) if inspect.isasyncgen(source) else next(source)
            yield json.dumps(item)
        finally:
            if inspect.isasyncgen(source):
                await source.aclose()
            else:
                source.close()
            closed.append(True)
    monkeypatch.setattr(ziwei, 'EventSourceResponse',
                        lambda source, **kw: StreamingResponse(first_then_close(source)))
    response = qa.client.post(f'/api/v1/ziwei/profiles/{qa.profile}/oracle/stream', headers=OWNER, json=REQUEST)
    assert response.status_code == 200
    assert closed == [True]
    assert remaining(qa) == 1


def test_asgi_disconnect_rolls_back_and_same_key_can_retry(qa, monkeypatch):
    """Exercise an actual ASGI http.disconnect after a streamed text frame."""
    import anyio
    import time
    from test_ziwei_contract_acceptance import CompleteStream
    fund(qa)
    class SlowStream(CompleteStream):
        @property
        def text_stream(self):
            for _ in range(100):
                time.sleep(0.01)
                yield 'Mock partial reading. '
    monkeypatch.setattr(ziwei.ZiweiOracle, '_system_prompt', lambda *a, **kw: 'QA')
    monkeypatch.setattr(ziwei, 'AIService', lambda: SimpleNamespace(is_available=True,
        client=SimpleNamespace(messages=SimpleNamespace(stream=lambda **kw: SlowStream()))))
    path = f'/api/v1/ziwei/profiles/{qa.profile}/oracle/stream'
    async def disconnect():
        output_seen = anyio.Event()
        received = False
        async def receive():
            nonlocal received
            if not received:
                received = True
                return {'type': 'http.request', 'body': json.dumps(REQUEST).encode(), 'more_body': False}
            await output_seen.wait()
            return {'type': 'http.disconnect'}
        async def send(message):
            if message['type'] == 'http.response.body' and b'"text"' in message.get('body', b''):
                output_seen.set()
        scope = {'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1',
                 'method': 'POST', 'scheme': 'http', 'path': path, 'raw_path': path.encode(),
                 'query_string': b'', 'root_path': '', 'server': ('testserver', 80),
                 'client': ('127.0.0.1', 1234), 'headers': [
                     (b'content-type', b'application/json'),
                     (b'x-device-id', b'qa-owner'), (b'idempotency-key', b'qa-reading-first')]}
        with anyio.fail_after(4):
            await qa.client.app(scope, receive, send)
        assert output_seen.is_set()
    anyio.run(disconnect)
    assert remaining(qa) == 1
    monkeypatch.setattr(ziwei, 'AIService', lambda: SimpleNamespace(is_available=True,
        client=SimpleNamespace(messages=SimpleNamespace(stream=lambda **kw: CompleteStream()))))
    retried = qa.client.post(path, headers=OWNER, json=REQUEST)
    assert retried.status_code == 200 and '"done"' in retried.text
    assert remaining(qa) == 0


@pytest.mark.parametrize('case', ['invalid_key', 'insufficient', 'upstream_failure'])
def test_rejected_stream_leaves_no_new_conversation(qa, monkeypatch, case):
    from sqlalchemy import select
    if case != 'insufficient':
        fund(qa)
    monkeypatch.setattr(ziwei.ZiweiOracle, '_system_prompt', lambda *a, **kw: 'QA')
    monkeypatch.setattr(ziwei, 'AIService', lambda: SimpleNamespace(is_available=True,
        client=SimpleNamespace(messages=SimpleNamespace(stream=lambda **kw: InterruptedStream()))))
    headers = {**OWNER, 'Idempotency-Key': 'short'} if case == 'invalid_key' else OWNER
    response = qa.client.post(f'/api/v1/ziwei/profiles/{qa.profile}/oracle/stream', headers=headers, json=REQUEST)
    expected = {'invalid_key': 400, 'insufficient': 402, 'upstream_failure': 200}[case]
    assert response.status_code == expected
    if case == 'upstream_failure':
        assert '"error"' in response.text and '"done"' not in response.text
    with qa.sessions() as db:
        assert db.scalars(select(ZiweiConversation)).all() == []
    assert remaining(qa) == (0 if case == 'insufficient' else 1)

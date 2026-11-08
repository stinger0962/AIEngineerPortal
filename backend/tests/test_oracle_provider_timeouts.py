"""Bounded interactive provider waits; all provider calls mocked."""
from types import SimpleNamespace

import httpx
import pytest

from app.api.v1.routes import ziwei, qian
from app.services.podcast_service import _tts_bytes
from test_paid_accounts import product, login, PROFILE
from sqlalchemy.orm import Session
from app.models.entities import ZiweiProfile


@pytest.mark.parametrize('failure,status', [(httpx.ReadTimeout('sensitive provider details'),504), (ValueError('sensitive provider details'),502)])
def test_tts_short_timeout_and_redacted_failure(product, monkeypatch, caplog, failure, status):
    login(product)
    monkeypatch.setattr(product.settings, 'minimax_api_key', 'synthetic-no-network')
    monkeypatch.setattr(product.settings, 'minimax_group_id', 'synthetic')
    calls=[]
    def provider(*args, **kwargs):
        calls.append(kwargs)
        raise failure
    monkeypatch.setattr(ziwei, '_tts_bytes', provider)
    response=product.client.post('/api/v1/ziwei/tts',json={'text':'synthetic'})
    assert response.status_code == status
    assert calls == [{'timeout':10.0}]
    assert 'sensitive provider details' not in response.text + caplog.text


def test_tts_podcast_timeout_default_preserved(monkeypatch):
    calls=[]
    def post(*args, **kwargs):
        calls.append(kwargs['timeout'])
        return httpx.Response(200, request=httpx.Request('POST','https://synthetic.test'),json={'data':{'audio':'494433'},'base_resp':{'status_code':0}})
    monkeypatch.setattr(httpx,'post',post)
    assert _tts_bytes('x','v','fake','fake') == b'ID3'
    assert _tts_bytes('x','v','fake','fake',timeout=15.0) == b'ID3'
    assert calls == [120.0,15.0]


@pytest.mark.parametrize('feature',['ziwei','qian'])
def test_stream_timeout_explicit_and_error_not_done(product, monkeypatch, feature):
    login(product)
    route=ziwei if feature=='ziwei' else qian
    calls=[]
    def stream(**kwargs):
        calls.append(kwargs)
        raise httpx.ReadTimeout('synthetic upstream timeout')
    monkeypatch.setattr(route, 'interactive_oracle_client', lambda client: client)
    monkeypatch.setattr(route,'AIService',lambda:SimpleNamespace(is_available=True,client=SimpleNamespace(messages=SimpleNamespace(stream=stream))))
    if feature=='ziwei':
        monkeypatch.setattr(ziwei.ZiweiOracle,'_system_prompt',lambda *a:'synthetic')
        pid=product.client.post('/api/v1/ziwei/profiles',json=PROFILE).json()['id']
        with Session(product.engine) as db:
            db.get(ZiweiProfile,pid).chart_json={'palaces':[{}]}
            db.commit()
        url=f'/api/v1/ziwei/profiles/{pid}/oracle/stream'
        payload={'message':'synthetic'}
    else:
        url='/api/v1/qian/oracle/stream'
        payload={'question':'synthetic','sign_id':7}
    response=product.client.post(url,json=payload)
    assert '"type": "error"' in response.text and '"type": "done"' not in response.text
    assert len(calls)==1 and calls[0]['timeout']==60.0


def test_real_sdk_options_disable_hidden_generation_retries(monkeypatch):
    import anthropic
    from app.services.oracle_transport import interactive_oracle_client
    for key in ('ALL_PROXY', 'HTTP_PROXY', 'HTTPS_PROXY', 'all_proxy', 'http_proxy', 'https_proxy'):
        monkeypatch.delenv(key, raising=False)
    original = anthropic.Anthropic(api_key='synthetic-never-sent')
    configured = interactive_oracle_client(original)
    try:
        assert configured.max_retries == 0
        assert configured.timeout == 60.0
        assert original.max_retries == 2  # unrelated portal AI defaults unchanged
    finally:
        configured.close()
        original.close()


def test_unknown_client_cannot_silently_keep_retries():
    from app.services.oracle_transport import interactive_oracle_client
    with pytest.raises(TypeError, match='explicit timeout and retry'):
        interactive_oracle_client(SimpleNamespace(messages=object()))

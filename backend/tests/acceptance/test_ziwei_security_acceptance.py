"""Regression gates for the two explicitly approved access-restricting fixes."""
import pytest
from app.core.config import Settings
from app.models.entities import ZiweiProfile, ZiweiConversation, ZiweiMessage
from app.services import stripe_billing


@pytest.mark.parametrize('stale_auto_adopt', [False, True])
def test_public_listing_never_claims_or_exposes_legacy_profiles(qa, stale_auto_adopt):
    qa.settings.ziwei_auto_adopt = stale_auto_adopt
    qa.settings.ziwei_claim_code = ''
    with qa.sessions() as db:
        legacy = ZiweiProfile(name='Private legacy', relation='self', gender='male',
            birth_date='1990-01-01', birth_time_index=0, device_id=None, chart_json={})
        db.add(legacy)
        db.flush()
        conversation = ZiweiConversation(profile_id=legacy.id, scenario='natal', title='Private history')
        db.add(conversation)
        db.flush()
        message = ZiweiMessage(conversation_id=conversation.id, role='assistant',
                               content='Legacy private text', chart_context_json={})
        db.add(message)
        db.commit()
        pid, cid, mid = legacy.id, conversation.id, message.id
    for headers in ({}, {'X-Device-Id': 'qa-other'}, {'X-Device-Id': 'qa-owner'}):
        for _ in range(2):
            response = qa.client.get('/api/v1/ziwei/profiles', headers=headers)
            assert response.status_code == 200
            assert pid not in [profile['id'] for profile in response.json()]
            assert [profile['id'] for profile in response.json()] == ([qa.profile] if headers.get('X-Device-Id') == 'qa-owner' else [])
        for path in (f'/profiles/{pid}', f'/profiles/{pid}/conversations', f'/conversations/{cid}/messages'):
            assert qa.client.get('/api/v1/ziwei' + path, headers=headers).status_code == 404
        assert qa.client.post('/api/v1/ziwei/claim', headers=headers, json={'code': ''}).status_code == 403
    with qa.sessions() as db:
        assert db.get(ZiweiProfile, pid).device_id is None
        assert db.get(ZiweiProfile, pid).name == 'Private legacy'
        assert db.get(ZiweiConversation, cid).profile_id == pid
        assert db.get(ZiweiMessage, mid).content == 'Legacy private text'


def test_auto_adopt_default_is_disabled():
    assert Settings.model_fields['ziwei_auto_adopt'].default is False


@pytest.mark.parametrize('callback', [
    'https://portal.leipan.cc.', 'https://PORTAL.LEIPAN.CC.',
    'https://leipan.cc.', 'https://other.leipan.cc.',
    'https://portal.leipan.cc\u3002', 'https://portal.leipan.cc:443',
    'https://portal.leipan.cc.:443',
])
def test_production_callback_spellings_fail_before_checkout(qa, monkeypatch, callback):
    import stripe
    calls = []
    monkeypatch.setattr(stripe.checkout.Session, 'create', lambda **kw: calls.append(kw))
    qa.settings.stripe_test_base_url = callback
    assert stripe_billing.is_configured() is False
    response = qa.client.post('/api/v1/billing/checkout', json={'pack': 'p10'},
        headers={'X-Device-Id': 'qa-owner', 'Idempotency-Key': 'qa-forbidden-callback'})
    assert response.status_code == 503
    assert calls == []


@pytest.mark.parametrize(('production', 'callback'), [
    ('https://production.example.', 'https://production.example'),
    ('https://production.example', 'https://PRODUCTION.EXAMPLE.'),
    ('https://b\u00fccher.example', 'https://xn--bcher-kva.example.'),
])
def test_configured_production_hostname_is_canonicalized_on_both_sides(qa, production, callback):
    qa.settings.public_base_url = production
    qa.settings.stripe_test_base_url = callback
    assert stripe_billing.is_configured() is False


def test_local_test_callback_remains_available(qa):
    qa.settings.stripe_test_base_url = 'http://127.0.0.1:3100'
    assert stripe_billing.is_configured() is True

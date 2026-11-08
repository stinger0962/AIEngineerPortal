"""Read-only private history contract on disposable paid-product fixtures."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Account, AccountDevice, CreditLedger, QianReading
from app.models.paid_accounts import PaidQianOwner, PaidVerifiedEmail
from test_paid_accounts import product, login, count


def test_detail_hides_unowned_legacy_and_missing_without_mutation(product):
    login(product)
    with Session(product.engine) as db:
        account_id = db.get(PaidVerifiedEmail, 'user@example.com').account_id
        rows = [QianReading(device_id='legacy-secret', question='legacy private', sign_id=1, response='legacy answer'),
                QianReading(device_id=None, question='unowned private', sign_id=2, response='unowned answer'),
                QianReading(device_id=None, question='owned full question, not masked', sign_id=3, response='saved partial answer',
                            context_json={'segments': [], 'camera_commands': []})]
        db.add_all(rows)
        db.flush()
        db.add(PaidQianOwner(reading_id=rows[2].id, account_id=account_id))
        db.commit()
        legacy, unowned, owned = [row.id for row in rows]
    models = (Account, AccountDevice, CreditLedger, QianReading, PaidQianOwner)
    before = [count(product, model) for model in models]
    missing = owned + 10000
    failures = []
    for reading_id in (legacy, unowned, missing):
        response = product.client.get(f'/api/v1/qian/readings/{reading_id}', headers={'X-Device-Id': 'legacy-secret'})
        assert response.status_code == 404
        assert response.headers['cache-control'] == 'no-store'
        failures.append(response.json())
    assert failures == [{'detail': '记录不存在'}] * 3
    response = product.client.get(f'/api/v1/qian/readings/{owned}')
    assert response.status_code == 200 and response.headers['cache-control'] == 'no-store'
    body = response.json()
    assert set(body) == {'id', 'question', 'sign_id', 'grade', 'response', 'context_json', 'created_at'}
    assert body['question'] == 'owned full question, not masked'
    assert body['response'] == 'saved partial answer'
    assert 'legacy-secret' not in response.text
    assert [count(product, model) for model in models] == before
    assert [row['id'] for row in product.client.get('/api/v1/qian/readings').json()] == [owned]
    with Session(product.engine) as db:
        assert db.scalar(select(QianReading.response).where(QianReading.id == owned)) == 'saved partial answer'

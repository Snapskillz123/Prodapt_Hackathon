import copy
import json
from datetime import date, timedelta

from backend.schemas import PlanDraft
from tests.conftest import DRAFT, register
from tests.test_tripai import preferences


def test_form_generates_and_persists_exact_preferences(client, providers, monkeypatch):
    async def structured(messages, schema):
        assert schema is PlanDraft  # No LLM preference extraction for validated form input.
        payload = json.loads(messages[-1]['content'])
        draft = copy.deepcopy(DRAFT)
        draft['days'] = [copy.deepcopy(DRAFT['days'][0]) for _ in range(payload['profile']['days'])]
        return PlanDraft.model_validate(draft)
    monkeypatch.setattr(providers, 'structured', structured)
    register(client)
    chat_id = client.post('/api/chats').json()['id']
    form = preferences()
    form.update(style='Relaxed', requirements='Keep afternoons quiet.')
    response = client.post(f'/api/chats/{chat_id}/preferences', json=form)
    assert response.status_code == 200
    result = response.json()
    assert result['profile']['style'] == 'Relaxed'
    assert result['profile']['requirements'] == 'Keep afternoons quiet.'
    assert result['profile']['budget'] == form['totalBudget']
    assert result['profile']['days'] == 2
    assert result['plan']['trace'][0] == 'validate_form_profile'
    assert result['version'] == 1
    assert client.get(f'/api/chats/{chat_id}').json()['plan'] == result['plan']


def test_form_request_access_and_invalid_dates(client):
    form = preferences()
    assert client.post('/api/chats/not-owned/preferences', json=form).status_code == 401
    register(client)
    assert client.post('/api/chats/not-owned/preferences', json=form).status_code == 404
    chat_id = client.post('/api/chats').json()['id']
    form['startDate'] = (date.today() - timedelta(days=1)).isoformat()
    form['endDate'] = date.today().isoformat()
    assert client.post(f'/api/chats/{chat_id}/preferences', json=form).status_code == 422


def test_form_provider_failure_preserves_conversation(client, providers):
    register(client)
    chat_id = client.post('/api/chats').json()['id']
    before = client.get(f'/api/chats/{chat_id}').json()
    providers.fail_places = True
    response = client.post(f'/api/chats/{chat_id}/preferences', json=preferences())
    assert response.status_code == 502
    assert client.get(f'/api/chats/{chat_id}').json() == before

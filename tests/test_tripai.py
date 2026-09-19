import asyncio
import copy
from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from backend.tripai.graph import build_trip_graph
from backend.tripai.schemas import TripRequest, TripDraft, TripResult
from backend.services import ServiceError
from tests.conftest import PLACES, register


def preferences():
    return {'destination': 'Jaipur', 'startDate': str(date.today() + timedelta(days=1)),
            'endDate': str(date.today() + timedelta(days=2)), 'travellers': 2,
            'totalBudget': 10000, 'interests': ['Culture', 'Food'], 'style': 'Relaxed', 'requirements': ''}


def draft():
    return {'region': 'Rajasthan, India', 'tagline': 'A relaxed cultural break',
            'days': [{'title': f'Day {i}', 'subtitle': 'Explore the city', 'activities': [
                {'placeId': 'place-1', 'time': '09:00', 'durationMinutes': 60,
                 'description': 'Visit the palace', 'cost': 200, 'category': 'Culture', 'budgetCategory': 'activities'},
                {'placeId': 'place-2', 'time': '11:00', 'durationMinutes': 60,
                 'description': 'Visit the museum', 'cost': 100, 'category': 'Culture', 'budgetCategory': 'activities'}
            ]} for i in range(1, 3)],
            'fixedCosts': {'accommodation': 1000, 'transport': 500, 'miscellaneous': 100},
            'packing': [{'id': 'essentials', 'name': 'Essentials',
                         'items': [{'id': 'water', 'name': 'Water bottle', 'checked': False}]}],
            'notes': ['Verify costs and opening hours.']}


class TripServices:
    def __init__(self):
        self.value = draft()
        self.invalid = 0
        self.calls = 0
        self.weather_failure = False

    async def places(self, *args):
        return copy.deepcopy(PLACES)

    async def weather(self, *args):
        if self.weather_failure:
            raise ServiceError('Unavailable')
        return []

    async def structured(self, messages, schema):
        assert schema is TripDraft
        self.calls += 1
        result = copy.deepcopy(self.value)
        if self.invalid:
            self.invalid -= 1
            result['days'][0]['activities'][0]['placeId'] = 'invented'
        return schema.model_validate(result)


def run(providers, request):
    return asyncio.run(build_trip_graph(providers).ainvoke({'request': request}, {'recursion_limit': 16}))['result']


def generation():
    return {'operation': 'generate', 'preferences': preferences()}


@pytest.mark.parametrize('field,value', [('travellers', 13), ('travellers', True), ('totalBudget', 950),
    ('totalBudget', 1001), ('interests', []), ('style', 'Fast'), ('requirements', 'x' * 1501)])
def test_form_limits(field, value):
    data = generation()
    data['preferences'][field] = value
    with pytest.raises(ValidationError):
        TripRequest.model_validate(data)


def test_operation_and_date_boundaries():
    with pytest.raises(ValidationError):
        TripRequest(operation='modify', modification='Cheaper')
    for start, end in [(date.today(), date.today()), (date.today() - timedelta(days=1), date.today()),
                       (date.today(), date.today() + timedelta(days=7))]:
        data = generation()
        data['preferences'].update(startDate=str(start), endDate=str(end))
        with pytest.raises(ValidationError):
            TripRequest.model_validate(data)


def test_generate_contract_and_budget():
    result = run(TripServices(), generation())
    TripResult.model_validate(result)
    assert result['budget']['estimatedSpend'] == 2200
    assert result['budget']['remaining'] == 7800
    assert result['trip']['days'][0]['activities'][0]['title'] == 'Test Palace'
    assert result['trace'] == ['validate_trip_request', 'lookup_trip_places', 'lookup_trip_weather',
                               'generate_trip_draft', 'validate_trip_draft', 'calculate_trip_budget']


def test_modify_preserves_identity_preferences_packing_and_recalculates():
    providers = TripServices()
    original = run(providers, generation())['trip']
    original['packing'][0]['items'][0]['checked'] = True
    snapshot = copy.deepcopy(original)
    providers.value['days'][0]['activities'][0]['cost'] = 0
    result = run(providers, {'operation': 'modify', 'existingTrip': original, 'modification': 'Make day one cheaper'})
    trip = result['trip']
    assert original == snapshot  # Failed or successful planning never mutates caller input.
    assert trip['id'] == original['id']
    assert trip['preferences'] == original['preferences']
    assert trip['packing'] == original['packing']
    assert trip['days'][0]['activities'][0]['id'] == original['days'][0]['activities'][0]['id']
    assert trip['days'][0]['activities'][0]['updated']
    assert not trip['days'][1]['activities'][0]['updated']
    assert result['budget']['estimatedSpend'] == 2000
    assert 'revise_trip_draft' in result['trace']


def test_food_not_double_counted_and_overspend_flagged():
    providers = TripServices()
    providers.value['days'][0]['activities'][0].update(budgetCategory='food', cost=9000)
    result = run(providers, generation())
    totals = {row['category']: row['amount'] for row in result['budget']['breakdown']}
    assert totals['food'] == 9000 and totals['activities'] == 400
    assert result['budget']['estimatedSpend'] == 11000
    assert result['budget']['remaining'] == -1000
    assert not result['budget']['withinBudget']


def test_bounded_repair():
    providers = TripServices()
    providers.invalid = 1
    run(providers, generation())
    assert providers.calls == 2
    providers.invalid = 2
    with pytest.raises(ServiceError, match='after one repair'):
        run(providers, generation())
    assert providers.calls == 4


@pytest.mark.parametrize('kind', ['overlap', 'duplicate', 'days', 'packing'])
def test_reject_invalid_business_drafts(kind):
    providers = TripServices()
    if kind == 'overlap':
        providers.value['days'][0]['activities'][1]['time'] = '09:20'
    elif kind == 'duplicate':
        providers.value['days'][0]['activities'][1]['placeId'] = 'place-1'
    elif kind == 'days':
        providers.value['days'].append(copy.deepcopy(providers.value['days'][0]))
    else:
        providers.value['packing'].append(copy.deepcopy(providers.value['packing'][0]))
    with pytest.raises(ServiceError):
        run(providers, generation())


def test_weather_failure_is_nonfatal():
    providers = TripServices()
    providers.weather_failure = True
    result = run(providers, generation())
    assert result['weather'] == []
    assert any('unavailable' in warning for warning in result['warnings'])


def test_authenticated_endpoint(client, app):
    assert client.post('/api/tripai/plan', json=generation()).status_code == 401
    register(client)
    app.state.trip_graph = build_trip_graph(TripServices())
    response = client.post('/api/tripai/plan', json=generation())
    assert response.status_code == 200
    trip = response.json()['trip']
    response = client.post('/api/tripai/plan', json={
        'operation': 'modify', 'existingTrip': trip, 'modification': 'Make this more relaxed'})
    assert response.status_code == 200
    assert response.json()['trip']['id'] == trip['id']
    bad = generation()
    bad['preferences']['travellers'] = 99
    assert client.post('/api/tripai/plan', json=bad).status_code == 422
    assert client.post('/api/tripai/plan', json=generation(),
                       headers={'origin': 'https://untrusted.example'}).status_code == 403

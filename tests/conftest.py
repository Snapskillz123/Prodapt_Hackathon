import copy
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import Settings
from backend.schemas import Extraction, PlanDraft
from backend.services import ServiceError


def profile_data():
    return {'destination': 'Jaipur, India', 'startDate': (date.today() + timedelta(days=1)).isoformat(),
            'days': 1, 'travelers': 2, 'budget': 10000, 'currency': 'INR', 'interests': 'history'}


PLACES = [{'id': 'place-1', 'name': 'Test Palace', 'address': 'Jaipur, India', 'lat': 26.92, 'lng': 75.82},
          {'id': 'place-2', 'name': 'Test Museum', 'address': 'Jaipur, India', 'lat': 26.93, 'lng': 75.83}]
DRAFT = {'summary': 'An easy day exploring Jaipur.', 'days': [{'title': 'Palaces and museums', 'activities': [
    {'placeId': 'place-1', 'time': '09:00', 'durationMinutes': 90, 'description': 'Explore the palace.', 'cost': 200},
    {'placeId': 'place-2', 'time': '11:00', 'durationMinutes': 60, 'description': 'Discover local history.', 'cost': 100}]}],
    'budget': {'accommodation': 0, 'food': 600, 'localTransport': 400, 'contingency': 200},
    'packing': ['Water bottle', 'Comfortable shoes'], 'notes': ['Confirm admission costs before visiting.']}


class FakeServices:
    """Deterministic providers for tests only. Never used by the running application."""
    def __init__(self):
        self.calls = []
        self.invalid_drafts = 0
        self.weather_failure = False
        self.fail_places = False

    async def structured(self, messages, schema):
        self.calls.append(schema.__name__)
        if schema is Extraction:
            text = messages[-1]['content']
            if text == 'hello':
                return Extraction.model_validate({'profile': {}, 'reply': 'Where would you like to go?', 'intent': 'conversation'})
            return Extraction.model_validate({'profile': profile_data(), 'reply': 'Let’s plan your trip.', 'intent': 'plan'})
        result = copy.deepcopy(DRAFT)
        if self.invalid_drafts:
            self.invalid_drafts -= 1
            result['days'][0]['activities'][0]['placeId'] = 'invented'
        return PlanDraft.model_validate(result)

    async def places(self, destination, interests):
        self.calls.append('places')
        if self.fail_places:
            raise ServiceError('Google Places is unavailable.')
        return copy.deepcopy(PLACES)

    async def weather(self, *args):
        self.calls.append('weather')
        if self.weather_failure:
            raise ServiceError('Weather unavailable.')
        return [{'date': profile_data()['startDate'], 'high': 30, 'low': 22, 'rain': 25}]

    async def close(self):
        pass


@pytest.fixture
def providers():
    return FakeServices()


@pytest.fixture
def app(tmp_path, providers):
    return create_app(Settings(data_dir=tmp_path), services=providers)


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client


def register(client, email='traveler@example.com'):
    return client.post('/api/auth/register', json={'name': 'Traveler', 'email': email, 'password': 'correct-horse-2026'})

import asyncio
import pytest
from backend.graph import build_graph
from backend.services import ServiceError


def run(providers, message='Plan my trip'):
    return asyncio.run(build_graph(providers).ainvoke({'history': [], 'message': message,
        'previous_profile': {}, 'previous_plan': None}, config={'recursion_limit': 15}))


def test_clarification_does_not_spend_place_or_weather_calls(providers):
    result = run(providers, 'hello')
    assert result['plan'] is None
    assert 'Still needed' in result['reply']
    assert providers.calls == ['Extraction']
    assert result['trace'] == ['extract_preferences', 'check_missing_preferences']


def test_happy_path_uses_all_meaningful_tools(providers):
    result = run(providers)
    assert result['plan']['budget']['total'] == 1500
    assert result['trace'] == ['extract_preferences', 'search_destination_places', 'fetch_trip_weather',
                               'draft_grounded_itinerary', 'validate_itinerary', 'package_travel_plan']


def test_one_invalid_draft_is_repaired(providers):
    providers.invalid_drafts = 1
    result = run(providers)
    assert result['repairs'] == 1
    assert 'repair_grounded_itinerary' in result['trace']
    assert providers.calls.count('PlanDraft') == 2


def test_repair_is_bounded(providers):
    providers.invalid_drafts = 5
    with pytest.raises(ServiceError, match='after one repair'):
        run(providers)
    assert providers.calls.count('PlanDraft') == 2


def test_weather_failure_is_nonfatal_and_disclosed(providers):
    providers.weather_failure = True
    result = run(providers)
    assert result['plan']['weather'] == []
    assert any('temporarily unavailable' in w for w in result['plan']['warnings'])


def test_no_fake_place_fallback(providers):
    providers.fail_places = True
    with pytest.raises(ServiceError):
        run(providers)
    assert 'PlanDraft' not in providers.calls

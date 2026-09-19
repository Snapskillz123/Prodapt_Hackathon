"""Offline dummy data and schema validation. Never instantiates API providers."""
import argparse
import copy
import json
from datetime import date, timedelta
from pathlib import Path

from pydantic import ValidationError

from ..schemas import Place
from .schemas import Trip, TripDraft, TripRequest, TripResult
from .tools import budget_for, materialize

MODELS = {'request': TripRequest, 'trip': Trip, 'draft': TripDraft, 'result': TripResult}


def build_samples():
    start = date.today() + timedelta(days=7)
    generation = {'operation': 'generate', 'preferences': {
        'destination': 'Jaipur, India', 'startDate': start.isoformat(),
        'endDate': (start + timedelta(days=1)).isoformat(), 'travellers': 2,
        'totalBudget': 10000, 'interests': ['Culture', 'Food'],
        'style': 'Relaxed', 'requirements': 'Keep afternoons relaxed.'}}
    request = TripRequest.model_validate(generation)
    # Entirely fictional records: do not treat these as Google Places responses.
    places = [Place(id='dummy-palace', name='Dummy Palace', address='Fictional example in Jaipur',
                    lat=26.92, lng=75.82),
              Place(id='dummy-cafe', name='Dummy Cafe', address='Fictional example in Jaipur',
                    lat=26.93, lng=75.83)]
    draft = TripDraft.model_validate({
        'region': 'Rajasthan, India', 'tagline': 'Dummy itinerary for schema testing',
        'days': [{'title': f'Dummy day {index}', 'subtitle': 'Illustrative visits, not recommendations',
                  'activities': [
                      {'placeId': 'dummy-palace', 'time': '09:00', 'durationMinutes': 90,
                       'description': 'Dummy cultural visit.', 'cost': 300,
                       'category': 'Culture', 'budgetCategory': 'activities'},
                      {'placeId': 'dummy-cafe', 'time': '12:00', 'durationMinutes': 60,
                       'description': 'Dummy lunch for two.', 'cost': 400,
                       'category': 'Food', 'budgetCategory': 'food'}]}
                 for index in (1, 2)],
        'fixedCosts': {'accommodation': 3000, 'transport': 800, 'miscellaneous': 200},
        'packing': [{'id': 'essentials', 'name': 'Essentials', 'items': [
            {'id': 'water', 'name': 'Water bottle', 'checked': False},
            {'id': 'charger', 'name': 'Phone charger', 'checked': False}]}],
        'notes': ['All places, costs and activities are dummy data.'],
    })
    # Also exercises local schedule, place-ID and budget business logic, without AI.
    trip = materialize(request, draft, places)
    # Stable sample identifiers make files easy to compare across exports.
    trip.id = 'dummy-trip-jaipur'
    for day_index, day in enumerate(trip.days, 1):
        day.id = f'dummy-day-{day_index}'
        for activity_index, activity in enumerate(day.activities, 1):
            activity.id = f'dummy-activity-{day_index}-{activity_index}'
    result = TripResult(trip=trip, budget=budget_for(trip), weather=[],
                        warnings=['DUMMY DATA: not a live itinerary or forecast.'],
                        notes=draft.notes, trace=['offline_sample_validation'])
    modification = TripRequest(operation='modify', existingTrip=trip,
                               modification='Make day two cheaper and more relaxed.')
    invalid = copy.deepcopy(generation)
    invalid['preferences'].update(travellers=99, totalBudget=-500)
    return {
        'valid-generation.json': generation,
        'valid-modification.json': modification.model_dump(mode='json', exclude_none=True),
        'valid-trip.json': trip.model_dump(mode='json'),
        'valid-draft.json': draft.model_dump(mode='json'),
        'valid-result.json': result.model_dump(mode='json'),
        'invalid-generation.json': invalid,
    }


def show_errors(error):
    for issue in error.errors(include_input=False, include_url=False):
        location = '.'.join(map(str, issue['loc'])) or 'request'
        print(f"  {location}: {issue['msg']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', type=Path, help='Validate your own JSON file without API calls.')
    parser.add_argument('--schema', choices=MODELS, default='request')
    parser.add_argument('--export', action='store_true', help='Regenerate the six dummy JSON files with future dates.')
    args = parser.parse_args()
    if args.file:
        if args.export:
            parser.error('--file and --export cannot be combined.')
        try:
            MODELS[args.schema].model_validate_json(args.file.read_text(encoding='utf-8-sig'))
        except ValidationError as error:
            print('INVALID')
            show_errors(error)
            return 1
        except OSError:
            print('Could not read the JSON file. Check its path and permissions.')
            return 1
        print(f'VALID: {args.schema} schema. No API calls made.')
        return 0

    samples = build_samples()
    for name, schema in [('valid-generation.json', TripRequest), ('valid-modification.json', TripRequest),
                         ('valid-trip.json', Trip), ('valid-draft.json', TripDraft), ('valid-result.json', TripResult)]:
        schema.model_validate(samples[name])
        print(f'PASS: {name}')
    try:
        TripRequest.model_validate(samples['invalid-generation.json'])
    except ValidationError as error:
        print('PASS: invalid-generation.json rejected as expected')
        show_errors(error)
    else:
        raise AssertionError('Invalid sample unexpectedly passed validation.')
    budget = samples['valid-result.json']['budget']
    assert budget['estimatedSpend'] == 5400 and budget['remaining'] == 4600
    print('PASS: estimated spend INR 5,400; remaining INR 4,600. No API calls made.')
    if args.export:
        destination = Path(__file__).resolve().parents[2] / 'examples' / 'tripai'
        destination.mkdir(parents=True, exist_ok=True)
        for name, payload in samples.items():
            (destination / name).write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
        print('Exported generated examples to examples/tripai. Existing sample files were refreshed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

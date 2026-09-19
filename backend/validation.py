"""Deterministic business rules, independent of the model and web framework."""
from decimal import Decimal

from .schemas import PlanDraft, Profile


def validate_plan(draft: PlanDraft, profile: Profile, places: list[dict]):
    if profile.missing():
        raise ValueError('Required trip preferences are missing.')
    if len(draft.days) != profile.days:
        raise ValueError(f'Expected exactly {profile.days} days.')
    known = {p['id']: p for p in places}
    days, activity_total = [], Decimal('0')
    for i, day in enumerate(draft.days):
        previous_end, seen, activities = 0, set(), []
        for item in day.activities:
            if item.placeId not in known:
                raise ValueError('An activity references a place ID outside the supplied records.')
            if item.placeId in seen:
                raise ValueError('The same place is scheduled twice in one day.')
            seen.add(item.placeId)
            hours, minutes = map(int, item.time.split(':'))
            start = hours * 60 + minutes
            if start < previous_end:
                raise ValueError('Activities overlap or leave less than 20 minutes between visits.')
            if start < 7 * 60 or start + item.durationMinutes > 22 * 60:
                raise ValueError('Visits must start after 07:00 and finish by 22:00.')
            previous_end = start + item.durationMinutes + 20
            cost = Decimal(str(item.cost)).quantize(Decimal('0.01'))
            activity_total += cost
            activities.append({'place': known[item.placeId], 'time': item.time,
                               'duration': f'{item.durationMinutes} min', 'durationMinutes': item.durationMinutes,
                               'description': item.description, 'cost': float(cost)})
        days.append({'day': i + 1, 'title': day.title, 'activities': activities})
    costs = {k: Decimal(str(v)).quantize(Decimal('0.01')) for k, v in draft.budget.model_dump().items()}
    costs['activities'] = activity_total
    total = sum(costs.values(), Decimal('0'))
    return {'summary': draft.summary, 'days': days, 'budget': {**{k: float(v) for k, v in costs.items()},
            'total': float(total), 'remaining': float(Decimal(str(profile.budget)) - total)},
            'packing': draft.packing, 'notes': draft.notes}

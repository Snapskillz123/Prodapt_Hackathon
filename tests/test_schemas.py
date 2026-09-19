import copy
import pytest
from pydantic import ValidationError
from backend.schemas import Profile, PlanDraft, Register, MessageRequest
from backend.validation import validate_plan
from .conftest import DRAFT, PLACES, profile_data


@pytest.mark.parametrize('changes', [{'days': 8}, {'days': 0}, {'days': True}, {'travelers': 21},
    {'startDate': '2027-02-30'}, {'budget': float('inf')}, {'currency': 'FAKE'}, {'extra_field': 'not allowed'}])
def test_invalid_preferences_rejected(changes):
    with pytest.raises(ValidationError):
        Profile.model_validate({**profile_data(), **changes})


def test_blank_message_rejected():
    with pytest.raises(ValidationError):
        MessageRequest(message='   ')


def test_password_never_appears_in_model_repr():
    r = Register(name='Test', email='test@example.com', password='private-password-123')
    assert 'private-password-123' not in repr(r)


def test_budget_is_computed_not_trusted():
    plan = validate_plan(PlanDraft.model_validate(DRAFT), Profile.model_validate(profile_data()), PLACES)
    assert plan['budget']['total'] == 1500
    assert plan['budget']['remaining'] == 8500


def test_over_budget_is_visible():
    p = Profile.model_validate({**profile_data(), 'budget': 500})
    plan = validate_plan(PlanDraft.model_validate(DRAFT), p, PLACES)
    assert plan['budget']['remaining'] == -1000


@pytest.mark.parametrize('change,match', [('place', 'outside'), ('overlap', 'overlap'), ('duplicate', 'twice'), ('night', '22:00')])
def test_business_constraints(change, match):
    raw = copy.deepcopy(DRAFT)
    activities = raw['days'][0]['activities']
    if change == 'place': activities[0]['placeId'] = 'fabricated'
    if change == 'overlap': activities[1]['time'] = '09:30'
    if change == 'duplicate': activities[1]['placeId'] = 'place-1'
    if change == 'night': activities[1]['time'] = '23:00'
    with pytest.raises(ValueError, match=match):
        validate_plan(PlanDraft.model_validate(raw), Profile.model_validate(profile_data()), PLACES)


def test_negative_estimate_rejected():
    raw = copy.deepcopy(DRAFT)
    raw['budget']['food'] = -1
    with pytest.raises(ValidationError):
        PlanDraft.model_validate(raw)


def test_day_count_must_match():
    with pytest.raises(ValueError, match='exactly 2'):
        validate_plan(PlanDraft.model_validate(DRAFT), Profile.model_validate({**profile_data(), 'days': 2}), PLACES)

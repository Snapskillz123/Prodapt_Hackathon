"""Proposed TripAI wire contract, based on the supplied frontend README.

Confirm property names against src/types/trip.ts before connecting the frontend.
Prices are INR for the whole party. End dates are inclusive.
"""
from datetime import date
from typing import Annotated, Literal, TypedDict

from pydantic import Field, model_validator

from ..schemas import StrictModel, Place, ForecastDay

Money = Annotated[float, Field(ge=0, le=10_000_000, allow_inf_nan=False)]
Text = Annotated[str, Field(min_length=1, max_length=700)]
Interest = Literal['Beaches', 'Food', 'Adventure', 'Culture', 'Nature', 'Shopping', 'Nightlife', 'Relaxation']
TravelStyle = Literal['Relaxed', 'Balanced', 'Packed']
BudgetCategory = Literal['accommodation', 'food', 'transport', 'activities', 'miscellaneous']


class TripPreferences(StrictModel):
    destination: str = Field(min_length=2, max_length=100)
    startDate: date
    endDate: date
    travellers: int = Field(ge=1, le=12, strict=True)
    totalBudget: Money = Field(ge=1000, multiple_of=100)
    interests: list[Interest] = Field(min_length=1, max_length=8)
    style: TravelStyle
    requirements: str = Field(default='', max_length=1500)

    @model_validator(mode='after')
    def check_dates(self):
        if self.endDate <= self.startDate:
            raise ValueError('End date must be after start date.')
        if self.day_count > 7:
            raise ValueError('The backend currently supports at most seven inclusive trip days.')
        if len(set(self.interests)) != len(self.interests):
            raise ValueError('Interests must be unique.')
        return self

    @property
    def day_count(self):
        return (self.endDate - self.startDate).days + 1


class Activity(StrictModel):
    id: str = Field(min_length=1, max_length=100)
    time: str = Field(pattern=r'^([01]\d|2[0-3]):[0-5]\d$')
    title: Text
    description: Text
    location: Text
    cost: Money
    duration: str = Field(min_length=1, max_length=50)
    category: Interest
    budgetCategory: Literal['food', 'activities']
    updated: bool = False


class ItineraryDay(StrictModel):
    id: str = Field(min_length=1, max_length=100)
    title: Text
    subtitle: Text
    activities: list[Activity] = Field(min_length=1, max_length=6)


class FixedCosts(StrictModel):
    accommodation: Money
    transport: Money
    miscellaneous: Money


class PackingItem(StrictModel):
    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=180)
    checked: bool = False


class PackingCategory(StrictModel):
    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=100)
    items: list[PackingItem] = Field(min_length=1, max_length=15)


class Trip(StrictModel):
    id: str = Field(min_length=1, max_length=100)
    region: Text
    tagline: Text
    artwork: Literal['goa', 'jaipur', 'manali']
    preferences: TripPreferences
    days: list[ItineraryDay] = Field(min_length=2, max_length=7)
    fixedCosts: FixedCosts
    packing: list[PackingCategory] = Field(min_length=1, max_length=8)

    @model_validator(mode='after')
    def check_structure(self):
        if len(self.days) != self.preferences.day_count:
            raise ValueError('Day count must match inclusive travel dates.')
        collections = [self.days, [a for d in self.days for a in d.activities],
                       self.packing, [i for c in self.packing for i in c.items]]
        for items in collections:
            if len({i.id for i in items}) != len(items):
                raise ValueError('Day, activity, packing section and packing item IDs must be unique within their type.')
        return self


class TripRequest(StrictModel):
    operation: Literal['generate', 'modify']
    preferences: TripPreferences | None = None
    existingTrip: Trip | None = None
    modification: str | None = Field(default=None, min_length=1, max_length=1000)

    @model_validator(mode='after')
    def check_operation(self):
        if self.operation == 'generate':
            if self.preferences is None or self.existingTrip is not None or self.modification is not None:
                raise ValueError('Generation requires only preferences.')
            if self.preferences.startDate < date.today():
                raise ValueError('Departure date must be today or later.')
        elif self.existingTrip is None or self.modification is None or self.preferences is not None:
            raise ValueError('Modification requires only existingTrip and modification.')
        return self


class ActivityDraft(StrictModel):
    placeId: str = Field(min_length=1, max_length=250)
    time: str = Field(pattern=r'^([01]\d|2[0-3]):[0-5]\d$')
    durationMinutes: int = Field(ge=15, le=360, strict=True)
    description: Text
    cost: Money
    category: Interest
    budgetCategory: Literal['food', 'activities']


class DayDraft(StrictModel):
    title: Text
    subtitle: Text
    activities: list[ActivityDraft] = Field(min_length=1, max_length=6)


class TripDraft(StrictModel):
    region: Text
    tagline: Text
    days: list[DayDraft] = Field(min_length=2, max_length=7)
    fixedCosts: FixedCosts
    packing: list[PackingCategory] = Field(min_length=1, max_length=8)
    notes: list[Text] = Field(max_length=8)


class BudgetBreakdown(StrictModel):
    category: BudgetCategory
    amount: float = Field(ge=0, allow_inf_nan=False)
    description: Text


class BudgetSummary(StrictModel):
    breakdown: list[BudgetBreakdown]
    estimatedSpend: float = Field(ge=0, allow_inf_nan=False)
    remaining: float = Field(allow_inf_nan=False)
    withinBudget: bool


class TripResult(StrictModel):
    trip: Trip
    budget: BudgetSummary
    weather: list[ForecastDay]
    warnings: list[str]
    notes: list[str]
    trace: list[str]


class RequestInput(StrictModel):
    request: TripRequest


class PlacesInput(StrictModel):
    preferences: TripPreferences


class WeatherInput(PlacesInput):
    places: list[Place] = Field(min_length=1, max_length=40)


class DraftInput(WeatherInput):
    request: TripRequest
    weather: list[ForecastDay] = Field(max_length=16)
    correction: str | None = None


class ValidateInput(StrictModel):
    request: TripRequest
    draft: TripDraft
    places: list[Place] = Field(min_length=1, max_length=40)


class FinalizeInput(StrictModel):
    trip: Trip
    weather: list[ForecastDay]
    warnings: list[str]
    notes: list[str]
    trace: list[str]


class TripState(TypedDict, total=False):
    request: dict
    preferences: dict
    places: list[dict]
    weather: list[dict]
    warnings: list[str]
    draft: dict
    trip: dict
    correction: str | None
    repairs: int
    trace: list[str]
    result: dict

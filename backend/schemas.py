from datetime import date
from typing import Annotated, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator

Amount = Annotated[float, Field(ge=0, le=10_000_000, allow_inf_nan=False)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Register(StrictModel):
    name: str = Field(min_length=1, max_length=60)
    email: EmailStr = Field(max_length=254)
    password: SecretStr = Field(min_length=10, max_length=128)


class Login(StrictModel):
    email: EmailStr = Field(max_length=254)
    password: SecretStr = Field(min_length=1, max_length=128)


class MessageRequest(StrictModel):
    message: str = Field(min_length=1, max_length=3000)


class Profile(StrictModel):
    destination: str | None = Field(default=None, min_length=2, max_length=150)
    startDate: date | None = None
    days: int | None = Field(default=None, ge=1, le=7, strict=True)
    travelers: int | None = Field(default=None, ge=1, le=20, strict=True)
    budget: Amount | None = None
    currency: Literal['INR', 'USD', 'EUR', 'GBP'] = 'INR'
    interests: str = Field(default='A balanced mix', max_length=600)
    style: Literal['Relaxed', 'Balanced', 'Packed'] = 'Balanced'
    requirements: str = Field(default='', max_length=1500)

    def missing(self):
        return [key for key in ('destination', 'startDate', 'days', 'travelers', 'budget') if not getattr(self, key)]


class Extraction(StrictModel):
    profile: Profile
    reply: str = Field(min_length=1, max_length=2000)
    intent: Literal['plan', 'conversation']


class Place(StrictModel):
    id: str = Field(min_length=1, max_length=250)
    name: str = Field(min_length=1, max_length=300)
    address: str = Field(max_length=700)
    lat: float = Field(ge=-90, le=90, allow_inf_nan=False)
    lng: float = Field(ge=-180, le=180, allow_inf_nan=False)


class ActivityDraft(StrictModel):
    placeId: str = Field(min_length=1, max_length=250)
    time: str = Field(pattern=r'^([01]\d|2[0-3]):[0-5]\d$')
    durationMinutes: int = Field(ge=15, le=360, strict=True)
    description: str = Field(min_length=1, max_length=700)
    cost: Amount


class DayDraft(StrictModel):
    title: str = Field(min_length=1, max_length=150)
    activities: list[ActivityDraft] = Field(min_length=1, max_length=4)


class BudgetDraft(StrictModel):
    accommodation: Amount
    food: Amount
    localTransport: Amount
    contingency: Amount


class PlanDraft(StrictModel):
    summary: str = Field(min_length=1, max_length=1500)
    days: list[DayDraft] = Field(min_length=1, max_length=7)
    budget: BudgetDraft
    packing: list[Annotated[str, Field(min_length=1, max_length=180)]] = Field(min_length=1, max_length=20)
    notes: list[Annotated[str, Field(max_length=500)]] = Field(max_length=8)


class ForecastDay(StrictModel):
    date: date
    high: float
    low: float
    rain: float = Field(ge=0, le=100)


class ScheduledActivity(StrictModel):
    place: Place
    time: str = Field(pattern=r'^([01]\d|2[0-3]):[0-5]\d$')
    duration: str
    durationMinutes: int = Field(ge=15, le=360)
    description: str = Field(max_length=700)
    cost: Amount


class ScheduledDay(StrictModel):
    day: int = Field(ge=1, le=7)
    title: str
    activities: list[ScheduledActivity] = Field(min_length=1, max_length=4)


class BudgetTotals(BudgetDraft):
    activities: Amount
    total: float = Field(ge=0, allow_inf_nan=False)
    remaining: float = Field(allow_inf_nan=False)


class ValidatedPlan(StrictModel):
    summary: str
    days: list[ScheduledDay]
    budget: BudgetTotals
    packing: list[str]
    notes: list[str]


class TravelPlan(ValidatedPlan):
    profile: Profile
    weather: list[ForecastDay]
    warnings: list[str]
    generatedAt: str
    trace: list[str]
    sources: list[str]


class HistoryMessage(StrictModel):
    role: Literal['user', 'assistant']
    content: str = Field(max_length=5000)


class ExtractInput(StrictModel):
    history: list[HistoryMessage] = Field(max_length=12)
    message: str = Field(min_length=1, max_length=3000)
    previous_profile: Profile
    previous_plan: dict | None = None


class ClarifyInput(StrictModel):
    profile: Profile
    reply: str = Field(max_length=2000)


class FormProfileInput(StrictModel):
    profile: Profile


class SearchInput(StrictModel):
    destination: str = Field(min_length=2, max_length=150)
    interests: str = Field(max_length=600)


class WeatherInput(StrictModel):
    profile: Profile
    place: Place


class DraftInput(StrictModel):
    profile: Profile
    message: str = Field(min_length=1, max_length=3000)
    places: list[Place] = Field(min_length=1, max_length=40)
    weather: list[ForecastDay] = Field(max_length=16)
    previous_plan: dict | None = None
    validation_error: str | None = None


class ValidateInput(StrictModel):
    draft: PlanDraft
    profile: Profile
    places: list[Place] = Field(min_length=1, max_length=40)


class PackageInput(StrictModel):
    plan: ValidatedPlan
    profile: Profile
    weather: list[ForecastDay]
    warnings: list[str]
    trace: list[str]


class PlanningState(TypedDict, total=False):
    """Graph transport state. Pydantic validates every tool boundary."""
    history: list[dict]
    form_profile: dict | None
    message: str
    previous_profile: dict
    previous_plan: dict | None
    profile: dict
    reply: str
    intent: str
    places: list[dict]
    weather: list[dict]
    warnings: list[str]
    draft: dict
    plan: dict | None
    validation_error: str | None
    repairs: int
    trace: list[str]

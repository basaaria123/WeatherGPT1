"""Pydantic request/response models — the wire contract shared with the frontend.

Field names here are the single source of truth; the React client mirrors them
exactly, so renaming anything in this file is a breaking API change.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

UserType = Literal["farmer", "fisherman", "traveler", "commuter", "aviation", "urban", "general"]
ResponseMode = Literal["normal", "simple", "emergency"]
RiskLevel = Literal["Low", "Moderate", "High", "Severe"]
Intent = Literal["current_weather", "forecast", "alert_check", "climate_trend", "out_of_scope"]

SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "English",
    "hi": "हिन्दी",
    "te": "తెలుగు",
    "as": "অসমীয়া",
    "bn": "বাংলা",
    "mr": "मराठी",
}

USER_TYPES: tuple[str, ...] = ("farmer", "fisherman", "traveler", "commuter", "aviation", "urban", "general")

HAZARDS: tuple[str, ...] = (
    "Heavy Rainfall",
    "Flood Risk",
    "Strong Wind",
    "Extreme Heat",
    "Lightning/Storm",
    "None",
)


# ---------------------------------------------------------------------------
# Risk engine contract (Role 2.1) — consumed by alerts, timeline, map, chat.
# ---------------------------------------------------------------------------
class RiskOutput(BaseModel):
    """The shared risk contract. Nothing outside the risk engine may build one."""

    risk_score: int = Field(..., ge=0, le=100)
    risk_level: RiskLevel
    detected_hazard: str
    hazard_scores: dict[str, int] = Field(default_factory=dict)
    # Human-readable English drivers, for the API and debugging.
    drivers: list[str] = Field(default_factory=list)
    # The same drivers as {code, value, unit} so any language can render them.
    # The engine stays language-neutral; i18n does the wording.
    driver_details: list[dict[str, Any]] = Field(default_factory=list)


class LocationOut(BaseModel):
    name: str
    admin1: str | None = None
    country: str | None = None
    latitude: float
    longitude: float
    timezone: str | None = None

    @property
    def label(self) -> str:
        parts = [self.name]
        if self.admin1 and self.admin1 != self.name:
            parts.append(self.admin1)
        return ", ".join(parts)


class CurrentWeatherOut(BaseModel):
    """Only fields the provider actually returned are populated; the rest stay None
    so the UI can omit them instead of rendering 'N/A'."""

    temperature_c: float | None = None
    apparent_temperature_c: float | None = None
    humidity_pct: float | None = None
    precipitation_mm: float | None = None
    precipitation_probability_pct: float | None = None
    wind_speed_kmh: float | None = None
    wind_gust_kmh: float | None = None
    wind_direction_deg: float | None = None
    pressure_hpa: float | None = None
    cloud_cover_pct: float | None = None
    visibility_km: float | None = None
    weather_code: int | None = None
    condition: str | None = None
    is_day: bool | None = None
    observed_at: str | None = None


class HourPoint(BaseModel):
    time: str
    temperature_c: float | None = None
    precipitation_probability_pct: float | None = None
    precipitation_mm: float | None = None
    wind_speed_kmh: float | None = None
    weather_code: int | None = None
    condition: str | None = None
    risk_level: RiskLevel = "Low"
    risk_score: int = 0


class DayPoint(BaseModel):
    date: str
    temp_max_c: float | None = None
    temp_min_c: float | None = None
    precipitation_sum_mm: float | None = None
    precipitation_probability_pct: float | None = None
    wind_speed_max_kmh: float | None = None
    weather_code: int | None = None
    condition: str | None = None
    risk_level: RiskLevel = "Low"
    risk_score: int = 0


class ImpactCard(BaseModel):
    category: str
    status: Literal["Safe", "Caution", "Avoid"]
    headline: str
    detail: str


class HistoricalComparison(BaseModel):
    event_name: str
    event_date: str
    region: str
    similarity_score: int
    sentence: str
    source_note: str


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1)
    session_id: str | None = None
    # The place the client is currently showing. Used only when the question
    # does not name one, so the answer cannot describe a different city from
    # the dashboard around it.
    location: str | None = None
    user_type: UserType | None = None
    language: str | None = Field(default=None, description="ISO code; omit to auto-detect")
    response_mode: ResponseMode | None = None
    voice_response: bool = False
    latitude: float | None = None
    longitude: float | None = None


class DegradationInfo(BaseModel):
    """Everything that quietly fell back, surfaced honestly rather than hidden."""

    llm_used: bool = False
    llm_error: str | None = None
    weather_error: str | None = None
    translation_error: str | None = None
    tts_error: str | None = None
    fallback_reason: str | None = None


class VerificationInfo(BaseModel):
    verified: bool = True
    checked_numbers: list[str] = Field(default_factory=list)
    rejected_numbers: list[str] = Field(default_factory=list)
    note: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    explanation: str | None = None
    action_mode: bool = False
    actions: list[str] = Field(default_factory=list)
    response_mode: ResponseMode = "normal"
    intent: Intent = "current_weather"
    user_type: UserType = "general"
    language: str = "en"
    detected_language: str = "en"
    in_scope: bool = True
    location: LocationOut | None = None
    current: CurrentWeatherOut | None = None
    risk: RiskOutput | None = None
    impacts: list[ImpactCard] = Field(default_factory=list)
    historical_comparison: HistoricalComparison | None = None
    audio_base64: str | None = None
    audio_mime: str | None = None
    data_source: str = "live"
    raw_weather: dict[str, Any] | None = None
    verification: VerificationInfo = Field(default_factory=VerificationInfo)
    degraded: DegradationInfo = Field(default_factory=DegradationInfo)


class VoiceChatResponse(ChatResponse):
    transcript: str = ""
    transcription_confidence: float | None = None


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------
class AlertOut(BaseModel):
    id: int
    location: str
    latitude: float | None = None
    longitude: float | None = None
    alert_type: str
    severity: RiskLevel
    risk_score: int
    timestamp: str
    message: str
    actions: list[str] = Field(default_factory=list)
    historical_comparison: HistoricalComparison | None = None
    active: bool = True


class SubscriptionRequest(BaseModel):
    location: str = Field(..., min_length=1)
    hazard_types: list[str] = Field(default_factory=list)
    phone_number: str | None = None
    min_severity: RiskLevel = "High"


class SubscriptionOut(BaseModel):
    id: int
    location: str
    latitude: float | None = None
    longitude: float | None = None
    hazard_types: list[str]
    phone_number: str | None = None
    min_severity: RiskLevel
    created_at: str


# ---------------------------------------------------------------------------
# Weather / risk endpoints
# ---------------------------------------------------------------------------
class TimelineResponse(BaseModel):
    location: LocationOut
    generated_at: str
    data_source: str
    hours: list[HourPoint]


class ForecastResponse(BaseModel):
    location: LocationOut
    generated_at: str
    data_source: str
    days: list[DayPoint]


class InsightOut(BaseModel):
    """The "what should I know?" answer, derived from measured values only."""

    headline: str
    supporting: str = ""
    factors: list[str] = Field(default_factory=list)
    user_type: str = "general"
    actionable: bool = False


class CurrentWeatherResponse(BaseModel):
    location: LocationOut
    generated_at: str
    data_source: str
    current: CurrentWeatherOut
    risk: RiskOutput
    impacts: list[ImpactCard] = Field(default_factory=list)
    insight: InsightOut | None = None
    # Official alerts are a separate concept from a detected hazard: this counts
    # warnings actually issued and stored for this location, which may be zero
    # while risk is high.
    official_alert_count: int = 0


class RiskMapEntry(BaseModel):
    location: str
    admin1: str | None = None
    latitude: float
    longitude: float
    risk_score: int
    risk_level: RiskLevel
    detected_hazard: str


class RiskMapResponse(BaseModel):
    generated_at: str
    data_source: str
    locations: list[RiskMapEntry]
    errors: list[str] = Field(default_factory=list)


class ClimateTrendResponse(BaseModel):
    location: LocationOut
    generated_at: str
    data_source: str
    period: str
    summary: str
    metrics: dict[str, Any]
    llm_used: bool = False

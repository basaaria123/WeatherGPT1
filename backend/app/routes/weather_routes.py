"""Weather data endpoints.

Every risk value on these responses comes from ``risk_engine``; none of them
recomputes anything locally, which is what keeps the timeline, the map and the
chat answer in agreement.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from ..config import get_settings
from ..db import fetch_alerts
from ..schemas import (
    ClimateTrendResponse,
    CurrentWeatherResponse,
    AdvisoryOut,
    CurrentWeatherOut,
    EmergencyOut,
    InsightOut,
    DayPoint,
    ForecastResponse,
    HourPoint,
    LocationOut,
    TimelineResponse,
)
from ..services import advisory, climate, risk_engine, weather
from ..services.weather import WeatherError

router = APIRouter(tags=["weather"])


def _resolve(location: str | None, latitude: float | None, longitude: float | None):
    if latitude is not None and longitude is not None:
        return weather.Location(name=location or "Selected location", latitude=latitude, longitude=longitude)
    if not location:
        raise HTTPException(status_code=422, detail="Provide either a location name or latitude and longitude.")
    found = weather.geocode(location)
    if found is None:
        raise HTTPException(
            status_code=404,
            detail=f"I could not find a place called '{location}'. Please check the spelling and try again.",
        )
    return found


def _bundle(location):
    try:
        return weather.fetch_weather(location)
    except WeatherError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _location_out(location) -> LocationOut:
    return LocationOut(
        name=location.name,
        admin1=location.admin1,
        country=location.country,
        latitude=location.latitude,
        longitude=location.longitude,
        timezone=location.timezone,
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@router.get("/geocode")
def geocode(q: str = Query(..., min_length=1, description="Place name to resolve")) -> dict:
    found = weather.geocode(q)
    if found is None:
        raise HTTPException(
            status_code=404,
            detail=f"I could not find a place called '{q}'. Please check the spelling and try again.",
        )
    return {"location": _location_out(found).model_dump()}


@router.get("/geocode/reverse")
def reverse_geocode(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
) -> dict:
    """Nearest covered city to a device coordinate.

    Returned as ``nearest``, not as the caller's position: the app covers a
    fixed set of places and this is the closest of them, which the UI says
    plainly rather than implying pinpoint accuracy.
    """
    found = weather.nearest_location(lat, lon)
    if found is None:
        raise HTTPException(status_code=404, detail="No covered location is near that position.")
    return {"location": _location_out(found).model_dump(), "nearest": True}


@router.get("/weather/current", response_model=CurrentWeatherResponse)
def current_weather(
    location: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    language: str = "en",
    user_type: str | None = Query(None, description="Tailors ordering and emphasis, never the facts"),
) -> CurrentWeatherResponse:
    resolved = _resolve(location, latitude, longitude)
    bundle = _bundle(resolved)
    risk = risk_engine.assess(bundle)

    # Warnings actually issued for this place — deliberately not derived from
    # the risk score, so the UI can say "hazard detected, no warning issued".
    try:
        official = len(fetch_alerts(location=bundle.location.name, limit=20))
    except Exception:  # noqa: BLE001 - an alert-store hiccup must not blank the dashboard
        official = 0

    return CurrentWeatherResponse(
        location=_location_out(bundle.location),
        generated_at=_now(),
        data_source=bundle.source,
        current=CurrentWeatherOut(**{
            k: v for k, v in (bundle.current or {}).items() if k in CurrentWeatherOut.model_fields
        }),
        risk=risk,
        impacts=advisory.impact_cards(bundle, risk, language, user_type),
        insight=InsightOut(**advisory.headline_insight(bundle, risk, user_type, language)),
        # The dashboard reaches emergency mode without anyone having to ask a
        # question, and carries the same advisory the chat would give.
        advisory=AdvisoryOut(**advisory.build_advisory(risk, user_type, language)),
        emergency=EmergencyOut(**advisory.build_emergency(bundle, risk, user_type, language)),
        official_alert_count=official,
    )


@router.get("/advisory/personas")
def advisory_personas(
    location: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    language: str = "en",
) -> dict:
    """The same conditions read by every persona at once.

    One weather fact fanning out into five different decisions is the clearest
    statement of what this product does, so it gets its own endpoint rather than
    five round trips.
    """
    resolved = _resolve(location, latitude, longitude)
    bundle = _bundle(resolved)
    risk = risk_engine.assess(bundle)
    return {
        "location": _location_out(bundle.location).model_dump(),
        "generated_at": _now(),
        "data_source": bundle.source,
        "risk": risk.model_dump(),
        # The shared fact, stated once, above the differing advice.
        "shared_condition": advisory.smart_explanation(bundle, risk, language, mode="simple"),
        "personas": advisory.advisory_for_every_persona(risk, language),
        "disclaimer": advisory.disclaimer(language),
    }


@router.get("/weather/timeline", response_model=TimelineResponse)
def timeline(
    location: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    hours: int = Query(24, ge=1, le=48),
) -> TimelineResponse:
    """Next-N-hour timeline, each hour carrying its own risk level."""
    resolved = _resolve(location, latitude, longitude)
    bundle = _bundle(resolved)
    return TimelineResponse(
        location=_location_out(bundle.location),
        generated_at=_now(),
        data_source=bundle.source,
        hours=[HourPoint(**hour) for hour in risk_engine.timeline(bundle, hours=hours)],
    )


@router.get("/weather/forecast", response_model=ForecastResponse)
def forecast(
    location: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    days: int = Query(7, ge=1, le=7),
) -> ForecastResponse:
    resolved = _resolve(location, latitude, longitude)
    bundle = _bundle(resolved)
    points: list[DayPoint] = []
    for day in (bundle.daily or [])[:days]:
        risk = risk_engine.assess_day(day)
        points.append(
            DayPoint(
                date=day.get("date", ""),
                temp_max_c=day.get("temp_max_c"),
                temp_min_c=day.get("temp_min_c"),
                precipitation_sum_mm=day.get("precipitation_sum_mm"),
                precipitation_probability_pct=day.get("precipitation_probability_pct"),
                wind_speed_max_kmh=day.get("wind_speed_max_kmh"),
                weather_code=day.get("weather_code"),
                condition=day.get("condition"),
                risk_level=risk.risk_level,
                risk_score=risk.risk_score,
            )
        )
    return ForecastResponse(
        location=_location_out(bundle.location),
        generated_at=_now(),
        data_source=bundle.source,
        days=points,
    )


@router.get("/climate-trend", response_model=ClimateTrendResponse)
def climate_trend(
    location: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    language: str = "en",
    years: int = Query(climate.DEFAULT_YEARS, ge=2, le=20),
) -> ClimateTrendResponse:
    """Historical-anomaly summary for the current month so far."""
    settings = get_settings()
    resolved = _resolve(location, latitude, longitude)
    try:
        metrics = climate.compute_trend(resolved, years=years)
    except WeatherError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    summary, llm_used = climate.summarise(metrics, resolved.label, language)
    return ClimateTrendResponse(
        location=_location_out(resolved),
        generated_at=_now(),
        data_source=settings.weather_data_mode,
        period=f"{metrics.month_name} {metrics.year} so far, against the previous {metrics.years_compared} years",
        summary=summary,
        metrics=metrics.to_dict(),
        llm_used=llm_used,
    )

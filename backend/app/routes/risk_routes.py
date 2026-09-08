"""Risk endpoints.

Both of these are thin views over ``risk_engine``. The India risk map exists so
the UI can show, at a glance, the same scores that drive alerts and chat.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from ..config import get_settings
from ..schemas import MapHour, RiskMapEntry, RiskMapResponse, RiskOutput
from ..services import map_insight, risk_engine, weather
from ..services.alerts import DEFAULT_WATCH
from ..services.weather import WeatherError

router = APIRouter(tags=["risk"])


@router.get("/risk", response_model=RiskOutput)
def risk_for_location(
    location: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> RiskOutput:
    if latitude is not None and longitude is not None:
        resolved = weather.Location(name=location or "Selected location", latitude=latitude, longitude=longitude)
    elif location:
        resolved = weather.geocode(location)
        if resolved is None:
            raise HTTPException(status_code=404, detail=f"I could not find a place called '{location}'.")
    else:
        raise HTTPException(status_code=422, detail="Provide either a location name or latitude and longitude.")

    try:
        bundle = weather.fetch_weather(resolved)
    except WeatherError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return risk_engine.assess(bundle)


def _peak_insight(series: list[dict], user_type: str | None, lang: str) -> str | None:
    """This location's most eventful hour, in one sentence.

    The map's detail box has room for a single line, so it gets the hour that
    decides the score rather than the hour that happens to come first. Composed
    by the same module the map page's hourly readings come from, in the same
    translated corpus — a preview cannot say something the timeline below it
    then contradicts.
    """
    if not series:
        return None
    lines = map_insight.build(series, user_type, lang)
    if not lines:
        return None
    peak = max(range(len(series)), key=lambda i: series[i].get("risk_score") or 0)
    # An hour with nothing measured yields an empty line; fall back to the first
    # hour that had something to say rather than showing a blank.
    return lines[peak] or next((line for line in lines if line), None)


def _score_one(
    name: str, hours: int = 0, user_type: str | None = None, lang: str = "en"
) -> tuple[RiskMapEntry | None, str | None]:
    """Score one watched location, and carry out the readings already fetched.

    The bundle is retrieved to compute the risk either way; returning the
    measured values alongside it costs nothing and is what lets the map colour
    real observations rather than interpolate a field it does not have.
    """
    try:
        location = weather.geocode(name)
        if location is None:
            return None, f"{name}: could not be resolved"
        bundle = weather.fetch_weather(location)
    except WeatherError as exc:
        return None, f"{name}: {exc}"
    risk = risk_engine.assess(bundle)
    current = bundle.current or {}

    forward: list[MapHour] = []
    insight: str | None = None
    if hours > 0:
        series = risk_engine.timeline(bundle, hours=hours)
        for hour in series:
            forward.append(MapHour(**{k: v for k, v in hour.items() if k in MapHour.model_fields}))
        insight = _peak_insight(series, user_type, lang)

    return (
        RiskMapEntry(
            location=location.name,
            admin1=location.admin1,
            latitude=location.latitude,
            longitude=location.longitude,
            risk_score=risk.risk_score,
            risk_level=risk.risk_level,
            detected_hazard=risk.detected_hazard,
            temperature_c=current.get("temperature_c"),
            precipitation_mm=current.get("precipitation_mm"),
            precipitation_probability_pct=current.get("precipitation_probability_pct"),
            wind_speed_kmh=current.get("wind_speed_kmh"),
            wind_direction_deg=current.get("wind_direction_deg"),
            cloud_cover_pct=current.get("cloud_cover_pct"),
            hours=forward,
            insight=insight,
        ),
        None,
    )


@router.get("/risk-map", response_model=RiskMapResponse)
async def risk_map(
    limit: int = Query(24, ge=1, le=85),
    all_locations: bool = Query(False, description="Score the whole gazetteer instead of the watchlist"),
    hours: int = Query(0, ge=0, le=12, description="Forward hours to carry per location; 0 omits them"),
    user_type: str | None = Query(None, description="Whose reading the per-location line is written for"),
    language: str = Query("en", description="Language for the per-location line"),
) -> RiskMapResponse:
    """Per-location risk for the India map, from the same engine as everything else.

    A location that cannot be scored is reported in ``errors`` rather than
    silently dropped, so a partial map is visibly partial.
    """
    settings = get_settings()
    if all_locations:
        names = [loc.name for loc in weather.gazetteer_locations()][:limit]
    else:
        names = list(DEFAULT_WATCH)[:limit]

    results = await asyncio.gather(
        *(asyncio.to_thread(_score_one, name, hours, user_type, language) for name in names)
    )

    entries = [entry for entry, _ in results if entry is not None]
    errors = [error for _, error in results if error]
    entries.sort(key=lambda e: e.risk_score, reverse=True)

    return RiskMapResponse(
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        data_source=settings.weather_data_mode,
        locations=entries,
        errors=errors,
    )

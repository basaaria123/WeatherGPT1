"""Risk endpoints.

Both of these are thin views over ``risk_engine``. The India risk map exists so
the UI can show, at a glance, the same scores that drive alerts and chat.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from ..config import get_settings
from ..schemas import RiskMapEntry, RiskMapResponse, RiskOutput
from ..services import risk_engine, weather
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


def _score_one(name: str) -> tuple[RiskMapEntry | None, str | None]:
    try:
        location = weather.geocode(name)
        if location is None:
            return None, f"{name}: could not be resolved"
        bundle = weather.fetch_weather(location)
    except WeatherError as exc:
        return None, f"{name}: {exc}"
    risk = risk_engine.assess(bundle)
    return (
        RiskMapEntry(
            location=location.name,
            admin1=location.admin1,
            latitude=location.latitude,
            longitude=location.longitude,
            risk_score=risk.risk_score,
            risk_level=risk.risk_level,
            detected_hazard=risk.detected_hazard,
        ),
        None,
    )


@router.get("/risk-map", response_model=RiskMapResponse)
async def risk_map(
    limit: int = Query(24, ge=1, le=85),
    all_locations: bool = Query(False, description="Score the whole gazetteer instead of the watchlist"),
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

    results = await asyncio.gather(*(asyncio.to_thread(_score_one, name) for name in names))

    entries = [entry for entry, _ in results if entry is not None]
    errors = [error for _, error in results if error]
    entries.sort(key=lambda e: e.risk_score, reverse=True)

    return RiskMapResponse(
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        data_source=settings.weather_data_mode,
        locations=entries,
        errors=errors,
    )

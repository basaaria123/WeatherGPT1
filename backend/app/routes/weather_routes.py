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
    RoleIntelligenceOut,
    SpokenAdviceResponse,
    TimelineResponse,
)
from ..services import (
    advisory,
    climate,
    i18n,
    map_insight,
    risk_engine,
    role_intel,
    speech,
    voice_brief,
    weather,
)
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
        # `condition` arrives from the provider as an English phrase. Every other
        # sentence on the dashboard is translated, so leaving this one in English
        # put "Overcast" under a Tamil temperature — the one word on the card
        # that had not been through i18n. It is rendered from the WMO code the
        # same way the assistant renders it, so the two cannot disagree.
        current=CurrentWeatherOut(**{
            **{k: v for k, v in (bundle.current or {}).items() if k in CurrentWeatherOut.model_fields},
            "condition": i18n.condition_label((bundle.current or {}).get("weather_code"), language),
            # Lifted from the daily block of the same bundle rather than fetched
            # again. `is_day` is only true at the moment of the reading; these
            # two are what let the client tell day from night an hour later.
            "sunrise": (bundle.daily or [{}])[0].get("sunrise"),
            "sunset": (bundle.daily or [{}])[0].get("sunset"),
        }),
        risk=risk,
        impacts=advisory.impact_cards(bundle, risk, language, user_type),
        insight=InsightOut(**advisory.headline_insight(bundle, risk, user_type, language)),
        # The dashboard reaches emergency mode without anyone having to ask a
        # question, and carries the same advisory the chat would give.
        # The bundle matters: without it a calm day returns no actions at all,
        # and the section the dashboard now leads with would be blank on exactly
        # the days nothing is wrong. Passing it lets the calm-day fallback give
        # this reader their own reading of the measurements.
        advisory=AdvisoryOut(**advisory.build_advisory(risk, user_type, language, bundle=bundle)),
        # The same bundle and the same risk, read for whoever is asking.
        role_intelligence=RoleIntelligenceOut(**role_intel.build(bundle, risk, user_type, language)),
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
    language: str = Query("en", description="Language for the per-hour readings"),
    user_type: str | None = Query(None, description="Frames the per-hour readings; never the numbers"),
) -> TimelineResponse:
    """Next-N-hour timeline, each hour carrying its own risk level.

    `insights` is only built when a profile is asked for, so the existing
    callers of this endpoint get byte-identical responses.
    """
    resolved = _resolve(location, latitude, longitude)
    bundle = _bundle(resolved)
    series = risk_engine.timeline(bundle, hours=hours)
    return TimelineResponse(
        location=_location_out(bundle.location),
        generated_at=_now(),
        data_source=bundle.source,
        hours=[HourPoint(**hour) for hour in series],
        insights=map_insight.build(series, user_type, language) if user_type else [],
    )


@router.get("/weather/spoken-advice", response_model=SpokenAdviceResponse)
def spoken_advice(
    location: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    language: str = "en",
    user_type: str | None = Query(None, description="Whose advice is being read out"),
    topic: str = Query(
        "advice",
        pattern="^(advice|conditions|impact)$",
        description="Which of the dashboard's three questions to answer aloud",
    ),
) -> SpokenAdviceResponse:
    """One of three short scripts, written and rendered to be heard.

    The dashboard asks three questions and this answers whichever was pressed:

        conditions   what is happening
        advice       what should I do
        impact       why it matters to me

    Three separate scripts rather than one, because a listener who presses
    three buttons and hears the same paragraph three times has learned that the
    buttons are decoration.

    Deliberately a request of its own rather than a field on the dashboard
    response: synthesis costs a network round trip to the voice provider, and
    nobody should pay for it on every refresh when most readers never press
    play. It is only ever called by a reader pressing a button, which is also
    what keeps audio from ever starting on its own.

    The script is composed from this location's own bundle — the same risk, the
    same advisory, the same forecast hours and the same official alert count the
    dashboard is showing — so what is heard cannot differ from what is on
    screen.
    """
    resolved = _resolve(location, latitude, longitude)
    bundle = _bundle(resolved)
    risk = risk_engine.assess(bundle)
    lang = i18n.normalise_lang(language)
    profile = i18n.canonical_profile(user_type)

    try:
        official = len(fetch_alerts(location=bundle.location.name, limit=20))
    except Exception:  # noqa: BLE001 - an alert-store hiccup must not silence the advice
        official = 0

    # Six hours is as far ahead as "act now" advice can usefully point.
    hours = risk_engine.timeline(bundle, hours=6)
    spoken = {"framing": "", "steps": ""}

    if topic == "conditions":
        spoken["framing"] = voice_brief.conditions_brief(
            location=bundle.location.name, current=bundle.current or {}, hours=hours, lang=lang
        )
    elif topic == "impact":
        spoken["framing"] = voice_brief.impact_brief(
            impacts=advisory.impact_cards(bundle, risk, lang, user_type), lang=lang
        )
    else:
        spoken = voice_brief.compose_parts(
            location=bundle.location.name,
            risk=risk,
            advisory=advisory.build_advisory(risk, user_type, lang, bundle=bundle),
            hours=hours,
            alert_count=official,
            lang=lang,
        )

    text = " ".join(x for x in (spoken["framing"], spoken["steps"]) if x)
    if not text:
        raise HTTPException(
            status_code=404, detail="There is nothing to read aloud for this place yet."
        )

    # Made easier to listen to, never re-decided. The model may only rephrase
    # what the rules already produced, and anything it returns that grew or
    # that carries a figure the advice did not is discarded in favour of the
    # text above. This endpoint is only ever reached by a reader pressing play,
    # which is also what keeps it off the dashboard's render path.
    # Only the advice framing is ever handed to a model, and only because the
    # instructions it belongs to are held back separately (see `voice_brief`).
    #
    # The other two topics have no such half to protect — their whole script is
    # the message — and the model does not treat that as a description. Asked to
    # smooth "Right now in Guwahati it is 24°C with very heavy rain showers", it
    # returned "Head ashore immediately and secure your boat, as heavy rain
    # showers are starting now": an instruction, in the panel whose entire job
    # is to say what is happening rather than what to do. So they go out as
    # composed — already short, already simple, already translated.
    if topic == "advice":
        spoken["framing"] = voice_brief.polish(
            spoken["framing"],
            lang=lang,
            user_type=profile,
            location=bundle.location.name,
            risk_level=risk.risk_level,
        )
    text = " ".join(x for x in (spoken["framing"], spoken["steps"]) if x)

    audio = mime = note = provider = None
    tts_error = None
    try:
        # The reading's own level shapes the delivery: steadier and flatter as
        # it worsens, which is the only prosody control the provider gives us.
        rendered = speech.synthesize_detailed(text, lang, risk.risk_level)
        audio, mime, note, provider = (
            rendered.audio_base64, rendered.mime, rendered.note, rendered.provider,
        )
    except speech.SynthesisError as exc:
        # Every server-side voice failed. The script still goes out: the browser
        # has Puter and its own synthesiser left to try.
        tts_error = str(exc)

    return SpokenAdviceResponse(
        location=bundle.location.name,
        language=lang,
        user_type=profile,
        risk_level=risk.risk_level,
        text=text,
        audio_base64=audio,
        audio_mime=mime,
        audio_provider=provider,
        voice_note=note,
        tts_error=tts_error,
    )


@router.get("/weather/forecast", response_model=ForecastResponse)
def forecast(
    location: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    days: int = Query(7, ge=1, le=7),
    language: str = "en",
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
                condition=i18n.condition_label(day.get("weather_code"), language),
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

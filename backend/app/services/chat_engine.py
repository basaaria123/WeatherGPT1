# -*- coding: utf-8 -*-
"""Chat orchestration — the path every question travels.

    detect language -> translate to English -> understand -> fetch weather
      -> score risk (shared engine) -> generate -> verify numbers
      -> emergency mode if warranted -> answer in the user's language

Two properties are structural rather than best-effort:

*Grounding.* The generated answer is scanned by ``verification`` and discarded
in favour of the deterministic template if it quotes a measurement the provider
did not return. The template substitutes real values, so the fallback for a
hallucination is a correct answer, not an apology.

*Availability.* Every external dependency — Anthropic, Open-Meteo, the
translator, TTS — has a defined degraded path. The response reports what
degraded in ``degraded`` instead of hiding it.

Voice chat reuses this module wholesale; it does not reimplement any of it.
"""

from __future__ import annotations

import logging
from typing import Any

from ..config import get_settings
from ..schemas import (
    USER_TYPES,
    ChatResponse,
    CurrentWeatherOut,
    DegradationInfo,
    LocationOut,
    RiskOutput,
    VerificationInfo,
)
from . import advisory, history, i18n, language, llm, memory, nlp_fallback, risk_engine, verification, weather
from .weather import Location, WeatherError

log = logging.getLogger("weathergpt.chat")

VALID_INTENTS = {"current_weather", "forecast", "alert_check", "climate_trend", "out_of_scope"}
VALID_MODES = {"normal", "simple", "emergency"}


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------
def _sanitise_extraction(raw: dict[str, Any] | None, *, fallback_language: str) -> dict[str, Any] | None:
    """Coerce an LLM extraction into known-good values, or reject it."""
    if not isinstance(raw, dict):
        return None
    intent = str(raw.get("intent", "")).strip()
    if intent not in VALID_INTENTS:
        intent = "current_weather"
    mode = str(raw.get("response_mode", "normal")).strip()
    if mode not in VALID_MODES:
        mode = "normal"
    user_type = str(raw.get("user_type", "general")).strip().lower()
    if user_type not in USER_TYPES:
        user_type = "general"
    try:
        day_offset = max(0, min(6, int(raw.get("day_offset", 0))))
    except (TypeError, ValueError):
        day_offset = 0
    return {
        "in_scope": bool(raw.get("in_scope", True)),
        "intent": intent,
        "location": str(raw.get("location", "") or "").strip(),
        "use_previous_location": bool(raw.get("use_previous_location", False)),
        "day_offset": day_offset,
        "user_type": user_type,
        # The model never gets to declare an emergency; measured risk does.
        "response_mode": "normal" if mode == "emergency" else mode,
        "language": i18n.normalise_lang(raw.get("language") or fallback_language),
        "_source": "llm",
    }


def understand(
    query: str,
    state: memory.SessionState,
    *,
    detected_language: str,
    degraded: DegradationInfo,
) -> dict[str, Any]:
    """Structured interpretation, LLM first with a rules fallback."""
    known = state.location_name
    if llm.available():
        # llm.* already swallows provider errors, but this is the boundary where
        # a turn is either answered or lost, so it does not take that on trust.
        try:
            raw = llm.extract_query(query, history=state.transcript(4), known_location=known)
        except Exception as exc:  # noqa: BLE001
            log.warning("extraction raised unexpectedly: %s", exc)
            raw = None
        clean = _sanitise_extraction(raw, fallback_language=detected_language)
        if clean is not None:
            degraded.llm_used = True
            return clean
        degraded.llm_error = "extraction unavailable"
        degraded.fallback_reason = "LLM extraction failed; used rule-based understanding"
    return nlp_fallback.extract(query, language=detected_language, known_location=known)


# ---------------------------------------------------------------------------
# Location resolution
# ---------------------------------------------------------------------------
def resolve_location(
    extraction: dict[str, Any],
    state: memory.SessionState,
    *,
    latitude: float | None = None,
    longitude: float | None = None,
    original_query: str = "",
    selected: str | None = None,
) -> Location | None:
    """Work out which place the question is about.

    Order matters. A place named in the question always wins. Failing that the
    client's currently-selected location wins, ahead of session memory: the user
    can see that location on screen, so answering about a different one — even
    one they asked about earlier — reads as a bug, not as continuity.
    """
    name = extraction.get("location") or ""
    if name:
        found = weather.geocode(name)
        if found is not None:
            return found
        # The model named a place we cannot resolve; try the raw text before giving up.
        found = nlp_fallback.detect_location(original_query)
        if found is not None:
            return found

    if selected:
        found = weather.geocode(selected)
        if found is not None:
            return found

    if not name or extraction.get("use_previous_location"):
        if state.has_location():
            return Location(
                name=state.location_name or "your area",
                latitude=float(state.latitude),  # type: ignore[arg-type]
                longitude=float(state.longitude),  # type: ignore[arg-type]
                admin1=state.admin1,
            )

    if latitude is not None and longitude is not None:
        return Location(name="Your location", latitude=latitude, longitude=longitude, admin1=None)

    return nlp_fallback.detect_location(original_query)


# ---------------------------------------------------------------------------
# Data payload handed to the model
# ---------------------------------------------------------------------------
def build_weather_payload(bundle: Any, risk: RiskOutput, *, day_offset: int = 0) -> dict[str, Any]:
    """Compact set of real values. This doubles as the verifier's allow-list,
    so it deliberately contains nothing the answer should not be quoting."""
    cur = dict(bundle.current or {})
    window = bundle.hourly[:24]

    def total(key: str) -> float:
        return round(sum(float(h.get(key) or 0.0) for h in window), 1)

    def peak(key: str) -> float | None:
        values = [float(h[key]) for h in window if isinstance(h.get(key), (int, float))]
        return round(max(values), 1) if values else None

    def trough(key: str) -> float | None:
        values = [float(h[key]) for h in window if isinstance(h.get(key), (int, float))]
        return round(min(values), 1) if values else None

    payload: dict[str, Any] = {
        "location": bundle.location.label,
        "data_source": bundle.source,
        "observed_at": cur.get("observed_at"),
        "current": {k: v for k, v in cur.items() if v is not None},
        "next_24_hours": {
            "precipitation_total_mm": total("precipitation_mm"),
            "max_temperature_c": peak("temperature_c"),
            "min_temperature_c": trough("temperature_c"),
            "max_wind_gust_kmh": peak("wind_gust_kmh"),
            "max_precipitation_probability_pct": peak("precipitation_probability_pct"),
            "hours_with_rain": sum(1 for h in window if (h.get("precipitation_mm") or 0) >= 0.5),
        },
        "risk": {
            "risk_score": risk.risk_score,
            "risk_level": risk.risk_level,
            "detected_hazard": risk.detected_hazard,
        },
    }

    days = bundle.daily or []
    if day_offset > 0 and days:
        day = days[min(day_offset, len(days) - 1)]
        payload["requested_day"] = {k: v for k, v in day.items() if v is not None}
    payload["daily_forecast"] = [
        {k: v for k, v in day.items() if v is not None and k not in {"sunrise", "sunset"}}
        for day in days[:7]
    ]
    return payload


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def handle_chat(
    *,
    query: str,
    session_id: str | None = None,
    user_type: str | None = None,
    requested_language: str | None = None,
    response_mode: str | None = None,
    voice_response: bool = False,
    latitude: float | None = None,
    longitude: float | None = None,
    selected_location: str | None = None,
    transcript: str | None = None,
) -> ChatResponse:
    settings = get_settings()
    degraded = DegradationInfo()
    state = memory.get_session(session_id)

    text = (query or "").strip()
    if len(text) > settings.max_query_chars:
        # Keep the head: the question is nearly always at the start.
        text = text[: settings.max_query_chars].rsplit(" ", 1)[0] + "…"

    # --- 1. Language -------------------------------------------------------
    detection = language.detect(text)
    if requested_language:
        # An explicit UI choice wins over detection.
        out_lang = i18n.normalise_lang(requested_language)
        detected = detection.language
    else:
        out_lang = detection.language if detection.supported else i18n.DEFAULT_LANG
        detected = detection.language
    if not detection.supported and not requested_language:
        degraded.translation_error = (
            f"Detected language '{detection.detected_raw}' is not supported yet; answering in English."
        )
    state.language = out_lang

    # --- 2. Query into English (the pipeline's working language) -----------
    english_query = text
    if detection.language != "en" and detection.supported and llm.available():
        try:
            english_query = language.translate(text, detection.language, "en", llm=llm) or text
        except language.TranslationError as exc:
            degraded.translation_error = str(exc)
            english_query = text  # rules-based extraction reads the original fine
        except Exception as exc:  # noqa: BLE001
            log.warning("inbound translation raised unexpectedly: %s", exc)
            english_query = text

    # --- 3. Understand -----------------------------------------------------
    extraction = understand(english_query, state, detected_language=detected, degraded=degraded)
    if user_type:
        extraction["user_type"] = user_type if user_type in USER_TYPES else extraction["user_type"]
    elif state.user_type and extraction["user_type"] == "general":
        extraction["user_type"] = state.user_type
    state.user_type = extraction["user_type"]

    if response_mode in VALID_MODES:
        # A caller may ask for "normal" or "simple". It may not ask for
        # "emergency": that is decided by measured risk further down, exactly as
        # it is for the LLM. Otherwise a request parameter could manufacture a
        # warning for a location with no hazard at all.
        extraction["response_mode"] = "normal" if response_mode == "emergency" else response_mode

    # --- 4. Scope guardrail ------------------------------------------------
    if not extraction["in_scope"] or extraction["intent"] == "out_of_scope":
        answer = i18n.sentence("out_of_scope", out_lang)
        memory.remember_turn(state, "user", text, language=out_lang, intent="out_of_scope")
        memory.remember_turn(state, "assistant", answer, language=out_lang)
        memory.persist(state)
        return ChatResponse(
            session_id=state.session_id,
            answer=answer,
            in_scope=False,
            intent="out_of_scope",
            user_type=extraction["user_type"],  # type: ignore[arg-type]
            language=out_lang,
            detected_language=detected,
            data_source=settings.weather_data_mode,
            degraded=degraded,
        )

    # --- 5. Location -------------------------------------------------------
    location = resolve_location(
        extraction,
        state,
        latitude=latitude,
        longitude=longitude,
        original_query=text,
        selected=selected_location,
    )
    if location is None:
        answer = i18n.sentence("no_location", out_lang)
        memory.remember_turn(state, "user", text, language=out_lang)
        memory.remember_turn(state, "assistant", answer, language=out_lang)
        memory.persist(state)
        return ChatResponse(
            session_id=state.session_id,
            answer=answer,
            intent=extraction["intent"],  # type: ignore[arg-type]
            user_type=extraction["user_type"],  # type: ignore[arg-type]
            language=out_lang,
            detected_language=detected,
            data_source=settings.weather_data_mode,
            degraded=degraded,
        )
    memory.set_location(state, location)

    # --- 6. Weather --------------------------------------------------------
    try:
        bundle = weather.fetch_weather(location)
    except WeatherError as exc:
        degraded.weather_error = str(exc)
        answer = i18n.sentence("no_data", out_lang)
        memory.remember_turn(state, "user", text, language=out_lang)
        memory.remember_turn(state, "assistant", answer, language=out_lang)
        memory.persist(state)
        return ChatResponse(
            session_id=state.session_id,
            answer=answer,
            intent=extraction["intent"],  # type: ignore[arg-type]
            user_type=extraction["user_type"],  # type: ignore[arg-type]
            language=out_lang,
            detected_language=detected,
            location=_location_out(location),
            data_source=settings.weather_data_mode,
            degraded=degraded,
        )

    # --- 7. Risk (single source of truth) ----------------------------------
    risk = risk_engine.assess(bundle)

    # --- 8. Response mode: measured risk decides emergency, nothing else ----
    mode = extraction["response_mode"]
    if risk_engine.is_actionable(risk):
        mode = "emergency"
    state.response_mode = mode

    day_offset = extraction["day_offset"]
    payload = build_weather_payload(bundle, risk, day_offset=day_offset)

    # --- 9. Generate -------------------------------------------------------
    answer = ""
    explanation: str | None = None
    actions: list[str] = []
    action_mode = False
    verification_info = VerificationInfo()

    if llm.available():
        extra = _extra_context(bundle, risk, mode, extraction["user_type"], out_lang)
        try:
            composed = llm.compose_answer(
                query=english_query,
                weather_data=payload,
                risk=payload["risk"],
                language_name=language.language_name(out_lang),
                user_type=extraction["user_type"],
                response_mode=mode,
                history=state.transcript(4),
                extra_context=extra,
            )
        except Exception as exc:  # noqa: BLE001 - fall through to the template
            log.warning("generation raised unexpectedly: %s", exc)
            composed = None
        if composed:
            candidate = str(composed.get("answer", "")).strip()
            candidate_expl = str(composed.get("explanation", "")).strip()
            ok, checked, rejected = verification.verify_numbers(
                f"{candidate}\n{candidate_expl}", payload
            )
            verification_info = VerificationInfo(
                verified=ok, checked_numbers=checked, rejected_numbers=rejected
            )
            if ok and candidate:
                degraded.llm_used = True
                answer = candidate
                explanation = candidate_expl or None
                actions = [str(a) for a in composed.get("actions", []) if str(a).strip()]
                action_mode = bool(composed.get("action_mode"))
            else:
                verification_info.note = (
                    "Generated answer quoted values that are not in the weather data; "
                    "replaced with a data-derived response."
                )
                degraded.fallback_reason = "numeric verification rejected the generated answer"
        else:
            degraded.llm_error = "generation unavailable"
            degraded.fallback_reason = degraded.fallback_reason or "LLM generation failed; used templated response"

    if not answer:
        answer = advisory.templated_answer(
            bundle,
            risk,
            intent=extraction["intent"],
            user_type=extraction["user_type"],
            lang=out_lang,
            mode=mode,
            day_offset=day_offset,
        )
        explanation = explanation or advisory.smart_explanation(bundle, risk, out_lang, mode="simple")

    # --- 10. Actions and emergency mode ------------------------------------
    if risk_engine.is_actionable(risk):
        action_mode = True
        if not actions:
            actions = advisory.action_checklist(risk, extraction["user_type"], out_lang)
    elif not actions:
        actions = []

    # --- 11. Ensure the answer really is in the user's language ------------
    answer, explanation, degraded = _ensure_language(answer, explanation, out_lang, degraded)

    comparison = history.comparison_for_bundle(bundle, risk)
    impacts = advisory.impact_cards(bundle, risk, out_lang)

    # --- 12. Remember ------------------------------------------------------
    state.last_intent = extraction["intent"]
    state.last_day_offset = day_offset
    memory.remember_turn(
        state, "user", text, language=out_lang, intent=extraction["intent"], location=location.name
    )
    memory.remember_turn(state, "assistant", answer, language=out_lang, location=location.name)
    memory.persist(state)

    return ChatResponse(
        session_id=state.session_id,
        answer=answer,
        explanation=explanation,
        action_mode=action_mode,
        actions=actions,
        response_mode=mode,  # type: ignore[arg-type]
        intent=extraction["intent"],  # type: ignore[arg-type]
        user_type=extraction["user_type"],  # type: ignore[arg-type]
        language=out_lang,
        detected_language=detected,
        location=_location_out(location),
        current=CurrentWeatherOut(**{
            k: v for k, v in (bundle.current or {}).items() if k in CurrentWeatherOut.model_fields
        }),
        risk=risk,
        impacts=impacts,
        historical_comparison=comparison,
        data_source=bundle.source,
        raw_weather=payload,
        verification=verification_info,
        degraded=degraded,
    )


def _extra_context(bundle: Any, risk: RiskOutput, mode: str, user_type: str, lang: str) -> str:
    """Guidance appended to the compose prompt for risky conditions."""
    if not risk_engine.is_actionable(risk):
        return ""
    drivers = "; ".join(risk.drivers) or "elevated measured risk"
    suggested = advisory.action_checklist(risk, user_type, "en")
    return (
        "EMERGENCY MODE IS ACTIVE because measured risk is "
        f"{risk.risk_level}. Structure the answer as: what is happening, why it matters, "
        "what to do. Keep it short and speakable.\n"
        f"MEASURED DRIVERS: {drivers}\n"
        "SUGGESTED ACTIONS (adapt the wording, keep the substance, do not add new "
        f"hazards): {suggested}"
    )


def _ensure_language(
    answer: str, explanation: str | None, target: str, degraded: DegradationInfo
) -> tuple[str, str | None, DegradationInfo]:
    """Catch the case where generation came back in the wrong language.

    Composition is asked to write directly in the user's language, which beats a
    translate-back round trip. This is the safety net for when it does not.
    """
    if target == "en" or not answer:
        return answer, explanation, degraded
    if language.detect(answer).language == target:
        return answer, explanation, degraded
    try:
        translated = language.translate(answer, "en", target, llm=llm)  # may return None
        if translated:
            if explanation:
                try:
                    explanation = language.translate(explanation, "en", target, llm=llm) or explanation
                except language.TranslationError:
                    pass
            return translated, explanation, degraded
    except language.TranslationError as exc:
        degraded.translation_error = str(exc)
    except Exception as exc:  # noqa: BLE001 - never lose an answer over wording
        log.warning("language safety net failed: %s", exc)
    return answer, explanation, degraded


def _location_out(location: Location) -> LocationOut:
    return LocationOut(
        name=location.name,
        admin1=location.admin1,
        country=location.country,
        latitude=location.latitude,
        longitude=location.longitude,
        timezone=location.timezone,
    )

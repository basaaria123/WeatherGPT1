# -*- coding: utf-8 -*-
"""Chat orchestration — the path every question travels.

    detect language -> understand (in the language asked) -> fetch weather
      -> score risk (shared engine) -> generate -> verify numbers
      -> emergency mode if warranted -> answer in the user's language

Two properties are structural rather than best-effort:

*Grounding.* The generated answer is scanned by ``verification`` and discarded
in favour of the deterministic template if it quotes a measurement the provider
did not return. The template substitutes real values, so the fallback for a
hallucination is a correct answer, not an apology.

*Availability.* Every external dependency — the LLM provider, Open-Meteo,
speech-to-text, TTS — has a defined degraded path. The response reports what
degraded in ``degraded`` instead of hiding it.

Voice chat reuses this module wholesale; it does not reimplement any of it.
"""

from __future__ import annotations

import logging
from typing import Any

from ..config import get_settings
from ..schemas import (
    AdvisoryOut,
    EmergencyOut,
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
        "advice_question": bool(raw.get("advice_question", False)),
        "language": i18n.normalise_lang(raw.get("language") or fallback_language),
        "_source": "llm",
    }


def understand(
    query: str,
    state: memory.SessionState,
    *,
    detected_language: str,
    degraded: DegradationInfo,
    selected_location: str | None = None,
) -> dict[str, Any]:
    """Structured interpretation, LLM first with a rules fallback."""
    # The place on the user's screen is context even on the first turn, before
    # any session memory exists. Without it, "what precautions should I take?"
    # has no location to attach to and the guardrail reads it as off-topic.
    known = state.location_name or selected_location
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

    Order matters. A place named in the question always wins. After that the
    conversation's own subject wins — but only when the user put it there by
    naming it. Asking "what about Chennai?" while the dashboard shows Guwahati
    and then "is it safe to travel?" used to snap back to Guwahati, which reads
    as the assistant forgetting the question it just answered. The dashboard
    selection still wins over a place the user never named, so a fresh question
    with no subject yet is answered about what is on screen.
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

    def remembered() -> Location | None:
        if not state.has_location():
            return None
        return Location(
            name=state.location_name or "your area",
            latitude=float(state.latitude),  # type: ignore[arg-type]
            longitude=float(state.longitude),  # type: ignore[arg-type]
            admin1=state.admin1,
        )

    if state.location_was_named:
        found = remembered()
        if found is not None:
            return found

    if selected:
        found = weather.geocode(selected)
        if found is not None:
            return found

    if not name or extraction.get("use_previous_location"):
        found = remembered()
        if found is not None:
            return found

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

    # --- 2. The question travels as written --------------------------------
    # This used to translate every non-English question into English before
    # understanding it, which cost a whole extra provider round trip on exactly
    # the turns that were already the slowest: a Telugu question took 17.1s
    # against English's 3.0s, and users read that as "Telugu does not work".
    #
    # The trip bought nothing. Extraction is a tool call whose schema names the
    # language field, and the model reads Telugu, Hindi, Bengali, Marathi and
    # Assamese directly — it returns location "Vijayawada" and language "te"
    # from the Telugu original. The rules-based fallback never used the
    # translation either: it matches Indic terms against the raw text.
    english_query = text

    # --- 3. Understand -----------------------------------------------------
    extraction = understand(
        english_query,
        state,
        detected_language=detected,
        degraded=degraded,
        selected_location=selected_location,
    )
    # "Is it safe to travel?" is an advice question whichever path read it, and
    # the rules detector is the one that actually knows the phrasings in all six
    # languages — so it has the final say rather than the model's guess.
    extraction["advice_question"] = bool(
        extraction.get("advice_question") or nlp_fallback.is_advice_question(text)
    )

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
    # Remember whether this place came from the question or from the dashboard,
    # so the next follow-up knows which one the conversation is actually about.
    memory.set_location(state, location, named=bool(extraction.get("location")))

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
            advice_question=extraction["advice_question"],
        )
        # "Why this answer?" has to add something. On a calm or moderate day the
        # answer already *is* the plain reading of the data, so the templated
        # explanation came back word for word identical and the panel showed the
        # user their own answer twice. An empty explanation is better than an
        # echo — the panel simply does not open.
        if not explanation:
            candidate = advisory.smart_explanation(bundle, risk, out_lang, mode="simple")
            if not _adds_something(candidate, answer):
                # Fall back to the evidence: the measured values the risk engine
                # actually scored. Localised, real, and by definition not a
                # restatement of the narrative above it. On a genuinely calm day
                # there are no drivers, so the panel stays closed rather than
                # inventing a reason.
                drivers = i18n.driver_labels(risk.driver_details, out_lang)
                end = i18n.terminator(out_lang)
                candidate = "".join(f"{driver}{end} " for driver in drivers[:3]).strip()
            explanation = candidate or None

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

    # --- Feature payloads, all driven by the one risk output ---------------
    advisory_block = advisory.build_advisory(risk, extraction["user_type"], out_lang, bundle=bundle)
    emergency_block = advisory.build_emergency(bundle, risk, extraction["user_type"], out_lang)

    similarity = history.similarity_for_bundle(bundle, risk)
    if similarity.get("matched"):
        event_name = similarity["event"]["name"]
        if event_name in state.seen_events:
            # Already shown this conversation: keep the payload shape, drop the
            # repeat so it reads as context rather than a recurring alarm.
            similarity = {"matched": False, "framing": "context"}
        else:
            state.seen_events.append(event_name)
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
        advisory=AdvisoryOut(**advisory_block),
        emergency=EmergencyOut(**emergency_block),
        historical_similarity=similarity,
        data_source=bundle.source,
        raw_weather=payload,
        verification=verification_info,
        degraded=degraded,
    )


def _adds_something(candidate: str, answer: str) -> bool:
    """True when `candidate` says anything the answer has not already said.

    Compared sentence by sentence rather than as whole strings: the templates
    share their opening clause, so a substring test would keep an explanation
    that only differs by its last few words.
    """
    candidate = (candidate or "").strip()
    if not candidate:
        return False
    said = set(advisory._sentences(answer or ""))
    return any(sentence not in said for sentence in advisory._sentences(candidate))


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

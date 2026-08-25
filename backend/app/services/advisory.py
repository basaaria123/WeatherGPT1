# -*- coding: utf-8 -*-
"""Turning numbers into guidance.

This module answers "what does this actually mean for me?" It never invents a
weather fact: every sentence is a localised template whose slots come straight
from the provider response, and every risk statement comes from the shared
risk engine. It is also the offline floor under the LLM — if Anthropic is
unreachable, these templates still produce a correct, multilingual answer.

All output here is written to be read aloud, so no tables, no bullets glued to
symbols, and no raw technical phrasing.
"""

from __future__ import annotations

from typing import Any

from ..schemas import ImpactCard, RiskOutput
from . import i18n, risk_engine

# Presentation thresholds. These change wording only; risk itself comes from
# the risk engine, and none of these ever creates a fact the data lacks.
HIGH_RAIN_PROB = 60
HUMID_PCT = 80
STRONG_WIND_KMH = 35
HOT_FEELS_C = 36


# Which sector card leads for each profile, and which factors that reader
# cares about first. Both are presentation-order only: no profile unlocks a
# weather fact another profile cannot see.
PROFILE_LEAD_CATEGORY: dict[str, str] = {
    "farmer": "farming",
    "fisherman": "fishing",
    "traveler": "travel",
    "commuter": "travel",
    "general": "",
}

# What each reader wants to hear first. "hazard" is not in these lists: an
# actionable hazard always leads regardless of profile, and a non-actionable one
# is appended after the profile's own concerns rather than crowding them out.
PROFILE_FACTOR_ORDER: dict[str, tuple[str, ...]] = {
    "farmer": ("rain", "heat", "wind", "visibility"),
    "fisherman": ("wind", "rain", "visibility", "heat"),
    "traveler": ("visibility", "rain", "heat", "wind"),
    "commuter": ("rain", "visibility", "wind", "heat"),
    "general": ("rain", "wind", "heat", "visibility"),
}

# How far ahead each reader is actually planning. A commuter cares about the
# next couple of hours; a farmer is planning the working day.
PROFILE_HORIZON_HOURS: dict[str, int] = {
    "farmer": 12,
    "fisherman": 12,
    "traveler": 12,
    "commuter": 6,
    "general": 12,
}

# Below this, a forecast hour does not count as "rain is coming".
RAIN_ONSET_PROB = 55
RAIN_ONSET_MM = 0.4
LOW_VISIBILITY_KM = 2.0


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _r(value: float | None, places: int = 0) -> Any:
    if value is None:
        return None
    return round(value, places) if places else int(round(value))


def smart_explanation(
    bundle: Any,
    risk: RiskOutput,
    lang: str = "en",
    *,
    mode: str = "normal",
) -> str:
    """Plain-language reading of current conditions (Role 3.5).

    ``simple`` mode keeps only the two most important sentences.
    """
    lang = i18n.normalise_lang(lang)
    cur = bundle.current or {}
    loc = bundle.location.label

    temp = _num(cur.get("temperature_c"))
    feels = _num(cur.get("apparent_temperature_c"))
    hum = _num(cur.get("humidity_pct"))
    prob = _num(cur.get("precipitation_probability_pct"))
    wind = _num(cur.get("wind_speed_kmh"))
    rain24 = sum(_num(h.get("precipitation_mm")) or 0.0 for h in bundle.hourly[:24])

    parts: list[str] = []
    if temp is not None:
        parts.append(
            i18n.sentence(
                "now", lang, loc=loc, temp=_r(temp, 1),
                cond=i18n.condition_label(cur.get("weather_code"), lang),
            )
        )

    # Only mention "feels like" when it actually differs enough to matter.
    if feels is not None and temp is not None and abs(feels - temp) >= 1.5:
        parts.append(i18n.sentence("feels", lang, feels=_r(feels, 1)))

    if prob is not None:
        parts.append(
            i18n.sentence("rain_high", lang, prob=_r(prob))
            if prob >= HIGH_RAIN_PROB
            else i18n.sentence("rain_low", lang)
        )

    if rain24 >= 1.0:
        parts.append(i18n.sentence("rain_24", lang, mm=_r(rain24, 1)))

    if mode != "simple":
        if hum is not None and hum >= HUMID_PCT:
            parts.append(i18n.sentence("humid", lang, hum=_r(hum)))
        if wind is not None:
            parts.append(
                i18n.sentence("wind_strong", lang, wind=_r(wind))
                if wind >= STRONG_WIND_KMH
                else i18n.sentence("wind_calm", lang, wind=_r(wind))
            )
        if feels is not None and feels >= HOT_FEELS_C:
            parts.append(i18n.sentence("heat_note", lang, feels=_r(feels, 1)))

    if risk.detected_hazard == "None" and not risk_engine.is_actionable(risk):
        parts.append(i18n.sentence("calm_tail", lang))

    if mode == "simple":
        parts = parts[:3]
    return " ".join(p for p in parts if p)


def action_checklist(risk: RiskOutput, user_type: str | None, lang: str = "en") -> list[str]:
    """Safety actions for the detected hazard, tailored by user profile.

    Profile tailoring changes which advice is prioritised — it never adds a
    weather claim the backend does not support.
    """
    lang = i18n.normalise_lang(lang)
    if risk.detected_hazard == "None":
        return []
    actions = i18n.hazard_actions(risk.detected_hazard, lang)
    profile_line = i18n.profile_action(user_type, risk.detected_hazard, lang)
    if profile_line:
        # The profile-specific action leads: it is the one most likely to be acted on.
        actions = [profile_line] + actions
    return actions[:4]


def emergency_brief(
    bundle: Any,
    risk: RiskOutput,
    user_type: str | None,
    lang: str = "en",
) -> str:
    """Short, voice-friendly emergency message: what -> why -> what to do.

    Only ever called when the risk engine reports High or Severe, so this can
    never manufacture an emergency on its own.
    """
    lang = i18n.normalise_lang(lang)
    loc = bundle.location.label
    hazard = i18n.hazard_label(risk.detected_hazard, lang)
    level = i18n.level_label(risk.risk_level, lang)

    lines = [i18n.sentence("emg_headline", lang, loc=loc, hazard=hazard)]

    # What is happening — the engine's own drivers, which are quoted real values.
    localised = i18n.driver_labels(risk.driver_details, lang)
    what = "; ".join(localised[:2]) if localised else smart_explanation(bundle, risk, lang, mode="simple")
    end = i18n.terminator(lang)
    lines.append(f"{i18n.sentence('emg_what', lang)}: {what}{end}")

    lines.append(
        f"{i18n.sentence('emg_why', lang)}: "
        + i18n.sentence("emg_why_text", lang, level=level, score=risk.risk_score)
    )

    actions = action_checklist(risk, user_type, lang)
    if actions:
        lines.append(f"{i18n.sentence('emg_do', lang)}: " + " ".join(actions))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Impact cards
# ---------------------------------------------------------------------------
def _status(score: float) -> str:
    if score >= 61:
        return "Avoid"
    if score >= 31:
        return "Caution"
    return "Safe"


def impact_cards(
    bundle: Any,
    risk: RiskOutput,
    lang: str = "en",
    user_type: str | None = None,
) -> list[ImpactCard]:
    """Sector impact cards derived from real values and the shared risk score.

    Each category is scored from the hazard sub-scores that genuinely bear on
    it, so "Fishing: Avoid" traces to wind and storm numbers, not to a guess.
    """
    lang = i18n.normalise_lang(lang)
    sub = risk.hazard_scores or {}
    rain = sub.get("Heavy Rainfall", 0)
    flood = sub.get("Flood Risk", 0)
    wind = sub.get("Strong Wind", 0)
    heat = sub.get("Extreme Heat", 0)
    storm = sub.get("Lightning/Storm", 0)

    cur = bundle.current or {}
    wind_kmh = _num(cur.get("wind_speed_kmh"))
    gust_kmh = _num(cur.get("wind_gust_kmh"))
    feels = _num(cur.get("apparent_temperature_c"))
    rain24 = sum(_num(h.get("precipitation_mm")) or 0.0 for h in bundle.hourly[:24])
    vis = _num(cur.get("visibility_km"))

    def detail_for(kind: str, score: float) -> str:
        """One sentence per sector, chosen from what actually bears on it.

        Categories deliberately do not share a sentence: telling a farmer and a
        traveller the same thing about the same rain is what made the old cards
        feel generic, and it wastes the one line each card gets.
        """
        hot = feels is not None and feels >= HOT_FEELS_C
        gust_or_wind = gust_kmh if gust_kmh is not None else wind_kmh

        if kind == "farming":
            if rain24 >= 1.0:
                return f"{i18n.sentence('impact_farming_rain', lang)} " + i18n.sentence(
                    "rain_24", lang, mm=_r(rain24, 1)
                )
            if hot:
                return i18n.sentence("heat_note", lang, feels=_r(feels, 1))
            return i18n.sentence("impact_farming_clear", lang)

        if kind == "fishing":
            if gust_or_wind is not None and (gust_or_wind >= STRONG_WIND_KMH or storm >= 40):
                return i18n.sentence("insight_small_boat", lang, wind=_r(gust_or_wind))
            if wind_kmh is not None:
                return i18n.sentence("impact_fishing_calm", lang, wind=_r(wind_kmh))
            return i18n.sentence("calm_tail", lang)

        if kind == "travel":
            if vis is not None and vis <= 2.0:
                return i18n.sentence("insight_visibility_low", lang, vis=_r(vis, 1))
            if rain24 >= 1.0:
                return i18n.sentence("impact_travel_rain", lang)
            return i18n.sentence("impact_travel_clear", lang)

        if kind == "household":
            if flood >= 31 or storm >= 40 or wind >= 40:
                return i18n.sentence("impact_household_risk", lang)
            return i18n.sentence("impact_household_calm", lang)

        # outdoor
        if score >= 61:
            return i18n.sentence("impact_outdoor_risk", lang)
        if hot:
            return i18n.sentence("heat_note", lang, feels=_r(feels, 1))
        if rain24 >= 1.0:
            return i18n.sentence("rain_24", lang, mm=_r(rain24, 1))
        return i18n.sentence("impact_outdoor_clear", lang)

    spec: list[tuple[str, float]] = [
        ("farming", max(flood, rain * 0.9, heat * 0.9, storm * 0.8)),
        ("fishing", max(wind, storm, rain * 0.75)),
        ("travel", max(rain * 0.95, flood * 0.95, wind * 0.85, storm * 0.9)),
        ("household", max(flood, storm * 0.7, heat * 0.8, wind * 0.6)),
        ("outdoor", max(rain, storm, heat, wind * 0.9)),
    ]

    # The reader's own sector leads. Ordering only — every card still shows,
    # and none of their content changes with the profile.
    lead = PROFILE_LEAD_CATEGORY.get(i18n.canonical_profile(user_type))
    if lead:
        spec.sort(key=lambda item: 0 if item[0] == lead else 1)

    cards: list[ImpactCard] = []
    for key, score in spec:
        status = _status(score)
        # Poor visibility is a travel hazard the hazard scores don't capture.
        if key == "travel" and vis is not None and vis <= 1.0 and status == "Safe":
            status = "Caution"
        cards.append(
            ImpactCard(
                category=i18n.category_label(key, lang),
                status=status,  # type: ignore[arg-type]
                headline=i18n.status_label(status, lang),
                detail=detail_for(key, score),
            )
        )
    return cards


def disclaimer(lang: str = "en") -> str:
    return i18n.sentence("disclaimer", i18n.normalise_lang(lang))


# ---------------------------------------------------------------------------
# Templated answers (the no-LLM path)
# ---------------------------------------------------------------------------
def _day_label(day_offset: int, lang: str) -> str:
    """Relative, localised day name — never an English weekday."""
    return i18n.day_label(day_offset, lang)


def forecast_answer(bundle: Any, lang: str, day_offset: int = 1) -> str:
    """Plain-language forecast for a specific day in the 7-day window."""
    lang = i18n.normalise_lang(lang)
    days = bundle.daily or []
    if not days:
        return i18n.sentence("no_data", lang)
    index = max(0, min(day_offset, len(days) - 1))
    day = days[index]
    lead = i18n.sentence(
        "forecast_lead", lang,
        loc=bundle.location.label,
        day=_day_label(index, lang),
        cond=i18n.condition_label(day.get("weather_code"), lang),
        tmin=_r(_num(day.get("temp_min_c")), 1),
        tmax=_r(_num(day.get("temp_max_c")), 1),
    )
    parts = [lead]
    rain = _num(day.get("precipitation_sum_mm")) or 0.0
    if rain >= 1.0:
        parts.append(i18n.sentence("rain_24", lang, mm=_r(rain, 1)))
    prob = _num(day.get("precipitation_probability_pct"))
    if prob is not None:
        parts.append(
            i18n.sentence("rain_high", lang, prob=_r(prob))
            if prob >= HIGH_RAIN_PROB
            else i18n.sentence("rain_low", lang)
        )
    wind = _num(day.get("wind_speed_max_kmh"))
    if wind is not None and wind >= STRONG_WIND_KMH:
        parts.append(i18n.sentence("wind_strong", lang, wind=_r(wind)))

    day_risk = risk_engine.assess_day(day)
    if risk_engine.is_actionable(day_risk):
        actions = action_checklist(day_risk, None, lang)
        if actions:
            parts.append(" ".join(actions[:2]))
    return " ".join(parts)


def alerts_answer(bundle: Any, alerts: list[dict[str, Any]], lang: str) -> str:
    """Answer for 'any alerts for my area?' built from stored alerts."""
    lang = i18n.normalise_lang(lang)
    loc = bundle.location.label
    if not alerts:
        return i18n.sentence("alert_none", lang, loc=loc)
    lead = i18n.sentence(
        "alert_some", lang, loc=loc, count=len(alerts),
        verb="is" if len(alerts) == 1 else "are",
        noun="alert" if len(alerts) == 1 else "alerts",
    )
    detail = " ".join(a.get("message", "") for a in alerts[:2])
    return f"{lead} {detail}".strip()


def templated_answer(
    bundle: Any,
    risk: RiskOutput,
    *,
    intent: str,
    user_type: str | None,
    lang: str,
    mode: str = "normal",
    day_offset: int = 1,
    alerts: list[dict[str, Any]] | None = None,
) -> str:
    """The full no-LLM answer. Correct, multilingual, and impossible to
    hallucinate with, because every number is substituted from real data."""
    lang = i18n.normalise_lang(lang)
    # Emergency wording is gated on the measured risk alone. `mode` cannot
    # promote a calm reading into a warning, only the risk engine can.
    if risk_engine.is_actionable(risk):
        return emergency_brief(bundle, risk, user_type, lang)
    if intent == "forecast":
        return forecast_answer(bundle, lang, day_offset=day_offset)
    if intent == "alert_check":
        return alerts_answer(bundle, alerts or [], lang)
    return smart_explanation(bundle, risk, lang, mode=mode)


# ---------------------------------------------------------------------------
# "What should I know?" — the single most important thing, right now
# ---------------------------------------------------------------------------
def _clock(iso: str | None) -> str | None:
    """HH:MM from a provider timestamp. Deliberately not localised into words:
    a digit clock reads the same in all six languages."""
    if not iso or "T" not in iso:
        return None
    return iso.split("T", 1)[1][:5]


def headline_insight(
    bundle: Any,
    risk: RiskOutput,
    user_type: str | None = None,
    lang: str = "en",
    *,
    horizon_hours: int | None = None,
) -> dict[str, Any]:
    """The one thing worth knowing, plus at most two supporting lines.

    Every candidate sentence below is built from a measured value; if the value
    is missing the sentence is simply not offered. The profile reorders which
    candidates surface first — it never adds one.
    """
    lang = i18n.normalise_lang(lang)
    profile = i18n.canonical_profile(user_type)
    horizon = horizon_hours or PROFILE_HORIZON_HOURS.get(profile, 12)
    cur = bundle.current or {}
    window = list(bundle.hourly[:horizon])

    feels = _num(cur.get("apparent_temperature_c"))
    vis = _num(cur.get("visibility_km"))
    wind_now = _num(cur.get("wind_speed_kmh"))

    candidates: dict[str, str] = {}
    factors: list[str] = []

    # --- Rain: when does it start, if at all? -----------------------------
    onset = None
    for hour in window:
        prob = _num(hour.get("precipitation_probability_pct")) or 0.0
        mm = _num(hour.get("precipitation_mm")) or 0.0
        if prob >= RAIN_ONSET_PROB or mm >= RAIN_ONSET_MM:
            onset = (hour, prob)
            break

    if onset is not None:
        hour, prob = onset
        clock = _clock(hour.get("time"))
        if clock:
            candidates["rain"] = i18n.sentence("insight_rain_from", lang, time=clock, prob=_r(prob))
            factors.append("rainfall")
    elif window:
        candidates["rain"] = i18n.sentence("insight_rain_clear", lang, hours=len(window))
        factors.append("rainfall")

    # --- Wind -------------------------------------------------------------
    winds = [_num(h.get("wind_speed_kmh")) for h in window]
    peak_wind = max([w for w in winds if w is not None], default=wind_now)
    if peak_wind is not None and peak_wind >= STRONG_WIND_KMH:
        # A fisherman's threshold for "difficult" is lower than a commuter's.
        candidates["wind"] = (
            i18n.sentence("insight_small_boat", lang, wind=_r(peak_wind))
            if profile == "fisherman"
            else i18n.sentence("insight_wind_later", lang, wind=_r(peak_wind))
        )
        factors.append("wind")
    elif profile == "fisherman" and wind_now is not None:
        candidates["wind"] = i18n.sentence("impact_fishing_calm", lang, wind=_r(wind_now))
        factors.append("wind")

    # --- Visibility -------------------------------------------------------
    if vis is not None and vis <= LOW_VISIBILITY_KM:
        candidates["visibility"] = i18n.sentence("insight_visibility_low", lang, vis=_r(vis, 1))
        factors.append("visibility")

    # --- Heat -------------------------------------------------------------
    if feels is not None and feels >= HOT_FEELS_C:
        candidates["heat"] = i18n.sentence("heat_note", lang, feels=_r(feels, 1))
        factors.append("temperature")

    # --- Hazard, straight from the shared engine --------------------------
    if risk.detected_hazard != "None" and risk.risk_score >= 31:
        candidates["hazard"] = i18n.sentence(
            "insight_hazard_active", lang,
            hazard=i18n.hazard_label(risk.detected_hazard, lang),
            level=i18n.level_label(risk.risk_level, lang),
        )
        factors.append("hazard indicators")

    order = PROFILE_FACTOR_ORDER.get(profile, PROFILE_FACTOR_ORDER["general"])
    # A hazard the engine calls actionable outranks everything; below that the
    # profile's own priorities lead and the hazard follows as context.
    if risk_engine.is_actionable(risk):
        order = ("hazard",) + order
    else:
        order = order + ("hazard",)
    chosen = [candidates[key] for key in order if key in candidates]
    # Anything the profile ordering did not name still beats an empty panel.
    chosen += [value for key, value in candidates.items() if key not in order]

    # --- Closing line: what this reader can actually do about it ----------
    # Each branch is gated on the value it talks about, so the closing can never
    # contradict a line above it (no "conditions are good" under 1 km fog).
    if not risk_engine.is_actionable(risk):
        vis_ok = vis is None or vis > LOW_VISIBILITY_KM
        if profile == "farmer":
            clock = _clock(onset[0].get("time")) if onset else None
            if clock:
                chosen.append(i18n.sentence("insight_window_until", lang, time=clock))
            elif onset is None:
                chosen.append(i18n.sentence("impact_farming_clear", lang))
        elif profile in {"traveler", "commuter"}:
            if onset is None and vis_ok:
                chosen.append(i18n.sentence("impact_travel_clear", lang))
        elif profile == "fisherman":
            if onset is None and (peak_wind is None or peak_wind < STRONG_WIND_KMH):
                chosen.append(i18n.sentence("impact_outdoor_clear", lang))
        elif onset is None and vis_ok:
            chosen.append(i18n.sentence("insight_safe_now", lang))

    if not chosen:
        chosen = [smart_explanation(bundle, risk, lang, mode="simple")]

    return {
        "headline": chosen[0],
        "supporting": " ".join(chosen[1:3]),
        "factors": sorted(set(factors)),
        "user_type": profile,
        "actionable": risk_engine.is_actionable(risk),
    }


# ---------------------------------------------------------------------------
# Structured persona advisory (Feature A)
#
# Deterministic: the action text comes from the rules tables in i18n, selected
# by (hazard, user_type). The risk level decides *how many* actions surface and
# how urgently they are framed — it does not select a different body of advice,
# because "High rain" and "Severe rain" call for the same actions with
# different urgency, and duplicating the text per level would treble a
# translated corpus for no safety gain.
#
# An LLM never chooses these. Where one is available it may rephrase them into
# the reader's language and response mode; it does not decide what they are.
# ---------------------------------------------------------------------------
ACTIONS_BY_LEVEL: dict[str, int] = {"Severe": 4, "High": 3, "Moderate": 2, "Low": 1}


def build_advisory(
    risk: RiskOutput,
    user_type: str | None = None,
    lang: str = "en",
) -> dict[str, Any]:
    """Ordered, sourced actions for one persona under one hazard.

    Fallback chain: the persona's own lead action for this hazard, then the
    hazard's shared actions, then — if a hazard is somehow unnamed while risk is
    actionable — a safe generic advisory. A High or Severe situation never
    returns an empty action list.
    """
    lang = i18n.normalise_lang(lang)
    profile = i18n.canonical_profile(user_type)
    hazard = risk.detected_hazard
    wanted = ACTIONS_BY_LEVEL.get(risk.risk_level, 1)

    actions: list[dict[str, Any]] = []

    # 1 — the persona's own action leads, and is the one carrying a reason.
    lead = i18n.profile_action(profile, hazard, lang)
    if lead:
        actions.append(
            {
                "action": lead,
                "reason": i18n.profile_reason(profile, hazard, lang),
                "priority": 1,
            }
        )

    # 2 — the hazard's shared safety actions.
    for text in i18n.hazard_actions(hazard, lang):
        if len(actions) >= wanted:
            break
        if any(existing["action"] == text for existing in actions):
            continue
        actions.append({"action": text, "reason": None, "priority": len(actions) + 1})

    # 3 — never leave a dangerous situation without guidance.
    if not actions and risk_engine.is_actionable(risk):
        actions = [
            {
                "action": i18n.sentence("advisory_generic", lang),
                "reason": None,
                "priority": 1,
            }
        ]

    return {
        "user_type": profile,
        "hazard": hazard,
        "risk_level": risk.risk_level,
        "actions": actions[:wanted],
        "disclaimer": disclaimer(lang),
        "source": "rules",
    }


def advisory_for_every_persona(risk: RiskOutput, lang: str = "en") -> list[dict[str, Any]]:
    """The same conditions read by each persona — one weather fact, several
    decisions. Backs the comparison view and the demo."""
    return [build_advisory(risk, profile, lang) for profile in PERSONAS]


PERSONAS: tuple[str, ...] = ("farmer", "fisherman", "traveler", "commuter", "general")


# ---------------------------------------------------------------------------
# Emergency mode (Feature B)
#
# The trigger is the risk engine and nothing else: this returns an inactive
# block below High, so a client cannot talk itself into an emergency. The
# content follows the order official emergency communication uses — what is
# happening, why it matters, what to do now.
# ---------------------------------------------------------------------------
def _voice_friendly(text: str) -> str:
    """Speech-shaped text. Imported lazily: the speech stack is optional, and a
    missing TTS dependency must not stop an emergency from rendering."""
    try:
        from .speech import voice_friendly

        return voice_friendly(text)
    except Exception:  # noqa: BLE001
        return text


def _valid_until(bundle: Any, hours: int = 24) -> str | None:
    """End of the run of hours that stay at an actionable level.

    Derived from the forecast the engine already scores, so the horizon is a
    real one. Open-Meteo publishes no expiry, and inventing a precise one would
    be a fabricated number.
    """
    run_end = None
    for hour in risk_engine.timeline(bundle, hours=hours):
        if hour["risk_level"] in {"High", "Severe"}:
            run_end = hour["time"]
        elif run_end is not None:
            break
    return run_end


def build_emergency(
    bundle: Any,
    risk: RiskOutput,
    user_type: str | None = None,
    lang: str = "en",
    *,
    is_simulated: bool = False,
) -> dict[str, Any]:
    """Structured emergency payload. Inactive unless the engine says otherwise."""
    lang = i18n.normalise_lang(lang)
    if not risk_engine.is_actionable(risk):
        return {
            "active": False,
            "risk_level": risk.risk_level,
            "hazard": risk.detected_hazard,
            "is_simulated": is_simulated,
        }

    hazard = i18n.hazard_label(risk.detected_hazard, lang)
    level = i18n.level_label(risk.risk_level, lang)
    end = i18n.terminator(lang)

    drivers = i18n.driver_labels(risk.driver_details, lang)
    what = "; ".join(drivers[:2]) if drivers else smart_explanation(bundle, risk, lang, mode="simple")

    advisory = build_advisory(risk, user_type, lang)
    immediate = [item["action"] for item in advisory["actions"]]

    # Written to be heard, not read: no bullets, no raw field names, short
    # sentences, and short enough to finish before someone stops listening.
    spoken = " ".join(
        [
            i18n.sentence("emg_headline", lang, loc=bundle.location.label, hazard=hazard),
            f"{what}{end}",
            i18n.sentence("emg_why_text", lang, level=level, score=risk.risk_score),
        ]
        + immediate[:3]
    )

    return {
        "active": True,
        "risk_level": risk.risk_level,
        "hazard": risk.detected_hazard,
        "headline": i18n.sentence("emg_headline", lang, loc=bundle.location.label, hazard=hazard),
        "what_is_happening": f"{what}{end}",
        "why_it_matters": i18n.sentence("emg_why_text", lang, level=level, score=risk.risk_score),
        "immediate_actions": immediate,
        "spoken_instructions": _voice_friendly(spoken),
        "valid_until": _valid_until(bundle),
        "is_simulated": is_simulated,
    }

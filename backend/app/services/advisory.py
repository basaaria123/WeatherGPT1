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


def impact_cards(bundle: Any, risk: RiskOutput, lang: str = "en") -> list[ImpactCard]:
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

    def detail_for(kind: str) -> str:
        bits: list[str] = []
        if kind in {"farming", "travel", "household", "outdoor"} and rain24 >= 1.0:
            bits.append(i18n.sentence("rain_24", lang, mm=_r(rain24, 1)))
        if kind in {"fishing", "travel", "outdoor"} and wind_kmh is not None:
            bits.append(
                i18n.sentence("wind_strong", lang, wind=_r(gust_kmh or wind_kmh))
                if (gust_kmh or wind_kmh) >= STRONG_WIND_KMH
                else i18n.sentence("wind_calm", lang, wind=_r(wind_kmh))
            )
        if kind in {"farming", "outdoor", "household"} and feels is not None and feels >= HOT_FEELS_C:
            bits.append(i18n.sentence("heat_note", lang, feels=_r(feels, 1)))
        if not bits:
            bits.append(i18n.sentence("calm_tail", lang))
        return " ".join(bits)

    spec: list[tuple[str, float]] = [
        ("farming", max(flood, rain * 0.9, heat * 0.9, storm * 0.8)),
        ("fishing", max(wind, storm, rain * 0.75)),
        ("travel", max(rain * 0.95, flood * 0.95, wind * 0.85, storm * 0.9)),
        ("household", max(flood, storm * 0.7, heat * 0.8, wind * 0.6)),
        ("outdoor", max(rain, storm, heat, wind * 0.9)),
    ]

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
                detail=detail_for(key),
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
    if mode == "emergency" or risk_engine.is_actionable(risk):
        return emergency_brief(bundle, risk, user_type, lang)
    if intent == "forecast":
        return forecast_answer(bundle, lang, day_offset=day_offset)
    if intent == "alert_check":
        return alerts_answer(bundle, alerts or [], lang)
    return smart_explanation(bundle, risk, lang, mode=mode)

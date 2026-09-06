# -*- coding: utf-8 -*-
"""What the map is showing, hour by hour, for whoever is reading it.

One line per forecast hour of the selected location, composed from two halves:
what the numbers do, and what that means for the profile in use. Both halves
come out of the same translated corpus as every other sentence WeatherGPT
speaks, filled from the same hourly series the timeline strip is drawn from.

There is no radar here and this module does not pretend otherwise. It compares
an hour against the present hour of the same place — "rises to", "eases to" —
which is a claim the forecast actually supports. It never says rain is moving
toward you, because nothing in this app's data can establish that.
"""

from __future__ import annotations

from typing import Any

from . import i18n

# Thresholds shared with the role panel's reading of the same numbers, so a
# map line and a role card cannot disagree about the same hour.
RAIN_LIKELY_PCT = 50
RAIN_MAYBE_PCT = 30
WIND_BRISK_KMH = 30
CHANGE_PCT = 15  # a swing smaller than this is noise, not a trend

_ROLE_CLAUSE = {
    "general": ("mi_role_general", "mi_role_general_calm"),
    "farmer": ("mi_role_farmer", "mi_role_farmer_calm"),
    "fisherman": ("mi_role_fisherman", "mi_role_fisherman_calm"),
    "traveler": ("mi_role_traveler", "mi_role_traveler_calm"),
    "driver": ("mi_role_driver", "mi_role_driver_calm"),
    "outdoor_worker": ("mi_role_outdoor_worker", "mi_role_outdoor_worker_calm"),
    "household": ("mi_role_household", "mi_role_household_calm"),
    "student": ("mi_role_student", "mi_role_student_calm"),
    "caregiver": ("mi_role_caregiver", "mi_role_caregiver_calm"),
    "commuter": ("mi_role_commuter", "mi_role_commuter_calm"),
}


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _clock(stamp: Any) -> str:
    text = str(stamp or "")
    return text.split("T", 1)[1][:5] if "T" in text else text


def build(hours: list[dict[str, Any]], user_type: str | None, lang: str = "en") -> list[str]:
    """One interpretation per hour, aligned index-for-index with ``hours``.

    Returns an empty list when there is nothing to interpret, so the caller
    shows no line rather than an empty one.
    """
    lang = i18n.normalise_lang(lang)
    role = (user_type or "general").strip().lower()
    if role not in _ROLE_CLAUSE:
        role = "general"
    active_key, calm_key = _ROLE_CLAUSE[role]

    if not hours:
        return []

    baseline = _num(hours[0].get("precipitation_probability_pct"))
    lines: list[str] = []

    for hour in hours:
        clock = _clock(hour.get("time"))
        prob = _num(hour.get("precipitation_probability_pct"))
        wind = _num(hour.get("wind_speed_kmh"))
        level = hour.get("risk_level") or "Low"

        # The lead clause names the single most decision-relevant fact, so a
        # reader gets one thing rather than a list to rank themselves. The
        # engine's own level for the hour outranks the raw probability: once
        # the risk is High, "95% chance of rain" is the less useful sentence.
        if level in ("High", "Severe"):
            lead = i18n.sentence("mi_storm", lang, time=clock, level=level)
            active = True
        elif prob is not None and prob >= RAIN_LIKELY_PCT:
            lead = i18n.sentence("mi_rain_high", lang, time=clock, prob=int(round(prob)))
            active = True
        elif prob is not None and baseline is not None and prob - baseline >= CHANGE_PCT:
            lead = i18n.sentence("mi_rain_rising", lang, time=clock, prob=int(round(prob)))
            active = prob >= RAIN_MAYBE_PCT
        elif prob is not None and baseline is not None and baseline - prob >= CHANGE_PCT:
            lead = i18n.sentence("mi_rain_easing", lang, time=clock, prob=int(round(prob)))
            active = False
        elif wind is not None and wind >= WIND_BRISK_KMH:
            lead = i18n.sentence("mi_wind", lang, time=clock, wind=int(round(wind)))
            active = True
        elif prob is None and wind is None:
            # Nothing measured for this hour: say nothing about it.
            lines.append("")
            continue
        else:
            lead = i18n.sentence("mi_calm", lang, time=clock)
            active = False

        lines.append(f"{lead} {i18n.sentence(active_key if active else calm_key, lang)}".strip())

    return lines

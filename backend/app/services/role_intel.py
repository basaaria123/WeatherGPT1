# -*- coding: utf-8 -*-
"""What today's weather means for the reader, rather than what it is.

One weather engine, seven readings of it. Every card below is derived from the
same ``bundle`` the dashboard is already rendering and the same ``RiskOutput``
the risk score came from — this module scores nothing of its own, fetches
nothing of its own, and cannot see a value the rest of the app cannot.

The shape of a card is deliberately dumb, because the frontend renders it
without interpreting it:

    id        stable key, for React and for tests
    icon      one glyph
    title     translated
    headline  the verdict, translated, short enough to read at a glance
    detail    one translated sentence, or empty
    tone      safe | caution | warn | danger | info — presentation only

Two rules run through all of it:

*   Nothing is invented. A card whose inputs are missing says so or does not
    appear. There is no wave height here, because no provider in this app
    returns one; the marine reading says as much rather than implying otherwise.
*   Nothing is prescribed. These are weather advisories — "consider", "monitor",
    "may" — not agronomy, medicine, or a guarantee about the sea.
"""

from __future__ import annotations

from typing import Any

from ..schemas import RiskOutput
from . import i18n, roles

# --- Thresholds -------------------------------------------------------------
# Named rather than inlined so a reviewer can see every number that decides a
# verdict in one place, and so the tests can quote them.

RAIN_LIKELY_PCT = 50          # probability at which an umbrella earns its space
RAIN_MAYBE_PCT = 30
RAIN_HEAVY_24H_MM = 10.0      # a wet day by any standard
RAIN_MEANINGFUL_24H_MM = 5.0  # enough to matter for irrigation
RAIN_TRACE_24H_MM = 1.0

HUMID_PCT = 75
VERY_HUMID_PCT = 85
WARM_C = 30
HOT_C = 35
COOL_C = 16

# Cloud, for the one role that reads it as a condition rather than as decoration.
CLOUD_OVERCAST_PCT = 80
CLOUD_BROKEN_PCT = 40

# How far ahead an escalation verdict looks, and how much movement in the
# engine's own hourly score counts as a direction rather than as noise.
ESCALATION_WINDOW_H = 12
ESCALATION_RISING = 15

# Temperature trend: the window, and the change below which "steady" is the
# honest word. 1.5 °C over six hours is weather; 0.4 °C is rounding.
TREND_WINDOW_H = 12
TREND_EPSILON_C = 1.5

WIND_BRISK_KMH = 30           # uncomfortable in the open
WIND_STRONG_KMH = 45          # unsafe for a small boat
VIS_POOR_KM = 2.0
VIS_LOW_KM = 5.0

STORM_CAUTION = 25            # Lightning/Storm sub-score
STORM_HIGH = 50

# Marine mode looks forward over these windows. Twelve hours is a tide's worth
# of planning and the span a small boat actually commits to.
PRESSURE_WINDOW_H = 12
WIND_WINDOW_H = 12
# hPa over the window. 3 hPa in twelve hours is the conventional line between a
# barograph that is drifting and one that is telling you something; 6 is the
# line at which it is telling you loudly.
PRESSURE_MOVE_HPA = 3.0
PRESSURE_FAST_HPA = 6.0
# km/h the peak must exceed the present by before the wind is said to be
# strengthening, so ordinary hour-to-hour noise is not reported as a change.
WIND_CHANGE_KMH = 8.0

# The commute windows the departure advice searches, in local hours.
# WORK_WINDOW is the daylight span the site reading searches instead.
MORNING_WINDOW = (6, 11)
EVENING_WINDOW = (16, 21)
WORK_WINDOW = (6, 18)

_LEVEL_ORDER = {"Low": 0, "Moderate": 1, "High": 2, "Severe": 3}


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


def _card(card_id: str, icon: str, title: str, headline: str, tone: str, detail: str = "") -> dict[str, Any]:
    return {
        "id": card_id,
        "icon": icon,
        "title": title,
        "headline": headline,
        "detail": detail,
        "tone": tone,
    }


class _Reading:
    """Everything the roles below share, measured once.

    Each attribute is either a real number from the payload or ``None``. There
    is no default-to-zero anywhere: a missing humidity reading must not become
    a dry day, and a missing forecast must not become a clear one.
    """

    def __init__(self, bundle: Any, risk: RiskOutput) -> None:
        cur = (getattr(bundle, "current", None) or {}) if bundle is not None else {}
        hourly = list(getattr(bundle, "hourly", None) or []) if bundle is not None else []
        daily = list(getattr(bundle, "daily", None) or []) if bundle is not None else []

        self.hourly = hourly
        self.daily = daily
        self.has_hourly = len(hourly) >= 6

        self.temp = _num(cur.get("temperature_c"))
        self.feels = _num(cur.get("apparent_temperature_c"))
        self.humidity = _num(cur.get("humidity_pct"))
        self.precip_now = _num(cur.get("precipitation_mm"))
        self.prob_now = _num(cur.get("precipitation_probability_pct"))
        self.wind = _num(cur.get("wind_speed_kmh"))
        self.gust = _num(cur.get("wind_gust_kmh"))
        self.direction = _num(cur.get("wind_direction_deg"))
        self.visibility = _num(cur.get("visibility_km"))
        self.cloud = _num(cur.get("cloud_cover_pct"))
        self.code = cur.get("weather_code")

        # Forward-looking totals, only when there are hours to total.
        rain_values = [_num(h.get("precipitation_mm")) for h in hourly[:24]]
        self.rain_24h = sum(v for v in rain_values if v is not None) if any(
            v is not None for v in rain_values
        ) else None

        probs = [_num(h.get("precipitation_probability_pct")) for h in hourly[:12]]
        known_probs = [v for v in probs if v is not None]
        self.prob_max_12h = max(known_probs) if known_probs else None

        # Marine mode reads forward, not just now. Both of these are None when
        # the provider did not send the series — never zero, which would read
        # as "no change" and "calm" rather than "we do not know".
        self.pressure = _num(cur.get("pressure_hpa"))
        self.pressure_window = [_num(h.get("pressure_hpa")) for h in hourly[:PRESSURE_WINDOW_H]]
        self.wind_window = [
            (h.get("time"), _num(h.get("wind_speed_kmh")), _num(h.get("wind_gust_kmh")))
            for h in hourly[:WIND_WINDOW_H]
        ]

        sub = risk.hazard_scores or {}
        self.storm_score = float(sub.get("Lightning/Storm", 0))
        self.rain_score = float(sub.get("Heavy Rainfall", 0))
        self.wind_score = float(sub.get("Strong Wind", 0))
        self.heat_score = float(sub.get("Extreme Heat", 0))
        self.flood_score = float(sub.get("Flood Risk", 0))
        self.level = risk.risk_level
        self.hazard = risk.detected_hazard

    # --- Derived questions the roles keep asking ---------------------------

    @property
    def rain_possible(self) -> bool:
        """Enough of a chance to be worth a cheap precaution.

        A packing list can carry an umbrella on a 30% chance and lose nothing.
        A verdict cannot — see `rain_likely`.
        """
        if self.rain_24h is not None and self.rain_24h >= RAIN_TRACE_24H_MM:
            return True
        if self.prob_max_12h is not None and self.prob_max_12h >= RAIN_MAYBE_PCT:
            return True
        return bool(self.precip_now and self.precip_now > 0)

    @property
    def rain_likely(self) -> bool:
        """Enough evidence to downgrade a verdict.

        Deliberately stricter than `rain_possible`: a 35% chance and a
        millimetre of drizzle is a reason to carry an umbrella, not a reason to
        tell someone their afternoon outdoors is compromised.
        """
        if self.rain_24h is not None and self.rain_24h >= 2.0:
            return True
        if self.prob_max_12h is not None and self.prob_max_12h >= RAIN_LIKELY_PCT:
            return True
        return bool(self.precip_now and self.precip_now > 0.2)

    @property
    def gust_or_wind(self) -> float | None:
        return self.gust if self.gust is not None else self.wind

    @property
    def severe(self) -> bool:
        return _LEVEL_ORDER.get(self.level, 0) >= _LEVEL_ORDER["High"]

    def hourly_risk(self, hour: dict[str, Any]) -> int:
        """The existing engine's own score for an hour, never a new one."""
        return int(_num(hour.get("risk_score")) or 0)


# ---------------------------------------------------------------------------
# General
# ---------------------------------------------------------------------------

def _general_full(m: _Reading, lang: str) -> list[dict[str, Any]]:
    """Umbrella, comfort, outdoors — and the main risk, named plainly."""
    cards = _general(m, lang)[:3]
    hazards = _by_id(_commuter(m, lang)).get("hazards")
    if hazards:
        cards.append(hazards)
    return cards[:5]


def _general(m: _Reading, lang: str) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []

    # --- Umbrella ---------------------------------------------------------
    if m.prob_max_12h is None and m.rain_24h is None and m.precip_now is None:
        cards.append(_card(
            "umbrella", "☔", i18n.sentence("ri_umbrella_title", lang),
            i18n.sentence("ri_no_data", lang), "info",
        ))
    elif m.rain_likely or m.rain_possible:
        detail = ""
        if m.prob_max_12h is not None:
            detail = i18n.sentence("ri_umbrella_prob", lang, prob=_r(m.prob_max_12h))
        elif m.rain_24h is not None:
            detail = i18n.sentence("ri_umbrella_mm", lang, mm=_r(m.rain_24h, 1))
        headline = i18n.sentence("ri_umbrella_yes" if m.rain_likely else "ri_umbrella_maybe", lang)
        cards.append(_card(
            "umbrella", "☔", i18n.sentence("ri_umbrella_title", lang), headline, "caution", detail,
        ))
    else:
        cards.append(_card(
            "umbrella", "☔", i18n.sentence("ri_umbrella_title", lang),
            i18n.sentence("ri_umbrella_no", lang), "safe",
        ))

    # --- Comfort ----------------------------------------------------------
    reading = m.feels if m.feels is not None else m.temp
    if reading is None:
        cards.append(_card(
            "comfort", "🌡️", i18n.sentence("ri_comfort_title", lang),
            i18n.sentence("ri_no_data", lang), "info",
        ))
    else:
        humid = m.humidity is not None and m.humidity >= HUMID_PCT
        if reading >= HOT_C:
            headline, tone = i18n.sentence("ri_comfort_hot", lang), "warn"
        elif reading >= WARM_C and humid:
            headline, tone = i18n.sentence("ri_comfort_muggy", lang), "caution"
        elif reading >= WARM_C:
            headline, tone = i18n.sentence("ri_comfort_warm", lang), "caution"
        elif reading <= COOL_C:
            headline, tone = i18n.sentence("ri_comfort_cool", lang), "info"
        else:
            headline, tone = i18n.sentence("ri_comfort_ok", lang), "safe"
        detail = i18n.sentence("ri_comfort_detail", lang, feels=_r(reading), hum=_r(m.humidity)) if (
            m.humidity is not None
        ) else i18n.sentence("ri_comfort_detail_temp", lang, feels=_r(reading))
        cards.append(_card("comfort", "🌡️", i18n.sentence("ri_comfort_title", lang), headline, tone, detail))

    # --- Outdoors ---------------------------------------------------------
    if m.level == "Severe" or m.storm_score >= STORM_HIGH:
        headline, tone = i18n.sentence("ri_outdoor_avoid", lang), "danger"
    elif m.severe or m.rain_likely or (m.gust_or_wind or 0) >= WIND_BRISK_KMH:
        headline, tone = i18n.sentence("ri_outdoor_caution", lang), "caution"
    else:
        headline, tone = i18n.sentence("ri_outdoor_good", lang), "safe"
    cards.append(_card(
        "outdoor", "🚶", i18n.sentence("ri_outdoor_title", lang), headline, tone,
        i18n.sentence(
            "ri_from_risk", lang,
            level=i18n.level_label(m.level, lang),
            hazard=i18n.hazard_label(m.hazard, lang),
        ),
    ))

    return cards


# ---------------------------------------------------------------------------
# Farmer
# ---------------------------------------------------------------------------

def _farmer(m: _Reading, lang: str) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []

    # --- Rain impact ------------------------------------------------------
    if m.rain_24h is None and m.prob_max_12h is None:
        cards.append(_card(
            "rain_impact", "🌧️", i18n.sentence("ri_rain_title", lang),
            i18n.sentence("ri_no_data", lang), "info",
        ))
    else:
        heavy = (m.rain_24h is not None and m.rain_24h >= RAIN_HEAVY_24H_MM) or (
            m.prob_max_12h is not None and m.prob_max_12h >= 70
        )
        some = (m.rain_24h is not None and m.rain_24h >= 2.0) or (
            m.prob_max_12h is not None and m.prob_max_12h >= 40
        )
        if heavy:
            headline, tone = i18n.sentence("ri_rain_high", lang), "warn"
        elif some:
            headline, tone = i18n.sentence("ri_rain_moderate", lang), "caution"
        else:
            headline, tone = i18n.sentence("ri_rain_low", lang), "safe"
        detail = (
            i18n.sentence("ri_rain_detail_mm", lang, mm=_r(m.rain_24h, 1))
            if m.rain_24h is not None
            else i18n.sentence("ri_rain_detail_prob", lang, prob=_r(m.prob_max_12h))
        )
        cards.append(_card("rain_impact", "🌧️", i18n.sentence("ri_rain_title", lang), headline, tone, detail))

    # --- Irrigation -------------------------------------------------------
    # The one card that must never guess: a wrong "delay" costs a crop.
    if m.rain_24h is None:
        cards.append(_card(
            "irrigation", "💧", i18n.sentence("ri_irrigation_title", lang),
            i18n.sentence("ri_irrigation_nodata", lang), "info",
        ))
    elif m.rain_24h >= RAIN_MEANINGFUL_24H_MM:
        cards.append(_card(
            "irrigation", "💧", i18n.sentence("ri_irrigation_title", lang),
            i18n.sentence("ri_irrigation_delay", lang), "safe",
            i18n.sentence("ri_irrigation_delay_detail", lang, mm=_r(m.rain_24h, 1)),
        ))
    elif m.rain_24h < RAIN_TRACE_24H_MM and (m.prob_max_12h is None or m.prob_max_12h < RAIN_MAYBE_PCT):
        cards.append(_card(
            "irrigation", "💧", i18n.sentence("ri_irrigation_title", lang),
            i18n.sentence("ri_irrigation_needed", lang), "caution",
            i18n.sentence("ri_irrigation_dry_detail", lang),
        ))
    else:
        cards.append(_card(
            "irrigation", "💧", i18n.sentence("ri_irrigation_title", lang),
            i18n.sentence("ri_irrigation_monitor", lang), "info",
            i18n.sentence("ri_irrigation_monitor_detail", lang, mm=_r(m.rain_24h, 1)),
        ))

    # --- Crop weather risk ------------------------------------------------
    # A weather advisory, never a diagnosis: warm, wet and humid air is a
    # condition under which fungal problems become more likely, and that is
    # all this claims.
    if m.humidity is None:
        cards.append(_card(
            "crop_risk", "🦠", i18n.sentence("ri_crop_title", lang),
            i18n.sentence("ri_no_data", lang), "info",
        ))
    else:
        warm = m.temp is not None and 18 <= m.temp <= 35
        wet = m.rain_24h is not None and m.rain_24h >= 2.0
        if m.humidity >= VERY_HUMID_PCT and warm and wet:
            headline, tone, key = i18n.sentence("ri_crop_high", lang), "warn", "ri_crop_high_detail"
        elif m.humidity >= HUMID_PCT or wet:
            headline, tone, key = i18n.sentence("ri_crop_moderate", lang), "caution", "ri_crop_moderate_detail"
        else:
            headline, tone, key = i18n.sentence("ri_crop_low", lang), "safe", "ri_crop_low_detail"
        cards.append(_card(
            "crop_risk", "🦠", i18n.sentence("ri_crop_title", lang), headline, tone,
            i18n.sentence(key, lang, hum=_r(m.humidity)),
        ))

    # --- Field advisory ---------------------------------------------------
    # The tone follows the sentence. A storm warning rendered in the same
    # neutral grey as "a usable window for field work" is a warning nobody
    # reads, which is the failure mode this card exists to avoid.
    if m.storm_score >= STORM_HIGH:
        line, tone = i18n.sentence("ri_field_storm", lang), "danger"
    elif m.storm_score >= STORM_CAUTION:
        line, tone = i18n.sentence("ri_field_storm", lang), "warn"
    elif m.rain_24h is not None and m.rain_24h >= RAIN_MEANINGFUL_24H_MM:
        line, tone = i18n.sentence("ri_field_rain", lang, mm=_r(m.rain_24h, 1)), "caution"
    elif m.humidity is not None and m.humidity >= VERY_HUMID_PCT:
        line, tone = i18n.sentence("ri_field_humid", lang, hum=_r(m.humidity)), "caution"
    elif m.feels is not None and m.feels >= HOT_C:
        line, tone = i18n.sentence("ri_field_hot", lang, feels=_r(m.feels)), "caution"
    else:
        line, tone = i18n.sentence("ri_field_clear", lang), "safe"
    cards.append(_card("field_advisory", "🌱", i18n.sentence("ri_field_title", lang), line, tone))

    return cards


# ---------------------------------------------------------------------------
# Fisherman
# ---------------------------------------------------------------------------

_POINTS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")


def _compass_point(degrees: float | None) -> str | None:
    """Eight-point bearing, or nothing. Never a guessed direction."""
    if degrees is None:
        return None
    return _POINTS[int(round((degrees % 360) / 45)) % 8]


def _pressure_card(m: _Reading, lang: str) -> dict[str, Any]:
    """What the barometer is doing, from the hourly series.

    A pressure reading on its own says almost nothing — 1004 hPa is ordinary in
    one place and a warning in another. What a mariner reads is the *slope*, so
    this reports the change across the window and names the present value only
    as context for it.

    Returns the "no forecast" card rather than a guess when the provider did not
    send the series: a missing barograph is not a flat one.
    """
    known = [v for v in m.pressure_window if v is not None]
    if m.pressure is None or len(known) < 2:
        return _card(
            "pressure", "🕭", i18n.sentence("ri_pressure_title", lang),
            i18n.sentence("ri_pressure_none", lang), "info",
        )

    delta = known[-1] - known[0]
    hours = len(known) - 1
    if delta <= -PRESSURE_FAST_HPA:
        headline, tone = i18n.sentence("ri_pressure_falling_fast", lang), "danger"
    elif delta <= -PRESSURE_MOVE_HPA:
        headline, tone = i18n.sentence("ri_pressure_falling", lang), "caution"
    elif delta >= PRESSURE_MOVE_HPA:
        headline, tone = i18n.sentence("ri_pressure_rising", lang), "safe"
    else:
        headline, tone = i18n.sentence("ri_pressure_steady", lang), "safe"

    return _card(
        "pressure", "🕭", i18n.sentence("ri_pressure_title", lang), headline, tone,
        i18n.sentence(
            "ri_pressure_detail", lang,
            hpa=_r(m.pressure), delta=f"{delta:+.1f}", hours=hours,
        ),
    )


def _wind_outlook(m: _Reading, lang: str) -> str:
    """"When will the wind increase?" — as a sentence, or an empty one.

    Answered from the hourly series and nothing else. The hour named is the
    first hour whose wind crosses the present by a margin wide enough not to be
    hour-to-hour noise; if no hour does, the honest answer is that little
    changes, not a time picked to have something to say.
    """
    readings = [(t, max(w or 0, g or 0)) for t, w, g in m.wind_window if w is not None or g is not None]
    if len(readings) < 3 or m.gust_or_wind is None:
        return ""

    now = m.gust_or_wind
    peak_time, peak = max(readings, key=lambda pair: pair[1])
    trough_time, trough = min(readings, key=lambda pair: pair[1])
    tail = i18n.sentence("ri_wind_peak", lang, kmh=_r(peak), hours=len(readings) - 1)

    if peak - now >= WIND_CHANGE_KMH:
        lead = i18n.sentence("ri_wind_rising", lang, time=_clock(peak_time))
    elif now - trough >= WIND_CHANGE_KMH:
        lead = i18n.sentence("ri_wind_easing", lang, time=_clock(trough_time))
    else:
        lead = i18n.sentence("ri_wind_steady", lang)
    return f"{lead}. {tail}" if lead else tail


def _clock(stamp: Any) -> str:
    """The hour from an ISO timestamp, or an empty string. Never a guess."""
    text = str(stamp or "")
    return text.split("T")[1][:5] if "T" in text else ""


def _marine(m: _Reading, lang: str) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []

    # --- Go / caution / avoid ---------------------------------------------
    # Deliberately pessimistic. Every branch that could send a small boat out
    # requires the absence of a hazard, not the presence of good news.
    wind = m.gust_or_wind
    if m.storm_score >= STORM_HIGH or m.level == "Severe" or (wind is not None and wind >= WIND_STRONG_KMH):
        headline, tone = i18n.sentence("ri_fishing_avoid", lang), "danger"
    elif (
        m.storm_score >= STORM_CAUTION
        or m.severe
        or (wind is not None and wind >= WIND_BRISK_KMH)
        or (m.visibility is not None and m.visibility < VIS_POOR_KM)
        or m.rain_likely
    ):
        headline, tone = i18n.sentence("ri_fishing_caution", lang), "caution"
    else:
        headline, tone = i18n.sentence("ri_fishing_favorable", lang), "safe"
    cards.append(_card(
        "fishing_conditions", "🎣", i18n.sentence("ri_fishing_title", lang), headline, tone,
        i18n.sentence("ri_fishing_detail", lang),
    ))

    # --- Wind --------------------------------------------------------------
    if m.wind is None:
        cards.append(_card(
            "wind", "🌬️", i18n.sentence("ri_wind_title", lang),
            i18n.sentence("ri_no_data", lang), "info",
        ))
    else:
        point = _compass_point(m.direction)
        headline = f"{_r(m.wind)} km/h" + (f" · {point}" if point else "")
        tone = "danger" if m.wind >= WIND_STRONG_KMH else "caution" if m.wind >= WIND_BRISK_KMH else "safe"
        # Now, then what it does next: a boat commits to the next twelve hours,
        # not to this minute.
        parts = [i18n.sentence("ri_wind_gust", lang, gust=_r(m.gust))] if m.gust is not None else []
        outlook = _wind_outlook(m, lang)
        if outlook:
            parts.append(outlook)
        cards.append(_card(
            "wind", "🌬️", i18n.sentence("ri_wind_title", lang), headline, tone, " ".join(parts),
        ))

    # --- Pressure -----------------------------------------------------------
    cards.append(_pressure_card(m, lang))

    # --- Lightning and storm ------------------------------------------------
    if m.storm_score >= STORM_HIGH:
        headline, tone, key = i18n.sentence("ri_storm_high", lang), "danger", "ri_storm_high_detail"
    elif m.storm_score >= STORM_CAUTION:
        headline, tone, key = i18n.sentence("ri_storm_moderate", lang), "caution", "ri_storm_moderate_detail"
    else:
        headline, tone, key = i18n.sentence("ri_storm_low", lang), "safe", "ri_storm_low_detail"
    cards.append(_card(
        "storm_risk", "⚡", i18n.sentence("ri_storm_title", lang), headline, tone, i18n.sentence(key, lang),
    ))

    # --- Visibility ---------------------------------------------------------
    if m.visibility is None:
        cards.append(_card(
            "visibility", "👁️", i18n.sentence("ri_visibility_title", lang),
            i18n.sentence("ri_no_data", lang), "info",
        ))
    else:
        tone = "danger" if m.visibility < VIS_POOR_KM else "caution" if m.visibility < VIS_LOW_KM else "safe"
        cards.append(_card(
            "visibility", "👁️", i18n.sentence("ri_visibility_title", lang),
            f"{_r(m.visibility, 1)} km", tone,
        ))

    return cards


# ---------------------------------------------------------------------------
# Commuter
# ---------------------------------------------------------------------------

def _reminder(m: _Reading, lang: str) -> dict[str, Any]:
    """The one line to leave with, shared by every reading that closes on one.

    Kept in one place because five roles end on it: two copies of this ladder
    would eventually disagree about what a 40% chance of rain is worth.
    """
    if m.storm_score >= STORM_HIGH:
        line, tone = i18n.sentence("ri_reminder_storm", lang), "danger"
    elif m.rain_possible:
        # Worth saying at a 30% chance; not worth an amber card when the risk
        # beside it reads Low and no hazard was detected.
        line = i18n.sentence("ri_reminder_rain", lang)
        tone = "caution" if m.rain_likely else "info"
    elif (m.gust_or_wind or 0) >= WIND_BRISK_KMH:
        line, tone = i18n.sentence("ri_reminder_wind", lang), "caution"
    else:
        line, tone = i18n.sentence("ri_reminder_clear", lang), "safe"
    return _card("reminder", "💬", i18n.sentence("ri_reminder_title", lang), line, tone)


def _best_departure(m: _Reading) -> tuple[str, int] | None:
    """The calmest hour in the next commute window, by the existing risk score.

    Returns ``None`` when there is no hourly series to search, rather than
    naming an hour on no evidence. The score is the engine's own — this picks a
    minimum, it does not compute one.
    """
    if not m.has_hourly:
        return None
    candidates: list[tuple[int, str]] = []
    for hour in m.hourly[:14]:
        stamp = str(hour.get("time") or "")
        # "2026-09-06T08:00" — the hour is the two characters after "T".
        if "T" not in stamp:
            continue
        try:
            local_hour = int(stamp.split("T", 1)[1][:2])
        except (ValueError, IndexError):
            continue
        in_window = (
            MORNING_WINDOW[0] <= local_hour <= MORNING_WINDOW[1]
            or EVENING_WINDOW[0] <= local_hour <= EVENING_WINDOW[1]
        )
        if in_window:
            candidates.append((m.hourly_risk(hour), stamp.split("T", 1)[1][:5]))
    if not candidates:
        return None
    score, label = min(candidates, key=lambda pair: pair[0])
    return label, score


def _commuter(m: _Reading, lang: str) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []

    # --- Commute risk ---------------------------------------------------------
    if m.level == "Severe" or m.storm_score >= STORM_HIGH:
        headline, tone = i18n.sentence("ri_commute_high", lang), "danger"
    elif m.rain_likely or m.severe or (m.visibility is not None and m.visibility < VIS_LOW_KM):
        headline, tone = i18n.sentence("ri_commute_moderate", lang), "caution"
    else:
        headline, tone = i18n.sentence("ri_commute_low", lang), "safe"
    cards.append(_card(
        "commute_risk", "🚗", i18n.sentence("ri_commute_title", lang), headline, tone,
        i18n.sentence("ri_commute_detail", lang),
    ))

    # --- Hazards actually detected ---------------------------------------------
    hazards: list[str] = []
    if m.rain_likely:
        hazards.append("🌧️ " + i18n.sentence("ri_factor_rain", lang))
    if m.storm_score >= STORM_CAUTION:
        hazards.append("⚡ " + i18n.sentence("ri_factor_storm", lang))
    if (m.gust_or_wind or 0) >= WIND_BRISK_KMH:
        hazards.append("💨 " + i18n.sentence("ri_factor_wind", lang))
    if m.visibility is not None and m.visibility < VIS_LOW_KM:
        hazards.append("👁️ " + i18n.sentence("ri_factor_visibility", lang))
    cards.append(_card(
        "hazards", "⚠️", i18n.sentence("ri_hazards_title", lang),
        " · ".join(hazards) if hazards else i18n.sentence("ri_hazards_none", lang),
        "caution" if hazards else "safe",
    ))

    # --- Best departure --------------------------------------------------------
    best = _best_departure(m)
    if best is not None:
        label, score = best
        cards.append(_card(
            "departure", "🕗", i18n.sentence("ri_departure_title", lang), label,
            "safe" if score < 31 else "caution",
            i18n.sentence("ri_departure_detail", lang),
        ))

    # --- One line to leave with -------------------------------------------------
    cards.append(_reminder(m, lang))

    return cards


# ---------------------------------------------------------------------------
# Driver
#
# A driver is steering through the weather rather than planning around it, so
# every card here is about the next stretch of road: what can be seen, what the
# surface is doing, and what the wind does to the vehicle.
# ---------------------------------------------------------------------------

def _driver_full(m: _Reading, lang: str) -> list[dict[str, Any]]:
    """The driving reading, with the two cards the brief adds to it.

    Road visibility, road surface and crosswind are what the road is doing;
    commute risk and the departure hour are what to do about it. The commuter
    reading already computed both from the same hours, so they are borrowed
    rather than recomputed — one departure hour in the system, not two.
    """
    commuter = _by_id(_commuter(m, lang))
    cards = _driver(m, lang)[:3]
    for key in ("commute_risk", "departure"):
        if commuter.get(key):
            cards.append(commuter[key])
    return cards[:5]


def _driver(m: _Reading, lang: str) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []

    # --- Road visibility ---------------------------------------------------
    if m.visibility is None:
        cards.append(_card(
            "road_visibility", "👁️", i18n.sentence("ri_road_vis_title", lang),
            i18n.sentence("ri_no_data", lang), "info",
        ))
    else:
        if m.visibility < VIS_POOR_KM:
            headline, tone = i18n.sentence("ri_road_vis_poor", lang), "danger"
        elif m.visibility < VIS_LOW_KM:
            headline, tone = i18n.sentence("ri_road_vis_reduced", lang), "caution"
        else:
            headline, tone = i18n.sentence("ri_road_vis_clear", lang), "safe"
        cards.append(_card(
            "road_visibility", "👁️", i18n.sentence("ri_road_vis_title", lang), headline, tone,
            i18n.sentence("ri_road_vis_detail", lang, km=_r(m.visibility, 1)),
        ))

    # --- Road surface ------------------------------------------------------
    if m.rain_24h is None and m.prob_max_12h is None and m.precip_now is None:
        cards.append(_card(
            "road_surface", "🛣️", i18n.sentence("ri_road_surface_title", lang),
            i18n.sentence("ri_no_data", lang), "info",
        ))
    else:
        heavy = (m.rain_24h is not None and m.rain_24h >= RAIN_HEAVY_24H_MM) or m.flood_score >= 40
        if heavy:
            headline, tone = i18n.sentence("ri_road_surface_standing", lang), "warn"
        elif m.rain_likely:
            headline, tone = i18n.sentence("ri_road_surface_wet", lang), "caution"
        else:
            headline, tone = i18n.sentence("ri_road_surface_dry", lang), "safe"
        detail = i18n.sentence("ri_road_surface_detail", lang) if m.rain_possible else ""
        cards.append(_card(
            "road_surface", "🛣️", i18n.sentence("ri_road_surface_title", lang), headline, tone, detail,
        ))

    # --- Crosswind ---------------------------------------------------------
    reading = m.gust_or_wind
    if reading is None:
        cards.append(_card(
            "crosswind", "💨", i18n.sentence("ri_crosswind_title", lang),
            i18n.sentence("ri_no_data", lang), "info",
        ))
    else:
        if reading >= WIND_STRONG_KMH:
            headline, tone = i18n.sentence("ri_crosswind_strong", lang), "warn"
        elif reading >= WIND_BRISK_KMH:
            headline, tone = i18n.sentence("ri_crosswind_brisk", lang), "caution"
        else:
            headline, tone = i18n.sentence("ri_crosswind_calm", lang), "safe"
        detail = i18n.sentence("ri_wind_gust", lang, gust=_r(m.gust)) if m.gust is not None else ""
        cards.append(_card(
            "crosswind", "💨", i18n.sentence("ri_crosswind_title", lang), headline, tone, detail,
        ))

    cards.append(_reminder(m, lang))
    return cards


# ---------------------------------------------------------------------------
# Outdoor worker
# ---------------------------------------------------------------------------

def _best_daylight_hour(m: _Reading) -> tuple[str, int] | None:
    """The calmest working hour in the forecast, by the engine's own score.

    Same discipline as ``_best_departure``: this picks a minimum out of scores
    the risk engine already produced, and returns ``None`` when there is no
    hourly series rather than naming an hour on no evidence.
    """
    if not m.has_hourly:
        return None
    candidates: list[tuple[int, str]] = []
    for hour in m.hourly[:14]:
        stamp = str(hour.get("time") or "")
        if "T" not in stamp:
            continue
        try:
            local_hour = int(stamp.split("T", 1)[1][:2])
        except (ValueError, IndexError):
            continue
        if WORK_WINDOW[0] <= local_hour <= WORK_WINDOW[1]:
            candidates.append((m.hourly_risk(hour), stamp.split("T", 1)[1][:5]))
    if not candidates:
        return None
    score, label = min(candidates, key=lambda pair: pair[0])
    return label, score


def _outdoor_worker_full(m: _Reading, lang: str) -> list[dict[str, Any]]:
    """Heat, lightning, the working window — plus what the site is exposed to."""
    cards = _outdoor_worker(m, lang)[:4]
    exposure = _by_id(_caregiver(m, lang)).get("exposure")
    if exposure:
        cards.append(exposure)
    return cards[:5]


def _outdoor_worker(m: _Reading, lang: str) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []

    # --- Heat stress -------------------------------------------------------
    # Apparent temperature is the right input here: humidity is exactly what
    # turns a workable 33°C into an unworkable one.
    reading = m.feels if m.feels is not None else m.temp
    if reading is None:
        cards.append(_card(
            "heat_stress", "🥵", i18n.sentence("ri_heatstress_title", lang),
            i18n.sentence("ri_no_data", lang), "info",
        ))
    else:
        humid = m.humidity is not None and m.humidity >= HUMID_PCT
        if reading >= HOT_C or m.heat_score >= 50:
            headline, tone = i18n.sentence("ri_heatstress_high", lang), "warn"
        elif reading >= WARM_C and humid:
            headline, tone = i18n.sentence("ri_heatstress_moderate", lang), "caution"
        else:
            headline, tone = i18n.sentence("ri_heatstress_ok", lang), "safe"
        detail = i18n.sentence("ri_comfort_detail", lang, feels=_r(reading), hum=_r(m.humidity)) if (
            m.humidity is not None
        ) else i18n.sentence("ri_comfort_detail_temp", lang, feels=_r(reading))
        cards.append(_card(
            "heat_stress", "🥵", i18n.sentence("ri_heatstress_title", lang), headline, tone, detail,
        ))

    # --- Lightning ---------------------------------------------------------
    if m.storm_score >= STORM_HIGH:
        headline, tone = i18n.sentence("ri_storm_high", lang), "danger"
        detail = i18n.sentence("ri_storm_high_detail", lang)
    elif m.storm_score >= STORM_CAUTION:
        headline, tone = i18n.sentence("ri_storm_moderate", lang), "caution"
        detail = i18n.sentence("ri_storm_moderate_detail", lang)
    else:
        headline, tone = i18n.sentence("ri_storm_low", lang), "safe"
        detail = i18n.sentence("ri_storm_low_detail", lang)
    cards.append(_card(
        "lightning", "⚡", i18n.sentence("ri_storm_title", lang), headline, tone, detail,
    ))

    # --- Easiest working window --------------------------------------------
    best = _best_daylight_hour(m)
    if best is None:
        cards.append(_card(
            "work_window", "🕗", i18n.sentence("ri_workwindow_title", lang),
            i18n.sentence("ri_workwindow_none", lang), "info",
        ))
    else:
        label, score = best
        cards.append(_card(
            "work_window", "🕗", i18n.sentence("ri_workwindow_title", lang), label,
            "safe" if score < 31 else "caution",
            i18n.sentence("ri_workwindow_detail", lang),
        ))

    cards.append(_reminder(m, lang))
    return cards


# ---------------------------------------------------------------------------
# Preparedness
# ---------------------------------------------------------------------------

def _preparedness_card(m: _Reading, lang: str) -> dict[str, Any]:
    """Part of the caregiver reading.

    Gated on storm and wind, because a power interruption is what those two
    actually predict — heavy rain alone is not a reason to tell someone to find
    a torch.
    """
    windy = (m.gust_or_wind or 0) >= WIND_STRONG_KMH
    if m.storm_score >= STORM_HIGH or m.level == "Severe" or windy:
        headline, tone = i18n.sentence("ri_prepare_high", lang), "warn"
    elif m.storm_score >= STORM_CAUTION or (m.gust_or_wind or 0) >= WIND_BRISK_KMH:
        headline, tone = i18n.sentence("ri_prepare_watch", lang), "caution"
    else:
        return _card(
            "prepare", "🔦", i18n.sentence("ri_prepare_title", lang),
            i18n.sentence("ri_prepare_normal", lang), "safe",
        )
    return _card(
        "prepare", "🔦", i18n.sentence("ri_prepare_title", lang), headline, tone,
        i18n.sentence("ri_prepare_detail", lang),
    )




# ---------------------------------------------------------------------------
# Student
#
# Built entirely from cards the other readings already own: a student's weather
# questions are the journey, the afternoon outdoors, and when to leave. Writing
# a second set of sentences for them would only create a way for the two to
# disagree.
# ---------------------------------------------------------------------------

def _retitle(card: dict[str, Any] | None, card_id: str, title_key: str, lang: str,
             icon: str | None = None) -> dict[str, Any] | None:
    """The same verdict, under the heading this reader would use for it.

    A verdict about visibility is the same verdict whoever is reading it — the
    measurement has not changed and neither has the threshold. What changes is
    what the reader calls the thing they are asking about, and a card headed
    "Road surface" in front of someone walking to college is a card written for
    somebody else.

    So this renames rather than recomputes. Nothing downstream can tell the
    difference between this and an original card, which is the point: there is
    still one visibility reading in the system.
    """
    if not card:
        return None
    renamed = dict(card)
    renamed["id"] = card_id
    # An empty key is a role that calls the thing by its ordinary name — it
    # still wants its own card id, so the chip and the tests can address it.
    if title_key:
        renamed["title"] = i18n.sentence(title_key, lang)
    if icon:
        renamed["icon"] = icon
    return renamed


def _student(m: _Reading, lang: str) -> list[dict[str, Any]]:
    """The campus reading.

    It used to be the driver's cards with a different heading above them: road
    visibility, road surface, crosswind. Those are answers to a question about a
    vehicle. A student is asking whether to cross the campus, how long the
    journey will take, and whether it is safe to be outside — so the readings are
    the same measurements under the headings that question uses.
    """
    general = _by_id(_general(m, lang))
    commuter = _by_id(_commuter(m, lang))
    marine = _by_id(_marine(m, lang))

    cards = [
        # Is it a day to be outside on campus?
        _retitle(general.get("outdoor"), "campus", "ri_campus_title", lang, "🎓"),
        # The journey there and back.
        _retitle(commuter.get("commute_risk"), "college_commute", "ri_college_title", lang, "🎒"),
        # The one hazard a campus cannot shelter from at short notice.
        _retitle(marine.get("storm_risk"), "lightning_safety", "ri_lightning_safety_title", lang, "⚡"),
        # When to set out.
        commuter.get("departure"),
        _retitle(_reminder(m, lang), "student_reminder", "ri_student_reminder_title", lang, "📌"),
    ]
    return [card for card in cards if card][:5]


def _by_id(cards: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Another reading's cards, addressable by name."""
    return {card["id"]: card for card in cards}


# ---------------------------------------------------------------------------
# Community / caregiver
# ---------------------------------------------------------------------------

def _drying_card(m: _Reading, lang: str) -> dict[str, Any]:
    """Will washing hung out today dry, or come in wetter than it went out.

    Kept when the household reading left the selector: whoever is running a home
    still asks it, and the caregiver reading is where that reader now lands.
    """
    if m.rain_24h is None and m.prob_max_12h is None and m.humidity is None:
        return _card(
            "home_rain", "🧺", i18n.sentence("ri_home_rain_title", lang),
            i18n.sentence("ri_no_data", lang), "info",
        )
    if m.rain_likely:
        headline, tone = i18n.sentence("ri_home_rain_wet", lang), "caution"
    elif m.rain_possible or (m.humidity is not None and m.humidity >= VERY_HUMID_PCT):
        headline, tone = i18n.sentence("ri_home_rain_maybe", lang), "info"
    else:
        headline, tone = i18n.sentence("ri_home_rain_dry", lang), "safe"
    if m.prob_max_12h is not None:
        detail = i18n.sentence("ri_umbrella_prob", lang, prob=_r(m.prob_max_12h))
    elif m.rain_24h is not None:
        detail = i18n.sentence("ri_umbrella_mm", lang, mm=_r(m.rain_24h, 1))
    else:
        detail = ""
    return _card("home_rain", "🧺", i18n.sentence("ri_home_rain_title", lang), headline, tone, detail)


def _caregiver(m: _Reading, lang: str) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []

    # --- The people being cared for ----------------------------------------
    reading = m.feels if m.feels is not None else m.temp
    if reading is None:
        cards.append(_card(
            "vulnerable", "🧓", i18n.sentence("ri_vulnerable_title", lang),
            i18n.sentence("ri_no_data", lang), "info",
        ))
    else:
        if reading >= HOT_C or m.heat_score >= 40:
            headline, tone = i18n.sentence("ri_vulnerable_heat", lang), "warn"
        elif reading <= COOL_C:
            headline, tone = i18n.sentence("ri_vulnerable_cold", lang), "caution"
        else:
            headline, tone = i18n.sentence("ri_vulnerable_ok", lang), "safe"
        detail = i18n.sentence("ri_comfort_detail", lang, feels=_r(reading), hum=_r(m.humidity)) if (
            m.humidity is not None
        ) else i18n.sentence("ri_comfort_detail_temp", lang, feels=_r(reading))
        cards.append(_card(
            "vulnerable", "🧓", i18n.sentence("ri_vulnerable_title", lang), headline, tone, detail,
        ))

    # --- Exposure outdoors -------------------------------------------------
    windy = (m.gust_or_wind or 0) >= WIND_BRISK_KMH
    if m.severe or m.storm_score >= STORM_HIGH:
        headline, tone = i18n.sentence("ri_exposure_high", lang), "danger"
    elif m.rain_likely or windy:
        headline, tone = i18n.sentence("ri_exposure_some", lang), "caution"
    else:
        headline, tone = i18n.sentence("ri_exposure_low", lang), "safe"
    cards.append(_card(
        "exposure", "🌧️", i18n.sentence("ri_exposure_title", lang), headline, tone,
        i18n.sentence("ri_exposure_detail", lang) if tone != "safe" else "",
    ))

    cards.append(_drying_card(m, lang))
    cards.append(_preparedness_card(m, lang))
    cards.append(_reminder(m, lang))
    return cards


# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# The readings the twelve professions are composed from
#
# Everything above this line produces cards in groups, because that is how the
# seven original readings were written: one function per role, each returning
# its whole panel. That shape could not survive twelve roles — an aviation
# visibility card and a driver visibility card would have been two copies of one
# threshold, and the second copy is where they drift apart.
#
# So a *reading* is now the unit: one measurement, one verdict, one card. A role
# is a list of readings with its own names for them (see `roles.py`). Nothing
# below recomputes anything the groups above already decide; the groups are the
# implementation, and this is the index into them.
# ---------------------------------------------------------------------------

_GROUPS = {
    "general": _general,
    "farmer": _farmer,
    "marine": _marine,
    "commuter": _commuter,
    "driver": _driver,
    "worker": _outdoor_worker,
    "care": _caregiver,
}


class _Library:
    """Every reading available for one request, each computed at most once.

    Twelve roles share nine or ten readings between them, and a role's panel
    asks for four or five. Without the cache, composing one panel would run the
    driver group three times over.
    """

    def __init__(self, m: _Reading, lang: str) -> None:
        self._m = m
        self._lang = lang
        self._cards: dict[str, dict[str, Any]] = {}
        self._done: set[str] = set()

    def _load(self, group: str) -> None:
        if group in self._done:
            return
        self._done.add(group)
        for card in _GROUPS[group](self._m, self._lang):
            # First writer wins. Two groups that both produce `reminder` produce
            # the same reminder — they call the same function — so this is a
            # guard against waste, not against disagreement.
            self._cards.setdefault(card["id"], card)

    def get(self, reading: str) -> dict[str, Any] | None:
        builder = _NEW_READINGS.get(reading)
        if builder is not None:
            if reading not in self._cards:
                card = builder(self._m, self._lang)
                if card is None:
                    return None
                self._cards[reading] = card
            return self._cards.get(reading)

        group = _READING_GROUP.get(reading)
        if group is None:
            return None
        self._load(group)
        return self._cards.get(reading)


# Which group produces which reading. Written out rather than discovered, so a
# reading named in `roles.py` that nothing produces fails a test rather than
# silently leaving a hole in somebody's panel.
_READING_GROUP: dict[str, str] = {
    "umbrella": "general", "comfort": "general", "outdoor": "general",
    "rain_impact": "farmer", "irrigation": "farmer", "crop_risk": "farmer",
    "field_advisory": "farmer",
    "fishing_conditions": "marine", "wind": "marine", "storm_risk": "marine",
    "visibility": "marine", "pressure": "marine",
    "commute_risk": "commuter", "hazards": "commuter", "departure": "commuter",
    "reminder": "commuter",
    "road_visibility": "driver", "road_surface": "driver", "crosswind": "driver",
    "heat_stress": "worker", "lightning": "worker", "work_window": "worker",
    "vulnerable": "care", "prepare": "care", "home_rain": "care",
    # Produced by the caregiver group, and deliberately only offered to it: its
    # detail line is about people who move slowly, which is that reader's
    # sentence and nobody else's.
    "exposure": "care",
}


# ---------------------------------------------------------------------------
# Readings the six new professions needed, and nobody had yet
#
# Each is built from a value the app already has. None of them fetches, none
# scores, and where the honest answer is "this application cannot measure that",
# the card says so instead of estimating it.
# ---------------------------------------------------------------------------

def _flight_conditions(m: _Reading, lang: str) -> dict[str, Any]:
    """Visibility, gusts and convection, read together.

    Deliberately a *summary of three measurements*, not an assessment of
    flyability. The wording stays in the register the rest of the app uses —
    "warrants caution", never "do not fly" — because the difference between an
    interpretation of a public forecast and aviation weather information is the
    whole reason this role carries a note.
    """
    vis, gust = m.visibility, m.gust_or_wind
    if vis is None and gust is None and not m.has_hourly:
        return _card("flight_conditions", "\u2708\ufe0f", i18n.sentence("ri_flight_title", lang),
                     i18n.sentence("ri_no_data", lang), "info")

    poor_vis = vis is not None and vis <= VIS_POOR_KM
    strong = gust is not None and gust >= WIND_STRONG_KMH
    if m.storm_score >= STORM_HIGH or poor_vis or strong:
        headline, tone = i18n.sentence("ri_flight_poor", lang), "danger"
    elif m.storm_score >= STORM_CAUTION or (vis is not None and vis <= VIS_LOW_KM) or (
        gust is not None and gust >= WIND_BRISK_KMH
    ):
        headline, tone = i18n.sentence("ri_flight_marginal", lang), "caution"
    else:
        headline, tone = i18n.sentence("ri_flight_good", lang), "safe"

    if vis is not None and gust is not None:
        detail = i18n.sentence("ri_flight_detail", lang, vis=_r(vis, 1), gust=_r(gust))
    elif vis is not None:
        detail = i18n.sentence("ri_flight_detail_vis", lang, vis=_r(vis, 1))
    elif gust is not None:
        detail = i18n.sentence("ri_flight_detail_wind", lang, gust=_r(gust))
    else:
        detail = ""
    return _card("flight_conditions", "\u2708\ufe0f", i18n.sentence("ri_flight_title", lang),
                 headline, tone, detail)


def _cloud(m: _Reading, lang: str) -> dict[str, Any]:
    if m.cloud is None:
        return _card("cloud", "\u2601\ufe0f", i18n.sentence("ri_cloud_title", lang),
                     i18n.sentence("ri_no_data", lang), "info")
    if m.cloud >= CLOUD_OVERCAST_PCT:
        headline, tone = i18n.sentence("ri_cloud_overcast", lang), "caution"
    elif m.cloud >= CLOUD_BROKEN_PCT:
        headline, tone = i18n.sentence("ri_cloud_broken", lang), "info"
    else:
        headline, tone = i18n.sentence("ri_cloud_clear", lang), "safe"
    return _card("cloud", "\u2601\ufe0f", i18n.sentence("ri_cloud_title", lang), headline, tone,
                 i18n.sentence("ri_cloud_detail", lang, pct=_r(m.cloud)))


# The exposures a hazard puts in play. Named from the hazard sub-scores the
# engine already produced — this is a restatement of those scores in the
# language of what is exposed, not a new judgement about where.
def _exposures(m: _Reading, lang: str) -> list[str]:
    out: list[str] = []
    if m.flood_score >= 31 or m.rain_score >= 40:
        out.append(i18n.sentence("ri_exposure_lowlying", lang))
    if m.wind_score >= 31 or m.storm_score >= STORM_CAUTION:
        out.append(i18n.sentence("ri_exposure_open", lang))
    if m.rain_score >= 31 or m.storm_score >= STORM_CAUTION or m.flood_score >= 31:
        out.append(i18n.sentence("ri_exposure_transport", lang))
    if m.heat_score >= 31:
        out.append(i18n.sentence("ri_exposure_outdoor", lang))
    return out


def _impact_area(m: _Reading, lang: str) -> dict[str, Any]:
    """What is exposed, from the hazard scores.

    NOT a geographic extent. This application scores one point at a time and
    has no polygon for an affected area; naming streets or wards from a single
    reading would be the exact kind of invention the product must not do. What
    it can say is which *kinds* of place a scored hazard bears on.
    """
    items = _exposures(m, lang)
    if not items:
        return _card("impact_area", "\U0001f5fa\ufe0f", i18n.sentence("ri_impact_area_title", lang),
                     i18n.sentence("ri_impact_area_none", lang), "safe")
    return _card("impact_area", "\U0001f5fa\ufe0f", i18n.sentence("ri_impact_area_title", lang),
                 " \u00b7 ".join(items), "caution" if len(items) < 3 else "warn",
                 i18n.sentence("ri_impact_area_detail", lang))


def _risk_path(m: _Reading) -> tuple[int, int, int] | None:
    """Now, the worst hour ahead, and how many hours until it.

    The engine's own hourly score, read rather than recomputed. ``None`` when
    the provider sent no hourly series — an escalation verdict on no series is
    a guess dressed as a trend.
    """
    if not m.has_hourly:
        return None
    scores = [m.hourly_risk(h) for h in m.hourly[:ESCALATION_WINDOW_H]]
    if not scores:
        return None
    peak = max(scores)
    return scores[0], peak, scores.index(peak)


def _escalation(m: _Reading, lang: str) -> dict[str, Any]:
    path = _risk_path(m)
    if path is None:
        return _card("escalation", "\U0001f4c8", i18n.sentence("ri_escalation_title", lang),
                     i18n.sentence("ri_no_data", lang), "info")
    now, peak, when = path
    if peak - now >= ESCALATION_RISING:
        headline, tone = i18n.sentence("ri_escalation_rising", lang), "warn"
    elif now - peak >= ESCALATION_RISING:
        headline, tone = i18n.sentence("ri_escalation_easing", lang), "safe"
    else:
        headline, tone = i18n.sentence("ri_escalation_steady", lang), "info"
    return _card("escalation", "\U0001f4c8", i18n.sentence("ri_escalation_title", lang), headline, tone,
                 i18n.sentence("ri_escalation_detail", lang, now=now, peak=peak, hours=max(when, 1)))


def _response_priority(m: _Reading, lang: str) -> dict[str, Any]:
    """Readiness, from the risk level and where it is heading.

    Three states, and the top one is "prepare to activate" rather than
    "activate": whether resources move is a decision for the person holding the
    roster, and a weather application is not in that chain of command.
    """
    path = _risk_path(m)
    rising = path is not None and path[1] - path[0] >= ESCALATION_RISING
    if m.level == "Severe" or (m.severe and rising):
        headline, tone, key = i18n.sentence("ri_response_activate", lang), "danger", "ri_response_activate_detail"
    elif m.severe or rising or m.storm_score >= STORM_CAUTION:
        headline, tone, key = i18n.sentence("ri_response_monitor", lang), "warn", "ri_response_monitor_detail"
    else:
        headline, tone, key = i18n.sentence("ri_response_routine", lang), "safe", "ri_response_routine_detail"
    return _card("response_priority", "\U0001f691", i18n.sentence("ri_response_title", lang),
                 headline, tone, i18n.sentence(key, lang))


def _official_status(m: _Reading, lang: str) -> dict[str, Any]:
    """The card that exists to say what this application is not.

    There is no official feed wired into this product. A response manager
    reading a screen that looks like a warning system has to be told that, in
    the panel, every time — not in a footnote under it.
    """
    return _card("official_status", "\U0001f4dc", i18n.sentence("ri_official_title", lang),
                 i18n.sentence("ri_official_none", lang), "info",
                 i18n.sentence("ri_official_detail", lang))


def _waterlogging(m: _Reading, lang: str) -> dict[str, Any]:
    """Whether water will stand, for somebody who owns the drains.

    Was the driver's road-surface verdict under a new title, which is how a
    municipal engineer came to be told about braking distance. The measurement
    is the same one — rainfall and the flood sub-score — but the question is
    not, and a retitle cannot change a sentence that names somebody else's
    windscreen.
    """
    if m.rain_24h is None and m.flood_score == 0 and m.rain_score == 0:
        return _card("waterlogging", "\U0001f30a", i18n.sentence("ri_waterlog_title", lang),
                     i18n.sentence("ri_no_data", lang), "info")
    heavy = m.flood_score >= 61 or (m.rain_24h is not None and m.rain_24h >= RAIN_HEAVY_24H_MM * 2)
    some = m.flood_score >= 31 or m.rain_score >= 40 or (
        m.rain_24h is not None and m.rain_24h >= RAIN_HEAVY_24H_MM
    )
    if heavy:
        headline, tone = i18n.sentence("ri_waterlog_high", lang), "warn"
    elif some:
        headline, tone = i18n.sentence("ri_waterlog_moderate", lang), "caution"
    else:
        headline, tone = i18n.sentence("ri_waterlog_low", lang), "safe"
    detail = (
        i18n.sentence("ri_urban_detail", lang, mm=_r(m.rain_24h, 1))
        if m.rain_24h is not None
        else i18n.sentence("ri_urban_detail_nodata", lang)
    )
    return _card("waterlogging", "\U0001f30a", i18n.sentence("ri_waterlog_title", lang),
                 headline, tone, detail)


def _urban_risk(m: _Reading, lang: str) -> dict[str, Any]:
    urban = max(m.flood_score, m.rain_score * 0.95, m.wind_score * 0.8, m.heat_score * 0.8)
    if urban >= 61:
        headline, tone = i18n.sentence("ri_urban_high", lang), "danger"
    elif urban >= 31:
        headline, tone = i18n.sentence("ri_urban_moderate", lang), "caution"
    else:
        headline, tone = i18n.sentence("ri_urban_low", lang), "safe"
    detail = (
        i18n.sentence("ri_urban_detail", lang, mm=_r(m.rain_24h, 1))
        if m.rain_24h is not None
        else i18n.sentence("ri_urban_detail_nodata", lang)
    )
    return _card("urban_risk", "\U0001f3d9\ufe0f", i18n.sentence("ri_urban_title", lang),
                 headline, tone, detail)


def _infrastructure(m: _Reading, lang: str) -> dict[str, Any]:
    if m.flood_score >= 31 or m.rain_score >= 40:
        headline, tone, key = i18n.sentence("ri_infra_drainage", lang), "warn", "ri_infra_drainage_detail"
    elif m.wind_score >= 31 or m.storm_score >= STORM_CAUTION:
        headline, tone, key = i18n.sentence("ri_infra_wind", lang), "warn", "ri_infra_wind_detail"
    elif m.heat_score >= 31:
        headline, tone, key = i18n.sentence("ri_infra_heat", lang), "caution", "ri_infra_heat_detail"
    else:
        headline, tone, key = i18n.sentence("ri_infra_low", lang), "safe", "ri_infra_low_detail"
    return _card("infrastructure", "\U0001f309", i18n.sentence("ri_infra_title", lang),
                 headline, tone, i18n.sentence(key, lang))


def _municipal_prep(m: _Reading, lang: str) -> dict[str, Any]:
    if m.level == "Severe" or m.flood_score >= 61:
        headline, tone = i18n.sentence("ri_municipal_act", lang), "warn"
    elif m.severe or m.flood_score >= 31 or m.rain_score >= 40:
        headline, tone = i18n.sentence("ri_municipal_watch", lang), "caution"
    else:
        headline, tone = i18n.sentence("ri_municipal_routine", lang), "safe"
    return _card("municipal_prep", "\U0001f6e0\ufe0f", i18n.sentence("ri_municipal_title", lang),
                 headline, tone, i18n.sentence("ri_municipal_detail", lang))


def _anomaly(m: _Reading, lang: str) -> dict[str, Any]:
    """Values outside the app's own thresholds — NOT a climatological anomaly.

    A real anomaly needs a baseline, and the baseline this product has lives
    behind an archive request that this module is not allowed to make. So the
    card reports what is measurably unusual against the thresholds the risk
    engine already uses, and points at the screen where the archive comparison
    actually is. Calling a threshold exceedance a climate anomaly would be the
    most quietly wrong thing on a researcher's screen.
    """
    notable: list[str] = []
    if m.feels is not None and m.feels >= HOT_C:
        notable.append(i18n.sentence("ri_anomaly_heat", lang, feels=_r(m.feels, 1)))
    if m.rain_24h is not None and m.rain_24h >= RAIN_HEAVY_24H_MM:
        notable.append(i18n.sentence("ri_anomaly_rain", lang, mm=_r(m.rain_24h, 1)))
    if (m.gust_or_wind or 0) >= WIND_STRONG_KMH:
        notable.append(i18n.sentence("ri_anomaly_wind", lang, wind=_r(m.gust_or_wind)))
    if m.humidity is not None and m.humidity >= VERY_HUMID_PCT:
        notable.append(i18n.sentence("ri_anomaly_humid", lang, hum=_r(m.humidity)))

    if notable:
        return _card("anomaly", "\U0001f4ca", i18n.sentence("ri_anomaly_title", lang),
                     i18n.sentence("ri_anomaly_notable", lang), "caution", " \u00b7 ".join(notable))
    return _card("anomaly", "\U0001f4ca", i18n.sentence("ri_anomaly_title", lang),
                 i18n.sentence("ri_anomaly_none", lang), "safe",
                 i18n.sentence("ri_anomaly_baseline", lang))


def _trend(m: _Reading, lang: str) -> dict[str, Any]:
    """Where temperature is heading, from the hourly series already fetched."""
    if not m.has_hourly:
        return _card("trend", "\U0001f4c9", i18n.sentence("ri_trend_title", lang),
                     i18n.sentence("ri_no_data", lang), "info")
    window = m.hourly[:TREND_WINDOW_H]
    temps = [_num(h.get("temperature_c")) for h in window]
    known = [t for t in temps if t is not None]
    if len(known) < 2:
        return _card("trend", "\U0001f4c9", i18n.sentence("ri_trend_title", lang),
                     i18n.sentence("ri_no_data", lang), "info")
    change = known[-1] - known[0]
    if change >= TREND_EPSILON_C:
        headline = i18n.sentence("ri_trend_warming", lang)
    elif change <= -TREND_EPSILON_C:
        headline = i18n.sentence("ri_trend_cooling", lang)
    else:
        headline = i18n.sentence("ri_trend_steady", lang)
    return _card("trend", "\U0001f4c9", i18n.sentence("ri_trend_title", lang), headline, "info",
                 i18n.sentence("ri_trend_detail", lang, start=_r(known[0], 1), end=_r(known[-1], 1),
                               hours=len(known)))


def _historical(m: _Reading, lang: str) -> dict[str, Any]:
    return _card("historical", "\U0001f4da", i18n.sentence("ri_historical_title", lang),
                 i18n.sentence("ri_historical_available", lang), "info",
                 i18n.sentence("ri_historical_detail", lang))


def _forecast_data(m: _Reading, lang: str) -> dict[str, Any]:
    """What series this reading is actually standing on."""
    if not m.hourly and not m.daily:
        return _card("forecast_data", "\U0001f4e1", i18n.sentence("ri_forecast_data_title", lang),
                     i18n.sentence("ri_no_data", lang), "info")
    return _card("forecast_data", "\U0001f4e1", i18n.sentence("ri_forecast_data_title", lang),
                 i18n.sentence("ri_forecast_data_head", lang, hours=len(m.hourly), days=len(m.daily)),
                 "info", i18n.sentence("ri_forecast_data_detail", lang))


def _indicators(m: _Reading, lang: str) -> dict[str, Any]:
    """The measured values, compactly, for a reader who wants the numbers."""
    parts: list[str] = []
    if m.temp is not None:
        parts.append(i18n.sentence("ri_ind_temp", lang, v=_r(m.temp, 1)))
    if m.humidity is not None:
        parts.append(i18n.sentence("ri_ind_hum", lang, v=_r(m.humidity)))
    if m.pressure is not None:
        parts.append(i18n.sentence("ri_ind_pressure", lang, v=_r(m.pressure)))
    if m.gust_or_wind is not None:
        parts.append(i18n.sentence("ri_ind_wind", lang, v=_r(m.gust_or_wind)))
    if m.rain_24h is not None:
        parts.append(i18n.sentence("ri_ind_rain", lang, v=_r(m.rain_24h, 1)))
    if not parts:
        return _card("indicators", "\U0001f4cb", i18n.sentence("ri_indicators_title", lang),
                     i18n.sentence("ri_no_data", lang), "info")
    return _card("indicators", "\U0001f4cb", i18n.sentence("ri_indicators_title", lang),
                 " \u00b7 ".join(parts), "info", i18n.sentence("ri_indicators_detail", lang))


_NEW_READINGS = {
    "flight_conditions": _flight_conditions,
    "cloud": _cloud,
    "impact_area": _impact_area,
    "escalation": _escalation,
    "response_priority": _response_priority,
    "official_status": _official_status,
    "waterlogging": _waterlogging,
    "urban_risk": _urban_risk,
    "infrastructure": _infrastructure,
    "municipal_prep": _municipal_prep,
    "anomaly": _anomaly,
    "trend": _trend,
    "historical": _historical,
    "forecast_data": _forecast_data,
    "indicators": _indicators,
}


def reading(bundle: Any, risk: RiskOutput, name: str, lang: str = "en") -> dict[str, Any] | None:
    """One reading, on its own.

    Every reading in the library is available to every role, and the roles pick
    from it — `pressure` is in here and on nobody's panel, because the brief
    gives marine five other cards. A reading nobody shows is still a reading
    that has to be right the day somebody does, so it stays covered.
    """
    return _Library(_Reading(bundle, risk), i18n.normalise_lang(lang)).get(name)


def readings() -> frozenset[str]:
    """Every reading a role may name. Used by the tests that keep the registry
    and this module from drifting apart."""
    return frozenset(_READING_GROUP) | frozenset(_NEW_READINGS)


def build(bundle: Any, risk: RiskOutput, user_type: str | None, lang: str = "en") -> dict[str, Any]:
    """Role-specific reading of the weather already fetched and already scored.

    The role says which readings it wants and what to call them; this composes
    them. A reading that has nothing to say for these conditions — a departure
    hour with no hourly series — is left out rather than filled in, so a panel
    is always as long as the data supports and never longer.
    """
    lang = i18n.normalise_lang(lang)
    spec = roles.get(user_type)
    library = _Library(_Reading(bundle, risk), lang)

    cards: list[dict[str, Any]] = []
    for card_id, reading, title_key, icon in spec.cards:
        card = library.get(reading)
        if not card:
            continue
        if card_id != card["id"] or title_key or icon:
            card = _retitle(card, card_id, title_key or "", lang, icon or None)
        cards.append(card)

    return {
        "user_type": spec.key,
        "icon": spec.icon,
        "heading": i18n.sentence(spec.heading_key, lang),
        "cards": cards[:5],
        "note": i18n.sentence(spec.note_key, lang) if spec.note_key else "",
    }

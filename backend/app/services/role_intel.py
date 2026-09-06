# -*- coding: utf-8 -*-
"""What today's weather means for the reader, rather than what it is.

One weather engine, nine readings of it. Every card below is derived from the
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
from . import i18n

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

WIND_BRISK_KMH = 30           # uncomfortable in the open
WIND_STRONG_KMH = 45          # unsafe for a small boat
VIS_POOR_KM = 2.0
VIS_LOW_KM = 5.0

STORM_CAUTION = 25            # Lightning/Storm sub-score
STORM_HIGH = 50

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
        self.code = cur.get("weather_code")

        # Forward-looking totals, only when there are hours to total.
        rain_values = [_num(h.get("precipitation_mm")) for h in hourly[:24]]
        self.rain_24h = sum(v for v in rain_values if v is not None) if any(
            v is not None for v in rain_values
        ) else None

        probs = [_num(h.get("precipitation_probability_pct")) for h in hourly[:12]]
        known_probs = [v for v in probs if v is not None]
        self.prob_max_12h = max(known_probs) if known_probs else None

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
        i18n.sentence("ri_from_risk", lang, level=m.level, hazard=i18n.hazard_label(m.hazard, lang)),
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


def _fisherman(m: _Reading, lang: str) -> list[dict[str, Any]]:
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
        detail = i18n.sentence("ri_wind_gust", lang, gust=_r(m.gust)) if m.gust is not None else ""
        cards.append(_card("wind", "🌬️", i18n.sentence("ri_wind_title", lang), headline, tone, detail))

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
# Traveller
# ---------------------------------------------------------------------------

def _traveller(m: _Reading, lang: str) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []

    # --- Today and tomorrow --------------------------------------------------
    if len(m.daily) >= 2:
        today, tomorrow = m.daily[0], m.daily[1]
        t_max = _num(today.get("temp_max_c"))
        t_min = _num(today.get("temp_min_c"))
        tom_rain = _num(tomorrow.get("precipitation_probability_pct"))
        headline = (
            f"{_r(t_min)}–{_r(t_max)}°C" if t_max is not None and t_min is not None else
            i18n.condition_label(today.get("weather_code"), lang)
        )
        detail = (
            i18n.sentence("ri_trip_tomorrow", lang, prob=_r(tom_rain))
            if tom_rain is not None
            else i18n.sentence("ri_trip_tomorrow_cond", lang,
                               cond=i18n.condition_label(tomorrow.get("weather_code"), lang))
        )
        cards.append(_card("trip_weather", "🗓️", i18n.sentence("ri_trip_title", lang), headline, "info", detail))
    else:
        cards.append(_card(
            "trip_weather", "🗓️", i18n.sentence("ri_trip_title", lang),
            i18n.sentence("ri_no_data", lang), "info",
        ))

    # --- Travel risk ----------------------------------------------------------
    # Named contributors only: a factor with no reading behind it is left out
    # rather than reported as absent.
    factors: list[str] = []
    if m.rain_likely:
        factors.append(i18n.sentence("ri_factor_rain", lang))
    if m.visibility is not None and m.visibility < VIS_LOW_KM:
        factors.append(i18n.sentence("ri_factor_visibility", lang))
    if (m.gust_or_wind or 0) >= WIND_BRISK_KMH:
        factors.append(i18n.sentence("ri_factor_wind", lang))
    if m.storm_score >= STORM_CAUTION:
        factors.append(i18n.sentence("ri_factor_storm", lang))

    if m.level == "Severe" or m.storm_score >= STORM_HIGH:
        headline, tone = i18n.sentence("ri_travel_high", lang), "danger"
    elif factors or m.severe:
        headline, tone = i18n.sentence("ri_travel_moderate", lang), "caution"
    else:
        headline, tone = i18n.sentence("ri_travel_low", lang), "safe"
    detail = i18n.sentence("ri_travel_factors", lang, factors=", ".join(factors)) if factors else i18n.sentence(
        "ri_travel_clear", lang
    )
    cards.append(_card("travel_risk", "🚗", i18n.sentence("ri_travel_title", lang), headline, tone, detail))

    # --- Outdoor suitability --------------------------------------------------
    if m.storm_score >= STORM_HIGH or m.level == "Severe":
        headline, tone = i18n.sentence("ri_activity_poor", lang), "danger"
    elif m.rain_likely or m.severe:
        headline, tone = i18n.sentence("ri_activity_caution", lang), "caution"
    elif (m.feels is not None and m.feels >= HOT_C) or (m.gust_or_wind or 0) >= WIND_BRISK_KMH:
        headline, tone = i18n.sentence("ri_activity_good", lang), "caution"
    else:
        headline, tone = i18n.sentence("ri_activity_excellent", lang), "safe"
    cards.append(_card("activity", "🌤️", i18n.sentence("ri_activity_title", lang), headline, tone))

    # --- Packing ---------------------------------------------------------------
    # Every item traces to a reading. Nothing generic gets added to pad the list.
    items: list[str] = []
    if m.rain_possible:
        items.append(i18n.sentence("ri_pack_umbrella", lang))
        items.append(i18n.sentence("ri_pack_raincoat", lang))
    if m.feels is not None and m.feels >= HOT_C:
        items.append(i18n.sentence("ri_pack_water", lang))
        items.append(i18n.sentence("ri_pack_sun", lang))
    if (m.temp is not None and m.temp <= COOL_C) or (m.daily and (_num(m.daily[0].get("temp_min_c")) or 99) <= COOL_C):
        items.append(i18n.sentence("ri_pack_layer", lang))
    if (m.gust_or_wind or 0) >= WIND_BRISK_KMH:
        items.append(i18n.sentence("ri_pack_windproof", lang))

    cards.append(_card(
        "packing", "🎒", i18n.sentence("ri_pack_title", lang),
        " · ".join(items) if items else i18n.sentence("ri_pack_nothing", lang),
        "info" if items else "safe",
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
# Household
# ---------------------------------------------------------------------------

def _preparedness_card(m: _Reading, lang: str) -> dict[str, Any]:
    """Shared by the household and caregiver readings.

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


def _household(m: _Reading, lang: str) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []

    # --- Comfort indoors ---------------------------------------------------
    # Same card the general reading shows, deliberately: the question "is it
    # comfortable?" does not change because the reader is at home, and two
    # answers to it would be two chances to disagree.
    cards.append(_general(m, lang)[1])

    # --- Washing and drying ------------------------------------------------
    if m.rain_24h is None and m.prob_max_12h is None and m.humidity is None:
        cards.append(_card(
            "home_rain", "🧺", i18n.sentence("ri_home_rain_title", lang),
            i18n.sentence("ri_no_data", lang), "info",
        ))
    else:
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
        cards.append(_card(
            "home_rain", "🧺", i18n.sentence("ri_home_rain_title", lang), headline, tone, detail,
        ))

    cards.append(_preparedness_card(m, lang))
    cards.append(_reminder(m, lang))
    return cards


# ---------------------------------------------------------------------------
# Student
#
# Built entirely from cards the other readings already own: a student's weather
# questions are the journey, the afternoon outdoors, and when to leave. Writing
# a second set of sentences for them would only create a way for the two to
# disagree.
# ---------------------------------------------------------------------------

def _student(m: _Reading, lang: str) -> list[dict[str, Any]]:
    commute = _commuter(m, lang)
    cards = [card for card in commute if card["id"] in {"commute_risk", "departure"}]
    # Insert the outdoor-activity reading between the journey and the timing.
    cards.insert(1, _general(m, lang)[2])
    cards.append(_reminder(m, lang))
    return cards


# ---------------------------------------------------------------------------
# Community / caregiver
# ---------------------------------------------------------------------------

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

    cards.append(_preparedness_card(m, lang))
    cards.append(_reminder(m, lang))
    return cards


# ---------------------------------------------------------------------------

_BUILDERS = {
    "general": _general,
    "farmer": _farmer,
    "fisherman": _fisherman,
    "traveler": _traveller,
    "driver": _driver,
    "outdoor_worker": _outdoor_worker,
    "household": _household,
    "student": _student,
    "caregiver": _caregiver,
    "commuter": _commuter,
}

_HEADINGS = {
    "general": "ri_heading_general",
    "farmer": "ri_heading_farmer",
    "fisherman": "ri_heading_fisherman",
    "traveler": "ri_heading_traveler",
    "driver": "ri_heading_driver",
    "outdoor_worker": "ri_heading_outdoor_worker",
    "household": "ri_heading_household",
    "student": "ri_heading_student",
    "caregiver": "ri_heading_caregiver",
    "commuter": "ri_heading_commuter",
}

_ICONS = {
    "general": "🌤️",
    "farmer": "🌾",
    "fisherman": "🎣",
    "traveler": "🧳",
    "driver": "🚚",
    "outdoor_worker": "🏗️",
    "household": "🏠",
    "student": "🏫",
    "caregiver": "🏥",
    "commuter": "🚗",
}

# Only the marine reading has to disclose an absence, because it is the only
# role whose questions this app cannot fully answer.
_NOTES = {"fisherman": "ri_note_marine"}


def build(bundle: Any, risk: RiskOutput, user_type: str | None, lang: str = "en") -> dict[str, Any]:
    """Role-specific reading of the weather already fetched and already scored."""
    lang = i18n.normalise_lang(lang)
    role = (user_type or "general").strip().lower()
    if role not in _BUILDERS:
        role = "general"

    measured = _Reading(bundle, risk)
    note_key = _NOTES.get(role)
    return {
        "user_type": role,
        "icon": _ICONS[role],
        "heading": i18n.sentence(_HEADINGS[role], lang),
        "cards": _BUILDERS[role](measured, lang),
        "note": i18n.sentence(note_key, lang) if note_key else "",
    }

"""Weather Risk Engine — the single source of truth for risk in WeatherGPT.

Nothing else in this codebase computes a risk score. Alerts, the 24-hour
timeline, the India risk map, the chat ``action_mode`` and the voice emergency
mode all call into this module, so a number shown on the map is by construction
the same number that fired the alert.

Contract (Role 2.1)::

    {"risk_score": 76, "risk_level": "High", "detected_hazard": "Heavy Rainfall"}

Scores are 0-100 and derive only from real weather values. Bands:
0-30 Low, 31-60 Moderate, 61-80 High, 81-100 Severe.

Thresholds follow IMD's published rainfall categories (7.6/35.6/64.5/115.6/
204.5 mm per 24 h) and conventional wind/heat advisory breakpoints, so the
numbers mean something to a domain expert rather than being invented curves.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from ..schemas import RiskOutput
from . import wmo

HEAVY_RAINFALL = "Heavy Rainfall"
FLOOD_RISK = "Flood Risk"
STRONG_WIND = "Strong Wind"
EXTREME_HEAT = "Extreme Heat"
LIGHTNING_STORM = "Lightning/Storm"
NO_HAZARD = "None"

HAZARDS: tuple[str, ...] = (HEAVY_RAINFALL, FLOOD_RISK, STRONG_WIND, EXTREME_HEAT, LIGHTNING_STORM)

# A hazard has to clear this to be named at all — below it, conditions are calm.
HAZARD_FLOOR = 20


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _scale(value: float | None, points: Sequence[tuple[float, float]]) -> float:
    """Piecewise-linear interpolation over (input, score) breakpoints."""
    if value is None:
        return 0.0
    if value <= points[0][0]:
        return points[0][1]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if value <= x1:
            if x1 == x0:
                return y1
            ratio = (value - x0) / (x1 - x0)
            return y0 + ratio * (y1 - y0)
    return points[-1][1]


# --- Calibration curves ----------------------------------------------------
RAIN_24H_MM = ((0, 0), (7.6, 12), (35.6, 34), (64.5, 57), (115.6, 76), (204.5, 92), (350, 100))
RAIN_RATE_MM_H = ((0, 0), (2, 14), (5, 34), (10, 54), (20, 74), (40, 94), (60, 100))
PRECIP_72H_MM = ((0, 0), (50, 14), (100, 34), (180, 57), (280, 77), (400, 94), (600, 100))
SUSTAINED_RAIN_HOURS = ((0, 0), (4, 7), (8, 17), (14, 27), (20, 35))
WIND_KMH = ((0, 0), (20, 10), (30, 22), (40, 40), (50, 55), (62, 70), (75, 84), (88, 95), (120, 100))
APPARENT_TEMP_C = ((30, 0), (35, 20), (38, 35), (40, 52), (42, 66), (45, 82), (48, 95), (52, 100))
CAPE_J_KG = ((0, 0), (500, 10), (1000, 22), (2000, 46), (3000, 66), (4000, 82), (5000, 92))


def level_for(score: int | float) -> str:
    """The one place risk bands are defined."""
    value = max(0, min(100, int(round(score))))
    if value <= 30:
        return "Low"
    if value <= 60:
        return "Moderate"
    if value <= 80:
        return "High"
    return "Severe"


@dataclass
class RiskInputs:
    """Normalised numeric inputs the engine scores. All optional — a missing
    field contributes nothing rather than defaulting to a scary value."""

    precipitation_rate_mm_h: float | None = None
    precipitation_24h_mm: float | None = None
    precipitation_72h_mm: float | None = None
    sustained_rain_hours: int = 0
    wind_speed_kmh: float | None = None
    wind_gust_kmh: float | None = None
    apparent_temperature_c: float | None = None
    temperature_c: float | None = None
    humidity_pct: float | None = None
    cape_j_kg: float | None = None
    thunderstorm: bool = False
    weather_code: int | None = None
    drivers: list[str] = field(default_factory=list)


def _fmt(value: float | None, unit: str, decimals: int = 0) -> str:
    if value is None:
        return "n/a"
    return f"{round(value, decimals):g} {unit}"


def score_inputs(inputs: RiskInputs) -> RiskOutput:
    """Score a normalised input set. This is the engine's core.

    Drivers are recorded structurally as ``{code, value, unit}``. The engine
    stays language-neutral; ``i18n.driver_labels`` does the wording, so a
    Telugu emergency brief never ends up quoting an English sentence.
    """
    details: list[dict[str, Any]] = []
    scores: dict[str, float] = {}

    def add(code: str, value: float | None = None, unit: str | None = None) -> None:
        details.append({"code": code, "value": value, "unit": unit})

    # --- Heavy rainfall -------------------------------------------------
    acc = _scale(inputs.precipitation_24h_mm, RAIN_24H_MM)
    rate = _scale(inputs.precipitation_rate_mm_h, RAIN_RATE_MM_H)
    rain_score = max(acc, rate)
    scores[HEAVY_RAINFALL] = rain_score
    if rain_score >= HAZARD_FLOOR:
        if acc >= rate and inputs.precipitation_24h_mm:
            add("rain_24h", inputs.precipitation_24h_mm, "mm")
        elif inputs.precipitation_rate_mm_h:
            add("rain_rate", inputs.precipitation_rate_mm_h, "mm/h")

    # --- Flood risk: sustained accumulation, not a single burst ----------
    flood_base = _scale(inputs.precipitation_72h_mm, PRECIP_72H_MM)
    sustained = _scale(float(inputs.sustained_rain_hours), SUSTAINED_RAIN_HOURS)
    # Hours of drizzle are not a flood. Gate the "it keeps raining" term on there
    # actually being enough accumulated water for runoff to matter.
    gate = min(1.0, (inputs.precipitation_72h_mm or 0.0) / 150.0)
    flood_score = min(100.0, flood_base * 0.80 + sustained * gate)
    scores[FLOOD_RISK] = flood_score
    if flood_score >= HAZARD_FLOOR:
        if inputs.precipitation_72h_mm:
            add("precip_72h", round(inputs.precipitation_72h_mm), "mm")
        if inputs.sustained_rain_hours >= 6:
            add("sustained_hours", inputs.sustained_rain_hours, "h")

    # --- Strong wind ----------------------------------------------------
    sustained_wind = _scale(inputs.wind_speed_kmh, WIND_KMH)
    gust = _scale(inputs.wind_gust_kmh, WIND_KMH) * 0.9
    wind_score = max(sustained_wind, gust)
    scores[STRONG_WIND] = wind_score
    if wind_score >= HAZARD_FLOOR:
        if gust > sustained_wind and inputs.wind_gust_kmh:
            add("gusts", round(inputs.wind_gust_kmh), "km/h")
        elif inputs.wind_speed_kmh:
            add("sustained_wind", round(inputs.wind_speed_kmh), "km/h")

    # --- Extreme heat ---------------------------------------------------
    felt = inputs.apparent_temperature_c if inputs.apparent_temperature_c is not None else inputs.temperature_c
    heat_score = _scale(felt, APPARENT_TEMP_C)
    scores[EXTREME_HEAT] = heat_score
    if heat_score >= HAZARD_FLOOR and felt is not None:
        add("feels_like", felt, "°C")

    # --- Lightning / storm ----------------------------------------------
    cape_score = _scale(inputs.cape_j_kg, CAPE_J_KG)
    storm_score = cape_score
    if inputs.thunderstorm:
        # A confirmed thunderstorm carries lightning risk on its own, independent
        # of how strong the wind underneath it happens to be.
        storm_score = max(storm_score, 62.0)
        add("thunderstorm")
    if inputs.wind_gust_kmh and inputs.wind_gust_kmh >= 60 and storm_score > 0:
        storm_score = min(100.0, storm_score + 10)
    scores[LIGHTNING_STORM] = storm_score
    if storm_score >= HAZARD_FLOOR and not inputs.thunderstorm and inputs.cape_j_kg:
        add("cape", round(inputs.cape_j_kg), "J/kg")

    # --- Combine ---------------------------------------------------------
    top_hazard = max(scores, key=lambda k: scores[k])
    top = scores[top_hazard]
    others = sorted((v for k, v in scores.items() if k != top_hazard), reverse=True)
    # Several hazards at once is worse than one; only meaningful hazards count.
    compound = 0.06 * sum(max(0.0, v - 40.0) for v in others[:2])
    total = int(round(min(100.0, max(0.0, top + compound))))

    hazard = top_hazard if top >= HAZARD_FLOOR else NO_HAZARD
    if hazard == NO_HAZARD:
        details = []
    details = details[:4]

    # Import here: i18n imports nothing from this module, but keeping the
    # dependency local documents that wording is not the engine's job.
    from .i18n import driver_labels

    return RiskOutput(
        risk_score=total,
        risk_level=level_for(total),
        detected_hazard=hazard,
        hazard_scores={k: int(round(v)) for k, v in scores.items()},
        drivers=driver_labels(details, "en"),
        driver_details=details,
    )


# ---------------------------------------------------------------------------
# Adapters: turn provider data into RiskInputs
# ---------------------------------------------------------------------------
def _sustained_rain_hours(hourly: Iterable[dict[str, Any]], threshold_mm: float = 2.5) -> int:
    return sum(1 for h in hourly if (_num(h.get("precipitation_mm")) or 0.0) >= threshold_mm)


def inputs_from_bundle(bundle: Any, hours: int = 24) -> RiskInputs:
    """Build engine inputs from a WeatherBundle (current + forward window)."""
    current = bundle.current or {}
    window = list(bundle.hourly[:hours])

    precip_24h = sum(_num(h.get("precipitation_mm")) or 0.0 for h in window)
    # 72h uses the daily sums, which extend past the hourly window.
    precip_72h = sum(_num(d.get("precipitation_sum_mm")) or 0.0 for d in (bundle.daily or [])[:3])
    if precip_72h < precip_24h:
        precip_72h = precip_24h

    gusts = [_num(h.get("wind_gust_kmh")) for h in window]
    winds = [_num(h.get("wind_speed_kmh")) for h in window]
    capes = [_num(h.get("cape")) for h in window[:12]]

    codes = [h.get("weather_code") for h in window[:12]]
    thunder = wmo.is_thunder(current.get("weather_code")) or any(wmo.is_thunder(c) for c in codes)

    return RiskInputs(
        precipitation_rate_mm_h=max(
            [_num(current.get("precipitation_mm")) or 0.0]
            + [_num(h.get("precipitation_mm")) or 0.0 for h in window[:6]]
        ),
        precipitation_24h_mm=round(precip_24h, 1),
        precipitation_72h_mm=round(precip_72h, 1),
        sustained_rain_hours=_sustained_rain_hours(window),
        wind_speed_kmh=max([v for v in winds if v is not None] + [_num(current.get("wind_speed_kmh")) or 0.0]),
        wind_gust_kmh=max([v for v in gusts if v is not None] + [_num(current.get("wind_gust_kmh")) or 0.0]),
        apparent_temperature_c=_num(current.get("apparent_temperature_c")),
        temperature_c=_num(current.get("temperature_c")),
        humidity_pct=_num(current.get("humidity_pct")),
        cape_j_kg=max([v for v in capes if v is not None], default=None),
        thunderstorm=thunder,
        weather_code=current.get("weather_code"),
    )


def assess(bundle: Any, hours: int = 24) -> RiskOutput:
    """Primary entry point: overall risk for a location right now."""
    return score_inputs(inputs_from_bundle(bundle, hours=hours))


def assess_hour(hour: dict[str, Any], *, rolling_precip_mm: float = 0.0) -> RiskOutput:
    """Risk for a single forecast hour — used to highlight the 24h timeline.

    ``rolling_precip_mm`` is the accumulation up to and including this hour, so
    the sixth straight hour of rain reads as riskier than the first.
    """
    rate = _num(hour.get("precipitation_mm")) or 0.0
    return score_inputs(
        RiskInputs(
            precipitation_rate_mm_h=rate,
            precipitation_24h_mm=rolling_precip_mm,
            precipitation_72h_mm=rolling_precip_mm,
            sustained_rain_hours=0,
            wind_speed_kmh=_num(hour.get("wind_speed_kmh")),
            wind_gust_kmh=_num(hour.get("wind_gust_kmh")),
            apparent_temperature_c=_num(hour.get("temperature_c")),
            humidity_pct=_num(hour.get("humidity_pct")),
            cape_j_kg=_num(hour.get("cape")),
            thunderstorm=wmo.is_thunder(hour.get("weather_code")),
            weather_code=hour.get("weather_code"),
        )
    )


def assess_day(day: dict[str, Any]) -> RiskOutput:
    """Risk for a forecast day — used by the 7-day strip."""
    total = _num(day.get("precipitation_sum_mm")) or 0.0
    return score_inputs(
        RiskInputs(
            precipitation_rate_mm_h=total / 24.0 if total else 0.0,
            precipitation_24h_mm=total,
            precipitation_72h_mm=total,
            sustained_rain_hours=0,
            wind_speed_kmh=_num(day.get("wind_speed_max_kmh")),
            wind_gust_kmh=_num(day.get("wind_gust_max_kmh")),
            apparent_temperature_c=_num(day.get("temp_max_c")),
            thunderstorm=wmo.is_thunder(day.get("weather_code")),
            weather_code=day.get("weather_code"),
        )
    )


def timeline(bundle: Any, hours: int = 24) -> list[dict[str, Any]]:
    """Next-N-hour timeline with per-hour risk from this same engine."""
    out: list[dict[str, Any]] = []
    rolling = 0.0
    for hour in bundle.hourly[:hours]:
        rolling += _num(hour.get("precipitation_mm")) or 0.0
        risk = assess_hour(hour, rolling_precip_mm=round(rolling, 1))
        out.append(
            {
                "time": hour.get("time"),
                "temperature_c": hour.get("temperature_c"),
                "precipitation_probability_pct": hour.get("precipitation_probability_pct"),
                "precipitation_mm": hour.get("precipitation_mm"),
                "wind_speed_kmh": hour.get("wind_speed_kmh"),
                "weather_code": hour.get("weather_code"),
                "condition": hour.get("condition"),
                "risk_level": risk.risk_level,
                "risk_score": risk.risk_score,
            }
        )
    return out


def is_actionable(risk: RiskOutput) -> bool:
    """High or Severe — the trigger for checklist/emergency presentation."""
    return risk.risk_level in {"High", "Severe"}

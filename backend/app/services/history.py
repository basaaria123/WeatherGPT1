"""Historical event comparison.

Comparisons are matched on explicit numeric criteria stored beside each event,
never on impression. Two rules are enforced here rather than left to callers:

1. A comparison is only produced when current risk is already High or Severe
   *and* the similarity score clears ``MIN_SIMILARITY``.
2. The sentence is always framed as historical context. It never says or
   implies that the past event is going to repeat.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from ..config import DATA_DIR
from ..schemas import HistoricalComparison, RiskOutput

log = logging.getLogger("weathergpt.history")

MIN_SIMILARITY = 60

_EVENTS: list[dict[str, Any]] | None = None


def _events() -> list[dict[str, Any]]:
    global _EVENTS
    if _EVENTS is None:
        try:
            payload = json.loads((DATA_DIR / "historical_events.json").read_text(encoding="utf-8"))
            _EVENTS = payload.get("events", [])
        except (OSError, json.JSONDecodeError) as exc:  # pragma: no cover
            log.error("historical events unreadable: %s", exc)
            _EVENTS = []
    return _EVENTS


def _ratio_points(value: float | None, threshold: float | None, max_points: int) -> tuple[int, bool]:
    """Points for meeting a numeric threshold, scaled by how far past it we are."""
    if threshold is None:
        return 0, True  # criterion not applicable to this event
    if value is None:
        return 0, False
    if value < threshold:
        return 0, False
    ratio = min(2.0, value / threshold)
    return int(round(max_points * (0.6 + 0.4 * (ratio - 1.0)))), True


def score_event(
    event: dict[str, Any],
    *,
    risk: RiskOutput,
    rain_24h_mm: float | None,
    rain_72h_mm: float | None,
    wind_gust_kmh: float | None,
    state: str | None,
    month: int,
) -> int:
    """Similarity between current conditions and one stored event.

    Can exceed 100: the raw value ranks candidates, and only the reported
    ``similarity_score`` is clamped. Any stated numeric threshold that is not
    met disqualifies the event outright — a dry gale is not a cyclone.
    """
    criteria = event.get("criteria", {})

    # Hazard family must match, or this is not a comparison at all. An event may
    # list several (the 2005 Mumbai deluge reads as heavy rainfall or flooding).
    allowed = criteria.get("hazards") or [criteria.get("hazard")]
    if risk.detected_hazard not in allowed:
        return 0

    score = 40
    met_any_numeric = False

    points, ok = _ratio_points(rain_24h_mm, criteria.get("rain_24h_min_mm"), 20)
    score += points
    met_any_numeric = met_any_numeric or (points > 0)
    if not ok:
        return 0  # a stated rainfall threshold that is not met disqualifies

    points, ok = _ratio_points(rain_72h_mm, criteria.get("rain_72h_min_mm"), 15)
    score += points
    met_any_numeric = met_any_numeric or (points > 0)
    if not ok:
        return 0

    points, ok = _ratio_points(wind_gust_kmh, criteria.get("wind_gust_min_kmh"), 20)
    score += points
    met_any_numeric = met_any_numeric or (points > 0)
    if not ok:
        return 0

    if not met_any_numeric:
        return 0

    # Region and season decide between events that clear the same thresholds:
    # an August flood in Assam should match the Assam event, not the Kerala one,
    # and a monsoon flood should not match a north-east-monsoon event.
    if state and state in event.get("states", []):
        score += 25
    elif state:
        score -= 10

    months = criteria.get("months") or []
    if months:
        score += 10 if month in months else -5

    return max(0, score)


def find_comparison(
    *,
    risk: RiskOutput,
    rain_24h_mm: float | None,
    rain_72h_mm: float | None,
    wind_gust_kmh: float | None,
    state: str | None,
    when: datetime | None = None,
) -> HistoricalComparison | None:
    """Best-matching historical event, or None when nothing genuinely matches."""
    if risk.risk_level not in {"High", "Severe"}:
        return None

    moment = when or datetime.now(timezone.utc)
    best: tuple[int, dict[str, Any]] | None = None
    for event in _events():
        score = score_event(
            event,
            risk=risk,
            rain_24h_mm=rain_24h_mm,
            rain_72h_mm=rain_72h_mm,
            wind_gust_kmh=wind_gust_kmh,
            state=state,
            month=moment.month,
        )
        if score >= MIN_SIMILARITY and (best is None or score > best[0]):
            best = (score, event)

    if best is None:
        return None

    score, event = best
    sentence = (
        f"For context, these conditions are in a similar range to the {event['name']} "
        f"({event['date']}) in {event['region']}, when {event['headline_fact']}. "
        f"This is a comparison of scale only — it is not a prediction that the same event will happen again."
    )
    return HistoricalComparison(
        event_name=event["name"],
        event_date=event["date"],
        region=event["region"],
        similarity_score=min(100, score),
        sentence=sentence,
        source_note=event.get("source_note", ""),
    )


def comparison_for_bundle(bundle: Any, risk: RiskOutput) -> HistoricalComparison | None:
    """Convenience wrapper that derives the numeric inputs from a bundle."""
    rain_24h = sum(float(h.get("precipitation_mm") or 0.0) for h in bundle.hourly[:24])
    rain_72h = sum(float(d.get("precipitation_sum_mm") or 0.0) for d in (bundle.daily or [])[:3])
    gusts = [float(h["wind_gust_kmh"]) for h in bundle.hourly[:24] if isinstance(h.get("wind_gust_kmh"), (int, float))]
    return find_comparison(
        risk=risk,
        rain_24h_mm=round(rain_24h, 1),
        rain_72h_mm=round(max(rain_72h, rain_24h), 1),
        wind_gust_kmh=max(gusts) if gusts else None,
        state=bundle.location.admin1,
    )


def all_events() -> list[dict[str, Any]]:
    """Event metadata for the UI, without the matching criteria."""
    return [
        {k: v for k, v in event.items() if k != "criteria"}
        for event in _events()
    ]

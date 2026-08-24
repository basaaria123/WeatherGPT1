# -*- coding: utf-8 -*-
"""Alerting: scheduled scanning, storage, live push and SMS.

The scan does not implement its own thresholds. It asks the shared risk engine
for a verdict on each tracked location and stores an alert when that verdict
crosses the configured level, which is why an alert's severity always equals
the severity the map and the chat answer show for the same place.

One scheduler serves everything. Subscriptions add locations to the existing
job rather than starting a second one.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from ..config import get_settings
from ..db import (
    deactivate_expired_alerts,
    fetch_alerts,
    insert_alert,
    list_subscriptions,
    recent_alert_exists,
)
from ..schemas import AlertOut, RiskOutput
from . import advisory, history, i18n, memory, risk_engine, weather
from .weather import Location, WeatherError

log = logging.getLogger("weathergpt.alerts")

SEVERITY_ORDER = {"Low": 0, "Moderate": 1, "High": 2, "Severe": 3}

# Scanned even with no subscribers, so the map and the demo have live content.
DEFAULT_WATCH = (
    "Guwahati", "Vijayawada", "Mumbai", "Chennai", "Kolkata", "New Delhi",
    "Bengaluru", "Hyderabad", "Puri", "Kochi", "Patna", "Jaisalmer",
    "Dibrugarh", "Shillong", "Ratnagiri", "Bhubaneswar",
)


# ---------------------------------------------------------------------------
# WebSocket hub
# ---------------------------------------------------------------------------
class AlertHub:
    """Tracks live WebSocket subscribers and fans alerts out to them.

    A send failure only removes that one client; a browser closing a tab must
    never interrupt the scan or the other listeners.
    """

    def __init__(self) -> None:
        self._clients: set[Any] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: Any) -> None:
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)
        log.info("alert client connected (%d live)", len(self._clients))

    async def disconnect(self, websocket: Any) -> None:
        async with self._lock:
            self._clients.discard(websocket)

    @property
    def client_count(self) -> int:
        return len(self._clients)

    async def broadcast(self, payload: dict[str, Any]) -> int:
        async with self._lock:
            targets = list(self._clients)
        if not targets:
            return 0
        message = json.dumps(payload, ensure_ascii=False, default=str)
        dead: list[Any] = []
        sent = 0
        for client in targets:
            try:
                await client.send_text(message)
                sent += 1
            except Exception:  # noqa: BLE001 - a dropped client is routine
                dead.append(client)
        if dead:
            async with self._lock:
                for client in dead:
                    self._clients.discard(client)
        return sent


hub = AlertHub()


# ---------------------------------------------------------------------------
# SMS
# ---------------------------------------------------------------------------
def send_sms(to_number: str, message: str) -> dict[str, Any]:
    """Send an alert SMS, or log it when Twilio is not configured."""
    settings = get_settings()
    if not settings.twilio_configured:
        log.info("[SMS FALLBACK] to=%s | %s", to_number, message)
        return {"delivered": False, "channel": "console", "reason": "Twilio not configured"}
    try:
        from twilio.rest import Client  # type: ignore

        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        result = client.messages.create(body=message[:1500], from_=settings.twilio_from_number, to=to_number)
        return {"delivered": True, "channel": "twilio", "sid": getattr(result, "sid", None)}
    except Exception as exc:  # noqa: BLE001 - SMS must never break the scan
        log.warning("Twilio send failed for %s: %s", to_number, exc)
        log.info("[SMS FALLBACK] to=%s | %s", to_number, message)
        return {"delivered": False, "channel": "console", "reason": str(exc)}


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------
def watched_locations() -> list[dict[str, Any]]:
    """Subscribed locations plus the default watchlist, de-duplicated."""
    entries: dict[str, dict[str, Any]] = {}
    for name in DEFAULT_WATCH:
        entries[name.lower()] = {
            "name": name, "latitude": None, "longitude": None,
            "hazard_types": [], "phone_numbers": [], "min_severity": "High",
        }
    for sub in list_subscriptions():
        key = (sub["location"] or "").lower()
        if not key:
            continue
        entry = entries.setdefault(
            key,
            {
                "name": sub["location"],
                # Coordinates were resolved at subscribe time; reuse them rather
                # than re-geocoding a "City, State" label on every scan.
                "latitude": sub.get("latitude"),
                "longitude": sub.get("longitude"),
                "hazard_types": [],
                "phone_numbers": [],
                "min_severity": sub["min_severity"],
            },
        )
        entry["hazard_types"] = sorted(set(entry["hazard_types"]) | set(sub.get("hazard_types") or []))
        if sub.get("phone_number"):
            entry["phone_numbers"].append(sub["phone_number"])
        # The most sensitive subscriber sets the bar for the location.
        if SEVERITY_ORDER.get(sub["min_severity"], 2) < SEVERITY_ORDER.get(entry["min_severity"], 2):
            entry["min_severity"] = sub["min_severity"]
    return list(entries.values())


def _alert_message(bundle: Any, risk: RiskOutput, comparison: Any) -> tuple[str, list[str]]:
    actions = advisory.action_checklist(risk, None, "en")
    drivers = "; ".join(risk.drivers[:2]) if risk.drivers else "elevated measured risk"
    message = (
        f"{risk.risk_level} {risk.detected_hazard} warning for {bundle.location.label}. "
        f"{drivers.capitalize()}. Risk score {risk.risk_score} out of 100."
    )
    if comparison is not None:
        message += " " + comparison.sentence
    return message, actions


def evaluate_location(entry: dict[str, Any]) -> dict[str, Any] | None:
    """Score one watched location and create an alert if warranted.

    Returns the created alert dict, or None when nothing is warranted. Runs in
    a worker thread: everything in here is blocking I/O.
    """
    settings = get_settings()
    name = entry["name"]
    try:
        if entry.get("latitude") is not None and entry.get("longitude") is not None:
            location = Location(
                name=name.split(",")[0].strip() or name,
                latitude=float(entry["latitude"]),
                longitude=float(entry["longitude"]),
                admin1=(name.split(",")[1].strip() if "," in name else None),
            )
        else:
            location = weather.geocode(name)
        if location is None:
            return None
        bundle = weather.fetch_weather(location)
    except WeatherError as exc:
        log.warning("alert scan skipped %s: %s", name, exc)
        return None

    risk = risk_engine.assess(bundle)

    threshold = max(
        settings.alert_min_risk_score,
        {"Low": 0, "Moderate": 31, "High": 61, "Severe": 81}.get(entry.get("min_severity", "High"), 61),
    )
    if risk.risk_score < threshold:
        return None

    wanted = entry.get("hazard_types") or []
    if wanted and risk.detected_hazard not in wanted:
        return None

    if recent_alert_exists(location.label, risk.detected_hazard, settings.alert_dedup_hours):
        return None

    comparison = history.comparison_for_bundle(bundle, risk)
    message, actions = _alert_message(bundle, risk, comparison)

    alert_id = insert_alert(
        location=location.label,
        latitude=location.latitude,
        longitude=location.longitude,
        alert_type=risk.detected_hazard,
        severity=risk.risk_level,
        risk_score=risk.risk_score,
        message=message,
        actions=actions,
        comparison=comparison.model_dump() if comparison else None,
    )

    for number in entry.get("phone_numbers", []):
        send_sms(number, message)

    return {
        "id": alert_id,
        "location": location.label,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "alert_type": risk.detected_hazard,
        "severity": risk.risk_level,
        "risk_score": risk.risk_score,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "message": message,
        "actions": actions,
        "historical_comparison": comparison.model_dump() if comparison else None,
        "active": True,
    }


async def run_alert_scan() -> list[dict[str, Any]]:
    """The scheduled job. Scans every watched location and pushes new alerts."""
    try:
        deactivate_expired_alerts()
    except Exception as exc:  # noqa: BLE001
        log.warning("expiring old alerts failed: %s", exc)

    entries = watched_locations()
    created: list[dict[str, Any]] = []
    for entry in entries:
        try:
            alert = await asyncio.to_thread(evaluate_location, entry)
        except Exception as exc:  # noqa: BLE001 - one bad location must not stop the scan
            log.warning("alert evaluation failed for %s: %s", entry.get("name"), exc)
            continue
        if alert:
            created.append(alert)
            await hub.broadcast({"type": "alert", "alert": alert})

    if created:
        log.info("alert scan created %d alert(s)", len(created))
    try:
        memory.housekeeping()
    except Exception:  # noqa: BLE001
        pass
    return created


def active_alerts(location: str | None = None, limit: int = 50) -> list[AlertOut]:
    rows = fetch_alerts(location=location, limit=limit)
    return [AlertOut(**row) for row in rows]


def localised_alert(alert: AlertOut, lang: str) -> dict[str, Any]:
    """Alert with hazard/severity labels in the requested language.

    The stored message stays English (it is what went out over SMS); the labels
    the UI renders are localised.
    """
    data = alert.model_dump()
    data["hazard_label"] = i18n.hazard_label(alert.alert_type, lang)
    data["severity_label"] = i18n.level_label(alert.severity, lang)
    data["actions_localised"] = i18n.hazard_actions(alert.alert_type, lang)
    return data

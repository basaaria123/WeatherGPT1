"""Alert endpoints: retrieval, subscription and the live push channel."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect

from ..db import delete_subscription, list_subscriptions, upsert_subscription
from ..schemas import SubscriptionOut, SubscriptionRequest
from ..services import alerts as alert_service
from ..services import risk_engine, weather

log = logging.getLogger("weathergpt.routes.alerts")

router = APIRouter(tags=["alerts"])


@router.get("/alerts")
def get_alerts(
    location: str | None = Query(default=None, description="Filter by location name"),
    language: str = "en",
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    active = alert_service.active_alerts(location=location, limit=limit)
    return {
        "count": len(active),
        "location": location,
        "alerts": [alert_service.localised_alert(alert, language) for alert in active],
    }


@router.post("/alerts/subscribe", response_model=SubscriptionOut)
def subscribe(payload: SubscriptionRequest) -> SubscriptionOut:
    """Subscribe a location and hazard set. Reuses the running scheduler."""
    location = weather.geocode(payload.location)
    if location is None:
        raise HTTPException(
            status_code=404,
            detail=f"I could not find a place called '{payload.location}'.",
        )
    unknown = [h for h in payload.hazard_types if h not in risk_engine.HAZARDS]
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown hazard type(s): {', '.join(unknown)}. Valid types: {', '.join(risk_engine.HAZARDS)}.",
        )
    record = upsert_subscription(
        location=location.label,
        latitude=location.latitude,
        longitude=location.longitude,
        hazard_types=payload.hazard_types,
        phone_number=payload.phone_number,
        min_severity=payload.min_severity,
    )
    return SubscriptionOut(**record)


@router.get("/alerts/subscriptions")
def get_subscriptions() -> dict:
    return {"subscriptions": list_subscriptions()}


@router.delete("/alerts/subscriptions/{subscription_id}")
def remove_subscription(subscription_id: int) -> dict:
    if not delete_subscription(subscription_id):
        raise HTTPException(status_code=404, detail="That subscription does not exist.")
    return {"deleted": subscription_id}


@router.post("/alerts/scan")
async def trigger_scan() -> dict:
    """Run the scan immediately instead of waiting for the schedule.

    Used by the live demo to make an alert fire on cue; it calls the same job
    the scheduler calls, so there is no second code path to keep in sync.
    """
    created = await alert_service.run_alert_scan()
    return {"created": len(created), "alerts": created}


@router.websocket("/ws/alerts")
async def alerts_socket(websocket: WebSocket) -> None:
    """Live alert push.

    Sends a snapshot on connect so a client that reconnects after a drop is
    immediately consistent, then streams new alerts. Heartbeats keep
    intermediaries from closing an idle socket.
    """
    await alert_service.hub.connect(websocket)
    try:
        snapshot = alert_service.active_alerts(limit=20)
        await websocket.send_json(
            {
                "type": "snapshot",
                "alerts": [alert.model_dump() for alert in snapshot],
            }
        )
        while True:
            try:
                # Any client message is treated as a ping; the timeout drives heartbeats.
                await asyncio.wait_for(websocket.receive_text(), timeout=25)
                await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat"})
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001 - a broken socket is routine
        log.info("alert socket closed: %s", exc)
    finally:
        await alert_service.hub.disconnect(websocket)

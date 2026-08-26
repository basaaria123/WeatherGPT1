"""Health, capability and reference endpoints.

``/health`` reports what actually works in this deployment (LLM configured,
speech engines present, live vs fixture data) so the frontend can hide controls
that cannot function instead of failing when a user presses them.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from ..config import get_settings
from ..schemas import SUPPORTED_LANGUAGES, USER_TYPES
from ..services import history, llm, risk_engine, speech
from ..services.alerts import hub

router = APIRouter(tags=["meta"])


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_source": settings.weather_data_mode,
        "simulated_data": settings.use_fixtures,
        "llm": {
            "configured": settings.llm_configured,
            "available": llm.available(),
            "provider": llm.provider() or None,
            "model": settings.active_llm_model or None,
        },
        "speech": speech.capabilities(),
        "alerts": {
            "scheduler_enabled": settings.scheduler_enabled,
            "interval_minutes": settings.alert_interval_minutes,
            "websocket_clients": hub.client_count,
            "websockets_supported": settings.websockets_supported,
            "sms_configured": settings.twilio_configured,
        },
        "runtime": {
            "serverless": settings.serverless,
            "api_mount_prefix": settings.api_mount_prefix,
        },
    }


@router.get("/config")
def config() -> dict:
    """Everything the UI needs to render its selectors without hardcoding."""
    settings = get_settings()
    return {
        "languages": [{"code": code, "label": label} for code, label in SUPPORTED_LANGUAGES.items()],
        "user_types": list(USER_TYPES),
        "response_modes": ["normal", "simple", "emergency"],
        "hazards": list(risk_engine.HAZARDS),
        "risk_bands": [
            {"level": "Low", "min": 0, "max": 30},
            {"level": "Moderate", "min": 31, "max": 60},
            {"level": "High", "min": 61, "max": 80},
            {"level": "Severe", "min": 81, "max": 100},
        ],
        "data_source": settings.weather_data_mode,
        "simulated_data": settings.use_fixtures,
        "voice_input_available": speech.transcription_available(),
        "voice_output_available": speech.synthesis_available(),
        # False on serverless hosts, where the client must poll /alerts instead
        # of holding a socket open.
        "websockets_supported": settings.websockets_supported,
        "alert_poll_seconds": max(30, settings.alert_interval_minutes * 60 // 10),
    }


@router.get("/historical-events")
def historical_events() -> dict:
    """Reference events used for context comparisons, for the UI to display."""
    return {"events": history.all_events(), "min_similarity": history.MIN_SIMILARITY}

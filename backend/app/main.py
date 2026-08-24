"""WeatherGPT FastAPI application.

Wires the routes together, starts the single alert scheduler, and installs the
error handling that keeps a failure inside one request from ever reaching the
user as a stack trace.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .db import init_db
from .routes import alerts_routes, chat, meta, risk_routes, weather_routes
from .services.alerts import run_alert_scan

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("weathergpt")

DESCRIPTION = """
Conversational, multilingual, voice-enabled weather intelligence for India.

All risk values — in chat, alerts, the 24-hour timeline and the India risk map —
come from one shared Weather Risk Engine, so they can never disagree.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    init_db()
    log.info(
        "WeatherGPT starting | data=%s | llm=%s | model=%s",
        settings.weather_data_mode,
        "configured" if settings.llm_configured else "fallback-only",
        settings.anthropic_model if settings.llm_configured else "-",
    )
    if settings.use_fixtures:
        log.warning("WEATHER_DATA_MODE=fixture — responses use SIMULATED data, not live observations.")
    if settings.serverless:
        log.info(
            "serverless runtime detected: in-process scheduler disabled (use a platform cron "
            "against %s/alerts/scan) and /ws/alerts is unavailable; clients fall back to polling.",
            settings.api_mount_prefix.rstrip("/"),
        )

    scheduler = None
    if settings.scheduler_enabled:
        # One scheduler for the whole app. Subscriptions extend this job's
        # watchlist; they never create a second scheduler.
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        scheduler = AsyncIOScheduler(timezone="UTC")
        scheduler.add_job(
            run_alert_scan,
            "interval",
            minutes=settings.alert_interval_minutes,
            id="alert_scan",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=300,
        )
        scheduler.start()
        log.info("alert scheduler started (every %d minutes)", settings.alert_interval_minutes)
    app.state.scheduler = scheduler

    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)
            log.info("alert scheduler stopped")


app = FastAPI(
    title="WeatherGPT",
    description=DESCRIPTION,
    version="1.0.0",
    lifespan=lifespan,
)

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _settings.cors_allow_all else _settings.cors_origins,
    allow_credentials=not _settings.cors_allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)

_ROUTERS = (meta.router, chat.router, weather_routes.router, alerts_routes.router, risk_routes.router)

for _router in _ROUTERS:
    app.include_router(_router)

# Also serve everything under the mount prefix. Platforms that route by path
# (Vercel services, an API gateway, an ingress rule) may forward the prefix
# rather than strip it; mounting both ways means the API works either way and
# needs no deployment-specific configuration.
_prefix = _settings.api_mount_prefix.rstrip("/")
if _prefix and _prefix != "/":
    for _router in _ROUTERS:
        app.include_router(_router, prefix=_prefix, include_in_schema=False)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Readable message instead of a raw pydantic error dump."""
    fields = ", ".join(".".join(str(p) for p in err.get("loc", [])[1:]) or "request" for err in exc.errors())
    return JSONResponse(
        status_code=422,
        content={"detail": f"That request was not valid. Please check: {fields}."},
    )


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last resort. The trace goes to the log, never to the client."""
    log.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong on our side. Please try again in a moment."},
    )


@app.get("/", tags=["meta"])
def root() -> dict:
    return {
        "name": "WeatherGPT",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }

# -*- coding: utf-8 -*-
"""Shared test setup.

Tests run against the offline fixture provider and a throwaway database, so
they are deterministic and need no network. That also means they exercise the
*degraded* path by default — which is exactly the path that must not break.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("WEATHER_DATA_MODE", "fixture")
os.environ.setdefault("SCHEDULER_ENABLED", "false")
os.environ.setdefault("LLM_ENABLED", "false")
os.environ.setdefault("TTS_ENABLED", "false")
os.environ.setdefault("WEATHERGPT_DB", str(Path(tempfile.mkdtemp()) / "test.db"))


@pytest.fixture(autouse=True)
def _clean_state():
    """Fresh caches per test so a pinned scenario cannot leak between them."""
    from app.services import memory, weather

    weather.clear_cache()
    memory.clear_cache()
    yield
    weather.clear_cache()
    memory.clear_cache()
    os.environ.pop("WEATHER_FIXTURE_SCENARIO", None)


@pytest.fixture
def scenario():
    """Force a fixture weather scenario for the duration of a test."""
    from app.services import weather

    def _set(name: str):
        os.environ["WEATHER_FIXTURE_SCENARIO"] = name
        weather.clear_cache()

    return _set


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def bundle_for():
    from app.services import weather

    def _get(place: str):
        location = weather.geocode(place)
        assert location is not None, f"gazetteer missing {place}"
        return weather.fetch_weather(location)

    return _get

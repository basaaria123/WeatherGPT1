# -*- coding: utf-8 -*-
"""Day and night, as the API reports them.

The client cannot tell a clear night from a clear noon without these fields, so
the tests here are about them being present, honest, and self-consistent.
"""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from app.main import app
from app.services import weather

client = TestClient(app)

STAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")


def test_current_carries_todays_solar_bounds():
    """`is_day` is a snapshot; the bounds are what hold a night together.

    A dashboard opened before sunset and left open would still be claiming
    daylight at midnight if all it had was `is_day`. These two let the client
    re-answer the question locally, all night, without a second request.
    """
    body = client.get("/weather/current", params={"location": "Vijayawada"}).json()
    current = body["current"]
    assert STAMP.match(current["sunrise"] or ""), current["sunrise"]
    assert STAMP.match(current["sunset"] or ""), current["sunset"]
    assert current["sunrise"] < current["sunset"]
    # And the timezone that makes them mean something at a distance.
    assert body["location"]["timezone"]


def test_the_bounds_agree_with_the_forecast_they_came_from():
    """Lifted from the same bundle, not fetched again — so they cannot differ."""
    bundle = weather.fetch_weather(weather.geocode("Vijayawada"))
    body = client.get("/weather/current", params={"location": "Vijayawada"}).json()
    assert body["current"]["sunrise"] == bundle.daily[0]["sunrise"]
    assert body["current"]["sunset"] == bundle.daily[0]["sunset"]


def test_the_fixture_does_not_claim_perpetual_daylight():
    """The offline fixture used to pin `is_day` true, which made night unreachable.

    It now reads its own clock against its own sunrise and sunset, so the demo
    can show the night interface at night — and so "always day" stops being a
    claim the fixture makes about the world.
    """
    bundle = weather._fixture_bundle(weather.geocode("Vijayawada"))
    now = weather._local_now(bundle.location)
    minutes = now.hour * 60 + now.minute
    expected = weather._FIXTURE_SUNRISE <= minutes < weather._FIXTURE_SUNSET
    assert bundle.current["is_day"] is expected
    # And it agrees with the bounds it publishes.
    assert bundle.current["sunrise"].endswith("T05:52")
    assert bundle.current["sunset"].endswith("T18:24")


def test_the_condition_wording_is_not_rewritten_for_night():
    """Night changes the picture, never the words.

    The provider says "mainly clear skies" at 2am too; inventing "clear night"
    would be fabricating a description nobody measured.
    """
    body = client.get("/weather/current", params={"location": "Vijayawada"}).json()
    assert "night" not in (body["current"]["condition"] or "").lower()

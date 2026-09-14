# -*- coding: utf-8 -*-
"""The year-by-year series behind Historical & Climate Insights.

Every assertion here is about one thing: that the screen can only ever show
numbers the archive actually measured. A chart is the easiest place in an
application to tell a confident lie — a zero-filled year looks like a drought,
a part-year mean looks like a cold snap, and a slope drawn through noise looks
like climate change — so each of those is a test.
"""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import climate, weather
from app.services.weather import WeatherError

client = TestClient(app)


@pytest.fixture
def chennai():
    return weather.gazetteer_lookup("Chennai")


def archive_of(rows: dict[str, tuple[float | None, float | None]]):
    """A stand-in archive: {date: (precipitation_mm, mean_temp_c)}."""
    times = sorted(rows)
    return {
        "daily": {
            "time": times,
            "precipitation_sum": [rows[t][0] for t in times],
            "temperature_2m_mean": [rows[t][1] for t in times],
        }
    }


def full_years(years: dict[int, tuple[float, float]]):
    """A complete 365-day year per entry: {year: (daily_mm, daily_temp)}."""
    rows = {}
    for year, (mm, temp) in years.items():
        for day in range(365):
            stamp = (date(year, 1, 1).toordinal() + day)
            rows[date.fromordinal(stamp).isoformat()] = (mm, temp)
    return archive_of(rows)


# --- What it measures ------------------------------------------------------
def test_a_year_is_the_mean_of_its_measured_days(chennai, monkeypatch):
    monkeypatch.setattr(
        weather, "fetch_archive",
        lambda *a, **k: full_years({2022: (2.0, 27.0), 2023: (2.0, 28.0), 2024: (2.0, 29.0)}),
    )
    series = climate.history_series(chennai, parameter="temperature", years=3, today=date(2025, 6, 1))
    assert series.available
    assert [p["value"] for p in series.points] == [27.0, 28.0, 29.0]
    assert series.average == 28.0
    assert (series.highest, series.highest_year) == (29.0, 2024)
    assert (series.lowest, series.lowest_year) == (27.0, 2022)


def test_rainfall_is_a_total_and_temperature_is_an_average(chennai, monkeypatch):
    """Summing temperature or averaging rainfall would both be nonsense, and
    both would produce a plausible-looking chart."""
    monkeypatch.setattr(weather, "fetch_archive", lambda *a, **k: full_years({2023: (3.0, 28.0), 2024: (3.0, 28.0)}))

    temps = climate.history_series(chennai, parameter="temperature", years=2, today=date(2025, 6, 1))
    rain = climate.history_series(chennai, parameter="rainfall", years=2, today=date(2025, 6, 1))

    assert temps.points[0]["value"] == 28.0
    assert temps.unit == "°C"
    assert rain.points[0]["value"] == pytest.approx(365 * 3.0, abs=1)
    assert rain.unit == "mm"


def test_the_current_year_is_excluded(chennai, monkeypatch):
    """A January-to-June mean plotted beside ten full years is a dip that is an
    artefact of the calendar, not the climate."""
    monkeypatch.setattr(weather, "fetch_archive", lambda *a, **k: full_years({2023: (2.0, 28.0), 2024: (2.0, 28.0)}))
    series = climate.history_series(chennai, parameter="temperature", years=5, today=date(2025, 6, 15))
    assert series.end_year == 2024
    assert all(point["year"] < 2025 for point in series.points)


# --- What it refuses to show ----------------------------------------------
def test_a_year_the_archive_barely_covered_is_dropped_not_scaled(chennai, monkeypatch):
    """A part-year rainfall total presented as an annual one reads as a drought
    that never happened."""
    rows = {}
    for day in range(365):
        rows[date.fromordinal(date(2023, 1, 1).toordinal() + day).isoformat()] = (2.0, 28.0)
    for day in range(40):  # 2024 has forty days of data
        rows[date.fromordinal(date(2024, 1, 1).toordinal() + day).isoformat()] = (2.0, 28.0)
    for day in range(365):
        rows[date.fromordinal(date(2022, 1, 1).toordinal() + day).isoformat()] = (2.0, 28.0)
    monkeypatch.setattr(weather, "fetch_archive", lambda *a, **k: archive_of(rows))

    series = climate.history_series(chennai, parameter="rainfall", years=3, today=date(2025, 6, 1))
    assert [p["year"] for p in series.points] == [2022, 2023]


def test_gaps_in_a_year_are_skipped_never_zero_filled(chennai, monkeypatch):
    """A None day counted as 0 mm drags an annual total down by a real amount."""
    rows = {}
    for day in range(365):
        stamp = date.fromordinal(date(2023, 1, 1).toordinal() + day).isoformat()
        rows[stamp] = (None, None) if day % 7 == 0 else (2.0, 28.0)
    for day in range(365):
        rows[date.fromordinal(date(2022, 1, 1).toordinal() + day).isoformat()] = (2.0, 28.0)
    monkeypatch.setattr(weather, "fetch_archive", lambda *a, **k: archive_of(rows))

    series = climate.history_series(chennai, parameter="temperature", years=2, today=date(2025, 1, 1))
    # Every surviving day was 28.0, so the mean is 28.0 — not dragged toward
    # zero by the days that were never measured.
    assert all(point["value"] == 28.0 for point in series.points)


def test_an_unreachable_archive_is_a_state_not_a_crash(chennai, monkeypatch):
    def down(*a, **k):
        raise WeatherError("archive is down")

    monkeypatch.setattr(weather, "fetch_archive", down)
    series = climate.history_series(chennai, parameter="temperature", years=5)
    assert series.available is False
    assert series.note == "archive_unavailable"
    # Empty, not zero: a zero on a chart reads as a measurement.
    assert series.points == []
    assert series.average is None and series.highest is None and series.lowest is None


def test_humidity_says_it_has_no_daily_series_rather_than_inventing_one(chennai):
    """Open-Meteo's daily archive carries temperature and precipitation and no
    relative humidity. Deriving one from something else would be a number
    nobody measured."""
    series = climate.history_series(chennai, parameter="humidity", years=5)
    assert series.available is False
    assert series.note == "no_daily_series"
    assert series.unit == "%"


def test_one_year_is_not_a_trend(chennai, monkeypatch):
    monkeypatch.setattr(weather, "fetch_archive", lambda *a, **k: full_years({2024: (2.0, 28.0)}))
    series = climate.history_series(chennai, parameter="temperature", years=5, today=date(2025, 6, 1))
    assert series.available is False
    assert series.note == "not_enough_years"


# --- What it says about direction -----------------------------------------
def test_a_change_inside_the_noise_floor_reads_as_steady(chennai, monkeypatch):
    """Reading a slope out of noise is the main way a chart like this lies."""
    monkeypatch.setattr(weather, "fetch_archive", lambda *a, **k: full_years({2023: (2.0, 28.0), 2024: (2.0, 28.1)}))
    series = climate.history_series(chennai, parameter="temperature", years=2, today=date(2025, 6, 1))
    assert series.direction == "steady"
    assert series.change == pytest.approx(0.1)


def test_a_real_change_is_named_with_its_direction(chennai, monkeypatch):
    monkeypatch.setattr(weather, "fetch_archive", lambda *a, **k: full_years({2023: (2.0, 27.0), 2024: (2.0, 29.0)}))
    rising = climate.history_series(chennai, parameter="temperature", years=2, today=date(2025, 6, 1))
    assert rising.direction == "rising"
    assert rising.change == pytest.approx(2.0)

    monkeypatch.setattr(weather, "fetch_archive", lambda *a, **k: full_years({2023: (2.0, 29.0), 2024: (2.0, 27.0)}))
    falling = climate.history_series(chennai, parameter="temperature", years=2, today=date(2025, 6, 1))
    assert falling.direction == "falling"


# --- The endpoint ----------------------------------------------------------
def test_the_endpoint_labels_which_archive_answered(scenario):
    """In fixture mode the archive is synthetic, and the response has to say so
    — that label is what stops a demo presenting a generated series as
    observations."""
    scenario("rain")
    response = client.get(
        "/api/climate/history", params={"location": "Chennai", "parameter": "temperature", "years": 5}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data_source"] == "fixture"
    assert body["available"] is True
    assert len(body["points"]) >= 2
    assert body["unit"] == "°C"


def test_missing_history_is_a_200_with_a_reason_not_a_500(scenario, monkeypatch):
    """This screen is built to show "we could not get it". An error page is not
    that, and it loses the selectors with it."""
    scenario("rain")

    def down(*a, **k):
        raise WeatherError("archive is down")

    monkeypatch.setattr(weather, "fetch_archive", down)
    response = client.get("/api/climate/history", params={"location": "Chennai", "years": 5})
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["note"] == "archive_unavailable"
    assert body["points"] == []


def test_an_unknown_parameter_falls_back_rather_than_erroring(scenario):
    scenario("rain")
    response = client.get(
        "/api/climate/history", params={"location": "Chennai", "parameter": "wind", "years": 3}
    )
    assert response.status_code == 200
    assert response.json()["parameter"] == "temperature"

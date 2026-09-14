# -*- coding: utf-8 -*-
"""The year-by-year series behind Historical & Climate Insights.

Every assertion here is about one thing: that the screen can only ever show
numbers the archive actually measured. A chart is the easiest place in an
application to tell a confident lie — a zero-filled year looks like a drought,
a part-year mean looks like a cold snap, and a slope drawn through noise looks
like climate change — so each of those is a test.
"""

from __future__ import annotations

import dataclasses
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


def test_humidity_is_measured_rather_than_refused(chennai):
    """The selector offers humidity, so it has to draw something.

    It was wired to `aggregate: None`, which meant the option could be pressed
    and could never plot anything — an honest answer to a question nobody had
    asked, since the daily archive does carry `relative_humidity_2m_mean`. It
    is still requested on its own, so an archive range that does not carry it
    fails the humidity chart and leaves temperature and rainfall alone.
    """
    series = climate.history_series(chennai, parameter="humidity", years=5)
    assert series.available is True
    assert series.unit == "%"
    assert len(series.points) >= 2
    # Measured, not derived from temperature: every value is a percentage.
    assert all(0 <= point["value"] <= 100 for point in series.points)


def test_humidity_is_asked_for_on_its_own(chennai, monkeypatch):
    """One measurement per request. Four variables for a one-line chart is most
    of the payload that was timing out."""
    asked: list[str | None] = []

    def spy(location, start, end, *, daily=None):
        asked.append(daily)
        return full_years({2023: (2.0, 28.0), 2024: (2.0, 29.0)})

    monkeypatch.setattr(weather, "fetch_archive", spy)
    climate.history_series(chennai, parameter="humidity", years=5)
    assert set(asked) == {"relative_humidity_2m_mean"}

    asked.clear()
    climate.history_series(chennai, parameter="rainfall", years=5)
    assert set(asked) == {"precipitation_sum"}


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


# --- Why the screen said the archive could not be reached ------------------
#
# It was reported from production: Chennai, five years, "The historical archive
# could not be reached for this place." The archive was reachable. The request
# was being held to the same twelve-second budget as a current observation,
# and Open-Meteo aggregating five years of daily ERA5 values does not finish in
# twelve seconds on a cold range.
def test_the_archive_gives_up_inside_the_platform_ceiling():
    """The obvious fix was a longer timeout, and it would not have worked.

    The backend runs as a serverless function with a hard wall-clock ceiling,
    so a client timeout above that ceiling is never reached — the platform
    kills the invocation and the browser gets nothing. The archive budget has
    to stay well under it, so a slow year is abandoned early enough for the
    years that did answer to be returned.
    """
    from app.config import get_settings

    settings = get_settings()
    assert 0 < settings.archive_timeout_seconds <= 10


def test_settled_history_is_cached_for_longer_than_an_observation():
    """A finished calendar year cannot change, so the only reason to re-fetch
    it is that the process restarted."""
    from app.config import get_settings

    settings = get_settings()
    assert settings.archive_cache_seconds > settings.weather_cache_seconds


def _live(monkeypatch, responder):
    """Run `fetch_archive` against a stand-in provider instead of the fixture."""
    live = dataclasses.replace(weather.get_settings(), weather_data_mode="live")
    weather.clear_cache()
    monkeypatch.setattr(weather, "_http_get", responder)
    monkeypatch.setattr(weather, "get_settings", lambda: live)


def test_a_refused_archive_request_is_retried(chennai, monkeypatch):
    """A reset or a 502 fails in milliseconds, so another go is nearly free."""
    calls = {"n": 0}

    def flaky(url, params, *, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise WeatherError("The weather service is unreachable right now.")
        return full_years({2023: (2.0, 28.0)})

    _live(monkeypatch, flaky)
    payload = weather.fetch_archive(
        chennai, date(2023, 1, 1), date(2023, 12, 31), daily="temperature_2m_mean",
    )
    assert calls["n"] == 2
    assert payload["daily"]["time"]


def test_a_timed_out_archive_request_is_not_retried(chennai, monkeypatch):
    """A provider that is already slow will still be slow a second later, and
    the retry spends the budget the other years of the chart need."""
    calls = {"n": 0}

    def slow(url, params, *, timeout=None):
        calls["n"] += 1
        raise weather.WeatherTimeout("too slow")

    _live(monkeypatch, slow)
    with pytest.raises(WeatherError):
        weather.fetch_archive(
            chennai, date(2023, 1, 1), date(2023, 12, 31), daily="temperature_2m_mean",
        )
    assert calls["n"] == 1


def test_the_archive_request_carries_the_archive_budget(chennai, monkeypatch):
    """Not the observation budget, and not httpx's default."""
    seen: list[float | None] = []

    def spy(url, params, *, timeout=None):
        seen.append(timeout)
        return full_years({2023: (2.0, 28.0)})

    _live(monkeypatch, spy)
    weather.fetch_archive(chennai, date(2023, 1, 1), date(2023, 12, 31), daily="temperature_2m_mean")
    assert seen == [weather.get_settings().archive_timeout_seconds]


def test_the_window_is_fetched_a_year_at_a_time(chennai, monkeypatch):
    """One request spanning five years is one request the platform can kill.

    Five small ones finish inside the ceiling, cache under their own keys so
    moving the selector from five years to ten re-fetches five, and fail
    independently.
    """
    spans: list[tuple[date, date]] = []

    def per_year(location, start, end, *, daily=None):
        spans.append((start, end))
        return full_years({start.year: (2.0, 27.0)})

    monkeypatch.setattr(weather, "fetch_archive", per_year)
    climate.history_series(chennai, parameter="temperature", years=5, today=date(2026, 9, 14))
    assert sorted(spans) == [
        (date(year, 1, 1), date(year, 12, 31)) for year in range(2021, 2026)
    ]


def test_a_year_that_fails_costs_that_year_and_not_the_chart(chennai, monkeypatch):
    """Four good years out of five is a real chart. "Could not be reached" is
    not, and that is what one failed request used to produce."""
    def per_year(location, start, end, *, daily=None):
        if start.year == 2021:
            raise WeatherError("this one year is missing")
        return full_years({start.year: (2.0, 27.0 + (start.year - 2021) * 0.5)})

    monkeypatch.setattr(weather, "fetch_archive", per_year)
    series = climate.history_series(
        chennai, parameter="temperature", years=5, today=date(2026, 9, 14),
    )
    assert series.available is True
    # The year that could not be fetched is absent, not zero-filled, and the
    # window reports the years actually plotted rather than the ones asked for.
    assert [p["year"] for p in series.points] == [2022, 2023, 2024, 2025]
    assert series.start_year == 2022


def test_a_window_that_fails_entirely_still_says_which_absence_it_is(chennai, monkeypatch):
    """"The archive does not go back far enough here" is a fact about the
    place; "we could not reach it" is a fact about this request. Saying the
    first when the second happened sends somebody looking for another city."""
    def down(*args, **kwargs):
        raise WeatherError("unreachable")

    monkeypatch.setattr(weather, "fetch_archive", down)
    series = climate.history_series(chennai, parameter="temperature", years=5)
    assert series.available is False
    assert series.note == "archive_unavailable"

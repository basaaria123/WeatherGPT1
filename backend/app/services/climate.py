# -*- coding: utf-8 -*-
"""Climate-trend analysis for /climate-trend.

The statistics are computed here in Python from Open-Meteo's historical
archive. The LLM is only ever asked to phrase an already-computed result, so it
cannot introduce an anomaly figure that was never measured — and when the LLM
is absent the templated summary states the same numbers in the user's language.
"""

from __future__ import annotations

import calendar
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from . import i18n, llm, weather
from .weather import Location, WeatherError

log = logging.getLogger("weathergpt.climate")

DEFAULT_YEARS = 10
# The archive lags real time by a few days; ask only for settled data.
ARCHIVE_LAG_DAYS = 6


@dataclass
class TrendMetrics:
    month_name: str
    year: int
    years_compared: int
    current_precip_mm: float | None
    baseline_precip_mm: float | None
    precip_anomaly_pct: float | None
    current_mean_temp_c: float | None
    baseline_mean_temp_c: float | None
    temp_anomaly_c: float | None
    days_counted: int
    baseline_days: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "month": self.month_name,
            "year": self.year,
            "years_compared": self.years_compared,
            "current_precipitation_mm": self.current_precip_mm,
            "baseline_precipitation_mm": self.baseline_precip_mm,
            "precipitation_anomaly_pct": self.precip_anomaly_pct,
            "current_mean_temperature_c": self.current_mean_temp_c,
            "baseline_mean_temperature_c": self.baseline_mean_temp_c,
            "temperature_anomaly_c": self.temp_anomaly_c,
            "days_counted": self.days_counted,
            "baseline_days_counted": self.baseline_days,
        }


def _daily(payload: dict[str, Any]) -> tuple[list[str], list[Any], list[Any]]:
    block = payload.get("daily") or {}
    times = list(block.get("time") or [])
    precip = list(block.get("precipitation_sum") or [])
    temps = list(block.get("temperature_2m_mean") or [])
    if not temps:
        # Some archive responses omit the mean; derive it from max/min.
        highs = list(block.get("temperature_2m_max") or [])
        lows = list(block.get("temperature_2m_min") or [])
        temps = [
            (h + l) / 2 if isinstance(h, (int, float)) and isinstance(l, (int, float)) else None
            for h, l in zip(highs, lows)
        ]
    precip += [None] * max(0, len(times) - len(precip))
    temps += [None] * max(0, len(times) - len(temps))
    return times, precip, temps


def _series(payload: dict[str, Any], field: str) -> tuple[list[str], list[Any]]:
    """One named daily variable, with the dates it was measured on.

    `_daily` above reads the two variables the monthly anomaly needs; this
    reads whichever one the chart asked for, so a parameter can be added to
    `PARAMETERS` without a second extraction path being written for it.
    """
    block = payload.get("daily") or {}
    times = list(block.get("time") or [])
    values = list(block.get(field) or [])
    if not values and field == "temperature_2m_mean":
        # Some archive responses omit the mean; derive it from max/min rather
        # than reporting a year as missing when both halves of it are present.
        highs = list(block.get("temperature_2m_max") or [])
        lows = list(block.get("temperature_2m_min") or [])
        values = [
            (h + l) / 2 if isinstance(h, (int, float)) and isinstance(l, (int, float)) else None
            for h, l in zip(highs, lows)
        ]
    values += [None] * max(0, len(times) - len(values))
    return times, values


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 1) if values else None


def compute_trend(location: Location, *, years: int = DEFAULT_YEARS, today: date | None = None) -> TrendMetrics:
    """Compare the month so far against the same window in prior years."""
    reference = (today or date.today()) - timedelta(days=ARCHIVE_LAG_DAYS)
    month, year, day_of_month = reference.month, reference.year, reference.day
    month_name = calendar.month_name[month]

    # Current period: the 1st of the month to the last settled day.
    current = weather.fetch_archive(location, date(year, month, 1), reference)
    _, cur_precip, cur_temp = _daily(current)
    cur_precip_values = [float(v) for v in cur_precip if isinstance(v, (int, float))]
    cur_temp_values = [float(v) for v in cur_temp if isinstance(v, (int, float))]

    # Baseline: the same calendar window in each of the previous `years` years,
    # so a part-month comparison is like-for-like rather than against a full month.
    totals: list[float] = []
    means: list[float] = []
    baseline_days = 0
    # Fetched together rather than one after another. Ten baseline years in
    # sequence is ten round trips inside one serverless invocation, which is
    # the same wall-clock ceiling that broke the history chart.
    windows = {}
    for offset in range(1, years + 1):
        past_year = year - offset
        last_day = min(day_of_month, calendar.monthrange(past_year, month)[1])
        windows[past_year] = (date(past_year, month, 1), date(past_year, month, last_day))

    payloads: dict[int, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=min(ARCHIVE_WORKERS, max(1, len(windows)))) as pool:
        futures = {
            pool.submit(weather.fetch_archive, location, start, end): past
            for past, (start, end) in windows.items()
        }
        for future in as_completed(futures):
            past = futures[future]
            try:
                payloads[past] = future.result()
            except WeatherError as exc:
                log.warning("archive year %s unavailable: %s", past, exc)

    for past_year in sorted(payloads):
        payload = payloads[past_year]
        _, precip, temp = _daily(payload)
        precip_values = [float(v) for v in precip if isinstance(v, (int, float))]
        temp_values = [float(v) for v in temp if isinstance(v, (int, float))]
        if precip_values:
            totals.append(sum(precip_values))
            baseline_days += len(precip_values)
        if temp_values:
            means.append(sum(temp_values) / len(temp_values))

    current_precip = round(sum(cur_precip_values), 1) if cur_precip_values else None
    baseline_precip = round(sum(totals) / len(totals), 1) if totals else None
    precip_anomaly = None
    if current_precip is not None and baseline_precip:
        precip_anomaly = round((current_precip - baseline_precip) / baseline_precip * 100, 1)

    current_temp = _mean(cur_temp_values)
    baseline_temp = _mean(means)
    temp_anomaly = (
        round(current_temp - baseline_temp, 1)
        if current_temp is not None and baseline_temp is not None
        else None
    )

    return TrendMetrics(
        month_name=month_name,
        year=year,
        years_compared=len(totals),
        current_precip_mm=current_precip,
        baseline_precip_mm=baseline_precip,
        precip_anomaly_pct=precip_anomaly,
        current_mean_temp_c=current_temp,
        baseline_mean_temp_c=baseline_temp,
        temp_anomaly_c=temp_anomaly,
        days_counted=len(cur_precip_values),
        baseline_days=baseline_days,
    )


def _direction(value: float, above: str, below: str, same: str) -> str:
    if value >= 5:
        return above
    if value <= -5:
        return below
    return same


TREND_NO_DATA: dict[str, str] = {
    "en": "There is not enough historical data for {loc} to compare this month against previous years.",
    "hi": "{loc} के लिए पिछले वर्षों से तुलना करने हेतु पर्याप्त ऐतिहासिक डेटा उपलब्ध नहीं है।",
    "te": "{loc} కోసం గత సంవత్సరాలతో పోల్చడానికి తగినంత చారిత్రక సమాచారం అందుబాటులో లేదు.",
    "bn": "{loc}-এর জন্য আগের বছরগুলির সঙ্গে তুলনা করার মতো যথেষ্ট ঐতিহাসিক তথ্য নেই।",
    "mr": "{loc} साठी मागील वर्षांशी तुलना करण्यासाठी पुरेशी ऐतिहासिक माहिती उपलब्ध नाही.",
    "as": "{loc}ৰ বাবে আগৰ বছৰবোৰৰ সৈতে তুলনা কৰিবলৈ পৰ্যাপ্ত ঐতিহাসিক তথ্য নাই।",
}

TREND_PRECIP: dict[str, dict[str, str]] = {
    "en": {
        "wetter": "This {month} has been about {pct}% wetter than the {years}-year average in {loc}, with {current} mm so far against a typical {baseline} mm.",
        "drier": "This {month} has been about {pct}% drier than the {years}-year average in {loc}, with {current} mm so far against a typical {baseline} mm.",
        "similar": "Rainfall this {month} in {loc} is close to the {years}-year average, with {current} mm so far against a typical {baseline} mm.",
    },
    "hi": {
        "wetter": "{loc} में इस {month} में {years}-वर्ष के औसत से लगभग {pct}% ज़्यादा बारिश हुई है — अब तक {current} मिमी, जबकि सामान्य {baseline} मिमी है।",
        "drier": "{loc} में इस {month} में {years}-वर्ष के औसत से लगभग {pct}% कम बारिश हुई है — अब तक {current} मिमी, जबकि सामान्य {baseline} मिमी है।",
        "similar": "{loc} में इस {month} की बारिश {years}-वर्ष के औसत के क़रीब है — अब तक {current} मिमी, सामान्य {baseline} मिमी।",
    },
    "te": {
        "wetter": "{loc}లో ఈ {month}లో {years} ఏళ్ల సగటు కంటే సుమారు {pct}% ఎక్కువ వర్షం పడింది — ఇప్పటివరకు {current} మి.మీ., సాధారణంగా {baseline} మి.మీ.",
        "drier": "{loc}లో ఈ {month}లో {years} ఏళ్ల సగటు కంటే సుమారు {pct}% తక్కువ వర్షం పడింది — ఇప్పటివరకు {current} మి.మీ., సాధారణంగా {baseline} మి.మీ.",
        "similar": "{loc}లో ఈ {month} వర్షపాతం {years} ఏళ్ల సగటుకు దగ్గరగా ఉంది — ఇప్పటివరకు {current} మి.మీ., సాధారణంగా {baseline} మి.మీ.",
    },
    "bn": {
        "wetter": "{loc}-এ এই {month} মাসে {years} বছরের গড়ের চেয়ে প্রায় {pct}% বেশি বৃষ্টি হয়েছে — এ পর্যন্ত {current} মিমি, স্বাভাবিক {baseline} মিমি।",
        "drier": "{loc}-এ এই {month} মাসে {years} বছরের গড়ের চেয়ে প্রায় {pct}% কম বৃষ্টি হয়েছে — এ পর্যন্ত {current} মিমি, স্বাভাবিক {baseline} মিমি।",
        "similar": "{loc}-এ এই {month} মাসের বৃষ্টি {years} বছরের গড়ের কাছাকাছি — এ পর্যন্ত {current} মিমি, স্বাভাবিক {baseline} মিমি।",
    },
    "mr": {
        "wetter": "{loc} मध्ये या {month} मध्ये {years} वर्षांच्या सरासरीपेक्षा सुमारे {pct}% जास्त पाऊस झाला आहे — आतापर्यंत {current} मिमी, नेहमीचा {baseline} मिमी.",
        "drier": "{loc} मध्ये या {month} मध्ये {years} वर्षांच्या सरासरीपेक्षा सुमारे {pct}% कमी पाऊस झाला आहे — आतापर्यंत {current} मिमी, नेहमीचा {baseline} मिमी.",
        "similar": "{loc} मध्ये या {month} चा पाऊस {years} वर्षांच्या सरासरीच्या जवळ आहे — आतापर्यंत {current} मिमी, नेहमीचा {baseline} मिमी.",
    },
    "as": {
        "wetter": "{loc}ত এই {month} মাহত {years} বছৰৰ গড়তকৈ প্ৰায় {pct}% বেছি বৰষুণ হৈছে — এতিয়ালৈকে {current} মি.মি., স্বাভাৱিক {baseline} মি.মি.।",
        "drier": "{loc}ত এই {month} মাহত {years} বছৰৰ গড়তকৈ প্ৰায় {pct}% কম বৰষুণ হৈছে — এতিয়ালৈকে {current} মি.মি., স্বাভাৱিক {baseline} মি.মি.।",
        "similar": "{loc}ত এই {month} মাহৰ বৰষুণ {years} বছৰৰ গড়ৰ ওচৰা-উচৰি — এতিয়ালৈকে {current} মি.মি., স্বাভাৱিক {baseline} মি.মি.।",
    },
}

TREND_TEMP: dict[str, dict[str, str]] = {
    "en": {
        "warmer": "Average temperature is running {delta}°C above the {years}-year normal, at {current}°C against {baseline}°C.",
        "cooler": "Average temperature is running {delta}°C below the {years}-year normal, at {current}°C against {baseline}°C.",
        "similar": "Average temperature is close to the {years}-year normal, at {current}°C against {baseline}°C.",
    },
    "hi": {
        "warmer": "औसत तापमान {years}-वर्ष के सामान्य से {delta}°C ऊपर चल रहा है — {current}°C बनाम {baseline}°C।",
        "cooler": "औसत तापमान {years}-वर्ष के सामान्य से {delta}°C नीचे चल रहा है — {current}°C बनाम {baseline}°C।",
        "similar": "औसत तापमान {years}-वर्ष के सामान्य के क़रीब है — {current}°C बनाम {baseline}°C।",
    },
    "te": {
        "warmer": "సగటు ఉష్ణోగ్రత {years} ఏళ్ల సాధారణం కంటే {delta}°C ఎక్కువగా ఉంది — {current}°C, సాధారణం {baseline}°C.",
        "cooler": "సగటు ఉష్ణోగ్రత {years} ఏళ్ల సాధారణం కంటే {delta}°C తక్కువగా ఉంది — {current}°C, సాధారణం {baseline}°C.",
        "similar": "సగటు ఉష్ణోగ్రత {years} ఏళ్ల సాధారణానికి దగ్గరగా ఉంది — {current}°C, సాధారణం {baseline}°C.",
    },
    "bn": {
        "warmer": "গড় তাপমাত্রা {years} বছরের স্বাভাবিকের চেয়ে {delta}°C বেশি — {current}°C, স্বাভাবিক {baseline}°C।",
        "cooler": "গড় তাপমাত্রা {years} বছরের স্বাভাবিকের চেয়ে {delta}°C কম — {current}°C, স্বাভাবিক {baseline}°C।",
        "similar": "গড় তাপমাত্রা {years} বছরের স্বাভাবিকের কাছাকাছি — {current}°C, স্বাভাবিক {baseline}°C।",
    },
    "mr": {
        "warmer": "सरासरी तापमान {years} वर्षांच्या सामान्यपेक्षा {delta}°C जास्त आहे — {current}°C, सामान्य {baseline}°C.",
        "cooler": "सरासरी तापमान {years} वर्षांच्या सामान्यपेक्षा {delta}°C कमी आहे — {current}°C, सामान्य {baseline}°C.",
        "similar": "सरासरी तापमान {years} वर्षांच्या सामान्याच्या जवळ आहे — {current}°C, सामान्य {baseline}°C.",
    },
    "as": {
        "warmer": "গড় উষ্ণতা {years} বছৰৰ স্বাভাৱিকতকৈ {delta}°C বেছি — {current}°C, স্বাভাৱিক {baseline}°C।",
        "cooler": "গড় উষ্ণতা {years} বছৰৰ স্বাভাৱিকতকৈ {delta}°C কম — {current}°C, স্বাভাৱিক {baseline}°C।",
        "similar": "গড় উষ্ণতা {years} বছৰৰ স্বাভাৱিকৰ ওচৰা-উচৰি — {current}°C, স্বাভাৱিক {baseline}°C।",
    },
}


def templated_summary(metrics: TrendMetrics, location_label: str, lang: str = "en") -> str:
    """Deterministic summary, used when the LLM is unavailable."""
    lang = i18n.normalise_lang(lang)
    if metrics.precip_anomaly_pct is None and metrics.temp_anomaly_c is None:
        return TREND_NO_DATA.get(lang, TREND_NO_DATA["en"]).format(loc=location_label)

    parts: list[str] = []
    if metrics.precip_anomaly_pct is not None:
        key = _direction(metrics.precip_anomaly_pct, "wetter", "drier", "similar")
        parts.append(
            TREND_PRECIP[lang][key].format(
                loc=location_label,
                month=metrics.month_name,
                pct=abs(metrics.precip_anomaly_pct),
                years=metrics.years_compared,
                current=metrics.current_precip_mm,
                baseline=metrics.baseline_precip_mm,
            )
        )
    if metrics.temp_anomaly_c is not None:
        # Scaled so a 0.5°C departure reads as meaningful, unlike a 0.5% one.
        key = _direction(metrics.temp_anomaly_c * 10, "warmer", "cooler", "similar")
        parts.append(
            TREND_TEMP[lang][key].format(
                delta=abs(metrics.temp_anomaly_c),
                current=metrics.current_mean_temp_c,
                baseline=metrics.baseline_mean_temp_c,
                years=metrics.years_compared,
            )
        )
    return " ".join(parts)


def summarise(metrics: TrendMetrics, location_label: str, lang: str = "en") -> tuple[str, bool]:
    """Return ``(summary, llm_used)``."""
    if llm.available():
        from .language import language_name

        text = llm.climate_summary(
            location=location_label,
            metrics=metrics.to_dict(),
            language_name=language_name(lang),
        )
        if text:
            return text, True
    return templated_summary(metrics, location_label, lang), False


# ---------------------------------------------------------------------------
# Year-by-year history, for the Historical & Climate Insights screen
# ---------------------------------------------------------------------------
#
# WHAT IS REAL HERE, AND WHAT IS NOT
#
# These numbers are measured. `weather.fetch_archive` reads Open-Meteo's
# historical archive — the same provider the dashboard uses for the forecast —
# and everything below is arithmetic over what it returns. Nothing is modelled,
# interpolated or invented, and a year the archive has no data for is absent
# from the series rather than filled in.
#
# The one exception is loudly labelled elsewhere: in fixture mode the archive is
# `weather._fixture_archive`, a deterministic synthetic series. Every response
# carries `data_source`, and the interface already says "SIMULATED DATA — not
# live observations" whenever that is "fixture".
#
# WHAT THE DAILY ARCHIVE DOES NOT CARRY
#
# Humidity. Open-Meteo's *daily* archive block has temperature and
# precipitation and no relative humidity — that exists only in the hourly
# block, and averaging ten years of hourly values to draw one line is a
# different and much heavier feature. So humidity is offered, and answers
# honestly that the series is not available, rather than being quietly computed
# from something else.

PARAMETERS: dict[str, dict[str, Any]] = {
    # key: what to ask the archive for, which field carries it, what unit, and
    # how a year is summarised.
    #
    # `daily` is per parameter because the chart draws one measurement and the
    # request used to carry four. On a five- or ten-year range that is most of
    # a megabyte of numbers nothing plots, inside the one request that was
    # already running out of time.
    "temperature": {
        # The mean, with max/min as the fallback `_series` derives it from —
        # some archive responses omit the mean for older ranges.
        "daily": "temperature_2m_mean,temperature_2m_max,temperature_2m_min",
        "field": "temperature_2m_mean",
        "unit": "°C", "aggregate": "mean", "decimals": 1,
    },
    # Rainfall and precipitation are one measurement in this archive
    # (`precipitation_sum`), so there is one option rather than two identical
    # ones under different names.
    "rainfall": {
        "daily": "precipitation_sum",
        "field": "precipitation_sum",
        "unit": "mm", "aggregate": "sum", "decimals": 0,
    },
    # Offered on the screen, so it has to measure something. It was wired to
    # `aggregate: None`, which meant the selector could be pressed and could
    # never draw anything — the honest answer to a question nobody had asked,
    # since the archive does carry a daily mean. Requested on its own, so that
    # if a given archive range does not carry it the temperature and rainfall
    # charts are unaffected.
    "humidity": {
        "daily": "relative_humidity_2m_mean",
        "field": "relative_humidity_2m_mean",
        "unit": "%", "aggregate": "mean", "decimals": 0,
    },
}

# A trend smaller than this over the whole window is reported as steady rather
# than as a direction. Reading a slope out of noise is the main way a chart like
# this tells a lie.
TREND_EPSILON = {"temperature": 0.3, "rainfall": 25.0, "humidity": 1.0}

MAX_YEARS = 30


@dataclass
class HistorySeries:
    """A year-by-year series, and what can honestly be said about it."""

    parameter: str
    unit: str
    start_year: int
    end_year: int
    points: list[dict[str, Any]]
    average: float | None
    highest: float | None
    highest_year: int | None
    lowest: float | None
    lowest_year: int | None
    direction: str            # rising | falling | steady | unknown
    change: float | None      # first year to last, in `unit`
    available: bool
    note: str | None

    def summary_average(self) -> float:
        return self.average if self.average is not None else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "parameter": self.parameter,
            "unit": self.unit,
            "start_year": self.start_year,
            "end_year": self.end_year,
            "points": self.points,
            "summary": {
                "average": self.average,
                "highest": self.highest,
                "highest_year": self.highest_year,
                "lowest": self.lowest,
                "lowest_year": self.lowest_year,
            },
            "trend": {"direction": self.direction, "change": self.change},
            "available": self.available,
            "note": self.note,
        }


def _unavailable(parameter: str, start: int, end: int, note: str) -> HistorySeries:
    """A series that cannot be built, said plainly.

    Every field a caller would read is present and empty, so the interface
    renders its own "no data" state rather than crashing on a missing key or —
    worse — showing a zero that looks like a measurement.
    """
    spec = PARAMETERS.get(parameter, PARAMETERS["temperature"])
    return HistorySeries(
        parameter=parameter, unit=spec["unit"], start_year=start, end_year=end,
        points=[], average=None, highest=None, highest_year=None,
        lowest=None, lowest_year=None, direction="unknown", change=None,
        available=False, note=note,
    )


# How many archive requests to have in flight at once. Six is enough to make a
# ten-year window feel instant and small enough not to look like a scrape.
ARCHIVE_WORKERS = 6


def _fetch_years(
    location: Location,
    daily: str,
    years: list[int],
) -> tuple[dict[int, dict[str, Any]], bool]:
    """One archive request per calendar year, in parallel.

    A year at a time rather than one request spanning the window, which is what
    this used to do and is why the screen said "the historical archive could
    not be reached for this place" about an archive that was answering fine.
    Three reasons, and the first is the one that broke production:

    * The backend runs as a serverless function with a hard wall-clock ceiling
      measured in seconds. One request asking Open-Meteo to aggregate five
      years of daily ERA5 values regularly takes longer than that, so the
      platform killed the function and the client never saw a reply. Raising
      the HTTP timeout cannot fix that — the limit is not ours. Five small
      requests running at once finish in about as long as the slowest one.
    * A year that fails costs that year, not the chart. Four years out of five
      is a real chart and an honest one; "could not be reached" is not.
    * Each year caches under its own key, so moving the selector from five
      years to ten re-fetches five years rather than all ten.

    Returns what came back and whether every year did.
    """
    payloads: dict[int, dict[str, Any]] = {}
    complete = True
    workers = min(ARCHIVE_WORKERS, max(1, len(years)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(
                weather.fetch_archive,
                location, date(year, 1, 1), date(year, 12, 31), daily=daily,
            ): year
            for year in years
        }
        for future in as_completed(futures):
            year = futures[future]
            try:
                payloads[year] = future.result()
            except WeatherError as exc:
                log.warning("archive year %s unavailable for %s: %s", year, location.name, exc)
                complete = False
    return payloads, complete


def _archive_days(
    location: Location,
    spec: dict[str, Any],
    start_year: int,
    end_year: int,
) -> tuple[list[str], list[Any], bool]:
    """Every measured day in the window, and whether all of it was reached."""
    payloads, complete = _fetch_years(
        location, spec["daily"], list(range(start_year, end_year + 1)),
    )
    times: list[str] = []
    values: list[Any] = []
    for year in sorted(payloads):
        stamp_year = str(year)
        for stamp, value in zip(*_series(payloads[year], spec["field"])):
            # Keep only the year this request asked for. With one request per
            # year the windows sit end to end, and `timezone=auto` can shift a
            # boundary day across the join — counted twice, a year's rainfall
            # total gains a day it did not have.
            if str(stamp).startswith(stamp_year):
                times.append(stamp)
                values.append(value)
    return times, values, complete


def history_series(
    location: Location,
    *,
    parameter: str = "temperature",
    years: int = 5,
    today: date | None = None,
) -> HistorySeries:
    """One value per calendar year, measured from the archive.

    The most recent complete year is the end of the window: the current year is
    part-way through, and a January-to-September mean plotted beside ten full
    years is a dip that is an artefact of the calendar rather than the climate.
    """
    parameter = (parameter or "temperature").strip().lower()
    if parameter not in PARAMETERS:
        parameter = "temperature"
    spec = PARAMETERS[parameter]

    reference = today or date.today()
    end_year = reference.year - 1
    years = max(2, min(int(years), MAX_YEARS))
    start_year = end_year - years + 1

    times, values, complete = _archive_days(location, spec, start_year, end_year)
    if not times:
        return _unavailable(parameter, start_year, end_year, "archive_unavailable")

    # Group by calendar year, keeping only the days the archive actually
    # measured. A year with no usable days is dropped, never zero-filled.
    buckets: dict[int, list[float]] = {}
    for stamp, value in zip(times, values):
        if not isinstance(value, (int, float)):
            continue
        try:
            year = int(str(stamp)[:4])
        except (TypeError, ValueError):
            continue
        buckets.setdefault(year, []).append(float(value))

    points: list[dict[str, Any]] = []
    for year in sorted(buckets):
        days = buckets[year]
        # A year missing most of its days cannot carry an annual total, and a
        # partial sum plotted as one would read as a drought that never
        # happened.
        if len(days) < 300:
            continue
        total = sum(days)
        value = total if spec["aggregate"] == "sum" else total / len(days)
        points.append({
            "year": year,
            "label": str(year),
            "value": round(value, spec["decimals"]),
            "days": len(days),
        })

    if len(points) < 2:
        # Which absence this is matters to the reader: "the archive does not go
        # back far enough here" is a fact about the place, and "we could not
        # reach it" is a fact about this request. Saying the first when the
        # second happened sends somebody looking for a different city.
        return _unavailable(
            parameter, start_year, end_year,
            "not_enough_years" if complete else "archive_unavailable",
        )

    readings = [point["value"] for point in points]
    highest = max(points, key=lambda p: p["value"])
    lowest = min(points, key=lambda p: p["value"])
    change = round(readings[-1] - readings[0], spec["decimals"])

    epsilon = TREND_EPSILON.get(parameter, 0.0)
    if abs(change) < epsilon:
        direction = "steady"
    else:
        direction = "rising" if change > 0 else "falling"

    return HistorySeries(
        parameter=parameter,
        unit=spec["unit"],
        start_year=points[0]["year"],
        end_year=points[-1]["year"],
        points=points,
        average=round(sum(readings) / len(readings), spec["decimals"]),
        highest=highest["value"],
        highest_year=highest["year"],
        lowest=lowest["value"],
        lowest_year=lowest["year"],
        direction=direction,
        change=change,
        available=True,
        note=None,
    )


# ---------------------------------------------------------------------------
# Answers for the assistant
# ---------------------------------------------------------------------------
def nwp_answer(lang: str = "en") -> str:
    """What this product does and does not do with numerical models.

    A fixed sentence, not a generated one, and deliberately so: this is a claim
    about the build, and a claim about the build is the last thing that should
    be phrased freshly each time. There is no GFS output to report because there
    is no GFS integration, and an assistant that improvised here would invent
    one.
    """
    return i18n.sentence("nwp_answer", i18n.normalise_lang(lang))


def history_answer(location: Location, text: str, lang: str = "en") -> str:
    """A climate-history question, answered from the archive or refused.

    Reads which measurement was asked about, fetches the real series, and states
    what it found. When the archive has nothing it says that instead — the one
    thing it will not do is describe a trend it did not measure.
    """
    lang = i18n.normalise_lang(lang)
    lowered = (text or "").lower()
    parameter = "rainfall" if any(
        word in lowered for word in ("rain", "rainfall", "precipitation", "monsoon", "बारिश", "वर्षा")
    ) else "humidity" if any(
        word in lowered for word in ("humid", "humidity", "नमी")
    ) else "temperature"

    years = 10
    for count, words in ((5, ("five", "5 year", "5-year", "पाँच")), (20, ("twenty", "20 year", "बीस")),
                         (3, ("three", "3 year", "तीन")), (1, ("last year", "one year"))):
        if any(word in lowered for word in words):
            years = max(2, count)
            break

    series = history_series(location, parameter=parameter, years=years)
    label = i18n.sentence(f"clim_param_{parameter}", lang)

    if not series.available:
        key = {
            "no_daily_series": "clim_no_series",
            "not_enough_years": "clim_too_few",
        }.get(series.note, "clim_no_archive")
        return i18n.sentence(key, lang, param=label, loc=location.label)

    decimals = 0 if series.unit == "mm" else 1
    return i18n.sentence(
        f"clim_says_{series.direction}",
        lang,
        param=label,
        loc=location.label,
        start=series.start_year,
        end=series.end_year,
        change=f"{abs(series.change or 0):.{decimals}f}{series.unit}",
        average=f"{series.summary_average():.{decimals}f}{series.unit}",
    )

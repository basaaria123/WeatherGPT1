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
    for offset in range(1, years + 1):
        past_year = year - offset
        try:
            last_day = min(day_of_month, calendar.monthrange(past_year, month)[1])
            payload = weather.fetch_archive(
                location, date(past_year, month, 1), date(past_year, month, last_day)
            )
        except WeatherError as exc:
            log.warning("archive year %s unavailable: %s", past_year, exc)
            continue
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

# -*- coding: utf-8 -*-
"""Does the assistant answer what was asked, or does it file a weather report?

The bug this file exists for: every question, however narrow, came back with
the temperature, the feels-like, the rain chance, the 24-hour total, the
humidity, the wind and a heat note. "Will it rain?" is a yes-or-no question and
it was answered with seven facts, six of which were not asked for.
"""

from __future__ import annotations

import pytest

from app.services import advisory, nlp_fallback


# --- What the question is about ---------------------------------------------

@pytest.mark.parametrize(
    "question,expected",
    [
        ("Will it rain in the next two hours?", {"rain"}),
        ("How windy is it?", {"wind"}),
        ("Is it hot today?", {"temperature"}),
        ("How is the visibility?", {"visibility"}),
        ("Why is the risk high?", {"risk"}),
        ("क्या बारिश होगी?", {"rain"}),
        ("வானிலை எப்படி இருக்கிறது?", set()),
    ],
)
def test_the_focus_is_read_from_the_readers_own_words(question, expected):
    assert expected.issubset(set(nlp_fallback.detect_focus(question)))


def test_a_broad_question_names_nothing_in_particular():
    """And that emptiness is the signal that the whole reading is the answer."""
    for question in ("What is the weather like?", "How's the weather?", "Tell me about today"):
        assert nlp_fallback.detect_focus(question) == (), question


# --- What comes back ---------------------------------------------------------

def _bundle(**current):
    from types import SimpleNamespace
    base = {
        "temperature_c": 29.6, "apparent_temperature_c": 33.0, "humidity_pct": 82.0,
        "precipitation_mm": 0.2, "precipitation_probability_pct": 35.0,
        "wind_speed_kmh": 17.0, "wind_gust_kmh": 24.0, "visibility_km": 9.0,
        "weather_code": 3,
    }
    base.update(current)
    hourly = [{"time": f"2026-09-13T{(6 + i) % 24:02d}:00", "precipitation_mm": 0.1,
               "precipitation_probability_pct": 30.0, "risk_score": 20} for i in range(24)]
    return SimpleNamespace(
        current=base, hourly=hourly,
        daily=[{"temp_max_c": 32.7, "temp_min_c": 22.8, "precipitation_probability_pct": 40.0, "weather_code": 3}],
        location=SimpleNamespace(name="Vijayawada", label="Vijayawada, Andhra Pradesh"),
        source="fixture",
    )


def _risk(level="Low", hazard="No active hazard"):
    from app.schemas import RiskOutput
    return RiskOutput(
        risk_score={"Low": 14, "Moderate": 45}[level], risk_level=level, detected_hazard=hazard,
        hazard_scores={"Heavy Rainfall": 0, "Flood Risk": 0, "Strong Wind": 0,
                       "Extreme Heat": 0, "Lightning/Storm": 0},
    )


def test_a_question_about_wind_is_answered_with_wind():
    answer = advisory.smart_explanation(_bundle(), _risk(), "en", focus=("wind",))
    assert "km/h" in answer
    for unasked in ("humidity", "°C"):
        assert unasked not in answer, answer


def test_a_question_about_rain_is_not_answered_with_the_temperature():
    answer = advisory.smart_explanation(_bundle(), _risk(), "en", focus=("rain",))
    assert "rain" in answer.lower()
    assert "29.6" not in answer, answer


def test_a_broad_question_still_gets_the_whole_reading():
    """The narrowing must not cost the answer to 'what's the weather like?'."""
    whole = advisory.smart_explanation(_bundle(), _risk(), "en")
    assert "29.6" in whole and "km/h" in whole
    assert len(whole) > len(advisory.smart_explanation(_bundle(), _risk(), "en", focus=("wind",)))


def test_a_focus_this_reading_cannot_answer_narrows_nothing():
    """'Why is the risk high' is answered by the hazard block, not by this text.

    Narrowing to a topic with no sentences would have returned an empty answer.
    """
    answer = advisory.smart_explanation(_bundle(), _risk(), "en", focus=("risk", "timing"))
    assert answer == advisory.smart_explanation(_bundle(), _risk(), "en")


def test_a_narrow_question_does_not_collect_role_framing():
    narrow = advisory.templated_answer(
        _bundle(), _risk(), intent="current_weather", user_type="farmer", lang="en",
        focus=("wind",), advice_question=False,
    )
    broad = advisory.templated_answer(
        _bundle(), _risk(), intent="current_weather", user_type="farmer", lang="en",
        advice_question=False,
    )
    assert len(narrow) < len(broad), (narrow, broad)


def test_an_advice_question_leads_with_advice_and_stops():
    """§14's shape: the guidance, then one sentence of evidence for it."""
    answer = advisory.templated_answer(
        _bundle(), _risk(), intent="current_weather", user_type="farmer", lang="en",
        advice_question=True,
    )
    # Short enough to be an answer rather than a briefing.
    assert len(advisory._sentences(answer)) <= 4, answer

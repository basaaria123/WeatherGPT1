# -*- coding: utf-8 -*-
"""The two questions the assistant used to get wrong.

Both were failures of the same kind: a question the model had no way to answer,
answered by the model anyway. One came back as an apology for data the
application actually had; the other risked coming back as a capability the
application does not have. Both are now settled before generation, and these
tests are what keep them there.
"""

from __future__ import annotations

import pytest

from app.services import chat_engine, climate, nlp_fallback, weather
from app.services.weather import WeatherError


# --- "Can you use GFS?" ----------------------------------------------------
@pytest.mark.parametrize(
    "query",
    [
        "Can WeatherGPT use GFS?",
        "Do you use the Global Forecast System?",
        "What model do you use?",
        "Is WRF supported?",
        "Do you run numerical weather prediction?",
    ],
)
def test_a_question_about_the_models_is_recognised(query):
    """These contain no weather noun, so the scope guard turned them away — a
    reasonable question about a forecasting product, answered with "I can only
    help with weather"."""
    assert nlp_fallback.mentions_models(query) is True
    assert nlp_fallback.detect_intent(query, 0) == "nwp_models"
    assert nlp_fallback.extract(query, known_location="Chennai")["in_scope"] is True


def test_the_model_answer_never_claims_a_live_integration(scenario):
    scenario("rain")
    response = chat_engine.handle_chat(
        query="Can WeatherGPT use GFS?", selected_location="Chennai", requested_language="en"
    )
    answer = response.answer
    assert response.intent == "nwp_models"
    assert "planned" in answer.lower()
    # The one thing it must never do: report a number as model output.
    for invented in ("gfs says", "according to gfs", "wrf predicts", "the model shows"):
        assert invented not in answer.lower()


def test_an_ordinary_weather_question_is_not_caught_by_the_model_intent():
    """"Is there a model aircraft show today" is contrived; "what is the
    weather" is not, and neither may be classified as a question about NWP."""
    for query in ("What is the weather?", "Will it rain today?", "Is it safe to travel?"):
        assert nlp_fallback.mentions_models(query) is False


# --- "How has it changed?" -------------------------------------------------
def test_a_history_question_is_answered_from_the_archive(scenario):
    """The failure this replaces: the model apologised for having no historical
    data while the archive behind the insights screen held ten years of it."""
    scenario("rain")
    response = chat_engine.handle_chat(
        query="How has the temperature changed in Chennai over the last five years?",
        selected_location="Chennai",
        requested_language="en",
    )
    assert response.intent == "climate_trend"
    answer = response.answer.lower()
    assert "chennai" in answer
    # A real answer names the window it measured.
    assert any(str(year) in response.answer for year in range(2015, 2031))
    assert "do not have" not in answer and "sorry" not in answer


def test_the_question_decides_which_measurement_is_read(scenario, monkeypatch):
    scenario("rain")
    seen: list[str] = []
    real = climate.history_series

    def spy(location, *, parameter="temperature", **kw):
        seen.append(parameter)
        return real(location, parameter=parameter, **kw)

    monkeypatch.setattr(climate, "history_series", spy)

    climate.history_answer(weather.gazetteer_lookup("Chennai"), "has rainfall increased?", "en")
    climate.history_answer(weather.gazetteer_lookup("Chennai"), "how has temperature changed?", "en")
    assert seen == ["rainfall", "temperature"]


def test_an_unreachable_archive_is_said_plainly_not_improvised(scenario, monkeypatch):
    scenario("rain")

    def down(*a, **k):
        raise WeatherError("archive is down")

    monkeypatch.setattr(weather, "fetch_archive", down)
    answer = climate.history_answer(
        weather.gazetteer_lookup("Chennai"), "how has temperature changed?", "en"
    )
    assert "not available" in answer.lower() or "could not be reached" in answer.lower()
    # No number is offered for data that was never fetched.
    assert "°c" not in answer.lower()


def test_humidity_history_is_answered_from_the_archive(scenario):
    """Humidity used to be refused here because the series was wired to
    nothing. It is a measured daily variable, so the assistant answers it the
    same way it answers temperature — with the archive's own numbers."""
    scenario("rain")
    answer = climate.history_answer(
        weather.gazetteer_lookup("Chennai"), "show me humidity over the years", "en"
    )
    assert "humidity" in answer.lower()
    assert "%" in answer


def test_every_language_has_both_answers():
    """A reader who set the interface to Tamil must not get an English sentence
    about GFS — the pack validator covers the keys, this covers the call."""
    from app.services import i18n

    for lang in i18n.LANGUAGES:
        nwp = climate.nwp_answer(lang)
        assert nwp and "{" not in nwp, lang
        assert "GFS" in nwp and "WRF" in nwp, lang

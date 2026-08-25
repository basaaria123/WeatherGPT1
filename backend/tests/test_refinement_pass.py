# -*- coding: utf-8 -*-
"""Tests for the refinement pass: insight, role tailoring, location precedence
and the hazard-vs-official-alert distinction.

The theme through all of these is that presentation may change with the reader
and the place, but the underlying facts may not.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("WEATHER_DATA_MODE", "fixture")

from app.services import advisory, i18n, risk_engine, weather  # noqa: E402

LANGS = ("en", "hi", "te", "bn", "mr", "as")


def bundle_for(city: str, scenario: str | None = None):
    if scenario:
        os.environ["WEATHER_FIXTURE_SCENARIO"] = scenario
    else:
        os.environ.pop("WEATHER_FIXTURE_SCENARIO", None)
    weather.clear_cache()
    location = weather.gazetteer_lookup(city)
    assert location is not None, city
    return weather.fetch_weather(location)


# ---------------------------------------------------------------------------
# Insight
# ---------------------------------------------------------------------------
def test_insight_is_never_empty_and_carries_named_factors():
    for scenario in ("calm", "rain", "flood", "heat", "wind", "fog", "storm"):
        b = bundle_for("Guwahati", scenario)
        insight = advisory.headline_insight(b, risk_engine.assess(b), "general", "en")
        assert insight["headline"].strip(), scenario
        # Every factor named must be one the generator actually evaluated.
        assert set(insight["factors"]) <= {
            "rainfall", "wind", "visibility", "temperature", "hazard indicators",
        }


def test_insight_leads_with_the_hazard_only_when_it_is_actionable():
    severe = bundle_for("Guwahati", "flood")
    risk = risk_engine.assess(severe)
    assert risk_engine.is_actionable(risk)
    lead = advisory.headline_insight(severe, risk, "farmer", "en")["headline"]
    assert i18n.hazard_label(risk.detected_hazard, "en") in lead

    calm = bundle_for("Bengaluru", "calm")
    calm_risk = risk_engine.assess(calm)
    assert not risk_engine.is_actionable(calm_risk)
    calm_lead = advisory.headline_insight(calm, calm_risk, "farmer", "en")["headline"]
    # A calm reading leads with the farmer's own concern, not with a hazard.
    assert "hazard" not in calm_lead.lower()


def test_profile_changes_emphasis_but_not_the_underlying_numbers():
    b = bundle_for("New Delhi", "fog")
    risk = risk_engine.assess(b)
    outputs = {p: advisory.headline_insight(b, risk, p, "en") for p in
               ("general", "farmer", "fisherman", "traveler", "commuter")}

    # The traveller is the one who should hear about visibility first.
    assert "visibilit" in outputs["traveler"]["headline"].lower()
    # Distinct emphasis across profiles...
    assert len({o["headline"] for o in outputs.values()}) > 1
    # ...but the risk they are all describing is one shared value.
    for profile in outputs:
        assert outputs[profile]["actionable"] is risk_engine.is_actionable(risk)


def test_insight_never_contradicts_itself_on_visibility():
    """A closing 'conditions are fine' must not follow a low-visibility line."""
    b = bundle_for("New Delhi", "fog")
    risk = risk_engine.assess(b)
    for profile in ("general", "traveler", "commuter"):
        text = " ".join(
            [advisory.headline_insight(b, risk, profile, "en")[k] for k in ("headline", "supporting")]
        ).lower()
        if "visibility is low" in text:
            assert "no major rain is expected" not in text
            assert "generally safe" not in text


@pytest.mark.parametrize("lang", LANGS)
def test_insight_is_produced_in_every_supported_language(lang):
    b = bundle_for("Chennai", "rain")
    insight = advisory.headline_insight(b, risk_engine.assess(b), "farmer", lang)
    assert insight["headline"].strip()
    if lang != "en":
        # A non-English request must not silently fall back to the English text.
        english = advisory.headline_insight(b, risk_engine.assess(b), "farmer", "en")
        assert insight["headline"] != english["headline"]


# ---------------------------------------------------------------------------
# Impact cards
# ---------------------------------------------------------------------------
def test_impact_cards_do_not_repeat_one_sentence_across_sectors():
    for scenario in ("calm", "rain", "flood", "heat"):
        b = bundle_for("Guwahati", scenario)
        cards = advisory.impact_cards(b, risk_engine.assess(b), "en")
        details = [c.detail for c in cards]
        assert len(set(details)) == len(details), f"{scenario}: {details}"


def test_profile_reorders_impact_cards_without_changing_their_verdicts():
    b = bundle_for("Chennai", "rain")
    risk = risk_engine.assess(b)
    general = advisory.impact_cards(b, risk, "en", "general")
    fisherman = advisory.impact_cards(b, risk, "en", "fisherman")

    assert fisherman[0].category == i18n.category_label("fishing", "en")
    # Same set of verdicts, only the order differs.
    assert {(c.category, c.status) for c in general} == {(c.category, c.status) for c in fisherman}


def test_avoid_status_requires_a_genuinely_high_sub_score():
    b = bundle_for("Bengaluru", "calm")
    cards = advisory.impact_cards(b, risk_engine.assess(b), "en")
    assert all(card.status != "Avoid" for card in cards)


# ---------------------------------------------------------------------------
# Location precedence — the single source of truth
# ---------------------------------------------------------------------------
def test_selected_location_is_used_when_the_question_names_none():
    from app.services import chat_engine, memory

    state = memory.get_session(None)
    resolved = chat_engine.resolve_location(
        {"location": None}, state, original_query="will it rain today?", selected="Chennai"
    )
    assert resolved is not None and resolved.name == "Chennai"


def test_a_named_place_still_outranks_the_selection():
    from app.services import chat_engine, memory

    state = memory.get_session(None)
    resolved = chat_engine.resolve_location(
        {"location": "Guwahati"}, state, original_query="weather in Guwahati", selected="Chennai"
    )
    assert resolved is not None and resolved.name == "Guwahati"


def test_selection_outranks_a_stale_remembered_location():
    """The user can see the selected place on screen; answering about a
    different one they mentioned earlier reads as a bug, not continuity."""
    from app.services import chat_engine, memory

    state = memory.get_session(None)
    memory.set_location(state, weather.gazetteer_lookup("Guwahati"))
    resolved = chat_engine.resolve_location(
        {"location": None, "use_previous_location": True},
        state,
        original_query="what about tomorrow?",
        selected="Mumbai",
    )
    assert resolved is not None and resolved.name == "Mumbai"


# ---------------------------------------------------------------------------
# Hazard vs official alert
# ---------------------------------------------------------------------------
def test_a_detected_hazard_does_not_imply_an_issued_warning(tmp_path, monkeypatch):
    """The two concepts are reported independently, so the UI can show a hazard
    alongside 'no official warning' without contradicting itself."""
    monkeypatch.setenv("WEATHERGPT_DB", str(tmp_path / "t.db"))
    monkeypatch.setenv("WEATHER_DATA_MODE", "fixture")
    monkeypatch.delenv("WEATHER_FIXTURE_SCENARIO", raising=False)

    from app.config import reset_settings
    from fastapi.testclient import TestClient

    reset_settings()
    weather.clear_cache()
    from app.main import app

    with TestClient(app) as client:
        payload = client.get("/weather/current?location=Mumbai").json()

    # Mumbai's fixture is a thunderstorm: a real hazard, with no alert scanned.
    assert payload["risk"]["detected_hazard"] != "None"
    assert payload["official_alert_count"] == 0

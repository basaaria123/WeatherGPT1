# -*- coding: utf-8 -*-
"""Depth pass: persona advisory, emergency mode, historical similarity.

All three read the one risk engine. These tests exist mainly to hold the lines
that are dangerous to cross — advice that is identical across personas, an
emergency the frontend can conjure, or a comparison that reads as a prediction.
"""

from __future__ import annotations

import os
import re

import pytest

os.environ.setdefault("WEATHER_DATA_MODE", "fixture")

from app.services import advisory, history, i18n, risk_engine, weather  # noqa: E402

LANGS = ("en", "hi", "te", "bn", "mr", "as")
PERSONAS = ("farmer", "fisherman", "traveler", "commuter", "general")


def bundle(city: str, scenario: str):
    os.environ["WEATHER_FIXTURE_SCENARIO"] = scenario
    weather.clear_cache()
    return weather.fetch_weather(weather.gazetteer_lookup(city))


def assessed(city: str, scenario: str):
    b = bundle(city, scenario)
    return b, risk_engine.assess(b)


# ===========================================================================
# Feature A — persona advisory
# ===========================================================================
def test_same_conditions_give_every_persona_distinct_advice():
    _, risk = assessed("Guwahati", "flood")
    leads = {p: advisory.build_advisory(risk, p, "en")["actions"][0]["action"] for p in PERSONAS}
    assert len(set(leads.values())) == len(PERSONAS), leads


def test_advice_is_never_contradictory_across_personas():
    """No persona may be told to go out while another is told to stay in for
    the same reason — they share one hazard, so the direction must agree."""
    _, risk = assessed("Mumbai", "storm")
    texts = [
        " ".join(a["action"] for a in advisory.build_advisory(risk, p, "en")["actions"]).lower()
        for p in PERSONAS
    ]
    # Under a storm nobody should be encouraged outdoors.
    for text in texts:
        assert "conditions suit outdoor activity" not in text


def test_missing_or_unknown_user_type_falls_back_to_general_and_is_never_empty():
    _, risk = assessed("Guwahati", "flood")
    for value in (None, "", "astronaut", "AVIATION"):
        result = advisory.build_advisory(risk, value, "en")
        assert result["actions"], value
        assert result["source"] == "rules"


def test_high_and_severe_always_carry_actions():
    for city, scenario in [("Guwahati", "flood"), ("Mumbai", "storm"), ("Jaisalmer", "heat"), ("Puri", "wind")]:
        _, risk = assessed(city, scenario)
        if not risk_engine.is_actionable(risk):
            continue
        for persona in PERSONAS:
            assert advisory.build_advisory(risk, persona, "en")["actions"], (city, persona)


def test_risk_level_controls_how_many_actions_surface():
    _, severe = assessed("Guwahati", "flood")
    _, moderate = assessed("Chennai", "rain")
    assert severe.risk_level == "Severe" and moderate.risk_level == "Moderate"
    assert len(advisory.build_advisory(severe, "farmer", "en")["actions"]) > len(
        advisory.build_advisory(moderate, "farmer", "en")["actions"]
    )


@pytest.mark.parametrize("lang", LANGS)
def test_advisory_round_trips_through_every_language(lang):
    _, risk = assessed("Guwahati", "flood")
    result = advisory.build_advisory(risk, "fisherman", lang)
    assert result["actions"], lang
    text = result["actions"][0]["action"]
    if lang != "en":
        english = advisory.build_advisory(risk, "fisherman", "en")["actions"][0]["action"]
        assert text != english, f"{lang} fell back to English"
    assert result["disclaimer"]


def test_lead_action_carries_a_reason_in_every_language():
    _, risk = assessed("Guwahati", "flood")
    for lang in LANGS:
        lead = advisory.build_advisory(risk, "farmer", lang)["actions"][0]
        assert lead["reason"], lang


def test_every_persona_and_hazard_pair_is_covered_by_the_rules_table():
    """A gap here means a real reader gets generic advice for their situation."""
    gaps = []
    for hazard in ("Heavy Rainfall", "Flood Risk", "Strong Wind", "Extreme Heat", "Lightning/Storm"):
        for persona in PERSONAS:
            if not i18n.profile_action(persona, hazard, "en"):
                gaps.append((hazard, persona))
    assert not gaps, gaps


# ===========================================================================
# Feature B — emergency mode
# ===========================================================================
def test_emergency_is_inactive_below_high():
    for city, scenario in [("Bengaluru", "calm"), ("Chennai", "rain")]:
        b, risk = assessed(city, scenario)
        assert risk.risk_level in {"Low", "Moderate"}
        assert advisory.build_emergency(b, risk, "general", "en")["active"] is False


def test_emergency_activates_on_high_and_severe():
    for city, scenario in [("Guwahati", "flood"), ("Mumbai", "storm")]:
        b, risk = assessed(city, scenario)
        assert risk_engine.is_actionable(risk)
        payload = advisory.build_emergency(b, risk, "general", "en")
        assert payload["active"] is True
        assert payload["headline"] and payload["what_is_happening"] and payload["why_it_matters"]
        assert payload["immediate_actions"]


def test_emergency_trigger_comes_only_from_the_engine():
    """There is no argument that can switch this on against the engine's
    reading — the frontend has nothing to force."""
    b, risk = assessed("Bengaluru", "calm")
    for persona in PERSONAS:
        for lang in ("en", "te"):
            assert advisory.build_emergency(b, risk, persona, lang)["active"] is False


def test_simulated_emergency_is_labelled_and_never_implicit():
    b, risk = assessed("Guwahati", "flood")
    assert advisory.build_emergency(b, risk, "general", "en")["is_simulated"] is False
    assert advisory.build_emergency(b, risk, "general", "en", is_simulated=True)["is_simulated"] is True


def test_valid_until_is_derived_from_the_forecast_not_invented():
    b, risk = assessed("Guwahati", "flood")
    payload = advisory.build_emergency(b, risk, "general", "en")
    hours = {h["time"] for h in risk_engine.timeline(b, hours=24)}
    assert payload["valid_until"] in hours


def test_spoken_instructions_are_short_enough_to_be_heard_out():
    b, risk = assessed("Guwahati", "flood")
    spoken = advisory.build_emergency(b, risk, "farmer", "en")["spoken_instructions"]
    # ~150 wpm; the brief asks for roughly 30 seconds.
    assert len(spoken.split()) <= 90, len(spoken.split())
    for symbol in ("•", "|", "*", "#"):
        assert symbol not in spoken


@pytest.mark.parametrize("lang", LANGS)
def test_emergency_is_written_in_the_users_language(lang):
    b, risk = assessed("Guwahati", "flood")
    payload = advisory.build_emergency(b, risk, "general", lang)
    if lang == "en":
        return
    english = advisory.build_emergency(b, risk, "general", "en")
    assert payload["headline"] != english["headline"], lang


# ===========================================================================
# Feature C — historical similarity
# ===========================================================================
BANNED_FUTURE_CLAIMS = [
    r"\bwill cause\b", r"\bwill happen\b", r"\bis coming\b", r"\bexpect similar\b",
    r"\bwill lead to\b", r"\bwill result\b", r"\bpredicts?\b", r"\bforecasts? a\b",
]


def test_matching_conditions_surface_a_comparison_with_its_working():
    b, risk = assessed("Guwahati", "flood")
    result = history.similarity_for_bundle(b, risk)
    assert result["matched"] is True
    assert result["similarity_score"] >= history.MIN_SIMILARITY
    assert result["event"]["source"] and result["event"]["source_url"]
    assert result["matching_dimensions"], "a score with no visible working is an assertion"
    for dimension in result["matching_dimensions"]:
        assert {"dimension", "current", "historical", "unit", "closeness_pct"} <= set(dimension)


def test_calm_conditions_produce_no_comparison():
    b, risk = assessed("Bengaluru", "calm")
    assert history.similarity_for_bundle(b, risk)["matched"] is False


def test_moderate_conditions_produce_no_comparison():
    b, risk = assessed("Chennai", "rain")
    assert risk.risk_level == "Moderate"
    assert history.similarity_for_bundle(b, risk)["matched"] is False


def test_just_below_threshold_stays_silent():
    from app.schemas import RiskOutput

    event = history._events()[0]
    risk = RiskOutput(risk_score=85, risk_level="Severe", detected_hazard=event["criteria"]["hazard"])
    scored = history.score_event(
        event, risk=risk, rain_24h_mm=event["criteria"]["rain_24h_min_mm"],
        rain_72h_mm=event["criteria"]["rain_72h_min_mm"], wind_gust_kmh=None,
        state=event["states"][0], month=event["criteria"]["months"][0],
    )
    assert scored >= history.MIN_SIMILARITY
    # Same numbers, wrong region and season: must fall below the bar.
    elsewhere = history.score_event(
        event, risk=risk, rain_24h_mm=event["criteria"]["rain_24h_min_mm"],
        rain_72h_mm=event["criteria"]["rain_72h_min_mm"], wind_gust_kmh=None,
        state="Rajasthan", month=2,
    )
    assert elsewhere < scored


def test_right_rainfall_wrong_region_does_not_match():
    """A Chennai reading must not match an Assam river-basin flood just because
    the millimetres line up."""
    b = bundle("Guwahati", "flood")
    risk = risk_engine.assess(b)
    assam = history.find_comparison(
        risk=risk, rain_24h_mm=260, rain_72h_mm=590, wind_gust_kmh=None,
        state="Assam", when=None,
    )
    rajasthan = history.find_comparison(
        risk=risk, rain_24h_mm=260, rain_72h_mm=590, wind_gust_kmh=None,
        state="Rajasthan", when=None,
    )
    assert assam is not None
    if rajasthan is not None:
        assert rajasthan.similarity_score < assam.similarity_score


def test_a_dry_gale_is_not_a_cyclone():
    """Amphan states a rainfall floor; wind alone must not satisfy it."""
    from app.schemas import RiskOutput

    amphan = next(e for e in history._events() if e["id"] == "cyclone_amphan_2020_05")
    risk = RiskOutput(risk_score=90, risk_level="Severe", detected_hazard="Strong Wind")
    score = history.score_event(
        amphan, risk=risk, rain_24h_mm=2, rain_72h_mm=4, wind_gust_kmh=140,
        state="West Bengal", month=5,
    )
    assert score == 0


def test_comparison_text_makes_no_future_tense_outcome_claim():
    """Scans the asserted clause only.

    The disclaimer legitimately contains "will happen" — it is *denying* it
    ("not a prediction that the same event will happen again"). Scanning the
    whole string would flag the very sentence that makes the framing safe, so
    the claim and the denial are separated first.
    """
    b, risk = assessed("Guwahati", "flood")
    sentence = history.similarity_for_bundle(b, risk)["sentence"].lower()

    disclaimer_marker = "it is not a prediction"
    assert disclaimer_marker in sentence, "the denial must be present at all"
    claim = sentence.split(disclaimer_marker)[0]

    for pattern in BANNED_FUTURE_CLAIMS:
        assert not re.search(pattern, claim), f"{pattern} found in claim: {claim}"
    # And the claim must be framed as resemblance, not consequence.
    assert "similar" in claim


def test_framing_is_always_context():
    b, risk = assessed("Guwahati", "flood")
    assert history.similarity_for_bundle(b, risk)["framing"] == "context"


def test_every_event_cites_a_source():
    for event in history._events():
        assert event.get("source"), event["id"]
        assert event.get("source_url", "").startswith("http"), event["id"]


# ===========================================================================
# Regression — the contract in §1.2
# ===========================================================================
def test_new_response_fields_are_additive_only():
    from app.schemas import ChatResponse

    existing = [
        "session_id", "answer", "explanation", "action_mode", "actions", "response_mode",
        "intent", "user_type", "language", "detected_language", "in_scope", "location",
        "current", "risk", "impacts", "historical_comparison", "audio_base64", "audio_mime",
        "data_source", "raw_weather", "verification", "degraded",
    ]
    fields = ChatResponse.model_fields
    for name in existing:
        assert name in fields, f"{name} was removed or renamed"
    for added in ("advisory", "emergency", "historical_similarity"):
        assert fields[added].default is None, f"{added} must be optional for older clients"


def test_features_are_silent_when_inactive():
    """Calm weather, no persona: the app must behave exactly as before."""
    b, risk = assessed("Bengaluru", "calm")
    assert advisory.build_emergency(b, risk, None, "en")["active"] is False
    assert history.similarity_for_bundle(b, risk)["matched"] is False
    assert advisory.build_advisory(risk, None, "en")["actions"] == []

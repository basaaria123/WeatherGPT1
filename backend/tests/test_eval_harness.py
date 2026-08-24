# -*- coding: utf-8 -*-
"""Eval harness: curated queries with expected structured outputs.

Covers varied phrasing, misspellings, vague queries, multi-turn follow-ups in
several languages, and off-topic input. Assertions target the *contract* — the
structured fields the rest of the app depends on — not exact wording, so the
same harness is meaningful whether the LLM path or the rule-based path is live.

Run with an ANTHROPIC_API_KEY set to evaluate the LLM path instead.
"""

from __future__ import annotations

import pytest

from app.services import chat_engine, memory

# (id, query, expectations)
CASES: list[tuple[str, str, dict]] = [
    ("plain-current", "What's the weather in Vijayawada?",
     {"in_scope": True, "location": "Vijayawada", "intent": {"current_weather", "forecast"}}),
    ("will-it-rain", "Will it rain in Guwahati today?",
     {"in_scope": True, "location": "Guwahati", "day_offset": 0}),
    ("misspelled-city", "hows the wether in vijaywada",
     {"in_scope": True, "location": "Vijayawada"}),
    ("short-form-city", "weather in vizag",
     {"in_scope": True, "location": "Visakhapatnam"}),
    ("lowercase-noise", "mumbai weather tomorrow??",
     {"in_scope": True, "location": "Mumbai", "day_offset": 1}),
    ("alert-query", "Any severe alerts for Guwahati?",
     {"in_scope": True, "location": "Guwahati", "intent": {"alert_check"}}),
    ("safety-query", "Is it safe to travel to Shillong today?",
     {"in_scope": True, "location": "Shillong"}),
    ("farmer-query", "I am a farmer in Warangal, should I irrigate tomorrow?",
     {"in_scope": True, "location": "Warangal", "user_type": "farmer", "day_offset": 1}),
    ("fisherman-query", "Can I take my boat out at Ratnagiri?",
     {"in_scope": True, "location": "Ratnagiri", "user_type": "fisherman"}),
    ("climate-trend", "Has this month been wetter than average in Kochi?",
     {"in_scope": True, "location": "Kochi", "intent": {"climate_trend"}}),
    ("day-after", "What is the forecast for Chennai the day after tomorrow?",
     {"in_scope": True, "location": "Chennai", "day_offset": 2}),
    ("simple-mode", "explain simply the weather in Patna",
     {"in_scope": True, "location": "Patna", "response_mode": "simple"}),
    ("hindi", "क्या दिल्ली में कल बारिश होगी?",
     {"in_scope": True, "location": "New Delhi", "language": "hi", "day_offset": 1}),
    ("telugu", "గువాహటిలో వాతావరణం ఎలా ఉంది?",
     {"in_scope": True, "location": "Guwahati", "language": "te"}),
    ("assamese", "ডিব্ৰুগড়ত আজি বতৰ কেনে?",
     {"in_scope": True, "location": "Dibrugarh", "language": "as"}),
    ("bengali", "আজ কলকাতায় আবহাওয়া কেমন?",
     {"in_scope": True, "location": "Kolkata", "language": "bn"}),
    ("marathi", "उद्या मुंबईत पाऊस पडेल का?",
     {"in_scope": True, "location": "Mumbai", "language": "mr", "day_offset": 1}),
    ("off-topic-sport", "Who won the cricket match yesterday?", {"in_scope": False}),
    ("off-topic-code", "Write me a Python function to sort a list", {"in_scope": False}),
    ("off-topic-recipe", "Give me a recipe for biryani", {"in_scope": False}),
]


@pytest.mark.parametrize("case_id,query,expected", CASES, ids=[c[0] for c in CASES])
def test_eval_case(case_id, query, expected):
    response = chat_engine.handle_chat(query=query)

    assert response.in_scope is expected["in_scope"], f"{case_id}: scope mismatch"
    assert response.answer.strip(), f"{case_id}: empty answer"

    if not expected["in_scope"]:
        # A redirect, not a weather answer, and no data fetched.
        assert response.intent == "out_of_scope"
        assert response.risk is None
        return

    if "location" in expected:
        assert response.location is not None, f"{case_id}: no location resolved"
        assert response.location.name == expected["location"], (
            f"{case_id}: got {response.location.name}"
        )
    if "intent" in expected:
        assert response.intent in expected["intent"], f"{case_id}: intent {response.intent}"
    if "language" in expected:
        assert response.language == expected["language"], f"{case_id}: language {response.language}"
    if "user_type" in expected:
        assert response.user_type == expected["user_type"], f"{case_id}: user_type {response.user_type}"
    if "response_mode" in expected and not response.action_mode:
        # Emergency mode legitimately overrides a "simple" request.
        assert response.response_mode == expected["response_mode"]

    # Contract guarantees that hold for every in-scope answer.
    assert response.risk is not None
    assert 0 <= response.risk.risk_score <= 100
    assert response.verification.verified, f"{case_id}: unverified numbers {response.verification.rejected_numbers}"
    assert response.data_source in {"live", "fixture"}


def test_day_offset_extraction():
    """day_offset is not on ChatResponse, so assert it at the extraction layer."""
    from app.services import nlp_fallback

    assert nlp_fallback.extract("weather tomorrow in Mumbai")["day_offset"] == 1
    assert nlp_fallback.extract("forecast day after tomorrow in Chennai")["day_offset"] == 2
    assert nlp_fallback.extract("weather now in Chennai")["day_offset"] == 0


def test_multi_turn_keeps_location():
    first = chat_engine.handle_chat(query="Will it rain in Guwahati today?")
    assert first.location is not None and first.location.name == "Guwahati"

    second = chat_engine.handle_chat(query="What about tomorrow?", session_id=first.session_id)
    assert second.location is not None and second.location.name == "Guwahati"
    assert second.session_id == first.session_id


def test_multi_turn_across_languages():
    """The spec's headline case: a Telugu follow-up to an English question."""
    first = chat_engine.handle_chat(query="Weather in Guwahati?")
    second = chat_engine.handle_chat(query="మరి ఎల్లుండి?", session_id=first.session_id)
    assert second.location is not None and second.location.name == "Guwahati"
    assert second.language == "te"
    assert second.answer.strip()


def test_two_rapid_follow_ups_in_one_session():
    first = chat_engine.handle_chat(query="Weather in Kochi?")
    second = chat_engine.handle_chat(query="And tomorrow?", session_id=first.session_id)
    third = chat_engine.handle_chat(query="What about the day after?", session_id=first.session_id)
    assert {second.location.name, third.location.name} == {"Kochi"}
    state = memory.get_session(first.session_id)
    assert len(state.turns) >= 6  # three user turns plus three answers


def test_profile_change_mid_session():
    first = chat_engine.handle_chat(query="Weather in Ratnagiri?", user_type="general")
    second = chat_engine.handle_chat(
        query="Weather in Ratnagiri?", session_id=first.session_id, user_type="fisherman"
    )
    assert second.user_type == "fisherman"


def test_profile_changes_advice_not_facts(scenario):
    """Profiles reprioritise wording; the measured risk must be identical."""
    scenario("storm")
    farmer = chat_engine.handle_chat(query="Weather in Mumbai?", user_type="farmer")
    fisher = chat_engine.handle_chat(query="Weather in Mumbai?", user_type="fisherman")
    assert farmer.risk.risk_score == fisher.risk.risk_score
    assert farmer.risk.detected_hazard == fisher.risk.detected_hazard
    if farmer.actions and fisher.actions:
        assert farmer.actions[0] != fisher.actions[0], "profile did not change prioritised advice"

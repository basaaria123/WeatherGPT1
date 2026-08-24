# -*- coding: utf-8 -*-
"""LLM request/response plumbing.

The live API is not reachable from CI, so these tests verify the two things
that would otherwise only fail in production: that the tool schemas satisfy
Anthropic's strict-tool-use rules, and that a realistic response object is
parsed correctly.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import chat_engine, llm


def _schemas():
    return [llm.EXTRACTION_TOOL, llm.COMPOSE_TOOL]


@pytest.mark.parametrize("tool", _schemas(), ids=lambda t: t["name"])
def test_strict_tool_schema_is_valid(tool):
    """Strict tool use requires additionalProperties:false and every key required."""
    assert tool.get("strict") is True
    schema = tool["input_schema"]
    assert schema["type"] == "object"
    assert schema.get("additionalProperties") is False
    assert set(schema["required"]) == set(schema["properties"]), (
        "strict mode requires every property to be listed in `required`"
    )
    assert tool.get("description"), "a tool without a description extracts poorly"


def test_extraction_enums_match_the_app_vocabulary():
    from app.schemas import USER_TYPES

    props = llm.EXTRACTION_TOOL["input_schema"]["properties"]
    assert set(props["user_type"]["enum"]) == set(USER_TYPES)
    assert "out_of_scope" in props["intent"]["enum"]
    assert props["day_offset"]["maximum"] == 6


def _response(blocks):
    return SimpleNamespace(content=blocks)


def test_tool_input_extracted_from_response():
    block = SimpleNamespace(type="tool_use", name="extract_weather_query", input={"intent": "forecast"})
    assert llm._tool_input(_response([block]), "extract_weather_query") == {"intent": "forecast"}


def test_tool_input_tolerates_a_json_string():
    """4.6-family models may escape tool input differently; parse, never string-match."""
    block = SimpleNamespace(type="tool_use", name="compose_weather_answer", input='{"answer": "ok"}')
    assert llm._tool_input(_response([block]), "compose_weather_answer") == {"answer": "ok"}


def test_tool_input_ignores_other_blocks():
    blocks = [
        SimpleNamespace(type="text", text="thinking out loud"),
        SimpleNamespace(type="tool_use", name="some_other_tool", input={"x": 1}),
    ]
    assert llm._tool_input(_response(blocks), "compose_weather_answer") is None


def test_text_extraction_joins_text_blocks():
    blocks = [
        SimpleNamespace(type="text", text="line one"),
        SimpleNamespace(type="tool_use", name="t", input={}),
        SimpleNamespace(type="text", text="line two"),
    ]
    assert llm._text(_response(blocks)) == "line one\nline two"


# --- Extraction sanitising -------------------------------------------------
def test_sanitise_rejects_non_dict():
    assert chat_engine._sanitise_extraction(None, fallback_language="en") is None
    assert chat_engine._sanitise_extraction("nope", fallback_language="en") is None


def test_sanitise_coerces_bad_values():
    clean = chat_engine._sanitise_extraction(
        {
            "in_scope": True,
            "intent": "nonsense",
            "location": "  Guwahati  ",
            "use_previous_location": False,
            "day_offset": 99,
            "user_type": "astronaut",
            "response_mode": "emergency",
            "language": "zz",
        },
        fallback_language="en",
    )
    assert clean["intent"] == "current_weather"
    assert clean["location"] == "Guwahati"
    assert clean["day_offset"] == 6
    assert clean["user_type"] == "general"
    # The model may never declare an emergency.
    assert clean["response_mode"] == "normal"
    assert clean["language"] == "en"


def test_sanitise_keeps_valid_values():
    clean = chat_engine._sanitise_extraction(
        {
            "in_scope": True,
            "intent": "climate_trend",
            "location": "Kochi",
            "use_previous_location": False,
            "day_offset": 2,
            "user_type": "fisherman",
            "response_mode": "simple",
            "language": "te",
        },
        fallback_language="en",
    )
    assert clean["intent"] == "climate_trend"
    assert clean["user_type"] == "fisherman"
    assert clean["response_mode"] == "simple"
    assert clean["language"] == "te"


# --- Full LLM path with a stubbed provider ---------------------------------
def test_full_llm_path_end_to_end(monkeypatch, scenario, bundle_for):
    """Exercise extraction → weather → risk → generation → verification."""
    scenario("flood")
    bundle = bundle_for("Guwahati")
    rain_24h = round(sum(h["precipitation_mm"] for h in bundle.hourly[:24]), 1)

    monkeypatch.setattr(llm, "available", lambda: True)
    monkeypatch.setattr(
        llm, "extract_query",
        lambda *a, **k: {
            "in_scope": True, "intent": "current_weather", "location": "Guwahati",
            "use_previous_location": False, "day_offset": 0, "user_type": "farmer",
            "response_mode": "normal", "language": "en",
        },
    )
    monkeypatch.setattr(
        llm, "compose_answer",
        lambda *a, **k: {
            "answer": f"Heavy flooding is likely in Guwahati — about {rain_24h} mm of rain is expected today. Move harvested grain to higher ground now.",
            "explanation": f"Based on {rain_24h} mm of forecast rainfall over 24 hours.",
            "actions": ["Move harvested grain to a dry, raised place.", "Avoid low-lying roads."],
            "action_mode": True,
        },
    )

    response = chat_engine.handle_chat(query="Will it flood in Guwahati?")
    assert response.degraded.llm_used is True
    assert response.verification.verified
    assert str(rain_24h) in response.answer
    assert response.user_type == "farmer"
    assert response.risk.detected_hazard == "Flood Risk"
    assert response.action_mode is True
    assert response.historical_comparison is not None

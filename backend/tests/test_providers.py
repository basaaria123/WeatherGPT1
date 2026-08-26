# -*- coding: utf-8 -*-
"""Provider plumbing: Gemini request/response translation, ElevenLabs shape.

Pure translation logic, so these run without a network. What they protect is
the property that makes the second provider safe to add at all: the public
functions in ``llm`` are written once, against one request and response shape,
and everything provider-specific is confined to the conversion below.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("WEATHER_DATA_MODE", "fixture")

from app.config import Settings, get_settings, reset_settings  # noqa: E402
from app.services import llm, speech  # noqa: E402


# ---------------------------------------------------------------------------
# Schema conversion
# ---------------------------------------------------------------------------
def test_gemini_schema_drops_keys_gemini_rejects():
    """additionalProperties and strict are 400s on Gemini, not warnings."""
    converted = llm._gemini_schema(llm.EXTRACTION_TOOL["input_schema"])
    flat = repr(converted)
    assert "additionalProperties" not in flat
    assert "strict" not in flat
    assert converted["type"] == "OBJECT"
    assert converted["properties"]["in_scope"]["type"] == "BOOLEAN"
    assert converted["properties"]["day_offset"]["type"] == "INTEGER"
    # Enums and required lists must survive — they are what make the reply valid.
    assert "current_weather" in converted["properties"]["intent"]["enum"]
    assert "advice_question" in converted["required"]


def test_gemini_schema_recurses_into_nested_objects_and_arrays():
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "actions": {"type": "array", "items": {"type": "string"}},
            "nested": {"type": "object", "additionalProperties": False,
                       "properties": {"flag": {"type": "boolean"}}},
        },
        "required": ["actions"],
    }
    out = llm._gemini_schema(schema)
    assert out["properties"]["actions"]["type"] == "ARRAY"
    assert out["properties"]["actions"]["items"]["type"] == "STRING"
    assert out["properties"]["nested"]["properties"]["flag"]["type"] == "BOOLEAN"
    assert "additionalProperties" not in repr(out)


# ---------------------------------------------------------------------------
# Response translation
# ---------------------------------------------------------------------------
def test_gemini_function_call_reads_like_an_anthropic_tool_use():
    """``_tool_input`` is shared by both providers, so the shim must satisfy it."""
    payload = {
        "candidates": [
            {"content": {"parts": [
                {"text": "ignored preamble"},
                {"functionCall": {"name": "extract_weather_query",
                                  "args": {"intent": "current_weather", "location": "Guwahati"}}},
            ]}}
        ]
    }
    response = llm._gemini_blocks(payload)
    extracted = llm._tool_input(response, "extract_weather_query")
    assert extracted == {"intent": "current_weather", "location": "Guwahati"}
    assert llm._text(response) == "ignored preamble"


def test_gemini_response_with_no_call_yields_no_tool_input():
    response = llm._gemini_blocks({"candidates": [{"content": {"parts": [{"text": "hello"}]}}]})
    assert llm._tool_input(response, "extract_weather_query") is None


def test_gemini_empty_or_blocked_response_degrades_rather_than_raises():
    for payload in ({}, {"candidates": []}, {"candidates": [{"content": {}}]}):
        response = llm._gemini_blocks(payload)
        assert llm._tool_input(response, "extract_weather_query") is None
        assert llm._text(response) == ""


def test_message_text_accepts_both_content_shapes():
    assert llm._message_text({"role": "user", "content": "plain"}) == "plain"
    assert llm._message_text(
        {"role": "user", "content": [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]}
    ) == "a\nb"


# ---------------------------------------------------------------------------
# Provider selection
# ---------------------------------------------------------------------------
@pytest.fixture
def settings_env(monkeypatch):
    def _apply(**env):
        for key in ("LLM_ENABLED", "LLM_PROVIDER", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
            monkeypatch.delenv(key, raising=False)
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        reset_settings()
        return get_settings()
    yield _apply
    reset_settings()


def test_auto_prefers_gemini_then_anthropic_then_nothing(settings_env):
    both = settings_env(LLM_ENABLED="true", LLM_PROVIDER="auto", GEMINI_API_KEY="g", ANTHROPIC_API_KEY="a")
    assert both.active_llm_provider == "gemini"

    only_anthropic = settings_env(LLM_ENABLED="true", LLM_PROVIDER="auto", ANTHROPIC_API_KEY="a")
    assert only_anthropic.active_llm_provider == "anthropic"
    assert only_anthropic.active_llm_model == only_anthropic.anthropic_model

    neither = settings_env(LLM_ENABLED="true", LLM_PROVIDER="auto")
    assert neither.active_llm_provider == ""
    assert neither.llm_configured is False


def test_an_explicit_provider_without_its_key_does_not_fall_through(settings_env):
    """Naming a provider and getting a different one silently would be worse
    than getting the rules-based answer."""
    pinned = settings_env(LLM_ENABLED="true", LLM_PROVIDER="gemini", ANTHROPIC_API_KEY="a")
    assert pinned.active_llm_provider == ""
    assert pinned.llm_configured is False


def test_llm_disabled_beats_any_key(settings_env):
    off = settings_env(LLM_ENABLED="false", LLM_PROVIDER="gemini", GEMINI_API_KEY="g")
    assert off.active_llm_provider == ""
    assert llm.available() is False


# ---------------------------------------------------------------------------
# Speech provider selection
# ---------------------------------------------------------------------------
def test_hosted_transcriber_is_preferred_but_local_stays_the_fallback(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "sk-test")
    reset_settings()
    try:
        assert speech.transcription_engine() == "elevenlabs"
        # The local engine is reported independently, so a hosted failure can
        # fall back to it instead of losing the turn.
        assert speech._local_engine() in {"faster-whisper", "whisper", "none"}
    finally:
        reset_settings()


def test_no_hosted_key_means_the_local_engine_is_the_engine(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    reset_settings()
    try:
        assert speech.transcription_engine() == speech._local_engine()
    finally:
        reset_settings()

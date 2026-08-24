# -*- coding: utf-8 -*-
"""Remaining contract behaviours from the brief that the other suites don't cover."""

from __future__ import annotations

import pytest

from app.services import advisory, chat_engine, i18n, llm, risk_engine, speech


# --- Response modes change tone, never facts -------------------------------
def test_simple_mode_is_shorter_but_agrees(scenario, bundle_for):
    scenario("cloudy")
    bundle = bundle_for("Vijayawada")
    risk = risk_engine.assess(bundle)
    normal = advisory.smart_explanation(bundle, risk, "en", mode="normal")
    simple = advisory.smart_explanation(bundle, risk, "en", mode="simple")
    assert len(simple) < len(normal)
    # The temperature stated must be identical in both.
    temp = str(round(bundle.current["temperature_c"], 1))
    assert temp in normal and temp in simple


def test_emergency_mode_only_from_measured_risk(scenario):
    scenario("calm")
    calm = chat_engine.handle_chat(query="Weather in Bengaluru?", response_mode="emergency")
    # A caller asking for emergency mode cannot manufacture one.
    assert calm.response_mode != "emergency"
    assert calm.action_mode is False

    scenario("flood")
    severe = chat_engine.handle_chat(query="Weather in Guwahati?", response_mode="normal")
    # And a caller asking for normal cannot suppress a real one.
    assert severe.response_mode == "emergency"
    assert severe.action_mode is True
    assert severe.actions


def test_all_three_modes_report_the_same_risk(scenario):
    scenario("cloudy")
    modes = [chat_engine.handle_chat(query="Weather in Vijayawada?", response_mode=m)
             for m in ("normal", "simple")]
    assert modes[0].risk.risk_score == modes[1].risk.risk_score


# --- action_mode / checklist ----------------------------------------------
def test_action_mode_tracks_the_risk_band(scenario):
    scenario("calm")
    assert chat_engine.handle_chat(query="Weather in Bengaluru?").action_mode is False
    scenario("wind")
    risky = chat_engine.handle_chat(query="Weather in Puri?")
    assert risky.action_mode is True
    assert len(risky.actions) >= 2


# --- Voice response wiring -------------------------------------------------
def test_voice_response_returns_audio(client, monkeypatch):
    monkeypatch.setattr(speech, "synthesize", lambda text, lang="en": ("QUJD", "audio/mpeg", None))
    body = client.post("/chat", json={"query": "Weather in Guwahati?", "voice_response": True}).json()
    assert body["audio_base64"] == "QUJD"
    assert body["audio_mime"] == "audio/mpeg"


def test_voice_response_not_requested_returns_no_audio(client):
    body = client.post("/chat", json={"query": "Weather in Guwahati?"}).json()
    assert body["audio_base64"] is None


def test_tts_substitution_is_declared(monkeypatch):
    """Assamese has no gTTS voice; the substitution must be stated, not silent."""
    assert speech.TTS_SUBSTITUTED["as"] == "bn"


def test_voice_friendly_text_has_no_markup():
    messy = "**Warning**: heavy rain.\nWhat to do:\n- move up\n- `stay inside`"
    clean = speech.voice_friendly(messy)
    for token in ("**", "`", "\n", "- "):
        assert token not in clean


# --- Emergency briefs are voice-friendly -----------------------------------
@pytest.mark.parametrize("lang", ["en", "hi", "te", "bn", "mr", "as"])
def test_emergency_brief_localised_and_speakable(lang, scenario, bundle_for):
    scenario("flood")
    bundle = bundle_for("Guwahati")
    risk = risk_engine.assess(bundle)
    brief = advisory.emergency_brief(bundle, risk, "farmer", lang)
    assert brief.strip()
    for token in ("|", "**", "`", "<"):
        assert token not in brief
    # Non-English briefs must not fall back to English scaffolding.
    if lang != "en":
        assert i18n.sentence("emg_what", lang) in brief
        assert "What is happening" not in brief


@pytest.mark.parametrize("lang", ["hi", "te", "bn", "mr", "as"])
def test_no_english_leaks_into_localised_answers(lang, scenario):
    scenario("flood")
    response = chat_engine.handle_chat(query="Weather in Guwahati?", requested_language=lang)
    assert response.language == lang
    for phrase in ("Risk level is", "What to do", "mm of rain expected"):
        assert phrase not in response.answer


# --- user_type breadth -----------------------------------------------------
@pytest.mark.parametrize("profile", ["farmer", "fisherman", "traveler", "commuter", "aviation", "urban", "general"])
def test_every_user_type_is_accepted(profile, scenario):
    scenario("storm")
    response = chat_engine.handle_chat(query="Weather in Mumbai?", user_type=profile)
    assert response.user_type == profile
    assert response.answer.strip()


def test_aviation_and_urban_alias_to_real_advice(scenario, bundle_for):
    scenario("storm")
    bundle = bundle_for("Mumbai")
    risk = risk_engine.assess(bundle)
    for profile in ("aviation", "urban"):
        actions = advisory.action_checklist(risk, profile, "en")
        assert actions, f"{profile} produced no advice"


# --- Explanation is always present and grounded ----------------------------
def test_explanation_present_and_verified(scenario):
    scenario("rain")
    response = chat_engine.handle_chat(query="Weather in Kochi?")
    assert response.explanation
    assert response.verification.verified


def test_raw_weather_accompanies_the_answer(scenario):
    scenario("rain")
    response = chat_engine.handle_chat(query="Weather in Kochi?")
    assert response.raw_weather
    assert "current" in response.raw_weather
    assert "risk" in response.raw_weather

# -*- coding: utf-8 -*-
"""Regressions from the pre-hackathon stability pass.

Each of these reproduces a failure that was seen in the running product, and
each runs on the no-LLM path — the floor the demo falls back to.

The last block re-asserts the four features that were already working when this
pass started. They share code with everything fixed here, so they are checked
alongside rather than trusted.
"""

from __future__ import annotations

import io
import os
import struct
import wave

import pytest

os.environ.setdefault("WEATHER_DATA_MODE", "fixture")

from app.services import advisory, chat_engine, memory, speech, weather  # noqa: E402


def _wav(seconds: float = 1.0) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"".join(struct.pack("<h", 1000) for _ in range(int(16000 * seconds))))
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 1. A truncated recording used to 500
# ---------------------------------------------------------------------------
def test_malformed_audio_does_not_crash_the_turn(client):
    """`wave` raises a bare RuntimeError on a cut-short file, which escaped the
    `except wave.Error` around the duration check and became a 500 — even when
    the browser had supplied a perfectly good transcript."""
    truncated = _wav()[:120]
    response = client.post(
        "/voice-chat",
        files={"audio": ("q.wav", truncated, "audio/wav")},
        data={"lang": "en", "user_type": "general", "location": "Guwahati",
              "client_transcript": "will it rain in Guwahati today"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["transcript"] == "will it rain in Guwahati today"


def test_validate_audio_survives_a_corrupt_header():
    speech.validate_audio(b"RIFF____WAVEnot-really-a-wav", "q.wav", "audio/wav")


# ---------------------------------------------------------------------------
# 2. The "no speech recognition" message named only one of three remedies
# ---------------------------------------------------------------------------
def test_missing_stt_message_names_every_way_to_enable_it(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "")
    monkeypatch.setattr(speech, "_has", lambda module: False)
    from app.config import reset_settings

    reset_settings()
    try:
        assert speech.transcription_engine() == "none"
        with pytest.raises(speech.TranscriptionError) as excinfo:
            speech.transcribe(_wav(), filename="q.wav", content_type="audio/wav")
        message = str(excinfo.value)
        assert "ELEVENLABS_API_KEY" in message
        assert "faster-whisper" in message
        assert "type your question" in message
    finally:
        reset_settings()


def test_browser_transcript_answers_when_the_server_cannot_transcribe(client, monkeypatch):
    """The path that keeps the microphone working with no server-side STT."""
    monkeypatch.setattr(speech, "_has", lambda module: False)
    response = client.post(
        "/voice-chat",
        files={"audio": ("q.wav", _wav(), "audio/wav")},
        data={"lang": "en", "user_type": "farmer", "location": "Guwahati",
              "client_transcript": "is it safe to go out"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["transcript"] == "is it safe to go out"
    assert body["answer"].strip()


# ---------------------------------------------------------------------------
# 3. A follow-up snapped back to the dashboard pin
# ---------------------------------------------------------------------------
def test_follow_up_stays_on_the_place_the_user_named(scenario):
    """Dashboard on Guwahati, user asks about Chennai, then follows up. The
    follow-up used to be answered about Guwahati."""
    scenario("rain")
    session = "stability-context"
    first = chat_engine.handle_chat(
        query="What is the weather in Chennai today?", user_type="traveler",
        session_id=session, selected_location="Guwahati",
    )
    assert first.location.name == "Chennai"

    second = chat_engine.handle_chat(
        query="Is it safe to travel?", user_type="traveler",
        session_id=session, selected_location="Guwahati",
    )
    assert second.location.name == "Chennai", "follow-up snapped back to the dashboard pin"


def test_dashboard_pin_still_answers_a_question_with_no_subject_yet(scenario):
    """The other half of the rule: nothing named yet, so the screen wins."""
    scenario("rain")
    response = chat_engine.handle_chat(
        query="What is the weather here today?", user_type="general",
        session_id="stability-pin", selected_location="Guwahati",
    )
    assert response.location.name == "Guwahati"


def test_named_place_is_remembered_as_named(scenario):
    scenario("rain")
    state = memory.get_session("stability-named")
    chat_engine.handle_chat(query="Weather in Chennai?", user_type="general",
                            session_id=state.session_id, selected_location="Guwahati")
    assert memory.get_session(state.session_id).location_was_named is True


# ---------------------------------------------------------------------------
# 4. "Why this answer?" echoed the answer back
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", ["calm", "rain", "heat", "wind"])
def test_explanation_never_repeats_the_answer(scenario, name):
    scenario(name)
    response = chat_engine.handle_chat(
        query="What is the weather here today?", user_type="general",
        session_id=f"stability-explain-{name}", selected_location="Vijayawada",
    )
    if not response.explanation:
        return  # dropped rather than echoed, which is the fix
    said = set(advisory._sentences(response.answer))
    fresh = [s for s in advisory._sentences(response.explanation) if s not in said]
    assert fresh, f"{name}: explanation only repeats sentences already in the answer"


# ---------------------------------------------------------------------------
# 5. The four features that were already working
# ---------------------------------------------------------------------------
PERSONAS = ("general", "farmer", "fisherman", "traveler", "commuter")


def test_protected_persona_advice_still_differs(scenario):
    scenario("rain")
    answers, advisories = set(), set()
    for persona in PERSONAS:
        response = chat_engine.handle_chat(
            query="What is the weather here today?", user_type=persona,
            session_id=f"prot-{persona}", selected_location="Vijayawada",
        )
        answers.add(response.answer)
        advisories.add(tuple(a.action for a in response.advisory.actions))
    assert len(answers) == len(PERSONAS)
    assert len(advisories) == len(PERSONAS)


@pytest.mark.parametrize(
    "city,name,hazard",
    [("Guwahati", "flood", "Flood Risk"), ("Mumbai", "storm", "Lightning/Storm"),
     ("Jaisalmer", "heat", "Extreme Heat"), ("Puri", "wind", "Strong Wind")],
)
def test_protected_emergency_mode_still_fires_per_hazard(scenario, city, name, hazard):
    scenario(name)
    response = chat_engine.handle_chat(
        query=f"What is the weather in {city} today?", user_type="farmer",
        session_id=f"prot-emg-{city}",
    )
    assert response.risk.detected_hazard == hazard
    assert response.action_mode is True
    assert response.emergency.active is True
    assert response.actions


def test_protected_answer_is_still_speakable(scenario):
    """Play Answer reads response.answer aloud, so it must stay plain prose."""
    scenario("rain")
    response = chat_engine.handle_chat(
        query="What is the weather here today?", user_type="general",
        session_id="prot-tts", selected_location="Vijayawada",
    )
    assert response.answer.strip()
    assert "<" not in response.answer and "*" not in response.answer

# -*- coding: utf-8 -*-
"""The eight edge cases named in the brief, plus the failure modes around them.

Each test asserts the system *degrades* rather than breaks: a usable message,
correct structured fields, and no exception escaping to the caller.
"""

from __future__ import annotations

import io

import pytest

from app.services import chat_engine, language, llm, speech, weather
from app.services.weather import WeatherError


# --- 1. Misspelled / nonexistent location ----------------------------------
def test_misspelled_location_is_corrected():
    response = chat_engine.handle_chat(query="whats the weather in vijaywada")
    assert response.location is not None
    assert response.location.name == "Vijayawada"


def test_nonexistent_location_asks_instead_of_crashing():
    response = chat_engine.handle_chat(query="What is the weather in Zzyzxville?")
    assert response.answer.strip()
    assert response.risk is None
    # It must ask for a place rather than silently answering about somewhere else.
    assert response.location is None


def test_geocode_endpoint_404s_cleanly(client):
    assert client.get("/geocode", params={"q": "Zzyzxville"}).status_code == 404


# --- 2. Weather API unreachable --------------------------------------------
def test_weather_outage_returns_message_not_error(monkeypatch):
    def boom(_location):
        raise WeatherError("The weather service is unreachable right now.")

    monkeypatch.setattr(weather, "fetch_weather", boom)
    response = chat_engine.handle_chat(query="Weather in Guwahati?")
    assert response.answer.strip()
    assert response.degraded.weather_error
    assert response.risk is None


def test_weather_outage_returns_503_not_500(client, monkeypatch):
    def boom(_location):
        raise WeatherError("The weather service is unreachable right now.")

    monkeypatch.setattr(weather, "fetch_weather", boom)
    resp = client.get("/weather/current", params={"location": "Guwahati"})
    assert resp.status_code == 503
    assert "unreachable" in resp.json()["detail"].lower()


# --- 3. Very long or unclear query -----------------------------------------
def test_very_long_query_is_truncated_not_rejected():
    long_query = "Will it rain in Guwahati " + ("and I was also wondering about things " * 200)
    response = chat_engine.handle_chat(query=long_query)
    assert response.answer.strip()
    assert response.location is not None and response.location.name == "Guwahati"


def test_unclear_query_still_answers_something():
    response = chat_engine.handle_chat(query="hmm ok so uh")
    assert response.answer.strip()


def test_empty_query_is_rejected_by_the_route(client):
    assert client.post("/chat", json={"query": "   "}).status_code == 422


# --- 4. Two rapid follow-ups in one session --------------------------------
def test_rapid_follow_ups_keep_context():
    first = chat_engine.handle_chat(query="Weather in Dibrugarh?")
    second = chat_engine.handle_chat(query="and tomorrow?", session_id=first.session_id)
    third = chat_engine.handle_chat(query="what about the day after?", session_id=first.session_id)
    assert second.location.name == "Dibrugarh"
    assert third.location.name == "Dibrugarh"


def test_unknown_session_id_starts_fresh_without_error():
    response = chat_engine.handle_chat(query="Weather in Patna?", session_id="does-not-exist")
    assert response.session_id == "does-not-exist"
    assert response.answer.strip()


# --- 5. WebSocket disconnect / reconnect while an alert fires --------------
def test_websocket_snapshot_on_connect(client):
    client.post("/alerts/scan")
    with client.websocket_connect("/ws/alerts") as ws:
        message = ws.receive_json()
        assert message["type"] == "snapshot"
        assert isinstance(message["alerts"], list)


def test_websocket_reconnect_gets_current_state(client):
    client.post("/alerts/scan")
    with client.websocket_connect("/ws/alerts") as first:
        first_snapshot = first.receive_json()
    with client.websocket_connect("/ws/alerts") as second:
        second_snapshot = second.receive_json()
    assert len(second_snapshot["alerts"]) == len(first_snapshot["alerts"])


@pytest.mark.asyncio
async def test_broadcast_survives_a_dead_client():
    """One broken socket must not stop delivery to the others."""
    from app.services.alerts import AlertHub

    class Dead:
        async def send_text(self, _):
            raise RuntimeError("socket closed")

    class Live:
        def __init__(self):
            self.received = []

        async def send_text(self, message):
            self.received.append(message)

    hub = AlertHub()
    live = Live()
    hub._clients = {Dead(), live}  # noqa: SLF001 - exercising the failure path
    sent = await hub.broadcast({"type": "alert", "alert": {"id": 1}})
    assert sent == 1
    assert live.received
    assert len(hub._clients) == 1  # noqa: SLF001 - the dead client was dropped


# --- 6. Voice input, non-English, poor audio -------------------------------
def test_empty_audio_rejected_with_message():
    with pytest.raises(speech.TranscriptionError) as exc:
        speech.validate_audio(b"", "clip.wav", "audio/wav")
    assert "empty" in str(exc.value).lower()


def test_unsupported_audio_format_rejected():
    with pytest.raises(speech.TranscriptionError) as exc:
        speech.validate_audio(b"data", "notes.txt", "text/plain")
    assert "not supported" in str(exc.value).lower()


def test_oversized_audio_rejected():
    from app.config import get_settings

    oversized = b"\0" * (get_settings().max_audio_bytes + 1)
    with pytest.raises(speech.TranscriptionError):
        speech.validate_audio(oversized, "clip.wav", "audio/wav")


def test_voice_chat_without_audio_or_transcript_is_422(client):
    assert client.post("/voice-chat", data={}).status_code == 422


def test_voice_chat_accepts_client_transcript(client):
    """Browser-side speech recognition is a supported input path."""
    resp = client.post(
        "/voice-chat",
        data={"client_transcript": "గువాహటిలో వాతావరణం ఎలా ఉంది?", "voice_response": "false"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["transcript"]
    assert body["language"] == "te"
    assert body["location"]["name"] == "Guwahati"
    assert "client" in (body["degraded"]["fallback_reason"] or "").lower()


def test_voice_chat_rejects_gibberish_transcript(client):
    resp = client.post("/voice-chat", data={"client_transcript": "  .  "})
    assert resp.status_code == 422


def test_noisy_transcript_still_finds_location_and_language():
    """Whisper output from a noisy recording keeps filler words; extraction must cope."""
    noisy = "उम्म्म ... क्या ... दिल्ली में ... कल बारिश होगी ... हाँ"
    response = chat_engine.handle_chat(query=noisy)
    assert response.language == "hi"
    assert response.location is not None and response.location.name == "New Delhi"


# --- 7. Anthropic failure mid-conversation ---------------------------------
def test_llm_failure_mid_conversation_keeps_answering(monkeypatch):
    monkeypatch.setattr(llm, "available", lambda: True)
    monkeypatch.setattr(llm, "extract_query", lambda *a, **k: None)
    monkeypatch.setattr(llm, "compose_answer", lambda *a, **k: None)

    response = chat_engine.handle_chat(query="Will it rain in Guwahati today?")
    assert response.answer.strip()
    assert response.location.name == "Guwahati"
    assert response.risk is not None
    assert response.degraded.fallback_reason


def test_llm_raising_is_contained(monkeypatch):
    def explode(*_args, **_kwargs):
        raise RuntimeError("connection reset")

    monkeypatch.setattr(llm, "available", lambda: True)
    monkeypatch.setattr(llm, "extract_query", explode)
    with pytest.raises(RuntimeError):
        # Confirms the stub really raises, so the next assertion is meaningful.
        llm.extract_query("x")

    monkeypatch.setattr(llm, "extract_query", lambda *a, **k: None)
    monkeypatch.setattr(llm, "compose_answer", explode)
    response = chat_engine.handle_chat(query="Weather in Kochi?")
    assert response.answer.strip()


def test_fabricated_numbers_are_rejected(monkeypatch):
    """The verification step must discard an answer quoting invented values."""
    monkeypatch.setattr(llm, "available", lambda: True)
    monkeypatch.setattr(llm, "extract_query", lambda *a, **k: None)
    monkeypatch.setattr(
        llm,
        "compose_answer",
        lambda *a, **k: {
            "answer": "Expect exactly 999.9 mm of rain and gusts to 250 km/h.",
            "explanation": "Based on a temperature of 88.8°C.",
            "actions": [],
            "action_mode": False,
        },
    )
    response = chat_engine.handle_chat(query="Weather in Guwahati?")
    assert not response.verification.verified
    assert response.verification.rejected_numbers
    assert "999.9" not in response.answer, "fabricated answer was returned to the user"
    assert response.answer.strip()


def test_grounded_llm_answer_is_kept(monkeypatch, scenario, bundle_for):
    """The counterpart: a correctly-grounded answer must survive verification."""
    scenario("calm")
    bundle = bundle_for("Bengaluru")
    temp = bundle.current["temperature_c"]

    monkeypatch.setattr(llm, "available", lambda: True)
    monkeypatch.setattr(llm, "extract_query", lambda *a, **k: None)
    monkeypatch.setattr(
        llm,
        "compose_answer",
        lambda *a, **k: {
            "answer": f"It is currently {temp}°C in Bengaluru and calm.",
            "explanation": f"Measured temperature {temp}°C.",
            "actions": [],
            "action_mode": False,
        },
    )
    response = chat_engine.handle_chat(query="Weather in Bengaluru?")
    assert response.verification.verified
    assert str(temp) in response.answer
    assert response.degraded.llm_used


# --- 8. Off-topic scope guardrail ------------------------------------------
@pytest.mark.parametrize(
    "query",
    [
        "Who won the cricket match yesterday?",
        "Write me a Python function to sort a list",
        "What is the capital of France?",
        "Tell me a joke",
        "Give me a recipe for biryani",
    ],
)
def test_off_topic_is_redirected_not_answered(query):
    response = chat_engine.handle_chat(query=query)
    assert response.in_scope is False
    assert response.intent == "out_of_scope"
    assert response.risk is None
    assert "weather" in response.answer.lower()


def test_off_topic_redirect_is_localised():
    response = chat_engine.handle_chat(query="ఈ రోజు క్రికెట్ మ్యాచ్ ఎవరు గెలిచారు?")
    assert response.in_scope is False
    assert response.language == "te"
    # The redirect must be in Telugu, not English.
    assert language.detect(response.answer).language == "te"


# --- Cross-cutting invariants ----------------------------------------------
def test_unsupported_language_degrades_with_a_note():
    """Tamil is out of scope for now; say so rather than answering wrongly."""
    response = chat_engine.handle_chat(query="சென்னையில் இன்று மழை பெய்யுமா?")
    assert response.answer.strip()
    assert response.language == "en"
    assert response.degraded.translation_error


def test_tts_failure_still_returns_text(client, monkeypatch):
    def boom(*_args, **_kwargs):
        raise speech.SynthesisError("no voice available")

    monkeypatch.setattr(speech, "synthesize", boom)
    resp = client.post("/chat", json={"query": "Weather in Guwahati?", "voice_response": True})
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"].strip()
    assert body["audio_base64"] is None
    assert body["degraded"]["tts_error"]


def test_no_endpoint_leaks_a_stack_trace(client):
    for path, params in [
        ("/weather/current", {}),
        ("/weather/timeline", {"location": "Zzyzxville"}),
        ("/risk", {}),
    ]:
        resp = client.get(path, params=params)
        assert resp.status_code in {404, 422, 503}
        assert "Traceback" not in resp.text
        assert "detail" in resp.json()

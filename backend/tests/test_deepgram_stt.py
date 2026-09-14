# -*- coding: utf-8 -*-
"""Deepgram, and the endpoint that exists so the browser never holds its key.

The live endpoint is unreachable from this environment, so these exercise the
driver against the response shapes Deepgram documents — which is the part that
can actually be wrong in this repository. What cannot be tested here is whether
Deepgram still answers at that path; what can be, and is, is that a correct
answer is read correctly and that every wrong one becomes a `TranscriptionError`
rather than a crash or a silent empty transcript.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import reset_settings
from app.main import app
from app.services import speech

client = TestClient(app)

OK_BODY = {
    "results": {
        "channels": [
            {
                "detected_language": "hi-IN",
                "alternatives": [{"transcript": "  क्या आज बारिश होगी?  ", "confidence": 0.94}],
            }
        ]
    }
}

# Enough bytes, and a header, to get past `validate_audio`.
AUDIO = b"\x1a\x45\xdf\xa3" + b"\x00" * 4000


@pytest.fixture
def deepgram(monkeypatch):
    """A configured key, and a captured request instead of a real one."""
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-key-not-a-real-one")
    monkeypatch.setenv("DEEPGRAM_LANGUAGES", "en,hi")
    reset_settings()

    captured: dict = {}
    body: dict = dict(OK_BODY)

    def fake_post(url, **kwargs):
        captured.clear()
        captured["url"] = url
        captured.update(kwargs)
        return httpx.Response(200, json=body, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)
    yield captured, body
    reset_settings()


# --- The chain -------------------------------------------------------------
def test_deepgram_leads_the_chain_when_configured(deepgram):
    assert speech.transcription_engine() == "deepgram"
    assert speech.transcription_chain()[0] == "deepgram"
    assert speech.deepgram_stt_available() is True


def test_no_key_means_deepgram_is_not_offered(monkeypatch):
    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)
    reset_settings()
    assert "deepgram" not in speech.transcription_chain()
    assert speech.deepgram_stt_available() is False
    reset_settings()


# --- The request -----------------------------------------------------------
def test_the_key_travels_in_a_header_and_the_audio_in_the_body(deepgram):
    captured, _ = deepgram
    speech._deepgram_transcribe(AUDIO, filename="q.webm", content_type="audio/webm", language="hi")

    assert captured["url"].endswith("/v1/listen")
    assert captured["headers"]["Authorization"].startswith("Token ")
    # Deepgram takes the audio as the raw body, not as a multipart part. Sending
    # it as `files=` returns a 400 that reads like an audio problem.
    assert captured["content"] == AUDIO
    assert "files" not in captured
    assert captured["headers"]["Content-Type"] == "audio/webm"


def test_a_known_language_is_named_and_an_unknown_one_is_detected(deepgram):
    captured, _ = deepgram

    speech._deepgram_transcribe(AUDIO, filename="q.webm", content_type="audio/webm", language="hi")
    assert captured["params"]["language"] == "hi"
    assert "detect_language" not in captured["params"]

    # Assamese is not in the configured set. Naming a code the model does not
    # know is a 400; asking it to detect is slower and always valid.
    speech._deepgram_transcribe(AUDIO, filename="q.webm", content_type="audio/webm", language="as")
    assert captured["params"]["detect_language"] == "true"
    assert "language" not in captured["params"]


# --- The response ----------------------------------------------------------
def test_the_transcript_is_read_from_the_path_deepgram_actually_uses(deepgram):
    """results.channels[0].alternatives[0].transcript, four levels down.

    A naive `payload["transcript"]` returns None for a perfectly good response,
    which surfaces to the reader as "I could not hear anything" for audio the
    recogniser heard correctly.
    """
    result = speech._deepgram_transcribe(
        AUDIO, filename="q.webm", content_type="audio/webm", language="hi"
    )
    assert result.text == "क्या आज बारिश होगी?"
    assert result.language == "hi"
    assert result.confidence == pytest.approx(0.94)
    assert result.engine == "deepgram"


@pytest.mark.parametrize(
    "body",
    [
        {"results": {"channels": [{"alternatives": [{"transcript": "   "}]}]}},
        {"results": {"channels": []}},
        {"results": {}},
        {"error": "nope"},
        {},
    ],
)
def test_every_unusable_response_is_an_error_not_an_empty_string(deepgram, monkeypatch, body):
    """Nothing here may return successfully with no text.

    An empty transcript that reaches the interface writes an empty value over
    whatever the reader could see, which is worse than an error: it looks like
    the app deleted their words.
    """
    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, **kw: httpx.Response(200, json=body, request=httpx.Request("POST", url)),
    )
    with pytest.raises(speech.TranscriptionError):
        speech._deepgram_transcribe(
            AUDIO, filename="q.webm", content_type="audio/webm", language="en"
        )


def test_a_network_failure_does_not_leak_the_request(deepgram, monkeypatch):
    def boom(url, **kw):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "post", boom)
    with pytest.raises(speech.TranscriptionError) as excinfo:
        speech._deepgram_transcribe(
            AUDIO, filename="q.webm", content_type="audio/webm", language="en"
        )
    assert "test-key" not in str(excinfo.value)


def test_deepgram_failing_falls_through_rather_than_losing_the_turn(deepgram, monkeypatch):
    """The chain exists so one provider being down is not the end of the turn."""
    monkeypatch.setattr(httpx, "post", lambda url, **kw: (_ for _ in ()).throw(httpx.ConnectError("x")))
    # No other provider is configured in the test environment, so this surfaces
    # as a TranscriptionError — the point is that it is *that*, with a sentence,
    # rather than the httpx exception escaping.
    with pytest.raises(speech.TranscriptionError):
        speech.transcribe(AUDIO, filename="q.webm", content_type="audio/webm", language="en")


# --- The endpoint ----------------------------------------------------------
def test_transcribe_endpoint_returns_the_words_and_nothing_else(deepgram):
    response = client.post(
        "/api/transcribe",
        files={"audio": ("q.webm", AUDIO, "audio/webm")},
        data={"lang": "hi"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["transcript"] == "क्या आज बारिश होगी?"
    assert body["engine"] == "deepgram"
    # Not a chat response: this endpoint answers nothing, and a shape carrying
    # an empty answer would invite a client to render one.
    assert "answer" not in body
    assert "advisory" not in body


def test_the_endpoint_never_puts_provider_configuration_on_the_wire(deepgram, monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda url, **kw: (_ for _ in ()).throw(httpx.ConnectError("x")))
    response = client.post(
        "/api/transcribe",
        files={"audio": ("q.webm", AUDIO, "audio/webm")},
        data={"lang": "en"},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "stt_unavailable"
    blob = response.text.lower()
    for secret in ("deepgram_api_key", "test-key", "api.deepgram.com", "faster-whisper", "token "):
        assert secret not in blob, secret

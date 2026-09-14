# -*- coding: utf-8 -*-
"""Why the microphone failed, as something the client can act on.

The bug these exist to keep fixed: every way speech-to-text could fail arrived
at the browser as one code and one sentence — "Speech recognition is unavailable
right now" — whether no provider was configured, a configured provider had just
returned 401, the upload was not audio, or the reader had simply said nothing.

That is not a wording problem. The client has a real decision to make on this
answer: when the server cannot transcribe *at all*, it should stop spending
recordings on it and give the microphone to the browser's own recogniser, which
needs no key and no round trip. It cannot make that decision from prose, and it
must not make it after a reader says nothing into a working recogniser.

So each situation carries its own code, and these tests are what keep them from
collapsing back into one.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import reset_settings
from app.main import app
from app.services import speech

client = TestClient(app)

# Enough bytes, and a plausible header, to get past `validate_audio`.
AUDIO = b"\x1a\x45\xdf\xa3" + b"\x00" * 4000


@pytest.fixture
def no_providers(monkeypatch):
    """A serverless deployment as actually shipped: no key, no on-device engine.

    `requirements-voice.txt` is deliberately not installed on serverless hosts,
    so this is not a broken machine — it is the normal state of the deployed
    product, and the one the reader in the bug report was talking to.
    """
    for name in ("DEEPGRAM_API_KEY", "SARVAM_API_KEY", "ELEVENLABS_API_KEY", "PUTER_TOKEN"):
        monkeypatch.setenv(name, "")
    monkeypatch.setattr(speech, "_has", lambda module: False)
    speech.note_transcription_result(True)  # clear any latch from another test
    reset_settings()
    yield
    reset_settings()


@pytest.fixture
def provider_that_fails(monkeypatch):
    """A key IS set, and the provider behind it refuses every call."""
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-key")
    for name in ("SARVAM_API_KEY", "ELEVENLABS_API_KEY", "PUTER_TOKEN"):
        monkeypatch.setenv(name, "")
    monkeypatch.setattr(speech, "_has", lambda module: False)
    monkeypatch.setattr(
        httpx, "post", lambda url, **kw: (_ for _ in ()).throw(httpx.ConnectError("refused"))
    )
    speech.note_transcription_result(True)
    reset_settings()
    yield
    reset_settings()


# --- nothing configured ----------------------------------------------------
def test_no_provider_and_no_engine_is_named_as_such(no_providers):
    with pytest.raises(speech.TranscriptionError) as excinfo:
        speech.transcribe(AUDIO, filename="q.webm", content_type="audio/webm")
    assert excinfo.value.code == "stt_not_configured"


def test_the_operator_is_told_what_to_set(no_providers):
    """The message goes to the log, so it names remedies rather than being tidy.

    Every provider the chain will actually try has to appear: naming only one of
    four is how an operator comes to believe the product needs the one key they
    do not have.
    """
    with pytest.raises(speech.TranscriptionError) as excinfo:
        speech.transcribe(AUDIO, filename="q.webm", content_type="audio/webm")
    message = str(excinfo.value)
    for remedy in ("DEEPGRAM_API_KEY", "SARVAM_API_KEY", "ELEVENLABS_API_KEY", "PUTER_TOKEN"):
        assert remedy in message, remedy
    assert "faster-whisper" in message


def test_that_message_never_reaches_the_browser(no_providers):
    """The remedies are for the log. The wire gets a sentence and a code."""
    response = client.post(
        "/api/transcribe", files={"audio": ("q.webm", AUDIO, "audio/webm")}, data={"lang": "en"}
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "stt_not_configured"
    blob = response.text.lower()
    for secret in ("deepgram_api_key", "elevenlabs_api_key", "puter_token", "faster-whisper"):
        assert secret not in blob, secret


# --- configured and failing ------------------------------------------------
def test_a_configured_provider_that_fails_is_not_called_unconfigured(provider_that_fails):
    """These need different answers from an operator, so they get different codes.

    One means "set a key". The other means "the key you set is not working" —
    and sending somebody looking for a missing key that is not missing is the
    most expensive kind of wrong error message.
    """
    with pytest.raises(speech.TranscriptionError) as excinfo:
        speech.transcribe(AUDIO, filename="q.webm", content_type="audio/webm")
    assert excinfo.value.code == "stt_provider_failed"


def test_the_failure_is_visible_in_health_without_leaking_anything(provider_that_fails):
    """"It does not work" becomes "Deepgram is refusing the connection"."""
    with pytest.raises(speech.TranscriptionError):
        speech.transcribe(AUDIO, filename="q.webm", content_type="audio/webm")

    reported = speech.capabilities()["transcription_last_error"]
    assert reported["provider"] == "deepgram"
    assert reported["reason"]

    body = client.get("/api/health").text.lower()
    for secret in ("test-key", "deepgram_api_key", "api.deepgram.com"):
        assert secret not in body, secret


def test_a_success_clears_the_last_error(provider_that_fails, monkeypatch):
    """Otherwise /health accuses a provider that has since started working."""
    with pytest.raises(speech.TranscriptionError):
        speech.transcribe(AUDIO, filename="q.webm", content_type="audio/webm")
    assert speech.capabilities()["transcription_last_error"] is not None

    speech.note_transcription_result(True)
    assert speech.capabilities()["transcription_last_error"] is None


# --- the reader's own doing ------------------------------------------------
def test_silence_is_not_reported_as_a_broken_recogniser(no_providers, monkeypatch):
    """A working recogniser that heard nothing must not look like a dead one.

    This is the code that would otherwise make the client give up on the server
    because somebody tapped the microphone twice by accident.
    """
    monkeypatch.setattr(speech, "_has", lambda module: module == "faster_whisper")
    monkeypatch.setattr(speech, "_load_model", lambda: (_Silent(), "faster-whisper"))
    reset_settings()
    with pytest.raises(speech.TranscriptionError) as excinfo:
        speech.transcribe(AUDIO, filename="q.webm", content_type="audio/webm")
    assert excinfo.value.code == "stt_no_speech"


def test_an_unusable_upload_is_its_own_code():
    with pytest.raises(speech.TranscriptionError) as excinfo:
        speech.transcribe(b"", filename="q.webm", content_type="audio/webm")
    assert excinfo.value.code == "stt_bad_audio"

    with pytest.raises(speech.TranscriptionError) as excinfo:
        speech.transcribe(AUDIO, filename="q.txt", content_type="text/plain")
    assert excinfo.value.code == "stt_bad_audio"


# --- the client/server agreement on file names -----------------------------
def test_every_extension_the_client_can_send_is_accepted():
    """`extensionFor()` in ChatPanel.jsx produces exactly these.

    `.aac` was missing from the server's list while the client could still name
    a recording `question.aac` — Safari offers `audio/aac` in the MediaRecorder
    fallback chain — so that recording was rejected before a provider was tried.
    """
    for ext in ("webm", "ogg", "m4a", "aac", "mp3", "wav"):
        assert f".{ext}" in speech.ALLOWED_AUDIO_SUFFIXES, ext


class _Silent:
    """A recogniser that starts fine and hears nothing."""

    def transcribe(self, path, **kwargs):  # noqa: D102 - matches faster-whisper
        return [], type("Info", (), {"language": "en", "language_probability": 0.0})()

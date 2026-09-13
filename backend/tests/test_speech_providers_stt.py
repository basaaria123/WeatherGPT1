# -*- coding: utf-8 -*-
"""Puter as a transcription provider, and the one thing that must never happen.

A Puter auth token is a full-access account credential with no expiry. The
SDK's normal home is the browser; this app calls the driver endpoint from the
server instead, and the test that matters most here is the one asserting the
token cannot reach a client.
"""

from __future__ import annotations

import json

import pytest

from app.config import reset_settings
from app.services import speech

TOKEN = "test-token-not-a-real-one"


@pytest.fixture
def with_puter(monkeypatch):
    monkeypatch.setenv("PUTER_TOKEN", TOKEN)
    monkeypatch.setenv("ELEVENLABS_API_KEY", "")
    reset_settings()
    yield
    reset_settings()


# --- The token stays on the server ------------------------------------------

def test_the_token_is_not_in_anything_the_client_receives(with_puter):
    """/health drives the UI. It may say whether Puter is on; never which token."""
    payload = json.dumps(speech.capabilities())
    assert TOKEN not in payload
    assert "puter_token" not in payload
    # Configured-or-not is the only thing a client needs to know.
    assert speech.capabilities()["puter_configured"] is True


def test_the_token_is_not_in_the_frontend_source():
    """The whole reason this provider is server-side."""
    from pathlib import Path

    frontend = Path(__file__).resolve().parents[2] / "frontend" / "src"
    for path in frontend.rglob("*.js*"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert "PUTER_TOKEN" not in text, path
        assert "puter" not in text.lower() or "puter.ai" not in text.lower(), path


# --- Where it sits in the chain ----------------------------------------------

def test_puter_is_tried_under_elevenlabs_not_over_it(monkeypatch):
    """ElevenLabs' request shape is verified against a live endpoint. This one
    is not, so it sits beneath rather than in front of it."""
    monkeypatch.setenv("PUTER_TOKEN", TOKEN)
    monkeypatch.setenv("ELEVENLABS_API_KEY", "some-key")
    reset_settings()
    chain = speech.transcription_chain()
    reset_settings()
    assert chain.index("elevenlabs") < chain.index("puter")


def test_no_token_means_the_provider_does_not_exist(monkeypatch):
    monkeypatch.setenv("PUTER_TOKEN", "")
    reset_settings()
    assert "puter" not in speech.transcription_chain()
    assert speech.puter_stt_available() is False
    reset_settings()


def test_a_configured_token_makes_voice_input_available(with_puter):
    assert speech.puter_stt_available() is True
    assert "puter" in speech.transcription_chain()


# --- Reading the reply -------------------------------------------------------

@pytest.mark.parametrize(
    "payload,expected",
    [
        ("just the text", "just the text"),
        ({"result": "wrapped text"}, "wrapped text"),
        ({"success": True, "result": {"text": "nested text"}}, "nested text"),
        ({"text": "flat text"}, "flat text"),
        ({"result": {"transcript": "other key"}}, "other key"),
        ({"success": False, "error": "nope"}, ""),
        ({}, ""),
        (None, ""),
    ],
)
def test_the_transcript_is_found_whatever_shape_it_arrives_in(payload, expected):
    """Driver replies are wrapped, and the wrapper has changed before."""
    assert speech._puter_text(payload) == expected


def test_an_unreachable_provider_costs_a_log_line_not_the_question(with_puter, monkeypatch):
    """The point of a chain: a provider that fails is skipped, not fatal."""
    import httpx

    def boom(*args, **kwargs):
        raise httpx.ConnectError("unreachable")

    monkeypatch.setattr(httpx, "post", boom)
    with pytest.raises(speech.TranscriptionError):
        speech._puter_transcribe(b"x" * 64, filename="q.webm", content_type="audio/webm", language="en")


def test_the_failure_message_does_not_carry_the_token(with_puter, monkeypatch):
    import httpx

    def boom(*args, **kwargs):
        raise httpx.HTTPError(f"bad request to {kwargs.get('url', '')}")

    monkeypatch.setattr(httpx, "post", boom)
    try:
        speech._puter_transcribe(b"x" * 64, filename="q.webm", content_type="audio/webm", language="en")
    except speech.TranscriptionError as exc:
        assert TOKEN not in str(exc)
        assert TOKEN not in repr(exc.__cause__ or "")


# --- Sarvam ------------------------------------------------------------------

SARVAM_KEY = "sk_test_not_a_real_one"


@pytest.fixture
def with_sarvam(monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", SARVAM_KEY)
    monkeypatch.setenv("ELEVENLABS_API_KEY", "")
    monkeypatch.setenv("PUTER_TOKEN", "")
    reset_settings()
    yield
    reset_settings()


def test_sarvam_leads_the_chain(monkeypatch):
    """An app that answers in eleven Indian languages asks the Indic model first."""
    monkeypatch.setenv("SARVAM_API_KEY", SARVAM_KEY)
    monkeypatch.setenv("ELEVENLABS_API_KEY", "some-key")
    monkeypatch.setenv("PUTER_TOKEN", "some-token")
    reset_settings()
    chain = speech.transcription_chain()
    reset_settings()
    assert chain[0] == "sarvam"
    assert chain.index("sarvam") < chain.index("elevenlabs") < chain.index("puter")


def test_every_language_the_app_offers_maps_to_something_sarvam_accepts():
    """Ten map to a code; Assamese maps to auto-detection rather than a lie."""
    from app.schemas import SUPPORTED_LANGUAGES

    accepted = {"bn-IN", "en-IN", "gu-IN", "hi-IN", "kn-IN", "ml-IN", "mr-IN", "od-IN", "pa-IN", "ta-IN", "te-IN"}
    for code in SUPPORTED_LANGUAGES:
        mapped = speech.SARVAM_LANGUAGES.get(code, "unknown")
        assert mapped in accepted or mapped == "unknown", (code, mapped)
    # Assamese is the one Sarvam does not list. Asking for it by name would be
    # asking for a model that does not exist.
    assert "as" not in speech.SARVAM_LANGUAGES
    assert speech.SARVAM_LANGUAGES.get("as", "unknown") == "unknown"


def test_the_request_matches_sarvams_published_contract(with_sarvam, monkeypatch):
    """Endpoint, auth header, form fields and file part, per their OpenAPI doc."""
    import httpx

    seen = {}

    class Reply:
        def raise_for_status(self): pass
        def json(self): return {"transcript": "hello", "language_code": "hi-IN", "language_probability": 0.9}

    def fake_post(url, **kw):
        seen.update(url=url, headers=kw.get("headers", {}), data=kw.get("data", {}), files=kw.get("files", {}))
        return Reply()

    monkeypatch.setattr(httpx, "post", fake_post)
    result = speech._sarvam_transcribe(b"x" * 64, filename="q.webm", content_type="audio/webm", language="hi")

    assert seen["url"].endswith("/speech-to-text")
    assert seen["headers"] == {"api-subscription-key": SARVAM_KEY}
    assert set(seen["data"]) == {"model", "language_code"}
    assert seen["data"]["language_code"] == "hi-IN"
    assert "file" in seen["files"]
    # The reply's BCP-47 code is narrowed to the two-letter one the app speaks.
    assert result.language == "hi"
    assert result.engine == "sarvam"


def test_an_empty_transcript_is_not_passed_off_as_an_answer(with_sarvam, monkeypatch):
    import httpx

    class Reply:
        def raise_for_status(self): pass
        def json(self): return {"transcript": "   ", "language_code": "hi-IN"}

    monkeypatch.setattr(httpx, "post", lambda url, **kw: Reply())
    with pytest.raises(speech.TranscriptionError):
        speech._sarvam_transcribe(b"x" * 64, filename="q.webm", content_type="audio/webm", language="hi")


def test_the_key_is_not_in_anything_the_client_receives(with_sarvam):
    payload = json.dumps(speech.capabilities())
    assert SARVAM_KEY not in payload
    assert speech.capabilities()["sarvam_configured"] is True


def test_the_key_is_not_in_the_frontend_source():
    from pathlib import Path

    frontend = Path(__file__).resolve().parents[2] / "frontend" / "src"
    for path in frontend.rglob("*.js*"):
        assert "SARVAM" not in path.read_text(encoding="utf-8", errors="ignore"), path

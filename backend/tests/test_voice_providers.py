# -*- coding: utf-8 -*-
"""The voice ladder: who speaks, in what order, and what happens when they don't.

`api.elevenlabs.io` is unreachable from CI and from the sandbox this was built
in, so every test here drives the provider through a stubbed transport rather
than the network. That is the point: the interesting behaviour is the failover,
and a test that needs the internet to prove a fallback works is testing the
wrong thing.
"""

from __future__ import annotations

import base64

import httpx
import pytest

from app.config import reset_settings
from app.services import speech


@pytest.fixture
def elevenlabs_key(monkeypatch):
    """A configured-but-fake key, and the settings singleton dropped either side.

    Dropped afterwards too: leaving a fake key cached would make every later
    test in the process think ElevenLabs was available.
    """
    # conftest turns speech off for the suite as a whole; these tests are the
    # ones that need it on.
    monkeypatch.setenv("TTS_ENABLED", "true")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "sk_test_not_a_real_key")
    reset_settings()
    yield
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.delenv("TTS_ENABLED", raising=False)
    reset_settings()


def _reply(status: int, **kwargs) -> httpx.Response:
    """A response with its request attached.

    `raise_for_status()` refuses to run on a Response built without one, so a
    stub that omits it fails for the wrong reason and every assertion below it
    quietly tests the gTTS path instead.
    """
    return httpx.Response(status, request=httpx.Request("POST", "https://api.elevenlabs.io/"), **kwargs)


def _stub_post(monkeypatch, handler):
    monkeypatch.setattr(httpx, "post", handler)


def test_speech_switched_off_reports_no_chain_at_all(monkeypatch):
    """A server with TTS disabled has no providers, whatever is installed.

    Reporting one because the gTTS package happens to be importable would have
    the UI offer a button that could never make a sound.
    """
    monkeypatch.setenv("TTS_ENABLED", "false")
    reset_settings()
    assert speech.synthesis_chain() == []
    assert speech.capabilities()["synthesis_provider"] == ""


def test_the_order_is_elevenlabs_then_gtts_then_pyttsx3():
    """Pinned, because the order *is* the feature.

    A refactor that quietly promotes gTTS would leave every demo sounding wrong
    while every other test still passed.
    """
    assert speech.TTS_PROVIDER_ORDER == ("elevenlabs", "gtts", "pyttsx3")


def test_elevenlabs_is_used_first_and_reports_itself(monkeypatch, elevenlabs_key):
    seen: dict = {}

    def handler(url, **kwargs):
        seen["url"] = url
        seen["headers"] = kwargs.get("headers", {})
        seen["json"] = kwargs.get("json", {})
        return _reply(200, content=b"ID3fake-mp3-bytes")

    _stub_post(monkeypatch, handler)
    out = speech.synthesize_detailed("Rain is expected in two hours.", "en", "Low")

    assert out.provider == "elevenlabs"
    assert base64.b64decode(out.audio_base64) == b"ID3fake-mp3-bytes"
    assert out.mime == "audio/mpeg"
    # The documented request shape, not one from memory.
    assert "/v1/text-to-speech/" in seen["url"]
    assert seen["headers"]["xi-api-key"] == "sk_test_not_a_real_key"
    assert seen["json"]["text"] == "Rain is expected in two hours."
    assert seen["json"]["model_id"] == "eleven_multilingual_v2"


def test_the_key_never_leaves_the_server(monkeypatch, elevenlabs_key):
    """It travels in a header to ElevenLabs and appears in no response body."""
    _stub_post(monkeypatch, lambda url, **kw: _reply(200, content=b"audio"))
    out = speech.synthesize_detailed("Hello.", "en", "Low")
    assert "sk_test" not in out.audio_base64
    assert "sk_test" not in (out.note or "")
    assert "sk_test" not in out.provider


@pytest.mark.parametrize(
    "failure",
    [
        _reply(401, json={"detail": "invalid api key"}),
        _reply(429, json={"detail": "rate limited"}),
        _reply(500, text="upstream boom"),
    ],
    ids=["unauthorised", "rate-limited", "server-error"],
)
def test_an_elevenlabs_failure_steps_quietly_to_the_next_provider(monkeypatch, elevenlabs_key, failure):
    """A 401 is an operator's problem, never a sentence shown to a citizen."""
    _stub_post(monkeypatch, lambda url, **kw: failure)
    try:
        out = speech.synthesize_detailed("Move to higher ground.", "en", "Severe")
    except speech.SynthesisError as exc:
        # No provider was reachable at all — still no provider detail leaked.
        assert "401" not in str(exc) and "api key" not in str(exc).lower()
        return
    assert out.provider != "elevenlabs"


def test_a_timeout_does_not_hang_the_chain(monkeypatch, elevenlabs_key):
    def handler(url, **kwargs):
        raise httpx.ReadTimeout("too slow", request=None)

    _stub_post(monkeypatch, handler)
    try:
        out = speech.synthesize_detailed("Delay departure.", "en", "High")
        assert out.provider != "elevenlabs"
    except speech.SynthesisError as exc:
        assert "timeout" not in str(exc).lower()


def test_severity_steadies_the_delivery_rather_than_raising_it(monkeypatch, elevenlabs_key):
    """Calmer as it gets worse — the opposite of a weather announcer.

    Stability is the only prosody control the provider offers, and higher is
    flatter and steadier. Severe advice is meant to be easy to follow, not
    dramatic, so stability rises and style falls as the reading worsens.
    """
    captured: dict[str, dict] = {}

    def handler(url, **kwargs):
        captured[kwargs["json"]["text"]] = kwargs["json"]["voice_settings"]
        return _reply(200, content=b"audio")

    _stub_post(monkeypatch, handler)
    for level in ("Low", "Moderate", "High", "Severe"):
        speech.synthesize_detailed(level, "en", level)

    stability = [captured[level]["stability"] for level in ("Low", "Moderate", "High", "Severe")]
    style = [captured[level]["style"] for level in ("Low", "Moderate", "High", "Severe")]
    assert stability == sorted(stability), stability
    assert style == sorted(style, reverse=True), style
    assert stability[-1] > stability[0]


def test_an_unknown_severity_is_read_calmly_rather_than_refused(monkeypatch, elevenlabs_key):
    captured: dict = {}
    _stub_post(monkeypatch, lambda url, **kw: (captured.update(kw["json"]), _reply(200, content=b"a"))[1])
    speech.synthesize_detailed("Hello.", "en", "Nonsense")
    assert captured["voice_settings"]["stability"] == speech.ELEVENLABS_DELIVERY["Low"]["stability"]


def test_without_a_key_elevenlabs_is_skipped_not_attempted(monkeypatch):
    monkeypatch.setenv("TTS_ENABLED", "true")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "")
    reset_settings()

    def handler(url, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("called ElevenLabs with no key configured")

    _stub_post(monkeypatch, handler)
    assert speech.elevenlabs_tts_available() is False
    try:
        speech.synthesize_detailed("Hello.", "en", "Low")
    except speech.SynthesisError:
        pass  # No provider reachable here either; the point is nothing crashed.


def test_capabilities_names_the_voice_that_would_answer(elevenlabs_key):
    caps = speech.capabilities()
    assert caps["synthesis_provider"] == "elevenlabs"
    assert caps["elevenlabs_configured"] is True
    assert caps["synthesis_chain"][0] == "elevenlabs"


def test_the_languages_reported_are_the_ones_that_can_be_spoken(elevenlabs_key):
    """ElevenLabs' multilingual model reads every script the corpus translates.

    Reporting gTTS's six while it is configured would hide four languages the
    product genuinely can speak; reporting eleven when it is *not* configured
    would promise four it cannot.
    """
    from app.services import i18n

    assert speech.spoken_languages() == set(i18n.LANGUAGES)

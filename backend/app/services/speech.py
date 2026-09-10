# -*- coding: utf-8 -*-
"""Speech in and speech out.

Both directions are optional capabilities, feature-detected at call time:

* Transcription prefers ElevenLabs Scribe when a key is configured — it needs
  no model download, which is what makes voice input work on a serverless host
  — then ``faster-whisper`` (much lighter than the reference implementation),
  then ``openai-whisper``. None is a hard dependency: the API stays up without
  any of them and reports the gap rather than pretending.
* Synthesis uses gTTS, with an offline ``pyttsx3``/espeak path when installed.

Nothing here is allowed to break a turn. If transcription fails the route
returns a clear, localised error; if synthesis fails the text response is still
returned with ``tts_error`` set. Losing audio must never mean losing the answer.
"""

from __future__ import annotations

import base64
import importlib.util
import io
import logging
import struct
import tempfile
import threading
import wave
from dataclasses import dataclass
from pathlib import Path

from ..config import get_settings

log = logging.getLogger("weathergpt.speech")

ALLOWED_AUDIO_SUFFIXES = {".wav", ".mp3", ".m4a", ".ogg", ".oga", ".webm", ".flac", ".mp4", ".mpeg", ".mpga"}
ALLOWED_AUDIO_MIME_PREFIXES = ("audio/", "video/webm", "video/mp4", "application/octet-stream")

# gTTS language codes for the six supported languages. Assamese has no gTTS
# voice; Bengali is the closest intelligible neighbour and is flagged as such.
TTS_LANG_MAP: dict[str, str] = {"en": "en", "hi": "hi", "te": "te", "bn": "bn", "mr": "mr", "as": "bn"}
TTS_SUBSTITUTED: dict[str, str] = {"as": "bn"}


class TranscriptionError(RuntimeError):
    """Audio could not be turned into text. Message is user-safe."""


class SynthesisError(RuntimeError):
    """Audio could not be produced. Never fatal — text still goes out."""


@dataclass
class Transcript:
    text: str
    language: str
    confidence: float | None = None
    engine: str = "none"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_audio(data: bytes, filename: str | None, content_type: str | None) -> None:
    settings = get_settings()
    if not data:
        raise TranscriptionError("The audio file was empty. Please record again.")
    if len(data) > settings.max_audio_bytes:
        limit_mb = settings.max_audio_bytes // (1024 * 1024)
        raise TranscriptionError(f"That recording is too large. Please keep it under {limit_mb} MB.")

    suffix = Path(filename or "").suffix.lower()
    if suffix and suffix not in ALLOWED_AUDIO_SUFFIXES:
        supported = ", ".join(sorted(s.lstrip(".") for s in ALLOWED_AUDIO_SUFFIXES))
        raise TranscriptionError(f"That audio format is not supported. Please use one of: {supported}.")
    if content_type and not content_type.startswith(ALLOWED_AUDIO_MIME_PREFIXES):
        raise TranscriptionError("That file does not look like audio. Please upload a voice recording.")

    # WAV headers are cheap to read, so catch over-long clips before transcribing.
    if suffix == ".wav" or data[:4] == b"RIFF":
        try:
            with wave.open(io.BytesIO(data)) as handle:
                frames, rate = handle.getnframes(), handle.getframerate()
                if rate and frames / float(rate) > settings.max_audio_seconds:
                    raise TranscriptionError(
                        f"That recording is longer than {settings.max_audio_seconds} seconds. "
                        "Please ask a shorter question."
                    )
        except (wave.Error, RuntimeError, EOFError, struct.error):
            # A truncated or malformed header is not a reason to fail the turn:
            # the browser may still have sent a usable transcript alongside it.
            # `wave` raises a bare RuntimeError when it cannot seek, which is
            # exactly what a cut-short mobile recording produces.
            pass


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------
_model = None
_model_lock = threading.Lock()
_model_kind: str | None = None


def _has(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def transcription_engine() -> str:
    """Which engine would be used: 'elevenlabs' | 'faster-whisper' | 'whisper' | 'none'."""
    if get_settings().elevenlabs_api_key:
        return "elevenlabs"
    if _has("faster_whisper"):
        return "faster-whisper"
    if _has("whisper"):
        return "whisper"
    return "none"


def _local_engine() -> str:
    """The on-device engine, ignoring any hosted one. Used as the fallback."""
    if _has("faster_whisper"):
        return "faster-whisper"
    if _has("whisper"):
        return "whisper"
    return "none"


# A library being importable is not the same as it working. Whisper still has
# to fetch model weights, and gTTS needs to reach Google; both fail on a locked
# down or offline host. These latch to False after the first real failure so
# /config stops advertising a capability the server cannot actually deliver.
_stt_working: bool | None = None
_tts_working: bool | None = None


def note_transcription_result(ok: bool) -> None:
    global _stt_working
    _stt_working = ok


def note_synthesis_result(ok: bool) -> None:
    global _tts_working
    _tts_working = ok


def transcription_available() -> bool:
    if _stt_working is False:
        return False
    return transcription_engine() != "none"


def _load_model():
    global _model, _model_kind
    settings = get_settings()
    with _model_lock:
        if _model is not None:
            return _model, _model_kind
        engine = _local_engine()
        if engine == "faster-whisper":
            from faster_whisper import WhisperModel  # type: ignore

            # First use downloads the weights from Hugging Face — inside the
            # user's request, which is why a cold machine looks "broken" rather
            # than slow. If the network is unavailable but the model was fetched
            # once before, fall back to the local copy instead of failing.
            try:
                _model = WhisperModel(
                    settings.whisper_model, device=settings.whisper_device, compute_type="int8"
                )
            except Exception as exc:  # noqa: BLE001 - almost always a network error
                log.warning("model download failed (%s); retrying from local cache only", exc)
                _model = WhisperModel(
                    settings.whisper_model,
                    device=settings.whisper_device,
                    compute_type="int8",
                    local_files_only=True,
                )
        elif engine == "whisper":
            import whisper  # type: ignore

            _model = whisper.load_model(settings.whisper_model, device=settings.whisper_device)
        else:
            raise TranscriptionError(
                "Speech recognition is not configured on this server. Set "
                "ELEVENLABS_API_KEY for hosted transcription (no download needed), "
                "or install faster-whisper for on-device transcription. Until then, "
                "voice still works in browsers that support speech recognition, and "
                "you can always type your question."
            )
        _model_kind = engine
        return _model, _model_kind


def _elevenlabs_transcribe(
    data: bytes,
    *,
    filename: str | None,
    content_type: str | None,
    language: str | None,
) -> Transcript:
    """ElevenLabs Scribe.

    Request shape taken from the official SDK's own client rather than from
    memory: POST /v1/speech-to-text, ``xi-api-key`` header, the audio in a
    ``file`` part and ``model_id``/``language_code`` as form fields; the reply
    carries ``text``, ``language_code`` and ``language_probability``.
    """
    import httpx

    settings = get_settings()
    form: dict[str, str] = {"model_id": settings.elevenlabs_stt_model}
    if language:
        # Telling Scribe the language beats letting it guess between the four
        # Indic scripts the app supports, and the UI already knows which one.
        form["language_code"] = language

    try:
        response = httpx.post(
            f"{settings.elevenlabs_api_base}/v1/speech-to-text",
            headers={"xi-api-key": settings.elevenlabs_api_key},
            data=form,
            files={"file": (filename or "question.webm", data, content_type or "audio/webm")},
            timeout=settings.elevenlabs_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:  # noqa: BLE001 - any failure falls back below
        log.exception("ElevenLabs transcription failed (full traceback follows)")
        raise TranscriptionError(f"ElevenLabs transcription failed: {exc}") from exc

    text = str(payload.get("text") or "").strip()
    if not text:
        raise TranscriptionError("I could not hear anything clear in that recording. Please try again.")
    return Transcript(
        text=text,
        language=str(payload.get("language_code") or language or "en"),
        confidence=payload.get("language_probability"),
        engine="elevenlabs",
    )


def warm_up() -> str:
    """Load the on-device model now instead of during someone's first question.

    Returns a one-line status. Call it from a terminal before a demo:
        python -c "import sys; sys.path.insert(0,'.'); from app.services import speech; print(speech.warm_up())"
    """
    if get_settings().elevenlabs_api_key:
        return "hosted transcription configured (ElevenLabs); no local model needed"
    if _local_engine() == "none":
        return "no on-device engine installed; nothing to warm up"
    try:
        _load_model()
    except Exception as exc:  # noqa: BLE001 - report, never crash a boot
        return f"model warm-up FAILED: {exc}"
    return f"on-device model ready ({_model_kind}, {get_settings().whisper_model})"


def transcribe(
    data: bytes,
    *,
    filename: str | None = None,
    content_type: str | None = None,
    language: str | None = None,
) -> Transcript:
    """Turn audio into text. Raises ``TranscriptionError`` with a usable message."""
    validate_audio(data, filename, content_type)

    settings = get_settings()
    if settings.elevenlabs_api_key:
        try:
            result = _elevenlabs_transcribe(
                data, filename=filename, content_type=content_type, language=language
            )
            note_transcription_result(True)
            return result
        except TranscriptionError as exc:
            # A hosted transcriber being down is not a reason to lose the turn
            # when a local model is installed, so try that before giving up.
            log.warning("ElevenLabs unavailable, trying on-device engine: %s", exc)
            if _local_engine() == "none":
                note_transcription_result(False)
                raise TranscriptionError(
                    "Speech recognition is unavailable right now. Please type your question instead."
                ) from exc

    suffix = Path(filename or "").suffix.lower() or ".wav"
    try:
        model, kind = _load_model()
    except TranscriptionError:
        raise
    except Exception as exc:  # noqa: BLE001 - model load can fail many ways
        log.exception("whisper model load failed (full traceback follows)")
        # Model weights are fetched on first use; on a host that cannot reach the
        # model host this never succeeds, so stop claiming the capability.
        note_transcription_result(False)
        raise TranscriptionError(
            "The speech recogniser could not start. Please type your question instead."
        ) from exc

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        if kind == "faster-whisper":
            segments, info = model.transcribe(tmp_path, beam_size=1, vad_filter=True)
            text = " ".join(segment.text for segment in segments).strip()
            detected = getattr(info, "language", "en") or "en"
            confidence = getattr(info, "language_probability", None)
        else:
            result = model.transcribe(tmp_path)
            text = str(result.get("text", "")).strip()
            detected = str(result.get("language", "en")) or "en"
            confidence = None
    except Exception as exc:  # noqa: BLE001
        log.exception("transcription failed (full traceback follows)")
        raise TranscriptionError(
            "I could not understand that recording. Please try again in a quieter place."
        ) from exc
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)

    if not text or len(text.strip()) < 2:
        raise TranscriptionError("I could not hear anything clear in that recording. Please try again.")

    note_transcription_result(True)
    return Transcript(text=text, language=detected, confidence=confidence, engine=kind)


# ---------------------------------------------------------------------------
# Synthesis
# ---------------------------------------------------------------------------
def voice_friendly(text: str) -> str:
    """Strip anything that reads badly aloud before handing text to TTS."""
    cleaned = text or ""
    for token in ("**", "*", "`", "#", "|", "- ", "•", "→", "…"):
        cleaned = cleaned.replace(token, " " if token != "…" else "...")
    # Section labels read better as sentences than as headings.
    cleaned = cleaned.replace(":\n", ". ").replace("\n", " ")
    while "  " in cleaned:
        cleaned = cleaned.replace("  ", " ")
    return cleaned.strip()


# How the voice carries itself, by how bad the reading is.
#
# ElevenLabs exposes stability and style rather than "calm" and "urgent", so
# this is the mapping between the two. Higher stability is a flatter, steadier
# read — which is what a severe instruction wants; a calm day can afford a
# little more variation and sound less like an announcement. Nothing here is
# dramatic: the top of the range is *steadier*, not louder, because the moment
# advice matters most is the moment it must be easiest to follow.
ELEVENLABS_DELIVERY: dict[str, dict[str, float]] = {
    "Low": {"stability": 0.40, "similarity_boost": 0.75, "style": 0.30},
    "Moderate": {"stability": 0.45, "similarity_boost": 0.75, "style": 0.25},
    "High": {"stability": 0.60, "similarity_boost": 0.80, "style": 0.15},
    "Severe": {"stability": 0.75, "similarity_boost": 0.85, "style": 0.05},
}

# Providers in the order they are tried, for /health and for the tests that
# assert the order has not quietly changed.
TTS_PROVIDER_ORDER: tuple[str, ...] = ("elevenlabs", "gtts", "pyttsx3")


def synthesis_chain() -> list[str]:
    """The providers that would actually be tried, in order.

    Gated on `tts_enabled` as a whole: a server with speech switched off has no
    chain, and reporting one because the gTTS package happens to be installed
    would have the UI offer a button that could never make a sound.
    """
    if not get_settings().tts_enabled:
        return []
    usable = {
        "elevenlabs": elevenlabs_tts_available,
        "gtts": lambda: _has("gtts"),
        "pyttsx3": lambda: _has("pyttsx3"),
    }
    return [name for name in TTS_PROVIDER_ORDER if usable[name]()]


def spoken_languages() -> set[str]:
    """Language codes the active synthesis provider can actually voice.

    ElevenLabs' multilingual model covers every language the corpus translates
    into; gTTS covers six of them and substitutes a neighbour for a seventh.
    Reporting the union would promise a voice the server cannot produce, so
    this reports the provider that would actually answer.
    """
    from . import i18n

    if elevenlabs_tts_available():
        return set(i18n.LANGUAGES)
    if _has("gtts"):
        return set(TTS_LANG_MAP)
    # pyttsx3 reads whatever the host has installed, which we cannot enumerate;
    # English is the only one it is safe to promise.
    return {"en"} if _has("pyttsx3") else set()


def elevenlabs_tts_available() -> bool:
    settings = get_settings()
    return bool(settings.tts_enabled and settings.elevenlabs_api_key)


def _elevenlabs_synthesize(text: str, language: str, severity: str | None) -> tuple[bytes, str]:
    """ElevenLabs text-to-speech.

    Request shape from the official API: POST /v1/text-to-speech/{voice_id},
    ``xi-api-key`` header, JSON body carrying ``text``, ``model_id`` and
    ``voice_settings``; the reply is the audio itself, not JSON.

    ``language`` is not sent: the multilingual model reads the script it is
    given, and passing a language code to a voice that does not have one is how
    you get an English mouth on a Tamil sentence.
    """
    import httpx

    settings = get_settings()
    delivery = ELEVENLABS_DELIVERY.get(severity or "Low", ELEVENLABS_DELIVERY["Low"])

    response = httpx.post(
        f"{settings.elevenlabs_api_base}/v1/text-to-speech/{settings.elevenlabs_voice_id}",
        headers={
            "xi-api-key": settings.elevenlabs_api_key,
            "accept": "audio/mpeg",
            "content-type": "application/json",
        },
        json={
            "text": text,
            "model_id": settings.elevenlabs_tts_model,
            "voice_settings": {**delivery, "use_speaker_boost": True},
        },
        timeout=settings.elevenlabs_tts_timeout_seconds,
    )
    response.raise_for_status()
    audio = response.content
    if not audio:
        raise SynthesisError("ElevenLabs returned no audio.")
    return audio, "audio/mpeg"


def synthesis_available() -> bool:
    if _tts_working is False:
        return False
    settings = get_settings()
    if not settings.tts_enabled:
        return False
    return bool(settings.elevenlabs_api_key) or _has("gtts") or _has("pyttsx3")


@dataclass
class Speech:
    """One rendered clip, and an honest account of where it came from."""

    audio_base64: str
    mime: str
    provider: str
    note: str | None = None


def synthesize(
    text: str, language: str = "en", severity: str | None = None
) -> tuple[str, str, str | None]:
    """Back-compatible shim: ``(base64, mime, note)``.

    Kept because the chat route has always called it this way. New callers that
    care which provider spoke should use :func:`synthesize_detailed`.
    """
    speech = synthesize_detailed(text, language, severity)
    return speech.audio_base64, speech.mime, speech.note


def synthesize_detailed(text: str, language: str = "en", severity: str | None = None) -> Speech:
    """Render ``text`` to audio, trying each provider in turn.

    The order is deliberate and is the whole point of the chain: ElevenLabs is
    the voice the product is meant to have, gTTS is the one that keeps working
    when it is not, and pyttsx3 is the one that works with no network at all.
    A provider that fails is logged and stepped over — never surfaced to the
    reader, who is owed "could not play that", not an HTTP status.

    Raises ``SynthesisError`` only when every provider has been tried. Callers
    return the text response regardless: losing the audio must never mean
    losing the advice.
    """
    settings = get_settings()
    if not settings.tts_enabled:
        raise SynthesisError("Text to speech is disabled on this server.")

    speech_text = voice_friendly(text)
    if not speech_text:
        raise SynthesisError("There was nothing to read aloud.")

    lang = (language or "en").lower()
    note = None

    # --- 1. ElevenLabs, the intended voice --------------------------------
    if elevenlabs_tts_available():
        try:
            audio, mime = _elevenlabs_synthesize(speech_text, lang, severity)
            note_synthesis_result(True)
            return Speech(base64.b64encode(audio).decode("ascii"), mime, "elevenlabs")
        except Exception as exc:  # noqa: BLE001 - every failure steps to the next
            log.warning("ElevenLabs synthesis failed, falling back: %s", exc)

    # --- 2. gTTS ----------------------------------------------------------
    # Only gTTS needs the language told to it, and only gTTS has gaps in the
    # set this app offers, so the substitution note belongs to this branch.
    tts_lang = TTS_LANG_MAP.get(lang, "en")
    if lang in TTS_SUBSTITUTED:
        note = (
            f"No text-to-speech voice exists for '{lang}'; "
            f"read using the closest available voice ('{TTS_SUBSTITUTED[lang]}')."
        )

    if _has("gtts"):
        try:
            from gtts import gTTS  # type: ignore

            buffer = io.BytesIO()
            gTTS(text=speech_text, lang=tts_lang, slow=False).write_to_fp(buffer)
            audio = buffer.getvalue()
            if audio:
                note_synthesis_result(True)
                return Speech(base64.b64encode(audio).decode("ascii"), "audio/mpeg", "gtts", note)
        except Exception:  # noqa: BLE001 - gTTS needs network
            log.exception("gTTS failed (full traceback follows)")

    # --- 3. pyttsx3, offline ----------------------------------------------
    if _has("pyttsx3"):
        tmp_path: str | None = None
        try:
            import pyttsx3  # type: ignore

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
            engine = pyttsx3.init()
            engine.save_to_file(speech_text, tmp_path)
            engine.runAndWait()
            audio = Path(tmp_path).read_bytes()
            if audio:
                note_synthesis_result(True)
                return Speech(base64.b64encode(audio).decode("ascii"), "audio/wav", "pyttsx3", note)
        except Exception as exc:  # noqa: BLE001
            log.warning("pyttsx3 failed: %s", exc)
        finally:
            if tmp_path:
                Path(tmp_path).unlink(missing_ok=True)

    # Every server-side engine failed. The browser still has two of its own —
    # Puter and its native synthesiser — so this is not the end of the ladder,
    # which is why the client is handed the script rather than an apology.
    note_synthesis_result(False)
    raise SynthesisError(
        "Could not produce audio right now. The text answer is still available."
    )


def capabilities() -> dict[str, object]:
    """Reported by /health so the UI can hide controls that cannot work."""
    settings = get_settings()
    return {
        "transcription": transcription_available(),
        "transcription_engine": transcription_engine(),
        "synthesis": synthesis_available(),
        # Which voice would speak next, and the whole ladder behind it, so the
        # UI can say "no voice configured" without guessing and an operator can
        # see at a glance which provider a demo is actually running on.
        "synthesis_provider": next(iter(synthesis_chain()), ""),
        "synthesis_chain": synthesis_chain(),
        "elevenlabs_configured": bool(settings.elevenlabs_api_key),
        # What can actually be spoken *by the provider that would answer*, not
        # by gTTS regardless. ElevenLabs' multilingual model reads every script
        # the app translates into, so reporting gTTS's six while it is
        # configured would hide four languages the product really can speak —
        # and the substitution note only applies to the gTTS path.
        "tts_languages": sorted(spoken_languages()),
        "tts_substitutions": {} if elevenlabs_tts_available() else TTS_SUBSTITUTED,
    }

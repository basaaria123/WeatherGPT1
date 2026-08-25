# -*- coding: utf-8 -*-
"""Speech in and speech out.

Both directions are optional capabilities, feature-detected at call time:

* Transcription prefers ``faster-whisper`` (much lighter than the reference
  implementation) and falls back to ``openai-whisper``. Neither is a hard
  dependency — the API stays up without them and reports the gap.
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
        except wave.Error:
            pass  # Not a readable WAV; let the transcriber decide.


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
    """Which engine would be used: 'faster-whisper' | 'whisper' | 'none'."""
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
        engine = transcription_engine()
        if engine == "faster-whisper":
            from faster_whisper import WhisperModel  # type: ignore

            _model = WhisperModel(settings.whisper_model, device=settings.whisper_device, compute_type="int8")
        elif engine == "whisper":
            import whisper  # type: ignore

            _model = whisper.load_model(settings.whisper_model, device=settings.whisper_device)
        else:
            raise TranscriptionError(
                "Voice input is not enabled on this server. "
                "Install faster-whisper (or openai-whisper) to turn it on, or type your question instead."
            )
        _model_kind = engine
        return _model, _model_kind


def transcribe(data: bytes, *, filename: str | None = None, content_type: str | None = None) -> Transcript:
    """Transcribe audio locally. Raises ``TranscriptionError`` with a usable message."""
    validate_audio(data, filename, content_type)

    suffix = Path(filename or "").suffix.lower() or ".wav"
    try:
        model, kind = _load_model()
    except TranscriptionError:
        raise
    except Exception as exc:  # noqa: BLE001 - model load can fail many ways
        log.error("whisper model load failed: %s", exc)
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
        log.error("transcription failed: %s", exc)
        raise TranscriptionError(
            "I could not understand that recording. Please try again in a quieter place."
        ) from exc
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)

    if not text or len(text.strip()) < 2:
        raise TranscriptionError("I could not hear anything clear in that recording. Please try again.")

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


def synthesis_available() -> bool:
    if _tts_working is False:
        return False
    return get_settings().tts_enabled and (_has("gtts") or _has("pyttsx3"))


def synthesize(text: str, language: str = "en") -> tuple[str, str, str | None]:
    """Return ``(base64_audio, mime_type, substitution_note)``.

    Raises ``SynthesisError``; callers return the text response regardless.
    """
    settings = get_settings()
    if not settings.tts_enabled:
        raise SynthesisError("Text to speech is disabled on this server.")

    speech_text = voice_friendly(text)
    if not speech_text:
        raise SynthesisError("There was nothing to read aloud.")

    lang = (language or "en").lower()
    tts_lang = TTS_LANG_MAP.get(lang, "en")
    note = None
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
                return base64.b64encode(audio).decode("ascii"), "audio/mpeg", note
        except Exception as exc:  # noqa: BLE001 - gTTS needs network
            log.warning("gTTS failed: %s", exc)

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
                return base64.b64encode(audio).decode("ascii"), "audio/wav", note
        except Exception as exc:  # noqa: BLE001
            log.warning("pyttsx3 failed: %s", exc)
        finally:
            if tmp_path:
                Path(tmp_path).unlink(missing_ok=True)

    # Every engine failed: stop advertising speech until the process restarts,
    # so the UI does not keep offering a play button that yields silence.
    note_synthesis_result(False)
    raise SynthesisError(
        "Could not produce audio right now. The text answer is still available."
    )


def capabilities() -> dict[str, object]:
    """Reported by /health so the UI can hide controls that cannot work."""
    return {
        "transcription": transcription_available(),
        "transcription_engine": transcription_engine(),
        "synthesis": synthesis_available(),
        "tts_languages": sorted(TTS_LANG_MAP),
        "tts_substitutions": TTS_SUBSTITUTED,
    }

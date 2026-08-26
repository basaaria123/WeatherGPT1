# -*- coding: utf-8 -*-
"""Chat and voice-chat endpoints.

``/voice-chat`` is a thin wrapper: it turns audio into text and then calls the
exact same ``chat_engine.handle_chat`` as ``/chat``. No weather logic, no risk
logic and no memory logic is duplicated here.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..config import get_settings
from ..schemas import ChatRequest, ChatResponse, VoiceChatResponse
from ..services import chat_engine, i18n, language, speech

log = logging.getLogger("weathergpt.routes.chat")

router = APIRouter(tags=["chat"])


def _attach_audio(response: ChatResponse, *, wanted: bool) -> ChatResponse:
    """Add TTS audio when asked. A synthesis failure never costs the text."""
    if not wanted:
        return response
    try:
        audio, mime, note = speech.synthesize(response.answer, response.language)
        response.audio_base64 = audio
        response.audio_mime = mime
        if note:
            response.degraded.tts_error = note
    except speech.SynthesisError as exc:
        response.degraded.tts_error = str(exc)
    except Exception as exc:  # noqa: BLE001 - audio is never worth a 500
        log.warning("unexpected TTS failure: %s", exc)
        response.degraded.tts_error = "Audio could not be generated. The text answer is still available."
    return response


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    if not payload.query.strip():
        raise HTTPException(status_code=422, detail="Please type a question.")
    response = chat_engine.handle_chat(
        query=payload.query,
        session_id=payload.session_id,
        user_type=payload.user_type,
        requested_language=payload.language,
        response_mode=payload.response_mode,
        latitude=payload.latitude,
        longitude=payload.longitude,
        selected_location=payload.location,
    )
    return _attach_audio(response, wanted=payload.voice_response)


@router.post("/voice-chat", response_model=VoiceChatResponse)
async def voice_chat(
    audio: UploadFile | None = File(default=None, description="Recorded question"),
    session_id: str | None = Form(default=None),
    user_type: str | None = Form(default=None),
    lang: str | None = Form(default=None, description="Force a language instead of auto-detecting"),
    response_mode: str | None = Form(default=None),
    voice_response: bool = Form(default=True),
    latitude: float | None = Form(default=None),
    longitude: float | None = Form(default=None),
    location: str | None = Form(default=None),
    client_transcript: str | None = Form(
        default=None,
        description=(
            "Text already transcribed on the client, e.g. by the browser Web Speech API. "
            "Used when supplied; server-side Whisper is used otherwise."
        ),
    ),
) -> VoiceChatResponse:
    settings = get_settings()
    transcript_text = ""
    detected_language: str | None = None
    confidence: float | None = None
    transcription_source = "none"

    if audio is not None:
        try:
            data = await audio.read()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail="The audio upload could not be read.") from exc

        try:
            result = speech.transcribe(
                data,
                filename=audio.filename,
                content_type=audio.content_type,
                # The UI already knows which language the user picked; passing
                # it stops the recogniser guessing between four Indic scripts.
                language=i18n.normalise_lang(lang) if lang else None,
            )
            transcript_text = result.text
            detected_language = result.language
            confidence = result.confidence
            transcription_source = result.engine
        except speech.TranscriptionError as exc:
            # A client-side transcript is a legitimate fallback, not a silent one.
            if client_transcript and client_transcript.strip():
                transcript_text = client_transcript.strip()
                transcription_source = "client"
            else:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
    elif client_transcript and client_transcript.strip():
        transcript_text = client_transcript.strip()
        transcription_source = "client"
    else:
        raise HTTPException(
            status_code=422,
            detail="Send an audio recording, or a client_transcript if you transcribed it in the browser.",
        )

    if language.looks_like_gibberish(transcript_text):
        raise HTTPException(
            status_code=422,
            detail="I could not make out any words in that recording. Please try again.",
        )

    # Whisper's language guess is a hint; our own detector decides, because it
    # is exact for Telugu and reliable for Assamese vs Bengali.
    forced_language = lang
    if not forced_language and detected_language:
        detected = language.detect(transcript_text)
        if detected.confidence < 0.6 and i18n.normalise_lang(detected_language) != i18n.DEFAULT_LANG:
            forced_language = i18n.normalise_lang(detected_language)

    response = chat_engine.handle_chat(
        query=transcript_text,
        session_id=session_id,
        user_type=user_type,
        requested_language=forced_language,
        response_mode=response_mode,
        latitude=latitude,
        longitude=longitude,
        selected_location=location,
    )
    response = _attach_audio(response, wanted=voice_response and settings.tts_enabled)

    if transcription_source == "client":
        note = "Transcribed on the client; server-side speech recognition was unavailable."
        response.degraded.fallback_reason = (
            f"{response.degraded.fallback_reason}; {note}" if response.degraded.fallback_reason else note
        )

    return VoiceChatResponse(
        **response.model_dump(),
        transcript=transcript_text,
        transcription_confidence=confidence,
    )

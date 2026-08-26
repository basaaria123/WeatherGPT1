"""Anthropic integration.

Two calls make up the chat path, both using **forced tool use** rather than
free-text parsing, so extraction is a validated JSON object instead of
something we have to regex out of prose:

* ``extract_query``  — location, intent, profile, scope, language
* ``compose_answer`` — the natural-language answer, explanation and actions

Every function here returns ``None`` (or raises ``LLMUnavailable``) rather than
propagating a provider error. The chat engine treats that as "degrade to the
deterministic path", which is why an Anthropic outage mid-conversation costs
quality but never availability.
"""

from __future__ import annotations

import json
import logging
import threading
from typing import Any

from ..config import get_settings
from ..schemas import USER_TYPES

log = logging.getLogger("weathergpt.llm")


class LLMUnavailable(RuntimeError):
    """No usable LLM. Callers must fall back, not fail."""


_client: Any = None
_client_lock = threading.Lock()
_client_key: str | None = None


def _get_client() -> Any:
    """Lazily build the Anthropic client, rebuilding if the key changed."""
    global _client, _client_key
    settings = get_settings()
    if not settings.llm_configured:
        raise LLMUnavailable("ANTHROPIC_API_KEY is not set")

    with _client_lock:
        if _client is None or _client_key != settings.anthropic_api_key:
            try:
                import anthropic
            except ImportError as exc:  # pragma: no cover - dependency missing
                raise LLMUnavailable("anthropic SDK is not installed") from exc
            _client = anthropic.Anthropic(
                api_key=settings.anthropic_api_key,
                timeout=settings.llm_timeout_seconds,
                max_retries=settings.llm_max_retries,
            )
            _client_key = settings.anthropic_api_key
    return _client


def available() -> bool:
    """True when an LLM call is worth attempting."""
    settings = get_settings()
    if not settings.llm_configured:
        return False
    try:
        _get_client()
        return True
    except LLMUnavailable:
        return False


def reset_client() -> None:
    """Drop the cached client (used by tests and after config changes)."""
    global _client, _client_key
    with _client_lock:
        _client = None
        _client_key = None


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------
EXTRACTION_TOOL: dict[str, Any] = {
    "name": "extract_weather_query",
    "description": (
        "Record the structured interpretation of the user's weather question. "
        "Call this exactly once for every user message."
    ),
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "in_scope": {
                "type": "boolean",
                "description": (
                    "True if the message is about weather, forecasts, weather alerts, "
                    "climate trends, or safety in relation to weather. False for anything else."
                ),
            },
            "intent": {
                "type": "string",
                "enum": ["current_weather", "forecast", "alert_check", "climate_trend", "out_of_scope"],
            },
            "location": {
                "type": "string",
                "description": (
                    "The place the user is asking about, in English, as a bare place name "
                    "(for example 'Guwahati'). Empty string if the message names no place."
                ),
            },
            "use_previous_location": {
                "type": "boolean",
                "description": (
                    "True when the message relies on the location from earlier in the "
                    "conversation, such as 'what about tomorrow?'."
                ),
            },
            "day_offset": {
                "type": "integer",
                "description": "0 for today or now, 1 for tomorrow, 2 for the day after tomorrow, up to 6.",
                "minimum": 0,
                "maximum": 6,
            },
            "user_type": {"type": "string", "enum": list(USER_TYPES)},
            "response_mode": {"type": "string", "enum": ["normal", "simple", "emergency"]},
            "advice_question": {
                "type": "boolean",
                "description": (
                    "True when the user is asking what to do rather than what the weather is — "
                    "safety, precautions, whether to travel, go out, harvest or sail."
                ),
            },
            "language": {
                "type": "string",
                "description": "ISO 639-1 code of the language the user wrote in, e.g. en, hi, te, bn, mr, as.",
            },
        },
        "required": [
            "in_scope", "intent", "location", "use_previous_location",
            "day_offset", "user_type", "response_mode", "advice_question", "language",
        ],
        "additionalProperties": False,
    },
}

COMPOSE_TOOL: dict[str, Any] = {
    "name": "compose_weather_answer",
    "description": "Record the final answer for the user. Call this exactly once.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "answer": {
                "type": "string",
                "description": (
                    "The spoken-style answer to the user, in their language. Two to five sentences. "
                    "No markdown, no tables, no bullet characters — it may be read aloud."
                ),
            },
            "explanation": {
                "type": "string",
                "description": (
                    "One or two sentences saying which measurements led to this answer, "
                    "quoting only values from the supplied data."
                ),
            },
            "actions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Practical steps. Empty list when conditions are calm.",
            },
            "action_mode": {
                "type": "boolean",
                "description": "True when the answer is a checklist-style safety response.",
            },
        },
        "required": ["answer", "explanation", "actions", "action_mode"],
        "additionalProperties": False,
    },
}

EXTRACTION_SYSTEM = """You interpret questions for WeatherGPT, an Indian weather-safety assistant.

Call extract_weather_query exactly once. Guidance:
- Locations are usually Indian cities, districts or states. Correct obvious misspellings
  ("Vijaywada" -> "Vijayawada") and expand common short forms ("Vizag" -> "Visakhapatnam").
- Write the location in English even when the user writes in another script.
- If the user names no place but the conversation already established one, set
  use_previous_location true and leave location empty.
- "tomorrow" is day_offset 1, "day after tomorrow" is 2, "today"/"now" is 0.
- Set user_type only when the user identifies themselves or their activity
  (farming, fishing, travelling, commuting, flying, city life). Otherwise use "general".
- Set response_mode "simple" only when the user asks for simpler or shorter wording.
  Never set "emergency" yourself: severity is decided from measured data, not from wording.
- Set advice_question true when the user asks what to do rather than what the weather is:
  "is it safe to travel?", "should I harvest today?", "can I go out?", "what precautions?".
- Greetings and thanks about weather remain in scope. Anything unrelated to weather
  (recipes, politics, code, general trivia) is out_of_scope with in_scope false."""

COMPOSE_SYSTEM = """You are WeatherGPT, explaining weather to people in India: farmers,
fishermen, travellers, commuters and families in disaster-prone areas.

ABSOLUTE RULE ON NUMBERS. You may only state numbers that appear in the WEATHER DATA
block given to you. Never estimate, round beyond one decimal place, convert units, or
infer a value that is not present. If you want to say something the data does not
support, describe it qualitatively instead or leave it out. A wrong number in a flood
warning is worse than no number.

Style:
- Write the way a person speaks. The answer may be read aloud by text to speech,
  so no markdown, no tables, no bullet symbols, no parentheses full of figures.
- Two to five sentences. Lead with what matters to this user.
- Translate measurements into meaning: not "precipitation probability 87 percent" but
  "there is a high chance of rain".
- Respect the user's profile in what you prioritise, but never invent specialised
  facts the data does not contain. You have no sea-state, road-closure, crop-stage or
  air-traffic data unless it appears in WEATHER DATA.
- Write in the language named as RESPONSE LANGUAGE.
- When RISK LEVEL is High or Severe, lead with the warning, say plainly why it matters,
  then give short concrete actions. Never exaggerate, and never soften a real hazard.
- When risk is Low or Moderate, answer normally and keep actions empty or minimal.

Call compose_weather_answer exactly once."""


def _tool_input(response: Any, tool_name: str) -> dict[str, Any] | None:
    """Pull the forced tool call's validated input out of a response."""
    for block in getattr(response, "content", []) or []:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == tool_name:
            data = getattr(block, "input", None)
            if isinstance(data, dict):
                return data
            if isinstance(data, str):
                # Defensive: 4.6-family models may escape JSON differently.
                try:
                    return json.loads(data)
                except json.JSONDecodeError:
                    return None
    return None


def _text(response: Any) -> str:
    parts = [
        block.text
        for block in getattr(response, "content", []) or []
        if getattr(block, "type", None) == "text"
    ]
    return "\n".join(parts).strip()


def _call(**kwargs: Any) -> Any:
    settings = get_settings()
    client = _get_client()
    return client.messages.create(model=settings.anthropic_model, **kwargs)


# ---------------------------------------------------------------------------
# Public operations
# ---------------------------------------------------------------------------
def extract_query(query: str, *, history: str = "", known_location: str | None = None) -> dict[str, Any] | None:
    """Structured interpretation of a user message, or None if the LLM failed."""
    context_lines = []
    if known_location:
        context_lines.append(f"Location established earlier in this conversation: {known_location}")
    if history:
        context_lines.append(f"Recent conversation:\n{history}")
    context = ("\n\n".join(context_lines) + "\n\n") if context_lines else ""

    try:
        response = _call(
            max_tokens=1024,
            system=EXTRACTION_SYSTEM,
            tools=[EXTRACTION_TOOL],
            tool_choice={"type": "tool", "name": EXTRACTION_TOOL["name"]},
            messages=[{"role": "user", "content": f"{context}User message:\n{query}"}],
        )
    except LLMUnavailable:
        return None
    except Exception as exc:  # noqa: BLE001 - any provider failure degrades
        log.warning("extraction call failed: %s", exc)
        return None
    return _tool_input(response, EXTRACTION_TOOL["name"])


def compose_answer(
    *,
    query: str,
    weather_data: dict[str, Any],
    risk: dict[str, Any],
    language_name: str,
    user_type: str,
    response_mode: str,
    history: str = "",
    extra_context: str = "",
) -> dict[str, Any] | None:
    """Generate the grounded answer, or None if the LLM failed."""
    blocks = [
        f"RESPONSE LANGUAGE: {language_name}",
        f"USER PROFILE: {user_type}",
        f"RESPONSE MODE: {response_mode}",
        f"RISK LEVEL: {risk.get('risk_level')} (score {risk.get('risk_score')} out of 100)",
        f"DETECTED HAZARD: {risk.get('detected_hazard')}",
        "WEATHER DATA (the only numbers you may use):",
        json.dumps(weather_data, ensure_ascii=False, indent=2, default=str),
    ]
    if extra_context:
        blocks.append(extra_context)
    if history:
        blocks.append(f"RECENT CONVERSATION:\n{history}")
    blocks.append(f"USER QUESTION:\n{query}")

    try:
        response = _call(
            max_tokens=2000,
            system=COMPOSE_SYSTEM,
            tools=[COMPOSE_TOOL],
            tool_choice={"type": "tool", "name": COMPOSE_TOOL["name"]},
            messages=[{"role": "user", "content": "\n\n".join(blocks)}],
        )
    except LLMUnavailable:
        return None
    except Exception as exc:  # noqa: BLE001
        log.warning("compose call failed: %s", exc)
        return None
    return _tool_input(response, COMPOSE_TOOL["name"])


def translate_text(text: str, *, source: str, target: str, system: str) -> str | None:
    """Translate text. Returns None on failure so the caller can use templates."""
    try:
        response = _call(
            max_tokens=1500,
            system=system,
            messages=[
                {
                    "role": "user",
                    "content": f"Translate from {source} to {target}. Text:\n\n{text}",
                }
            ],
        )
    except LLMUnavailable:
        return None
    except Exception as exc:  # noqa: BLE001
        log.warning("translation call failed: %s", exc)
        return None
    return _text(response) or None


def climate_summary(*, location: str, metrics: dict[str, Any], language_name: str) -> str | None:
    """Plain-language summary of computed climate anomalies.

    The anomaly maths happens in Python; the model only phrases the result, so
    it cannot introduce a statistic that was not measured.
    """
    system = (
        "You explain climate statistics for an Indian weather assistant. "
        "You are given anomaly figures that have already been computed from the "
        "historical record. State them plainly in two or three sentences. "
        "Use only the numbers given. Do not add causes, predictions or advice. "
        f"Write in {language_name}. Reply with the summary text only."
    )
    try:
        response = _call(
            max_tokens=800,
            system=system,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Location: {location}\n"
                        f"Computed anomalies:\n{json.dumps(metrics, ensure_ascii=False, indent=2, default=str)}"
                    ),
                }
            ],
        )
    except LLMUnavailable:
        return None
    except Exception as exc:  # noqa: BLE001
        log.warning("climate summary call failed: %s", exc)
        return None
    return _text(response) or None

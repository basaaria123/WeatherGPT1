# -*- coding: utf-8 -*-
"""Language detection and translation.

Detection is script-first and runs entirely offline. For the languages this
product targets that is not a compromise — it is the more reliable option:

* Telugu occupies its own Unicode block, so detection is exact.
* Devanagari is shared by Hindi and Marathi, disambiguated by function words.
* Bengali script is shared by Bengali and Assamese, but Assamese uses ``ৰ``
  (U+09F0) and ``ৱ`` (U+09F1) where Bengali uses ``র`` and ``ব`` — a near
  perfect signal that never needs a network call.

Translation prefers the LLM (it preserves place names, relative dates like
"day after tomorrow", and weather terminology far better than a phrase table).
When the LLM is unavailable the chat engine does **not** silently answer in
English: it switches to multilingual keyword extraction plus the localised
templates in ``i18n``, so the user is still answered in their own language.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass

from .i18n import DEFAULT_LANG, LANGUAGES, normalise_lang

log = logging.getLogger("weathergpt.language")

# --- Unicode blocks ---------------------------------------------------------
_SCRIPT_RANGES: tuple[tuple[str, int, int], ...] = (
    ("devanagari", 0x0900, 0x097F),
    ("bengali", 0x0980, 0x09FF),
    ("telugu", 0x0C00, 0x0C7F),
    ("gurmukhi", 0x0A00, 0x0A7F),
    ("gujarati", 0x0A80, 0x0AFF),
    ("odia", 0x0B00, 0x0B7F),
    ("tamil", 0x0B80, 0x0BFF),
    ("kannada", 0x0C80, 0x0CFF),
    ("malayalam", 0x0D00, 0x0D7F),
)

# Assamese-only letters within the Bengali block.
_ASSAMESE_LETTERS = {"ৰ", "ৱ"}  # ৰ, ৱ

# Function words that separate the two languages sharing each script.
_MARATHI_MARKERS = ("आहे", "आणि", "नाही", "तुम्ही", "मध्ये", "कसे", "काय", "पाऊस", "हवामान", "उद्या", "साठी", "किती")
_HINDI_MARKERS = ("है", "और", "नहीं", "आप", "में", "कैसे", "क्या", "बारिश", "मौसम", "कल", "के लिए", "कितना", "हूँ", "रहा")
_ASSAMESE_MARKERS = ("বতৰ", "হৈছে", "নাই", "কেনে", "আজি", "কাইলৈ", "বৰষুণ", "ক'ত", "আছে")
_BENGALI_MARKERS = ("আবহাওয়া", "হচ্ছে", "নেই", "কেমন", "আজ", "আগামীকাল", "বৃষ্টি", "কোথায়", "আছে")

SUPPORTED = set(LANGUAGES)

# Scripts we recognise but do not yet support end-to-end.
_UNSUPPORTED_SCRIPT_LANG = {
    "gurmukhi": "pa",
    "gujarati": "gu",
    "odia": "or",
    "tamil": "ta",
    "kannada": "kn",
    "malayalam": "ml",
}


@dataclass(frozen=True)
class Detection:
    language: str
    confidence: float
    script: str
    supported: bool
    detected_raw: str  # what we actually saw, even when unsupported


def _script_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for ch in text:
        if not ch.isalpha():
            continue
        cp = ord(ch)
        if cp < 0x0250:
            counts["latin"] = counts.get("latin", 0) + 1
            continue
        for name, lo, hi in _SCRIPT_RANGES:
            if lo <= cp <= hi:
                counts[name] = counts.get(name, 0) + 1
                break
        else:
            counts["other"] = counts.get("other", 0) + 1
    return counts


def _score_markers(text: str, markers: tuple[str, ...]) -> int:
    return sum(1 for m in markers if m in text)


def detect(text: str, *, default: str = DEFAULT_LANG) -> Detection:
    """Detect the query language. Never raises; falls back to ``default``."""
    cleaned = (text or "").strip()
    if not cleaned:
        return Detection(default, 0.0, "none", True, default)

    counts = _script_counts(cleaned)
    if not counts:
        return Detection(default, 0.2, "none", True, default)

    script = max(counts, key=lambda k: counts[k])
    total = sum(counts.values()) or 1
    share = counts[script] / total

    if script == "telugu":
        return Detection("te", min(0.99, 0.75 + share * 0.24), script, True, "te")

    if script == "devanagari":
        mr = _score_markers(cleaned, _MARATHI_MARKERS)
        hi = _score_markers(cleaned, _HINDI_MARKERS)
        if mr > hi:
            return Detection("mr", min(0.95, 0.6 + 0.1 * mr), script, True, "mr")
        if hi > mr:
            return Detection("hi", min(0.95, 0.6 + 0.1 * hi), script, True, "hi")
        # Devanagari with no decisive marker: Hindi is the far likelier default.
        return Detection("hi", 0.55, script, True, "hi")

    if script == "bengali":
        if any(ch in cleaned for ch in _ASSAMESE_LETTERS):
            return Detection("as", 0.95, script, True, "as")
        as_score = _score_markers(cleaned, _ASSAMESE_MARKERS)
        bn_score = _score_markers(cleaned, _BENGALI_MARKERS)
        if as_score > bn_score:
            return Detection("as", min(0.9, 0.6 + 0.1 * as_score), script, True, "as")
        return Detection("bn", min(0.92, 0.65 + 0.08 * bn_score), script, True, "bn")

    if script in _UNSUPPORTED_SCRIPT_LANG:
        code = _UNSUPPORTED_SCRIPT_LANG[script]
        return Detection(DEFAULT_LANG, 0.8, script, False, code)

    if script == "latin":
        return Detection("en", min(0.9, 0.55 + share * 0.35), script, True, "en")

    return Detection(default, 0.3, script, True, default)


def language_name(code: str) -> str:
    from ..schemas import SUPPORTED_LANGUAGES

    return SUPPORTED_LANGUAGES.get(normalise_lang(code), code)


# ---------------------------------------------------------------------------
# Translation
# ---------------------------------------------------------------------------
class TranslationError(RuntimeError):
    """Translation could not be performed; caller must degrade, not crash."""


_TRANSLATE_SYSTEM = (
    "You are a precise translator for a weather-safety assistant used in India.\n"
    "Rules you must follow exactly:\n"
    "1. Translate the meaning, not word-for-word.\n"
    "2. Keep every number, unit and percentage exactly as given. Never change a value.\n"
    "3. Keep place names recognisable. Do not translate or invent place names.\n"
    "4. Keep relative time expressions exact: today, tomorrow, day after tomorrow, tonight.\n"
    "5. Keep weather terminology accurate (rainfall, gusts, humidity, flood, thunderstorm).\n"
    "6. Use simple everyday wording that sounds natural when read aloud.\n"
    "Reply with the translation only. No preamble, no quotes, no explanation."
)


def translate(text: str, source: str, target: str, *, llm=None) -> str:
    """Translate ``text`` from ``source`` to ``target``.

    ``llm`` is the LLM service module (injected to avoid a circular import).
    Raises ``TranslationError`` when no provider can do the work — callers are
    expected to fall back to localised templates rather than to English prose.
    """
    text = (text or "").strip()
    source = normalise_lang(source)
    target = normalise_lang(target)
    if not text or source == target:
        return text

    if llm is not None and llm.available():
        try:
            out = llm.translate_text(text, source=source, target=target, system=_TRANSLATE_SYSTEM)
            if out and out.strip():
                return out.strip()
        except Exception as exc:  # noqa: BLE001 - degrade, never crash the turn
            log.warning("LLM translation %s->%s failed: %s", source, target, exc)

    # Optional third-party providers, used only if the operator installed one.
    try:
        from deep_translator import GoogleTranslator  # type: ignore

        return GoogleTranslator(source=source, target=target).translate(text)
    except ImportError:
        pass
    except Exception as exc:  # noqa: BLE001
        log.warning("deep_translator %s->%s failed: %s", source, target, exc)

    raise TranslationError(f"No translation provider available for {source}->{target}")


def strip_diacritics(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def looks_like_gibberish(text: str) -> bool:
    """Cheap guard for empty or unusable transcriptions."""
    cleaned = re.sub(r"[\s\W_]+", "", text or "", flags=re.UNICODE)
    return len(cleaned) < 2

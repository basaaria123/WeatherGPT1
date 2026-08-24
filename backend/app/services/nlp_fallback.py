# -*- coding: utf-8 -*-
"""Deterministic query understanding, used when the LLM is unavailable.

Produces the same dict shape as ``llm.extract_query`` so the chat engine has a
single code path. It works directly on the original text in any of the six
supported languages rather than translating first — translation also needs the
LLM, so depending on it here would defeat the purpose.
"""

from __future__ import annotations

import difflib
import re
from typing import Any

from ..schemas import USER_TYPES
from . import weather
from .i18n import normalise_lang

# --- Multilingual keyword tables -------------------------------------------
WEATHER_TERMS: tuple[str, ...] = (
    # English
    "weather", "rain", "rainfall", "temperature", "temp", "wind", "storm", "flood",
    "forecast", "humid", "humidity", "hot", "cold", "sunny", "cloud", "cloudy", "fog",
    "climate", "monsoon", "cyclone", "thunder", "lightning", "heat", "heatwave",
    "alert", "warning", "advisory", "safe", "outside", "umbrella", "degrees",
    # Hindi
    "मौसम", "बारिश", "वर्षा", "तापमान", "हवा", "तूफ़ान", "तूफान", "बाढ़", "पूर्वानुमान",
    "नमी", "गर्मी", "ठंड", "धूप", "बादल", "कोहरा", "जलवायु", "मानसून", "चेतावनी", "बिजली",
    # Marathi
    "हवामान", "पाऊस", "वारा", "वादळ", "पूर", "अंदाज", "उकाडा", "थंडी", "ढग", "धुके", "इशारा",
    # Telugu
    "వాతావరణం", "వర్షం", "ఉష్ణోగ్రత", "గాలి", "తుఫాను", "వరద", "సూచన", "తేమ", "వేడి",
    "చలి", "ఎండ", "మేఘం", "పొగమంచు", "హెచ్చరిక", "పిడుగు", "వాన",
    # Bengali
    "আবহাওয়া", "বৃষ্টি", "তাপমাত্রা", "বাতাস", "ঝড়", "বন্যা", "পূর্বাভাস", "আর্দ্রতা",
    "গরম", "ঠান্ডা", "রোদ", "মেঘ", "কুয়াশা", "সতর্কতা", "বজ্র",
    # Assamese
    "বতৰ", "বৰষুণ", "উষ্ণতা", "বতাহ", "ধুমুহা", "বানপানী", "পূৰ্বাভাস", "গৰম", "ঠাণ্ডা",
    "ৰ'দ", "ডাৱৰ", "কুঁৱলী", "সতৰ্কবাণী", "বজ্ৰ",
)

# offset -> the words that mean it, across all six languages
DAY_TERMS: dict[int, tuple[str, ...]] = {
    2: ("day after tomorrow", "the day after", "overmorrow", "परसों", "परवा", "ఎల్లుండి",
        "পরশু", "পৰহিলৈ", "পরহিলৈ"),
    1: ("tomorrow", "कल", "उद्या", "रेपु", "రేపు", "আগামীকাল", "কাল", "কাইলৈ"),
    0: ("today", "now", "right now", "currently", "tonight", "आज", "अभी", "आत्ता",
        "ఈరోజు", "ఇప్పుడు", "আজ", "এখন", "আজি", "এতিয়া"),
}

ALERT_TERMS: tuple[str, ...] = (
    "alert", "alerts", "warning", "warnings", "advisory", "danger", "emergency",
    "चेतावनी", "अलर्ट", "ख़तरा", "खतरा", "इशारा", "धोका",
    "హెచ్చరిక", "ప్రమాదం", "সতর্কতা", "বিপদ", "সতৰ্কবাণী", "বিপদ",
)

TREND_TERMS: tuple[str, ...] = (
    "trend", "trends", "average", "normal", "anomaly", "climate", "compared to last",
    "this year", "wetter", "drier", "warmer", "historically", "past years",
    "औसत", "जलवायु", "रुझान", "सरासरी", "हवामान बदल",
    "సగటు", "ధోరణి", "వాతావరణ మార్పు", "প্রবণতা", "জলবায়ু", "গড়ে", "ধাৰা",
)

FORECAST_TERMS: tuple[str, ...] = (
    "forecast", "will it", "going to", "next week", "coming days", "later",
    "पूर्वानुमान", "होगी", "होगा", "अंदाज", "पडेल", "సూచన", "పడుతుందా", "ఉంటుందా",
    "পূর্বাভাস", "হবে", "পূৰ্বাভাস", "হ'ব",
)

PROFILE_TERMS: dict[str, tuple[str, ...]] = {
    "farmer": ("farm", "farming", "farmer", "crop", "crops", "harvest", "sowing", "irrigation",
               "paddy", "field", "खेती", "किसान", "फ़सल", "फसल", "शेती", "शेतकरी", "पीक",
               "వ్యవసాయం", "రైతు", "పంట", "কৃষি", "চাষ", "ফসল", "কৃষক", "খেতি", "শস্য"),
    "fisherman": ("fish", "fishing", "fisherman", "boat", "sea", "trawler", "nets", "coast",
                  "मछली", "मछुआरा", "नाव", "समुद्र", "मासेमारी", "होडी",
                  "చేపల", "పడవ", "సముద్రం", "মাছ", "নৌকা", "সমুদ্র", "মাছ ধৰা", "নাও"),
    "traveler": ("travel", "trip", "journey", "tour", "visit", "flight", "highway", "road trip",
                 "यात्रा", "सफ़र", "प्रवास", "ప్రయాణం", "যাত্রা", "ভ্রমণ", "যাত্ৰা"),
    "commuter": ("commute", "office", "work", "school", "bike", "two-wheeler", "bus", "train",
                 "दफ़्तर", "ऑफिस", "कार्यालय", "ఆఫీసు", "অফিস", "কাৰ্যালয়"),
    "aviation": ("aviation", "pilot", "airport", "runway", "takeoff", "landing", "visibility for flight"),
    "urban": ("city drainage", "waterlogging", "traffic", "urban", "municipal"),
}

# Deictic openers that signal a follow-up to the previous turn rather than a
# fresh question. Only ever consulted when a location is already established.
FOLLOWUP_TERMS: tuple[str, ...] = (
    "what about", "how about", "and", "then", "there", "also", "what if", "same",
    "और", "फिर", "वहाँ", "आणि", "मग", "तिथे",
    "మరి", "అక్కడ", "అయితే",
    "আর", "তাহলে", "সেখানে", "আৰু", "তেনেহ'লে", "তাত",
)

SIMPLE_TERMS: tuple[str, ...] = (
    "simply", "simple words", "in simple", "easy words", "short", "briefly", "explain simply",
    "आसान", "सरल", "सोप्या", "సులభంగా", "সহজ", "সহজভাৱে",
)

# Words that follow a preposition but are not places.
_STOPWORDS = {
    "the", "a", "an", "my", "your", "our", "this", "that", "here", "there",
    "today", "tomorrow", "morning", "evening", "night", "afternoon", "week",
    "area", "region", "city", "town", "village", "district", "place", "hours", "days",
}

_LOCATION_PATTERNS = (
    re.compile(r"\b(?:in|at|for|near|around|over)\s+([A-Za-z][A-Za-z\s\.'-]{2,40})", re.IGNORECASE),
    re.compile(r"\b([A-Za-z][A-Za-z\s\.'-]{2,40})\s+(?:weather|forecast|temperature|rain)\b", re.IGNORECASE),
)


_TOKEN_SPLIT = re.compile(r"[\s,.;:!?()\[\]\"'/\\\u0964-]+", re.UNICODE)


def _tokens(text: str) -> list[str]:
    return [t for t in _TOKEN_SPLIT.split(text.lower()) if t]


def _contains(text: str, terms: tuple[str, ...]) -> bool:
    """Keyword match that respects Indic agglutination without false positives.

    Single words match at a token *start*, so "వాతావరణంలో" still matches
    "వాతావరణం" (suffixing languages append, they do not prepend) while
    "ডিব্ৰুগড়ত" no longer matches "গড়" ("average") buried in its middle.
    Multi-word phrases fall back to plain substring matching.
    """
    lowered = text.lower()
    tokens = _tokens(lowered)
    for term in terms:
        needle = term.lower()
        if " " in needle:
            if needle in lowered:
                return True
        elif any(token.startswith(needle) for token in tokens):
            return True
    return False


# The English nouns worth correcting a typo for. Kept small so fuzzy matching
# cannot quietly pull unrelated words into scope.
_FUZZY_CORE: tuple[str, ...] = (
    "weather", "rain", "rainfall", "forecast", "temperature", "humidity",
    "storm", "flood", "cyclone", "monsoon", "thunder", "lightning", "sunny",
    "cloudy", "windy", "climate", "drizzle", "heatwave",
)
# Real English words that are near-misses for the above and must not trigger.
_FUZZY_BLOCK = frozenset({"whether", "wetter", "rein", "reign", "brain", "train", "drain", "grain", "chain"})


def _fuzzy_weather_token(text: str) -> bool:
    """Tolerate a typo in a core weather noun without widening scope generally."""
    for token in _tokens(text):
        if len(token) < 4 or not token.isascii() or token in _FUZZY_BLOCK:
            continue
        if difflib.get_close_matches(token, _FUZZY_CORE, n=1, cutoff=0.82):
            return True
    return False


def is_weather_related(text: str) -> bool:
    """Scope guardrail for the no-LLM path."""
    return _contains(text, WEATHER_TERMS) or _fuzzy_weather_token(text)


def detect_day_offset(text: str) -> int:
    lowered = text.lower()
    # Longest phrases first: "day after tomorrow" must beat "tomorrow".
    for offset in (2, 1, 0):
        if _contains(text, DAY_TERMS[offset]):
            return offset
    match = re.search(r"\bin\s+(\d)\s+days?\b", lowered)
    if match:
        return max(0, min(6, int(match.group(1))))
    return 0


def detect_user_type(text: str) -> str | None:
    for profile, terms in PROFILE_TERMS.items():
        if _contains(text, terms) and profile in USER_TYPES:
            return profile
    return None


def detect_intent(text: str, day_offset: int) -> str:
    if _contains(text, ALERT_TERMS):
        return "alert_check"
    if _contains(text, TREND_TERMS):
        return "climate_trend"
    if day_offset > 0 or _contains(text, FORECAST_TERMS):
        return "forecast"
    return "current_weather"


def detect_location(text: str) -> weather.Location | None:
    """Resolve a place from raw text.

    Native-script and whole-string fuzzy matching happen inside
    ``gazetteer_lookup``; the regexes below only help when an English sentence
    wraps the place name in filler.
    """
    native = weather.native_lookup(text)
    if native is not None:
        return native

    for pattern in _LOCATION_PATTERNS:
        for match in pattern.finditer(text):
            candidate = match.group(1).strip(" .,'-")
            # Trim trailing filler: "Guwahati today" -> "Guwahati"
            words = [w for w in candidate.split() if w.lower() not in _STOPWORDS]
            while words:
                found = weather.gazetteer_lookup(" ".join(words))
                if found is not None:
                    return found
                words.pop()

    # Last resort: does any token match the gazetteer directly?
    for token in re.findall(r"[A-Za-z][A-Za-z'-]{3,}", text):
        if token.lower() in _STOPWORDS:
            continue
        found = weather.gazetteer_lookup(token, cutoff=0.86)
        if found is not None:
            return found
    return None


def extract(query: str, *, language: str = "en", known_location: str | None = None) -> dict[str, Any]:
    """Mirror of ``llm.extract_query`` built from rules only."""
    text = (query or "").strip()
    day_offset = detect_day_offset(text)
    location = detect_location(text)
    user_type = detect_user_type(text)

    # Scope is broader than the weather nouns: asking about alerts, averages or
    # a forecast is on-topic even when the word "weather" never appears.
    in_scope = (
        is_weather_related(text)
        or _contains(text, ALERT_TERMS)
        or _contains(text, TREND_TERMS)
        or _contains(text, FORECAST_TERMS)
    )
    if not in_scope and location is not None and (day_offset > 0 or user_type is not None):
        # "I'm a farmer near Warangal, should I harvest tomorrow?"
        in_scope = True
    if not in_scope and known_location and (day_offset > 0 or _contains(text, FOLLOWUP_TERMS)):
        # A bare follow-up ("and tomorrow?", "మరి ఎల్లుండి?") continues the
        # running topic rather than starting a new, locationless question.
        in_scope = True

    intent = detect_intent(text, day_offset) if in_scope else "out_of_scope"

    return {
        "in_scope": in_scope,
        "intent": intent,
        "location": location.name if location else "",
        "use_previous_location": location is None and bool(known_location),
        "day_offset": day_offset,
        "user_type": user_type or "general",
        "response_mode": "simple" if _contains(text, SIMPLE_TERMS) else "normal",
        "language": normalise_lang(language),
        "_source": "rules",
    }

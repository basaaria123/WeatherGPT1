# -*- coding: utf-8 -*-
"""What a reader gets when the translation round trip fails.

The one thing that must never happen is an English answer to someone who chose
Telugu. It is the failure a remote deployment hits most — composition succeeds,
the extra translate call is the one that meets the rate limit or the function's
time budget — and it is silent, because nothing on screen says the language was
dropped.
"""

from __future__ import annotations

import re
from unittest.mock import patch

import pytest

from app.schemas import DegradationInfo
from app.services import advisory, chat_engine, language, risk_engine, weather

SCRIPTS = {
    "te": r"[ఀ-౿]",
    "hi": r"[ऀ-ॿ]",
    "as": r"[ঀ-৿]",
    "bn": r"[ঀ-৿]",
    "mr": r"[ऀ-ॿ]",
    "ta": r"[஀-௿]",
}
ENGLISH = "The weather in Hyderabad today is mainly clear with a temperature of 29.8 degrees."


def _localised_for(lang: str):
    bundle = weather.fetch_weather(weather.geocode("Hyderabad"))
    risk = risk_engine.assess(bundle)

    def build():
        return (
            advisory.templated_answer(
                bundle, risk, intent="current_weather", user_type="general",
                lang=lang, mode="normal", day_offset=0, advice_question=False,
            ),
            advisory.smart_explanation(bundle, risk, lang, mode="simple") or None,
        )

    return build


@pytest.mark.parametrize("lang", sorted(SCRIPTS))
def test_a_failed_translation_falls_back_to_the_template_not_to_english(lang):
    """The localised template is written in the reader's language. English is not."""
    with patch.object(language, "translate", side_effect=language.TranslationError("rate limited")):
        answer, explanation, degraded = chat_engine._ensure_language(
            ENGLISH, "why, in English", lang, DegradationInfo(), localised=_localised_for(lang)
        )
    assert answer != ENGLISH, lang
    assert re.search(SCRIPTS[lang], answer), answer
    # An English "why this answer" under a translated answer is the same bug
    # one panel down, so the explanation is replaced rather than carried over.
    assert explanation != "why, in English"
    assert degraded.fallback_reason, "the drop was not recorded"


@pytest.mark.parametrize("lang", sorted(SCRIPTS))
def test_a_translation_that_returns_nothing_is_treated_as_a_failure(lang):
    """`translate` may return None rather than raise; both mean the same thing."""
    with patch.object(language, "translate", return_value=None):
        answer, _, degraded = chat_engine._ensure_language(
            ENGLISH, None, lang, DegradationInfo(), localised=_localised_for(lang)
        )
    assert answer != ENGLISH
    assert re.search(SCRIPTS[lang], answer), answer
    assert degraded.translation_error


def test_a_working_translation_is_still_preferred():
    """The template is the fallback, not the default: a real translation wins."""
    with patch.object(language, "translate", return_value="అనువదించిన సమాధానం"):
        answer, _, degraded = chat_engine._ensure_language(
            ENGLISH, None, "te", DegradationInfo(), localised=_localised_for("te")
        )
    assert answer == "అనువదించిన సమాధానం"
    assert not degraded.fallback_reason


def test_an_answer_already_in_the_right_language_is_left_alone():
    """No round trip when composition did what it was asked."""
    telugu = "హైదరాబాద్‌లో ఈరోజు వాతావరణం ప్రధానంగా నిర్మలంగా ఉంది."
    with patch.object(language, "translate", side_effect=AssertionError("should not translate")):
        answer, _, _ = chat_engine._ensure_language(
            telugu, None, "te", DegradationInfo(), localised=_localised_for("te")
        )
    assert answer == telugu


def test_english_never_takes_the_fallback_path():
    with patch.object(language, "translate", side_effect=AssertionError("should not translate")):
        answer, _, _ = chat_engine._ensure_language(ENGLISH, None, "en", DegradationInfo())
    assert answer == ENGLISH


def test_a_broken_template_does_not_cost_the_answer():
    """A fallback that raises is still better than a 500."""
    def explode():
        raise RuntimeError("template blew up")

    answer, _, _ = chat_engine._ensure_language(
        ENGLISH, None, "te", DegradationInfo(), localised=explode
    )
    assert answer == ENGLISH  # degraded, but delivered


@pytest.mark.parametrize("lang", ["te", "hi", "as"])
def test_the_endpoint_answers_in_the_chosen_language(client, lang):
    """The three the tester reported, end to end through the real route."""
    body = client.post(
        "/chat",
        json={
            "query": "What is the weather in Hyderabad today?",
            "location": "Hyderabad",
            "user_type": "general",
            "language": lang,
        },
    ).json()
    assert body["language"] == lang
    assert re.search(SCRIPTS[lang], body["answer"]), body["answer"]


def test_english_still_answers_in_english(client):
    body = client.post(
        "/chat",
        json={"query": "What is the weather in Hyderabad today?", "location": "Hyderabad",
              "user_type": "general", "language": "en"},
    ).json()
    assert body["language"] == "en"
    assert not re.search(r"[ऀ-෿]", body["answer"]), body["answer"]

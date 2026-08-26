# -*- coding: utf-8 -*-
"""Role 3 — voice, language, context, emergency mode and grounded explanation.

These cover the paths that run when the LLM is unavailable, because that is the
floor the product has to hold: understanding, language and safety advice all
have to keep working without a provider.
"""

from __future__ import annotations

import os
import re

import pytest

os.environ.setdefault("WEATHER_DATA_MODE", "fixture")

from app.services import advisory, i18n, nlp_fallback, risk_engine, weather  # noqa: E402

SCRIPTS = {
    "hi": r"[ऀ-ॿ]",
    "mr": r"[ऀ-ॿ]",
    "te": r"[ఀ-౿]",
    "bn": r"[ঀ-৿]",
    "as": r"[ঀ-৿]",
}


def bundle(city: str, scenario: str):
    os.environ["WEATHER_FIXTURE_SCENARIO"] = scenario
    weather.clear_cache()
    return weather.fetch_weather(weather.gazetteer_lookup(city))


# ---------------------------------------------------------------------------
# Multilingual understanding
# ---------------------------------------------------------------------------
# Inflected forms: these languages attach case endings, so a term list holding
# one fixed form silently stops matching the moment a user phrases it normally.
IN_SCOPE = [
    ("te", "ఈరోజు ప్రయాణం చేయడం సురక్షితమేనా?"),
    ("te", "బయటికి వెళ్లడం సురక్షితమా?"),
    ("te", "ఏ జాగ్రత్తలు తీసుకోవాలి?"),
    ("te", "ఈరోజు వర్షం పడుతుందా?"),
    ("hi", "क्या आज यात्रा करना सुरक्षित है?"),
    ("hi", "क्या सावधानियाँ बरतनी चाहिए?"),
    ("mr", "आज प्रवास करणे सुरक्षित आहे का?"),
    ("mr", "काय खबरदारी घ्यावी?"),
    ("bn", "আজ ভ্রমণ করা কি নিরাপদ?"),
    ("as", "আজি যাত্ৰা কৰাটো নিৰাপদ নেকি?"),
    ("as", "কি সাৱধানতা ল'ব লাগে?"),
]


@pytest.mark.parametrize("lang,query", IN_SCOPE)
def test_indic_safety_questions_are_understood(lang, query):
    assert nlp_fallback.extract(query, language=lang, known_location="Guwahati")["in_scope"], query


@pytest.mark.parametrize(
    "query",
    ["ఒక కవిత రాయండి", "मुझे एक कविता लिखो", "এটা কবিতা লিখা", "who won the match?"],
)
def test_off_topic_is_still_redirected_in_every_script(query):
    assert not nlp_fallback.extract(query, known_location="Guwahati")["in_scope"], query


@pytest.mark.parametrize("lang", ["hi", "te", "bn", "mr", "as"])
def test_answers_come_back_in_the_asked_language(lang):
    """A non-English question must never be answered in English."""
    b = bundle("Guwahati", "flood")
    text = advisory.templated_answer(
        b, risk_engine.assess(b), intent="current_weather", user_type="general", lang=lang
    )
    assert re.search(SCRIPTS[lang], text), f"{lang} answer had no native script: {text[:80]}"


@pytest.mark.parametrize("lang", ["hi", "te", "bn", "mr", "as"])
def test_numbers_survive_translation_unchanged(lang):
    """Weather values are substituted, not translated, so they must appear
    identically whichever language is asked for."""
    b = bundle("Guwahati", "flood")
    risk = risk_engine.assess(b)
    english = advisory.templated_answer(b, risk, intent="current_weather", user_type="general", lang="en")
    other = advisory.templated_answer(b, risk, intent="current_weather", user_type="general", lang=lang)
    english_numbers = set(re.findall(r"\d+\.?\d*", english))
    other_numbers = set(re.findall(r"\d+\.?\d*", other))
    assert english_numbers == other_numbers, f"{lang}: {english_numbers ^ other_numbers}"


# ---------------------------------------------------------------------------
# Emergency mode
# ---------------------------------------------------------------------------
def test_each_hazard_gets_its_own_actions():
    """One shared checklist for every hazard is the failure mode here: telling
    someone in a heatwave to avoid flood water is worse than saying nothing."""
    per_hazard = {}
    for city, scenario in [("Guwahati", "flood"), ("Mumbai", "storm"), ("Jaisalmer", "heat"), ("Puri", "wind")]:
        b = bundle(city, scenario)
        risk = risk_engine.assess(b)
        per_hazard[risk.detected_hazard] = set(advisory.action_checklist(risk, "general", "en"))

    assert len(per_hazard) == 4, per_hazard.keys()
    shared = set.intersection(*per_hazard.values())
    assert not shared, f"identical advice across hazards: {shared}"


def test_emergency_mode_stays_off_in_calm_conditions():
    b = bundle("Bengaluru", "calm")
    risk = risk_engine.assess(b)
    assert not risk_engine.is_actionable(risk)
    assert advisory.action_checklist(risk, "farmer", "en") == []


def test_emergency_brief_states_hazard_why_and_what_to_do():
    b = bundle("Guwahati", "flood")
    risk = risk_engine.assess(b)
    brief = advisory.emergency_brief(b, risk, "farmer", "en")
    assert i18n.hazard_label(risk.detected_hazard, "en") in brief
    for section in ("What is happening", "Why it matters", "What to do"):
        assert section in brief, section
    assert str(risk.risk_score) in brief


# ---------------------------------------------------------------------------
# User-specific advice
# ---------------------------------------------------------------------------
def test_every_profile_receives_different_leading_advice():
    b = bundle("Mumbai", "storm")
    risk = risk_engine.assess(b)
    leads = {p: advisory.action_checklist(risk, p, "en")[0]
             for p in ("farmer", "fisherman", "traveler", "commuter", "general")}
    assert len(set(leads.values())) == 5, leads


def test_profile_advice_is_translated_too():
    b = bundle("Mumbai", "storm")
    risk = risk_engine.assess(b)
    for lang in ("hi", "te", "as"):
        lead = advisory.action_checklist(risk, "fisherman", lang)[0]
        assert re.search(SCRIPTS[lang], lead), f"{lang}: {lead}"


# ---------------------------------------------------------------------------
# Smart explanation grounding
# ---------------------------------------------------------------------------
def test_explanation_only_quotes_values_the_provider_returned():
    b = bundle("Bengaluru", "calm")
    text = advisory.smart_explanation(b, risk_engine.assess(b), "en")
    cur = b.current
    allowed = set()
    for value in (cur.get("temperature_c"), cur.get("apparent_temperature_c"),
                  cur.get("humidity_pct"), cur.get("wind_speed_kmh"),
                  cur.get("precipitation_probability_pct")):
        if value is None:
            continue
        allowed |= {str(int(round(value))), f"{value:.1f}", str(value)}
    allowed |= {str(h) for h in range(0, 25)}  # hour counts in "next N hours"

    for number in re.findall(r"\d+\.?\d*", text):
        assert number in allowed, f"unsupported number {number!r} in: {text}"


# ---------------------------------------------------------------------------
# Regressions found by tracing the Role 3 features end to end.
#
# Each of these failed before the fix, in the no-LLM path that a demo actually
# runs on. They are written against ``handle_chat`` rather than the helpers so
# they cover the wiring, which is where all four bugs lived.
# ---------------------------------------------------------------------------
PERSONAS = ("general", "farmer", "fisherman", "traveler", "commuter")


def _answers_by_persona(scenario: str, question: str = "What is the weather in Vijayawada today?"):
    os.environ["WEATHER_FIXTURE_SCENARIO"] = scenario
    # Bundles are cached for ten minutes, so a scenario switch inside one
    # process would otherwise re-read the previous scenario's weather.
    weather.clear_cache()
    from app.services import chat_engine

    out = {}
    for persona in PERSONAS:
        response = chat_engine.handle_chat(
            query=question, user_type=persona, session_id=f"reg-{scenario}-{persona}"
        )
        out[persona] = response
    return out


@pytest.mark.parametrize("scenario", ["calm", "rain", "storm", "flood", "heat", "wind"])
def test_selected_role_changes_the_answer_at_every_risk_level(scenario):
    """The role reached the advisory panel but not the answer.

    Below the emergency threshold every persona was handed the same sentence,
    which is precisely the calm-weather case a demo is most likely to hit.
    """
    answers = {p: r.answer for p, r in _answers_by_persona(scenario).items()}
    assert len(set(answers.values())) == len(PERSONAS), (
        f"{scenario}: personas share an answer -> {answers}"
    )


@pytest.mark.parametrize("scenario", ["calm", "rain", "storm", "flood", "heat", "wind"])
def test_advisory_is_never_empty_and_differs_from_general(scenario):
    """``build_advisory`` returned nothing when no hazard was named."""
    responses = _answers_by_persona(scenario)
    general = [a.action for a in responses["general"].advisory.actions]
    assert general, f"{scenario}: general advisory is empty"
    for persona in ("farmer", "fisherman", "traveler", "commuter"):
        actions = [a.action for a in responses[persona].advisory.actions]
        assert actions, f"{scenario}/{persona}: advisory is empty"
        assert actions != general, f"{scenario}/{persona}: advisory matches general"


def test_safety_follow_up_keeps_the_place_and_answers_about_safety():
    """"Is it safe to travel?" kept Hyderabad but replied with a plain reading."""
    os.environ["WEATHER_FIXTURE_SCENARIO"] = "rain"
    weather.clear_cache()
    from app.services import chat_engine

    session = "reg-context"
    first = chat_engine.handle_chat(
        query="What is the weather in Hyderabad today?", user_type="traveler", session_id=session
    )
    assert first.location and first.location.name == "Hyderabad"

    second = chat_engine.handle_chat(
        query="Is it safe to travel?", user_type="traveler", session_id=session
    )
    assert second.location and second.location.name == "Hyderabad", "lost the running location"
    assert second.answer != first.answer, "the safety question got the same generic answer"
    # The travel-specific line from the rules table, not an invented one.
    assert i18n.profile_action("traveler", second.risk.detected_hazard, "en") in second.answer

    third = chat_engine.handle_chat(
        query="What about tomorrow?", user_type="traveler", session_id=session
    )
    assert third.location and third.location.name == "Hyderabad"
    assert third.intent == "forecast"


def test_assamese_place_names_and_advice_questions_resolve():
    """Assamese ৰ/ৱ never matched the Bengali র/ব stored in the gazetteer, and
    "can I go outside?" in Assamese fell out of scope while Telugu did not."""
    os.environ["WEATHER_FIXTURE_SCENARIO"] = "rain"
    weather.clear_cache()
    from app.services import chat_engine

    assert weather.native_lookup("হায়দৰাবাদত").name == "Hyderabad"
    assert weather.native_lookup("গুৱাহাটীত").name == "Guwahati"
    assert nlp_fallback.is_advice_question("মই বাহিৰলৈ যাব পাৰোঁনে?")

    response = chat_engine.handle_chat(
        query="মই বাহিৰলৈ যাব পাৰোঁনে?",
        user_type="traveler",
        session_id="reg-as",
        selected_location="Vijayawada",
    )
    assert response.in_scope, "Assamese advice question was redirected as off-topic"
    assert response.language == "as"
    assert re.search(SCRIPTS["as"], response.answer)


def test_emergency_mode_still_only_fires_on_measured_risk():
    """The persona wiring must not manufacture a warning on a calm day."""
    calm = _answers_by_persona("calm")["farmer"]
    assert calm.risk.risk_level == "Low"
    assert calm.action_mode is False
    assert calm.actions == []

    severe = _answers_by_persona("flood")["farmer"]
    assert severe.risk.risk_level in {"High", "Severe"}
    assert severe.action_mode is True
    assert severe.actions

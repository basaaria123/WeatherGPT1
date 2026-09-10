# -*- coding: utf-8 -*-
"""What WeatherGPT says when it speaks.

The tests that matter here are about restraint and register: a spoken brief
must lead with what to do rather than what was measured, must get shorter and
plainer as the weather gets worse, and must never be English wearing another
language's name.
"""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import RiskOutput
from app.services import i18n, voice_brief

client = TestClient(app)

LANGUAGES = list(i18n.LANGUAGES) if hasattr(i18n, "LANGUAGES") else ["en", "hi", "te", "bn", "mr", "as", "ta", "kn", "ml", "gu", "pa"]

ADVISORY = {
    "actions": [
        {"action": "Move harvested grain to a dry, raised place.", "priority": 1},
        {"action": "Move to higher ground if water enters your area.", "priority": 2},
        {"action": "Keep documents and medicines in a waterproof bag.", "priority": 3},
        {"action": "Do not walk through moving flood water.", "priority": 4},
    ]
}


def risk(level: str, hazard: str = "Flood Risk", score: int = 70) -> RiskOutput:
    return RiskOutput(risk_score=score, risk_level=level, detected_hazard=hazard)


def lead_of(text: str) -> str:
    """Everything the brief says before its first action.

    Not "the first sentence": a lead is allowed more than one, and the leads
    for High and Severe deliberately open the same way before diverging. The
    actions are the fixture's own English, so they are a reliable boundary in
    every language — minus the trailing stop, which the brief replaces with
    whichever terminator the language actually uses.
    """
    boundary = ADVISORY["actions"][0]["action"].rstrip(" .")
    return text.split(boundary)[0].strip()


def hours(peak_at: int = 3, level: str = "High") -> list[dict]:
    return [
        {
            "time": f"2026-09-08T{(14 + i) % 24:02d}:00",
            "risk_score": 80 if i == peak_at else 20,
            "risk_level": level if i == peak_at else "Low",
        }
        for i in range(6)
    ]


def test_nothing_to_say_stays_silent():
    """No actions means no audio button, not a sentence about nothing."""
    assert voice_brief.compose(location="Puri", risk=risk("Low"), advisory={"actions": []}) == ""


def test_the_brief_leads_with_what_to_do():
    text = voice_brief.compose(location="Puri", risk=risk("Moderate"), advisory=ADVISORY)
    assert "Move harvested grain to a dry, raised place" in text
    # The counter-example from the brief: a spoken advisory is not a readout.
    assert not re.search(r"humidity|hPa|percent humidity|kilometres per hour", text, re.I)


def test_severity_changes_the_register_not_only_the_words():
    """Calm is allowed a clause; severe is instructions.

    The synthesiser has one voice at one speed, so the only thing that can make
    a brief sound urgent is the shape of its sentences. This is that promise,
    written down. Note what is *not* claimed: High is meant to be direct, not
    brief — it spends words naming the level and issuing an imperative, and can
    run slightly longer than the calm lead as a result. Only Severe is short.
    """
    calm = voice_brief.compose(location="Puri", risk=risk("Low"), advisory=ADVISORY, hours=hours())
    high = voice_brief.compose(location="Puri", risk=risk("High"), advisory=ADVISORY, hours=hours())
    severe = voice_brief.compose(location="Puri", risk=risk("Severe"), advisory=ADVISORY, hours=hours())

    leads = [lead_of(text) for text in (calm, high, severe)]
    assert len(set(leads)) == 3, leads
    assert len(leads[2]) < min(len(leads[0]), len(leads[1])), leads

    # Timing helps when there is time to use it and competes with a step when
    # there is not, so severe drops it. Read from the fixture rather than typed
    # in, so a change to the fixture cannot leave this quietly asserting on an
    # hour that is no longer the peak.
    peak = hours()[3]["time"][11:16]
    assert peak in calm and peak in high
    assert peak not in severe


@pytest.mark.parametrize("level", ["Low", "Moderate", "High", "Severe"])
def test_the_voice_gives_one_action_however_bad_it_gets(level):
    """The screen ranks three to five; the voice speaks the one that matters.

    A reader can scan a list. A listener cannot — by the fourth item the first
    is gone — so a spoken list is the thing people stop listening to. The extra
    steps stay on the card, which is where a list belongs.
    """
    spoken = voice_brief.compose(location="Puri", risk=risk(level), advisory=ADVISORY)
    assert ADVISORY["actions"][0]["action"].rstrip(".") in spoken
    for extra in ADVISORY["actions"][1:]:
        assert extra["action"].rstrip(".") not in spoken, (level, spoken)


def test_a_window_is_only_claimed_when_the_forecast_shows_one():
    flat = [{"time": f"2026-09-08T{14 + i:02d}:00", "risk_score": 10, "risk_level": "Low"} for i in range(6)]
    text = voice_brief.compose(location="Puri", risk=risk("Moderate"), advisory=ADVISORY, hours=flat)
    assert not re.search(r"\d\d:\d\d", text), text
    # Nor when the peak is the hour the reader is already in.
    now = voice_brief.compose(
        location="Puri", risk=risk("Moderate"), advisory=ADVISORY, hours=hours(peak_at=0)
    )
    assert not re.search(r"\d\d:\d\d", now), now


def test_a_clear_day_does_not_open_by_naming_a_hazard():
    text = voice_brief.compose(
        location="Puri", risk=risk("Low", hazard="None", score=5), advisory=ADVISORY
    )
    assert "Puri" in text
    assert "None" not in text


def test_official_warnings_are_spoken_and_agree_with_themselves():
    one = voice_brief.compose(location="Puri", risk=risk("High"), advisory=ADVISORY, alert_count=1)
    many = voice_brief.compose(location="Puri", risk=risk("High"), advisory=ADVISORY, alert_count=3)
    assert "is 1 active weather alert" in one
    assert "are 3 active weather alerts" in many
    # A calm day's brief is not the place for an alert count.
    calm = voice_brief.compose(location="Puri", risk=risk("Low"), advisory=ADVISORY, alert_count=3)
    assert "active weather" not in calm


@pytest.mark.parametrize("lang", ["hi", "te", "bn", "mr", "as", "ta", "kn", "ml", "gu", "pa"])
def test_the_lead_is_translated_in_every_language(lang):
    """The words we wrote for the voice must exist in every language we offer.

    Only the lead is checked: the actions come from the advisory, which has its
    own parity tests, and asserting on those here would just duplicate them.
    """
    for level in ("Low", "High", "Severe"):
        lead = lead_of(
            voice_brief.compose(location="Puri", risk=risk(level), advisory=ADVISORY, lang=lang)
        )
        assert not re.search(r"[A-Za-z]{4,}", lead.replace("Puri", "")), (lang, level, lead)


# --- The endpoint -----------------------------------------------------------
def test_spoken_advice_returns_the_script_even_when_synthesis_fails():
    """Losing the audio must never mean losing the advice.

    This deployment has no route to a voice provider, so the response arrives
    with `tts_error` set — and still 200, still carrying the exact script, which
    is what lets the browser read it aloud instead.
    """
    body = client.get(
        "/weather/spoken-advice", params={"location": "Guwahati", "user_type": "farmer"}
    ).json()
    assert body["text"]
    assert body["risk_level"] in {"Low", "Moderate", "High", "Severe"}
    assert body["audio_base64"] or body["tts_error"]


def test_spoken_advice_is_written_for_the_reader_who_asked():
    def script(role):
        return client.get(
            "/weather/spoken-advice", params={"location": "Guwahati", "user_type": role}
        ).json()["text"]

    assert script("farmer") != script("fisherman")


def test_spoken_advice_speaks_the_language_it_was_asked_for():
    body = client.get(
        "/weather/spoken-advice",
        params={"location": "Guwahati", "user_type": "farmer", "language": "ta"},
    ).json()
    assert body["language"] == "ta"
    assert re.search(r"[\u0b80-\u0bff]", body["text"]), body["text"]


# ---------------------------------------------------------------------------
# What a model is and is not allowed to touch
# ---------------------------------------------------------------------------
def test_the_brief_splits_framing_from_instructions():
    """The split is the safety property, so it is asserted rather than assumed."""
    parts = voice_brief.compose_parts(location="Puri", risk=risk("Severe"), advisory=ADVISORY)
    assert parts["framing"], parts
    assert parts["steps"], parts
    # The framing describes; it never instructs.
    for action in (a["action"] for a in ADVISORY["actions"]):
        assert action.rstrip(".") not in parts["framing"]
    # Every spoken step is the advisory's own sentence, unchanged.
    assert ADVISORY["actions"][0]["action"].rstrip(".") in parts["steps"]


def test_polish_is_never_handed_an_instruction(monkeypatch):
    """Structural, not filtered — the model cannot rewrite what it never sees.

    Asked to rewrite a farmer's flood advice, Gemini once turned "move
    harvested grain and fertiliser to a dry, raised place" into "move harvested
    grain, fertilizer, and livestock to higher ground": fluent, plausible, and
    an instruction nobody wrote. No output check short of understanding the
    domain would have caught it, so the instructions are simply never sent.
    """
    seen: list[str] = []

    def fake_voice_line(text, **kwargs):
        seen.append(text)
        return None

    monkeypatch.setattr(voice_brief.llm, "available", lambda: True)
    monkeypatch.setattr(voice_brief.llm, "voice_line", fake_voice_line)

    parts = voice_brief.compose_parts(location="Puri", risk=risk("Severe"), advisory=ADVISORY)
    voice_brief.polish(
        parts["framing"], lang="en", user_type="farmer", location="Puri", risk_level="Severe"
    )
    assert len(seen) == 1
    for action in (a["action"] for a in ADVISORY["actions"]):
        assert action.rstrip(".") not in seen[0], seen[0]


def test_a_rewrite_that_invents_a_figure_is_discarded(monkeypatch):
    monkeypatch.setattr(voice_brief.llm, "available", lambda: True)
    monkeypatch.setattr(
        voice_brief.llm, "voice_line", lambda text, **kw: "Flood risk in Puri, 95% chance."
    )
    framing = "Flood Risk in Puri. Do this now."
    assert voice_brief.polish(
        framing, lang="en", user_type="farmer", location="Puri", risk_level="Severe"
    ) == framing


def test_a_rewrite_that_rambles_is_discarded(monkeypatch):
    monkeypatch.setattr(voice_brief.llm, "available", lambda: True)
    monkeypatch.setattr(voice_brief.llm, "voice_line", lambda text, **kw: text + " " + text)
    framing = "Flood Risk in Puri. Do this now."
    assert voice_brief.polish(
        framing, lang="en", user_type="farmer", location="Puri", risk_level="Severe"
    ) == framing


def test_a_good_rewrite_is_kept(monkeypatch):
    monkeypatch.setattr(voice_brief.llm, "available", lambda: True)
    monkeypatch.setattr(voice_brief.llm, "voice_line", lambda text, **kw: "Flooding in Puri. Act now.")
    assert voice_brief.polish(
        "Flood Risk in Puri. Do this now.",
        lang="en", user_type="farmer", location="Puri", risk_level="Severe",
    ) == "Flooding in Puri. Act now."


def test_no_model_means_the_deterministic_text_verbatim(monkeypatch):
    monkeypatch.setattr(voice_brief.llm, "available", lambda: False)
    framing = "Flood Risk in Puri. Do this now."
    assert voice_brief.polish(
        framing, lang="ta", user_type="farmer", location="Puri", risk_level="Severe"
    ) == framing


def test_the_endpoint_speaks_the_advisory_word_for_word(client):
    """Whatever the model did to the framing, the steps are the rules table's."""
    current = client.get(
        "/weather/current", params={"location": "Guwahati", "user_type": "farmer"}
    ).json()
    spoken = client.get(
        "/weather/spoken-advice", params={"location": "Guwahati", "user_type": "farmer"}
    ).json()
    lead = current["advisory"]["actions"][0]["action"]
    assert lead.rstrip(".") in spoken["text"], spoken["text"]

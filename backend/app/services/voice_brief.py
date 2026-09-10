# -*- coding: utf-8 -*-
"""What WeatherGPT says out loud, and how it carries itself while saying it.

A spoken brief is not the dashboard read down a microphone. Nobody listens to
"31 degrees, 72 percent humidity, 14 kilometres per hour" and then knows what
to do; they listen to "rain within two hours — finish the outdoor work first"
and act. So this module composes the shortest sentence that answers *what do I
do now*, from the same advisory the screen is already showing.

Everything spoken here is assembled from strings the translated corpus already
carries — the hazard name, the risk level, this reader's own advisory actions —
plus four short connectives per language. Nothing is written for the voice that
is not also written for the screen, so the two can never say different things.

TONE. The synthesiser has no prosody control: gTTS reads what it is given, at
one speed, in one voice. So "calmer" and "more urgent" are not settings we can
send it — they are properties of the sentences we hand it, and that is where
this module puts them:

    Low / Moderate  conversational — a lead that frames, two actions, unhurried
    High            direct — the hazard and the level up front, then act
    Severe          instruction-only — the shortest lead, three bare steps

That is a real difference a listener can hear, because sentence length and
clause count are most of what makes a synthetic voice sound calm or urgent. It
is also the honest limit: we shape the words, not the voice.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from . import i18n, language as language_service, llm

log = logging.getLogger("weathergpt.voice_brief")

# One action, at every level.
#
# The screen lists three to five, ranked, and a reader can scan them. A
# listener cannot: by the time the fourth arrives the first is gone, and a
# spoken list is the thing people stop listening to. So the voice gives the
# one that matters and leaves the rest on the card, which is where a list
# belongs.
ACTIONS_SPOKEN = {"Low": 1, "Moderate": 1, "High": 1, "Severe": 1}

URGENT_LEVELS = ("High", "Severe")


def _clock(stamp: Any) -> str:
    text = str(stamp or "")
    return text.split("T", 1)[1][:5] if "T" in text else ""


def _hazard_window(hours: list[dict[str, Any]]) -> str | None:
    """When the hazard is expected, from the forecast the screen already shows.

    Timing is the single most actionable thing a spoken brief can carry — it is
    the difference between "rain is coming" and "finish before four". It is
    returned only when the forecast actually puts the peak ahead of the reader:
    an hour that has already passed is not a warning, and the current hour does
    not need one.
    """
    if not hours:
        return None
    peak = max(range(len(hours)), key=lambda i: hours[i].get("risk_score") or 0)
    if peak == 0 or (hours[peak].get("risk_level") or "Low") == "Low":
        return None
    return _clock(hours[peak].get("time")) or None


def compose_parts(
    *,
    location: str,
    risk: Any,
    advisory: dict[str, Any],
    hours: list[dict[str, Any]] | None = None,
    alert_count: int = 0,
    lang: str = "en",
) -> str:
    """The spoken brief, in two halves.

    ``framing`` is what WeatherGPT says about the situation — ours to phrase.
    ``steps`` are the advisory's own instructions, verbatim.

    Both are empty when there is nothing worth saying aloud, so the caller
    offers no audio rather than reading out a sentence about nothing.
    """
    lang = i18n.normalise_lang(lang)
    level = getattr(risk, "risk_level", None) or "Low"
    hazard = getattr(risk, "detected_hazard", None) or "None"
    actions = [line for line in (a.get("action") or "" for a in advisory.get("actions") or []) if line]
    if not actions:
        return {"framing": "", "steps": ""}

    hazard_text = i18n.hazard_label(hazard, lang) if hazard != "None" else ""

    # The lead does the work the voice cannot: it sets the register. Severe
    # states the hazard and stops; a calm day is allowed a whole clause.
    if level == "Severe" or level == "High":
        # An elevated score always comes from a hazard, but if one ever arrives
        # without a name, the level is the subject rather than an empty gap.
        subject = hazard_text or i18n.level_label(level, lang)
        key = "vb_lead_severe" if level == "Severe" else "vb_lead_high"
        lead = i18n.sentence(
            key, lang, loc=location, hazard=subject, level=i18n.level_label(level, lang)
        )
    elif hazard_text:
        lead = i18n.sentence("vb_lead_calm", lang, loc=location, hazard=hazard_text)
    else:
        # Nothing detected. The advisory still has something worth doing, but
        # the brief must not open by naming a hazard that is not there.
        lead = i18n.sentence("vb_lead_clear", lang, loc=location)

    # Two halves, kept apart on purpose. `framing` is ours to phrase; `steps`
    # are the advisory's own words and stay exactly as written. See `polish`.
    framing = [lead]

    # Timing, when the forecast supports it. Not for Severe: that brief is a
    # set of instructions, and a clock time in the middle of one is a detail
    # competing with a step.
    window = _hazard_window(hours or [])
    if window and level != "Severe":
        framing.append(i18n.sentence("vb_window", lang, time=window))

    steps = list(actions[: ACTIONS_SPOKEN.get(level, 2)])

    # An official warning is the one fact that outranks our own reading, so it
    # is spoken even though the advisory above did not come from it.
    if alert_count > 0 and level in URGENT_LEVELS:
        steps.append(
            i18n.sentence(
                "alert_some",
                lang,
                loc=location,
                count=alert_count,
                # English needs the agreement; the languages that do not carry
                # these slots simply drop them, as they do everywhere else.
                verb="is" if alert_count == 1 else "are",
                noun="alert" if alert_count == 1 else "alerts",
            )
        )

    end = i18n.terminator(lang)
    join = lambda lines: " ".join(x.rstrip(" .।") + end for x in lines if x).strip()  # noqa: E731
    return {"framing": join(framing), "steps": join(steps)}


def compose(**kwargs: Any) -> str:
    """The whole spoken brief as one paragraph."""
    parts = compose_parts(**kwargs)
    return " ".join(x for x in (parts["framing"], parts["steps"]) if x).strip()


# --- Making it sound spoken -------------------------------------------------
# The framing above is correct and a little stiff — it is joined from table
# entries and it reads like it. Gemini may smooth *that*, and nothing else.
#
# The instructions never reach the model, and that is not caution for its own
# sake. Asked to rewrite a farmer's flood advice, Gemini turned "move harvested
# grain and fertiliser to a dry, raised place" into "move harvested grain,
# fertilizer, and livestock to higher ground" — a livestock instruction nobody
# wrote, in a sentence somebody might act on. It was fluent, plausible and
# invented, and no output check short of understanding the domain would have
# caught it.
#
# So the split is structural rather than a filter. The model is handed one or
# two sentences of framing that contain no instruction, and the steps are
# concatenated afterwards exactly as the rules table wrote them. What a
# reviewer reads in that table is still exactly what a citizen hears.

MAX_GROWTH = 1.15


def _invents_no_figures(spoken: str, source: str) -> bool:
    """True when `spoken` introduces no number the source did not carry.

    A second line of defence on the framing, which does carry figures — a clock
    time, a percentage. It is not what keeps the instructions honest; the fact
    that they are never sent is.
    """
    return set(re.findall(r"\d+", spoken)) <= set(re.findall(r"\d+", source))


def polish(
    framing: str, *, lang: str, user_type: str | None, location: str, risk_level: str
) -> str:
    """The framing, made easier to listen to — or exactly as it arrived.

    Never raises and never returns empty: every path out of here is a sentence
    the reader can be given, so an outage, a rate limit or a refusal costs
    phrasing and never guidance.
    """
    if not framing.strip() or not llm.available():
        return framing

    spoken = llm.voice_line(
        framing,
        language_name=language_service.language_name(i18n.normalise_lang(lang)),
        user_type=user_type or "general",
        location=location,
        risk_level=risk_level,
    )
    if not spoken:
        return framing
    if len(spoken) > len(framing) * MAX_GROWTH:
        log.info("voice framing discarded: longer than the source")
        return framing
    if not _invents_no_figures(spoken, framing):
        log.warning("voice framing discarded: introduced a figure the advice did not contain")
        return framing
    return spoken


# --- The other two things worth hearing -------------------------------------
# Three buttons, three questions, three answers that must not be the same
# sentence in different clothes:
#
#   conditions   what is happening
#   advice       what I should do          (compose_parts, above)
#   impact       why it matters to me
#
# Both of the briefs below are assembled from sentences the corpus already
# carries, so they are translated everywhere the app is and neither invents a
# reading. They are also deliberately short: a spoken summary that runs past
# two sentences has stopped being a summary.


def conditions_brief(*, location: str, current: dict[str, Any], hours: list[dict[str, Any]] | None = None,
                     lang: str = "en") -> str:
    """What the sky is doing, and what it is about to do.

    Temperature and condition, then the one near-term change worth knowing.
    Everything else the card shows — humidity, pressure, gust direction — is a
    number a listener cannot hold and would not act on, so it stays on the card.
    """
    lang = i18n.normalise_lang(lang)
    if not current:
        return ""

    temp = current.get("temperature_c")
    parts: list[str] = []
    if temp is not None:
        parts.append(
            i18n.sentence(
                "now", lang,
                loc=location,
                temp=int(round(float(temp))),
                cond=i18n.condition_label(current.get("weather_code"), lang),
            )
        )

    # The near-term change, from the same forecast hours the timeline draws.
    # Only when it is actually ahead of the listener: rain that started an hour
    # ago is not news, and the first line already said it is raining.
    onset = _rain_onset(hours or [])
    if onset:
        parts.append(i18n.sentence("insight_rain_from", lang, time=onset[0], prob=onset[1]))

    end = i18n.terminator(lang)
    return " ".join(part.rstrip(" .।") + end for part in parts if part).strip()


# Matches the threshold `advisory.headline_insight` uses to call rain likely,
# so the spoken line and the panel cannot disagree about when it starts.
RAIN_ONSET_PROB = 55


def _rain_onset(hours: list[dict[str, Any]]) -> tuple[str, int] | None:
    for hour in hours[1:]:
        prob = hour.get("precipitation_probability_pct")
        if prob is not None and float(prob) >= RAIN_ONSET_PROB:
            clock = _clock(hour.get("time"))
            if clock:
                return clock, int(round(float(prob)))
    return None


def impact_brief(*, impacts: list[Any], lang: str = "en") -> str:
    """Why this weather matters to *this* reader, in their own category.

    The first card is theirs — the backend orders them by profile — and it is
    the only one spoken. The others are on screen as chips precisely because
    they are context rather than the answer to the question this button asks.
    """
    lang = i18n.normalise_lang(lang)
    if not impacts:
        return ""
    mine = impacts[0]
    category = getattr(mine, "category", None) or mine.get("category", "")
    headline = getattr(mine, "headline", None) or mine.get("headline", "")
    detail = getattr(mine, "detail", None) or mine.get("detail", "")
    if not detail:
        return ""

    end = i18n.terminator(lang)
    verdict = f"{category} — {headline}".strip(" —") if category or headline else ""
    return " ".join(part.rstrip(" .।") + end for part in (verdict, detail) if part).strip()

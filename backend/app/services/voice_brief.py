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

from typing import Any

from . import i18n

# How many actions a listener is given before the list stops being a list.
# Severe gets one more because each of its steps is shorter.
ACTIONS_SPOKEN = {"Low": 2, "Moderate": 2, "High": 2, "Severe": 3}

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


def compose(
    *,
    location: str,
    risk: Any,
    advisory: dict[str, Any],
    hours: list[dict[str, Any]] | None = None,
    alert_count: int = 0,
    lang: str = "en",
) -> str:
    """The spoken brief, as one short paragraph in ``lang``.

    Returns an empty string when there is nothing worth saying aloud, so the
    caller offers no audio rather than reading out a sentence about nothing.
    """
    lang = i18n.normalise_lang(lang)
    level = getattr(risk, "risk_level", None) or "Low"
    hazard = getattr(risk, "detected_hazard", None) or "None"
    actions = [line for line in (a.get("action") or "" for a in advisory.get("actions") or []) if line]
    if not actions:
        return ""

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

    parts = [lead]

    # Timing, when the forecast supports it. Not for Severe: that brief is a
    # set of instructions, and a clock time in the middle of one is a detail
    # competing with a step.
    window = _hazard_window(hours or [])
    if window and level != "Severe":
        parts.append(i18n.sentence("vb_window", lang, time=window))

    parts.extend(actions[: ACTIONS_SPOKEN.get(level, 2)])

    # An official warning is the one fact that outranks our own reading, so it
    # is spoken even though the advisory above did not come from it.
    if alert_count > 0 and level in URGENT_LEVELS:
        parts.append(
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
    return " ".join(part.rstrip(" .।") + end for part in parts if part).strip()

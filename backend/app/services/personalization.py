# -*- coding: utf-8 -*-
"""One weather reading, personalised once.

Before this module, "what does this weather mean for *this* reader?" was
answered in pieces: the route called five services in a row and stitched the
results together, the chat engine built its own role framing, the voice brief
built a third, and the frontend made its own small role decisions on top —
which hours to show, which metric to lead with. Four places that all had to
agree, and nothing that made them.

`personalize` is now the only place a role turns into a reading. Everything
below it is unchanged and still individually testable; this module composes,
it does not compute. Three rules hold throughout:

*   **It never fetches and never scores.** The bundle and the ``RiskOutput``
    arrive already built. Personalisation can reorder what a reader is told and
    choose which of it to lead with — it cannot change a number, and it cannot
    produce a reading the shared risk engine did not.
*   **It never invents.** A metric the provider did not return is reported as
    absent, not as zero. A question this app cannot answer is disclosed through
    the role's ``note`` rather than answered anyway.
*   **The facts are identical for everyone.** Two readers standing in the same
    place get the same temperature, the same risk level and the same hazard.
    What differs is the order, the emphasis and the advice.
"""

from __future__ import annotations

from typing import Any

from ..schemas import RiskOutput
from . import advisory, i18n, role_intel, roles

# How loudly an alert speaks to this reader. Presentation only — it reorders a
# list, it never changes a severity the alert itself carries.
EMPHASIS_PRIMARY = "primary"
EMPHASIS_NORMAL = "normal"


def priority_metrics(bundle: Any, role: roles.Role) -> list[dict[str, Any]]:
    """The measurements this reader looks at first, in their order.

    Only metrics the provider actually returned appear. A missing visibility
    reading is left out of a driver's list entirely rather than shown as zero,
    because zero visibility is a statement and "we don't know" is a different
    one.
    """
    current = (getattr(bundle, "current", None) or {}) if bundle is not None else {}
    out: list[dict[str, Any]] = []
    for name in role.metrics:
        value = current.get(name)
        if value is None:
            continue
        out.append({"metric": name, "value": value})
    return out


def alert_emphasis(alerts: list[dict[str, Any]] | None, role: roles.Role) -> list[dict[str, Any]]:
    """The same alerts, ordered by what this reader has to act on.

    A strong-wind warning is the first thing a fisherman needs and the fourth
    thing a student needs; both still see all of them. Severity decides the
    order first — an Extreme alert outranks a role's interest in a Moderate one,
    because emphasis must never bury an emergency.
    """
    items = list(alerts or [])
    if not items:
        return []

    severity_rank = {"Extreme": 0, "Severe": 1, "High": 2, "Moderate": 3, "Low": 4}
    wanted = tuple(role.alert_hazards)

    def sort_key(alert: dict[str, Any]) -> tuple[int, int]:
        severity = severity_rank.get(str(alert.get("severity") or ""), 5)
        hazard = str(alert.get("hazard") or alert.get("event") or "")
        interest = wanted.index(hazard) if hazard in wanted else len(wanted)
        return (severity, interest)

    ordered = sorted(items, key=sort_key)
    return [
        {
            **alert,
            "emphasis": (
                EMPHASIS_PRIMARY
                if str(alert.get("hazard") or alert.get("event") or "") in wanted
                else EMPHASIS_NORMAL
            ),
        }
        for alert in ordered
    ]


def suggested_questions(cards: list[dict[str, Any]], role: roles.Role, lang: str) -> list[dict[str, str]]:
    """Questions worth offering this reader, in their language.

    The chip's label is the title of one of the reader's own cards, which the
    corpus has already translated into every supported language; the question
    that travels to the assistant is the English one from the registry. So a
    Tamil reader is offered a Tamil chip without a single new string having to
    be translated, and the assistant is asked in the language its context is
    written in.

    A chip is only offered when its card is actually on screen. A farmer on a
    day with no irrigation card is not asked whether to irrigate.
    """
    present = {card.get("id"): card for card in cards}
    out: list[dict[str, str]] = []
    for card_id, question in role.ask:
        card = present.get(card_id)
        if not card:
            continue
        label = str(card.get("title") or "").strip()
        if not label:
            continue
        out.append({"id": card_id, "label": label, "query": question})
    return out


def ai_context(bundle: Any, risk: RiskOutput, role: roles.Role, metrics: list[dict[str, Any]]) -> str:
    """What the assistant is told about who is asking, in English.

    Deliberately a statement of *interest*, not of fact: the measurements the
    assistant reasons over reach it through its own context builder, from the
    same bundle. This line only says which of them this reader cares about and
    what they are trying to decide, so an answer leads with the number that
    matters to them instead of the first one in the payload.
    """
    where = getattr(bundle, "location", None)
    # `label` carries the state as well as the city, which is what stops the
    # assistant confusing one of India's several Hyderabads for another.
    location = getattr(where, "label", None) or getattr(where, "name", None) or "the selected location"
    leading = ", ".join(m["metric"] for m in metrics[:4]) or "the available readings"
    hazards = ", ".join(role.alert_hazards) or "any hazard"
    return (
        f"The reader's role is '{role.key}'. They are asking about {location}. "
        f"Lead with these measurements, in this order: {leading}. "
        f"Give the most weight to these hazards: {hazards}. "
        f"Current risk level is {risk.risk_level}; detected hazard is {risk.detected_hazard}. "
        "Answer only from measurements you were given; if one is missing, say it is unavailable."
    )


def personalize(
    *,
    bundle: Any,
    risk: RiskOutput,
    role: str | None = None,
    language: str = "en",
    alerts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Everything this reader's screen needs, decided in one place.

    The keys are the questions a reader has, in the order a screen answers them:

        role, icon, heading      who this reading is for
        priority_metrics         which numbers they look at first
        risk_interpretation      what the conditions mean, in plain language
        insight                  the one thing worth knowing right now
        impacts                  Weather Impact — sector by sector
        advisory                 What should I do now?
        role_cards               their own reading, card by card
        best_time                Best time to… , when the hours support one
        note                     where this app cannot answer their question
        suggested_questions      what to ask the assistant next
        ai_context               what the assistant is told about them
        alert_emphasis           which warnings to raise, and how loudly
        emergency                the override, when one applies
    """
    lang = i18n.normalise_lang(language)
    spec = roles.get(role)

    intelligence = role_intel.build(bundle, risk, spec.key, lang)
    cards = intelligence.get("cards") or []
    metrics = priority_metrics(bundle, spec)

    return {
        "role": spec.key,
        "icon": spec.icon,
        "heading": intelligence.get("heading", ""),
        "priority_metrics": metrics,
        "risk_interpretation": advisory.smart_explanation(bundle, risk, lang, mode="simple"),
        "insight": advisory.headline_insight(bundle, risk, spec.key, lang),
        "impacts": advisory.impact_cards(bundle, risk, lang, spec.key),
        "advisory": advisory.build_advisory(risk, spec.key, lang, bundle=bundle),
        "role_cards": cards,
        # The timing cards the role builders already produce are the honest
        # answer to "best time to…": they come from the hourly series, so a
        # role with no hourly data simply has no such card and no such answer.
        "best_time": _best_time(cards),
        "note": intelligence.get("note", ""),
        "suggested_questions": suggested_questions(cards, spec, lang),
        "ai_context": ai_context(bundle, risk, spec, metrics),
        "alert_emphasis": alert_emphasis(alerts, spec),
        "emergency": advisory.build_emergency(bundle, risk, spec.key, lang),
        "timing": spec.timing,
        "disclaimer": advisory.disclaimer(lang),
    }


# The cards that answer "when", rather than "what". Only these two search the
# hourly series for an hour and name it — everything else on a role's screen
# describes the present. Listed rather than inferred, so that promoting a card
# to "best time to…" is a deliberate act and not an accident of its wording.
_TIMING_CARDS = ("departure", "work_window")


def _best_time(cards: list[dict[str, Any]]) -> dict[str, str]:
    """The reader's own timing card, promoted to a field of its own.

    Returns an empty dict rather than a placeholder when there is no such card:
    a screen can then omit the section instead of printing "best time: unknown",
    which reads as a failure rather than as an absence of hours to search.
    """
    for card_id in _TIMING_CARDS:
        for card in cards:
            if card.get("id") == card_id and card.get("headline"):
                return {
                    "id": card_id,
                    "title": card.get("title", ""),
                    "headline": card.get("headline", ""),
                    "detail": card.get("detail", ""),
                }
    return {}

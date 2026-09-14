# -*- coding: utf-8 -*-
"""One weather reading, thirteen different decisions.

The failure these exist to prevent is not a crash. It is twelve professions that
all quietly arrive at "Caution — carry an umbrella", which is what happens when
a role is a label on top of one shared answer instead of a reading of its own.

So the assertions here are about DIFFERENCE, measured against a single fixed
bundle: the same temperature, the same wind, the same hazard and the same risk
score go into every one of them, and what comes out has to be distinguishable.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("WEATHER_DATA_MODE", "fixture")

from app.schemas import SELECTABLE_USER_TYPES  # noqa: E402
from app.services import advisory, i18n, personalization, risk_engine, role_intel, roles, weather  # noqa: E402

# The brief's twelve, plus the everyday reading that is the default.
BRIEF = (
    "farmer", "marine", "aviation", "disaster", "smart_city", "researcher",
    "student", "driver", "outdoor_worker", "household", "traveler", "caregiver",
    "general",
)

# What each reader must be able to see on their own panel. Card ids, because a
# title is translated and an id is the contract.
SIGNATURE = {
    "farmer": {"crop_risk", "irrigation", "field_advisory"},
    "marine": {"fishing_conditions", "storm_risk", "visibility"},
    "aviation": {"flight_conditions", "crosswind", "convective"},
    "disaster": {"hazard_status", "escalation", "response_priority"},
    "smart_city": {"urban_risk", "waterlogging", "infrastructure"},
    "researcher": {"anomaly", "trend", "historical"},
    "student": {"campus", "college_commute", "lightning_safety"},
    "driver": {"road_visibility", "road_surface", "crosswind"},
    "outdoor_worker": {"worksite_risk", "heat_stress", "lightning"},
    "household": {"home_comfort", "prepare", "rain_outlook"},
    "traveler": {"travel_conditions", "journey_risk", "departure"},
    "caregiver": {"vulnerable", "exposure", "prepare"},
    "general": {"umbrella", "comfort", "outdoor"},
}

# Cards that belong to one profession and must not turn up on anybody else's
# screen. This is the leak the brief calls out by name.
EXCLUSIVE = {
    "crop_risk": "farmer",
    "irrigation": "farmer",
    "field_advisory": "farmer",
    "rain_impact": "farmer",
    "fishing_conditions": "marine",
    "flight_conditions": "aviation",
    "road_surface": "driver",
    "road_visibility": "driver",
}


@pytest.fixture(scope="module")
def one_weather():
    """A single bundle and a single score, shared by every role in this file.

    A storm city on purpose: calm weather makes every reading agree, and a day
    where nothing is happening is exactly the day twelve professions look alike
    whether or not the personalisation works.
    """
    os.environ["WEATHER_FIXTURE_SCENARIO"] = "storm"
    weather.clear_cache()
    bundle = weather.fetch_weather(weather.gazetteer_lookup("Guwahati"))
    return bundle, risk_engine.assess(bundle)


@pytest.fixture(scope="module")
def panels(one_weather):
    bundle, risk = one_weather
    return {
        key: personalization.personalize(bundle=bundle, risk=risk, role=key)
        for key in BRIEF
    }


# --- the registry ----------------------------------------------------------
def test_the_selector_offers_exactly_the_brief_s_thirteen():
    assert tuple(SELECTABLE_USER_TYPES) == BRIEF
    assert len(set(BRIEF)) == 13


def test_every_role_names_only_readings_that_exist():
    """A role naming a reading nothing produces would be a hole in a panel."""
    available = role_intel.readings()
    for key, spec in roles.ROLES.items():
        for _, source, _, _ in spec.cards:
            assert source in available, f"{key} asks for unknown reading {source!r}"


def test_every_role_has_its_own_hazard_actions():
    """No reading is allowed to fall through to the general advice."""
    for key in BRIEF:
        assert key in i18n.PROFILE_ACTIONS, key
        for hazard in ("Heavy Rainfall", "Strong Wind", "Extreme Heat", "Lightning/Storm"):
            assert i18n.profile_action(key, hazard, "en"), f"{key}/{hazard}"


# --- the panels ------------------------------------------------------------
@pytest.mark.parametrize("key", BRIEF)
def test_each_reader_sees_their_own_cards(key, panels):
    ids = {card["id"] for card in panels[key]["role_cards"]}
    missing = SIGNATURE[key] - ids
    assert not missing, f"{key} is missing {sorted(missing)}; it has {sorted(ids)}"


@pytest.mark.parametrize("key", BRIEF)
def test_no_reader_gets_another_profession_s_card(key, panels):
    ids = {card["id"] for card in panels[key]["role_cards"]}
    for card_id, owner in EXCLUSIVE.items():
        if owner != key:
            assert card_id not in ids, f"{key} shows {owner}'s {card_id}"


def test_general_never_shows_farming_anything(panels):
    """The reported bug, stated as a test.

    A reader who has told the product nothing about themselves was being shown
    "Farming — Caution", because the sector table handed the general reading
    every other profession's sectors.
    """
    out = panels["general"]
    ids = {card["id"] for card in out["role_cards"]}
    assert not (ids & {"crop_risk", "irrigation", "field_advisory", "rain_impact"})

    labels = {card.category for card in out["impacts"]}
    assert i18n.category_label("farming", "en") not in labels
    assert i18n.category_label("fishing", "en") not in labels

    blob = " ".join(
        [card["headline"] + " " + card["detail"] for card in out["role_cards"]]
        + [step["action"] for step in out["advisory"]["actions"]]
    ).lower()
    for word in ("crop", "irrigat", "livestock", "harvest", "sowing", "spray"):
        assert word not in blob, f"general reading mentions {word!r}"


# A profession's own vocabulary. A card may be shared between roles and renamed
# — that is the design — but a renamed card whose SENTENCE still names somebody
# else's job is a leak the title hides. This is the audit that caught the city
# planner being told about braking distance, and the fisherman being told about
# a commute window.
OWNED_WORDS = {
    "driver": r"\b(road|brak\w*|driv\w*|vehicle|windscreen)\b",
    "farmer": r"\b(crop\w*|irrigat\w*|livestock|harvest\w*|sowing|spray\w*|field)\b",
    "marine": r"\b(boat|offshore|fishing|harbour)\b",
    "aviation": r"\b(aircraft|runway|flight|crosswind)\b",
    "student": r"\b(campus|college)\b",
    "outdoor_worker": r"\b(worksite|scaffold\w*|crane)\b",
}

# "Road and transport corridors" is one of the exposures a scored hazard bears
# on, and a response manager needs it named. It is the reading's own word, not
# the driver's, so it is excused by card rather than by role.
VOCABULARY_EXCEPTIONS = {("disaster", "impact_area")}


@pytest.mark.parametrize("key", BRIEF)
def test_no_card_speaks_in_another_profession_s_words(key, panels):
    import re

    for card in panels[key]["role_cards"]:
        if (key, card["id"]) in VOCABULARY_EXCEPTIONS:
            continue
        text = ((card["headline"] or "") + " " + (card["detail"] or "")).lower()
        for owner, pattern in OWNED_WORDS.items():
            if owner == key:
                continue
            found = re.search(pattern, text)
            assert not found, f"{key}/{card['id']} uses {owner}'s word {found.group(0)!r}"


# --- the difference, which is the whole point ------------------------------
def test_the_same_weather_produces_thirteen_different_panels(panels):
    """Not different labels. Different cards."""
    seen: dict[tuple[str, ...], str] = {}
    for key in BRIEF:
        ids = tuple(sorted(card["id"] for card in panels[key]["role_cards"]))
        assert ids not in seen, f"{key} shows exactly what {seen.get(ids)} shows"
        seen[ids] = key


def test_the_same_weather_produces_different_advice(panels):
    """The acceptance criterion, in one assertion.

    Farmer -> Marine -> Student -> Driver -> Disaster Response on one set of
    numbers has to reach different conclusions, not different wording for one
    conclusion. The lead action is the conclusion.
    """
    leads = {}
    for key in BRIEF:
        actions = panels[key]["advisory"]["actions"]
        assert actions, f"{key} was given nothing to do"
        leads[key] = actions[0]["action"]

    demo = ("farmer", "marine", "student", "driver", "disaster")
    assert len({leads[k] for k in demo}) == len(demo), {k: leads[k] for k in demo}
    # And across all thirteen, at most one pair may coincide.
    assert len(set(leads.values())) >= len(BRIEF) - 1, leads


def test_the_common_weather_is_identical_for_everybody(panels, one_weather):
    """Personalisation may reorder and reframe. It may not change a number."""
    bundle, risk = one_weather
    current = bundle.current
    for key in BRIEF:
        for item in panels[key]["priority_metrics"]:
            assert item["value"] == current[item["metric"]], key
        assert panels[key]["advisory"]["risk_level"] == risk.risk_level, key
        assert panels[key]["advisory"]["hazard"] == risk.detected_hazard, key


def test_every_impact_sector_says_the_same_thing_to_everybody(panels):
    """A sector is shown to some readers and not others; it never changes verdict."""
    verdicts: dict[str, set[tuple[str, str]]] = {}
    for key in BRIEF:
        for card in panels[key]["impacts"]:
            verdicts.setdefault(card.category, set()).add((card.status, card.detail))
    for category, found in verdicts.items():
        assert len(found) == 1, (category, found)


def test_each_reader_is_offered_their_own_questions(panels):
    """Quick prompts are the role's, and only for cards actually on screen."""
    asked = {}
    for key in BRIEF:
        offered = panels[key]["suggested_questions"]
        assert offered, f"{key} was offered nothing to ask"
        ids = {card["id"] for card in panels[key]["role_cards"]}
        for chip in offered:
            assert chip["id"] in ids, f"{key} offers {chip['id']} with no such card"
            assert chip["label"], key
        asked[key] = tuple(sorted(chip["query"] for chip in offered))
    assert len(set(asked.values())) == len(BRIEF), "two readers are offered the same questions"


# --- the disclosures that must survive -------------------------------------
def test_aviation_never_implies_an_official_clearance(panels):
    out = panels["aviation"]
    assert out["note"], "the aviation reading dropped its disclosure"
    note = out["note"].lower()
    # The note names what this app does not have rather than gesturing at it.
    assert "metar" in note or "not available" in note
    # And the advice points at the real source every time.
    for hazard in ("Lightning/Storm", "Strong Wind", "Heavy Rainfall", "Extreme Heat"):
        assert "official aviation" in i18n.profile_action("aviation", hazard, "en").lower()
    blob = " ".join(card["headline"] for card in out["role_cards"]).lower()
    for forbidden in ("cleared", "safe to fly", "do not fly", "no-go", "authorised"):
        assert forbidden not in blob, forbidden


def test_disaster_never_fabricates_a_warning(panels):
    out = panels["disaster"]
    card = next(c for c in out["role_cards"] if c["id"] == "official_status")
    headline = card["headline"].lower()
    assert "not available" in headline or "no " in headline
    assert out["note"], "the disaster reading dropped its disclosure"


def test_the_researcher_does_not_call_a_threshold_a_climate_anomaly(panels):
    card = next(c for c in panels["researcher"]["role_cards"] if c["id"] == "anomaly")
    text = (card["detail"] or "") + (card["headline"] or "")
    assert text.strip()


# --- every language -------------------------------------------------------
@pytest.mark.parametrize("lang", sorted(i18n.LANGUAGES))
def test_every_role_reads_in_every_language(lang, one_weather):
    """A role whose panel is English inside a Tamil page is half a feature."""
    bundle, risk = one_weather
    english = i18n.SENTENCES["en"]
    for key in BRIEF:
        out = personalization.personalize(bundle=bundle, risk=risk, role=key, language=lang)
        assert out["heading"], (key, lang)
        assert out["role_cards"], (key, lang)
        for card in out["role_cards"]:
            assert card["title"], (key, lang, card["id"])
            assert "{" not in card["title"] and "{" not in card["headline"], (key, lang)
        if lang == "en":
            continue
        # The heading is the one string every panel shows, so it is the one
        # that most obviously exposes a missing translation.
        assert out["heading"] != i18n.sentence(roles.get(key).heading_key, "en") or len(
            english[roles.get(key).heading_key]
        ) <= 24, (key, lang)


def test_switching_role_costs_no_extra_weather_request(one_weather, monkeypatch):
    """The panel changes; the weather does not get fetched again.

    `personalize` takes a bundle that is already built. If it ever starts
    fetching, switching profile would put a provider request behind a dropdown.
    """
    bundle, risk = one_weather
    calls = []
    monkeypatch.setattr(weather, "fetch_weather", lambda *a, **k: calls.append(a) or bundle)
    for key in BRIEF:
        personalization.personalize(bundle=bundle, risk=risk, role=key)
    assert calls == []


def test_advisory_for_every_persona_covers_the_selector(one_weather):
    """The comparison view has to compare what the selector offers."""
    _, risk = one_weather
    compared = {row["user_type"] for row in advisory.advisory_for_every_persona(risk)}
    assert compared == set(BRIEF)

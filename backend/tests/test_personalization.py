# -*- coding: utf-8 -*-
"""The personalization engine: does the role change the reading, and only that?

Two questions, and the second one carries the weight. A role is worth having if
a driver and a farmer are told different things first. It is only safe to ship
if neither of them is told a number the provider never sent, and if the facts
underneath — temperature, risk level, detected hazard — are the same for both.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.schemas import RiskOutput
from app.services import i18n, personalization, roles

ALL_ROLES = list(roles.keys())


def _risk(level="Low", hazard="No active hazard", **scores) -> RiskOutput:
    return RiskOutput(
        risk_score={"Low": 12, "Moderate": 45, "High": 70, "Severe": 88}[level],
        risk_level=level,
        detected_hazard=hazard,
        hazard_scores={
            "Heavy Rainfall": 0, "Flood Risk": 0, "Strong Wind": 0,
            "Extreme Heat": 0, "Lightning/Storm": 0, **scores,
        },
    )


def _bundle(hours=12, **current):
    base = {
        "temperature_c": 29.0, "apparent_temperature_c": 31.0, "humidity_pct": 62.0,
        "precipitation_mm": 0.0, "precipitation_probability_pct": 10.0,
        "wind_speed_kmh": 11.0, "wind_gust_kmh": 18.0, "wind_direction_deg": 200.0,
        "visibility_km": 12.0, "pressure_hpa": 1008.0, "weather_code": 1,
    }
    base.update({k: v for k, v in current.items() if not k.startswith("_")})
    hourly = [
        {
            "time": f"2026-09-06T{(6 + i) % 24:02d}:00",
            "precipitation_mm": current.get("_hourly_mm", 0.0),
            "precipitation_probability_pct": current.get("_hourly_prob", 10.0),
            "risk_score": 10 + i,
        }
        for i in range(hours)
    ]
    daily = [{"temp_max_c": 33.0, "temp_min_c": 23.0, "precipitation_probability_pct": 20.0, "weather_code": 1}]
    return SimpleNamespace(
        current=base, hourly=hourly, daily=daily,
        location=SimpleNamespace(name="Vijayawada", label="Vijayawada, Andhra Pradesh"),
        source="fixture",
    )


# --- Shape -----------------------------------------------------------------

@pytest.mark.parametrize("role", ALL_ROLES)
def test_every_role_gets_a_complete_envelope(role):
    out = personalization.personalize(bundle=_bundle(), risk=_risk(), role=role)
    for key in (
        "role", "icon", "heading", "priority_metrics", "risk_interpretation",
        "insight", "impacts", "advisory", "role_cards", "best_time", "note",
        "suggested_questions", "ai_context", "alert_emphasis", "emergency",
    ):
        assert key in out, key
    assert out["role"] == role
    assert out["heading"] and out["icon"]
    assert out["priority_metrics"]


def test_an_unknown_role_reads_as_the_general_one():
    """An old tab sending a key this build dropped must still get a screen."""
    out = personalization.personalize(bundle=_bundle(), risk=_risk(), role="astronaut")
    assert out["role"] == "general"


# --- The role changes the emphasis ------------------------------------------

def test_a_driver_is_told_visibility_first_and_a_farmer_rainfall():
    bundle, risk = _bundle(), _risk()
    driver = personalization.personalize(bundle=bundle, risk=risk, role="driver")
    farmer = personalization.personalize(bundle=bundle, risk=risk, role="farmer")
    assert driver["priority_metrics"][0]["metric"] == "visibility_km"
    assert farmer["priority_metrics"][0]["metric"] == "precipitation_mm"


def test_the_same_weather_reads_differently_for_different_roles():
    """§12's test: heavy rain and strong wind must not produce one answer."""
    bundle = _bundle(
        precipitation_mm=14.0, precipitation_probability_pct=90.0,
        wind_speed_kmh=52.0, wind_gust_kmh=71.0, visibility_km=1.4,
        _hourly_mm=6.0, _hourly_prob=90.0,
    )
    risk = _risk("Severe", "Heavy Rainfall", **{"Heavy Rainfall": 80, "Strong Wind": 70})
    readings = {
        role: personalization.personalize(bundle=bundle, risk=risk, role=role)
        for role in ("farmer", "fisherman", "traveler", "driver")
    }
    headlines = {
        role: tuple(card["headline"] for card in out["role_cards"])
        for role, out in readings.items()
    }
    # No two roles may be handed the same set of verdicts.
    assert len(set(headlines.values())) == len(headlines)


# --- It may reorder. It may not invent. -------------------------------------

def test_the_facts_are_identical_whoever_is_asking():
    bundle, risk = _bundle(), _risk("High", "Strong Wind", **{"Strong Wind": 65})
    outs = [personalization.personalize(bundle=bundle, risk=risk, role=r) for r in ALL_ROLES]
    # Personalisation reorders and re-words. It cannot move the risk engine.
    assert {o["risk_interpretation"] for o in outs} == {outs[0]["risk_interpretation"]}


def test_a_metric_the_provider_did_not_send_is_omitted_not_zeroed():
    bundle = _bundle()
    bundle.current["visibility_km"] = None
    out = personalization.personalize(bundle=bundle, risk=_risk(), role="driver")
    names = [m["metric"] for m in out["priority_metrics"]]
    assert "visibility_km" not in names
    # And what is there is the provider's own value, not a substitute.
    for metric in out["priority_metrics"]:
        assert metric["value"] == bundle.current[metric["metric"]]


def test_every_priority_metric_is_a_field_the_reading_actually_has():
    from app.schemas import CurrentWeatherOut

    for role in ALL_ROLES:
        for name in roles.get(role).metrics:
            assert name in CurrentWeatherOut.model_fields, f"{role}: {name}"


def test_the_marine_reading_still_discloses_what_it_cannot_answer():
    """No provider here returns wave, swell, tide or current. Say so."""
    out = personalization.personalize(bundle=_bundle(), risk=_risk(), role="fisherman")
    assert out["note"]


# --- Questions offered ------------------------------------------------------

@pytest.mark.parametrize("role", ALL_ROLES)
def test_a_question_is_only_offered_when_its_card_is_on_screen(role):
    out = personalization.personalize(bundle=_bundle(), risk=_risk(), role=role)
    shown = {card["id"] for card in out["role_cards"]}
    for question in out["suggested_questions"]:
        assert question["id"] in shown
        assert question["label"] and question["query"]


def test_the_chip_is_offered_in_the_readers_language():
    """The label is a card title the corpus already carries, so it translates."""
    en = personalization.personalize(bundle=_bundle(), risk=_risk(), role="farmer")
    ta = personalization.personalize(bundle=_bundle(), risk=_risk(), role="farmer", language="ta")
    assert en["suggested_questions"], "no chips to compare"
    by_id_en = {q["id"]: q for q in en["suggested_questions"]}
    by_id_ta = {q["id"]: q for q in ta["suggested_questions"]}
    assert set(by_id_en) == set(by_id_ta)
    for qid, q_en in by_id_en.items():
        assert by_id_ta[qid]["label"] != q_en["label"], qid
        # The question itself stays English — that is what the assistant reads.
        assert by_id_ta[qid]["query"] == q_en["query"]


# --- Alerts -----------------------------------------------------------------

def test_emphasis_never_buries_a_more_severe_alert():
    alerts = [
        {"id": 1, "hazard": "Extreme Heat", "severity": "Extreme"},
        {"id": 2, "hazard": "Strong Wind", "severity": "Moderate"},
    ]
    out = personalization.personalize(
        bundle=_bundle(), risk=_risk(), role="fisherman", alerts=alerts
    )
    # Wind is this reader's first interest; the Extreme alert still comes first.
    assert [a["id"] for a in out["alert_emphasis"]] == [1, 2]
    assert out["alert_emphasis"][1]["emphasis"] == personalization.EMPHASIS_PRIMARY


def test_emphasis_orders_by_interest_within_one_severity():
    alerts = [
        {"id": 1, "hazard": "Extreme Heat", "severity": "High"},
        {"id": 2, "hazard": "Strong Wind", "severity": "High"},
    ]
    out = personalization.personalize(
        bundle=_bundle(), risk=_risk(), role="fisherman", alerts=alerts
    )
    assert [a["id"] for a in out["alert_emphasis"]] == [2, 1]


def test_emphasis_keeps_every_alert():
    alerts = [{"id": i, "hazard": "Flood Risk", "severity": "Low"} for i in range(5)]
    out = personalization.personalize(bundle=_bundle(), risk=_risk(), role="student", alerts=alerts)
    assert len(out["alert_emphasis"]) == 5


# --- What the assistant is told ---------------------------------------------

def test_the_ai_context_names_the_role_the_place_and_the_measured_risk():
    out = personalization.personalize(bundle=_bundle(), risk=_risk("High", "Strong Wind"), role="driver")
    context = out["ai_context"]
    assert "driver" in context
    assert "Vijayawada" in context
    assert "High" in context and "Strong Wind" in context
    assert "visibility_km" in context


def test_the_ai_context_forbids_filling_a_gap_with_an_invention():
    out = personalization.personalize(bundle=_bundle(), risk=_risk(), role="farmer")
    assert "unavailable" in out["ai_context"].lower()


# --- Timing -----------------------------------------------------------------

def test_best_time_is_absent_rather_than_empty_when_there_are_no_hours():
    bundle = _bundle(hours=0)
    out = personalization.personalize(bundle=bundle, risk=_risk(), role="commuter")
    assert out["best_time"] == {}


def test_the_registry_is_the_only_list_of_roles():
    """role_intel must not carry a second, quietly diverging one."""
    import inspect

    from app.services import role_intel

    source = inspect.getsource(role_intel)
    for name in ("_ICONS", "_HEADINGS", "_NOTES"):
        assert name not in source, f"{name} is a duplicate role table"


# --- The twelve-role brief (§11) and the differentiation test (§12) ---------

# The roles the brief names, and the key each is served by here. "at least"
# these twelve: the app also carries household, caregiver and commuter, which
# predate the brief and are still offered.
BRIEF_ROLES = {
    "General Public": "general",
    "Farmer": "farmer",
    "Marine / Fisherman": "fisherman",
    "Traveller": "traveler",
    "Driver": "driver",
    "Commuter": "commuter",
    "Student": "student",
    "Researcher / Climate Analyst": "researcher",
    "Disaster Manager": "disaster_manager",
    "Aviation Professional": "aviation",
    "Government / Smart City": "government",
    "Outdoor Worker": "outdoor_worker",
    "Event / Outdoor Planner": "event_planner",
}


@pytest.mark.parametrize("name,key", sorted(BRIEF_ROLES.items()))
def test_every_named_role_exists_and_reads(name, key):
    assert roles.known(key), f"{name} has no role"
    out = personalization.personalize(bundle=_bundle(), risk=_risk(), role=key)
    assert out["role"] == key, f"{name} fell back to another reading"
    assert out["role_cards"], name
    assert out["heading"], name


def _severe():
    """Heavy rain, strong winds, severe warning — the brief's own scenario."""
    bundle = _bundle(
        temperature_c=36.0, apparent_temperature_c=41.0, humidity_pct=78.0,
        precipitation_mm=14.0, precipitation_probability_pct=90.0,
        wind_speed_kmh=52.0, wind_gust_kmh=71.0, visibility_km=1.4,
        pressure_hpa=996.0, _hourly_mm=6.0, _hourly_prob=90.0,
    )
    risk = _risk(
        "Severe", "Heavy Rainfall",
        **{"Heavy Rainfall": 80, "Flood Risk": 60, "Strong Wind": 70,
           "Extreme Heat": 45, "Lightning/Storm": 55},
    )
    return bundle, risk


def test_one_severe_forecast_reads_differently_for_every_named_role():
    """§12. Same rain, same wind, same warning — thirteen different readings."""
    bundle, risk = _severe()
    seen: dict[tuple, str] = {}
    for name, key in BRIEF_ROLES.items():
        out = personalization.personalize(bundle=bundle, risk=risk, role=key)
        # What this reader is shown, and in what order. Two roles handed the
        # same cards in the same order are one role with two names.
        signature = (
            tuple(card["id"] for card in out["role_cards"]),
            tuple(m["metric"] for m in out["priority_metrics"][:3]),
        )
        assert signature not in seen, f"{name} reads identically to {seen[signature]}"
        seen[signature] = name


def test_severe_weather_is_equally_severe_for_everyone():
    """Emphasis may differ. The measured danger may not."""
    bundle, risk = _severe()
    outs = [
        personalization.personalize(bundle=bundle, risk=risk, role=key)
        for key in BRIEF_ROLES.values()
    ]
    assert {o["emergency"]["active"] for o in outs} == {outs[0]["emergency"]["active"]}
    assert {o["risk_interpretation"] for o in outs} == {outs[0]["risk_interpretation"]}


def test_the_aviation_reading_discloses_what_it_does_not_carry():
    """No METAR, TAF, cloud base, icing or turbulence. Say so, as marine does."""
    out = personalization.personalize(bundle=_bundle(), risk=_risk(), role="aviation")
    note = out["note"]
    assert note
    for missing in ("METAR", "TAF"):
        assert missing in note


def test_no_new_role_invented_its_own_vocabulary():
    """Composed readings must reuse cards, so their wording is already checked."""
    bundle, risk = _severe()
    known_ids = set()
    for key in ("general", "farmer", "fisherman", "traveler", "driver",
                "commuter", "outdoor_worker", "household", "student", "caregiver"):
        out = personalization.personalize(bundle=bundle, risk=risk, role=key)
        known_ids.update(card["id"] for card in out["role_cards"])
    for key in ("researcher", "disaster_manager", "aviation", "government", "event_planner"):
        out = personalization.personalize(bundle=bundle, risk=risk, role=key)
        for card in out["role_cards"]:
            assert card["id"] in known_ids, f"{key} invented card {card['id']}"


@pytest.mark.parametrize("key", ["researcher", "disaster_manager", "aviation",
                                 "government", "event_planner"])
def test_new_roles_are_translated_not_left_in_english(key):
    en = personalization.personalize(bundle=_bundle(), risk=_risk(), role=key)
    for lang in ("hi", "ta", "pa", "ml", "gu", "kn", "te", "bn", "mr", "as"):
        other = personalization.personalize(
            bundle=_bundle(), risk=_risk(), role=key, language=lang
        )
        assert other["heading"] != en["heading"], f"{key}/{lang} heading is English"
        if en["note"]:
            assert other["note"] != en["note"], f"{key}/{lang} note is English"

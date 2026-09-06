# -*- coding: utf-8 -*-
"""Role intelligence: does it say something useful, and can it lie?

The second question gets most of the tests. A role panel is only worth having
if a farmer can act on it, and it is only safe to ship if it cannot invent the
rainfall it is advising against.
"""

from __future__ import annotations

import re
from types import SimpleNamespace

import pytest

from app.schemas import RiskOutput
from app.services import i18n, role_intel
from app.services._role_sentences import ROLE_SENTENCES

ROLES = [
    "general", "farmer", "fisherman", "traveler", "driver",
    "outdoor_worker", "household", "student", "caregiver", "commuter",
]


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
        "visibility_km": 12.0, "weather_code": 1,
    }
    base.update(current)
    hourly = [
        {
            "time": f"2026-09-06T{(6 + i) % 24:02d}:00",
            "precipitation_mm": current.get("_hourly_mm", 0.0),
            "precipitation_probability_pct": current.get("_hourly_prob", 10.0),
            "risk_score": 10 + i,
        }
        for i in range(hours)
    ]
    daily = [
        {"temp_max_c": 33.0, "temp_min_c": 23.0, "precipitation_probability_pct": 20.0, "weather_code": 1},
        {"temp_max_c": 32.0, "temp_min_c": 24.0, "precipitation_probability_pct": 65.0, "weather_code": 61},
    ]
    return SimpleNamespace(current=base, hourly=hourly, daily=daily)


# --- Shape -----------------------------------------------------------------

@pytest.mark.parametrize("role", ROLES)
def test_every_role_produces_a_readable_panel(role):
    out = role_intel.build(_bundle(), _risk(), role, "en")
    assert out["user_type"] == role
    assert out["heading"]
    # The brief caps the panel at five cards; fewer is fine, none is not.
    assert 3 <= len(out["cards"]) <= 5
    for card in out["cards"]:
        assert card["id"] and card["title"] and card["headline"]
        assert card["tone"] in {"safe", "caution", "warn", "danger", "info"}


@pytest.mark.parametrize("role", ROLES)
def test_no_unfilled_template_slots(role):
    """A stray {mm} on screen is a bug that reads as a broken app."""
    for lang in ROLE_SENTENCES:
        out = role_intel.build(_bundle(), _risk(), role, lang)
        blob = out["heading"] + out["note"] + "".join(
            c["title"] + c["headline"] + c["detail"] for c in out["cards"]
        )
        assert not re.search(r"\{[a-z_]+\}", blob), (role, lang, blob)


def test_unknown_role_falls_back_to_general():
    out = role_intel.build(_bundle(), _risk(), "astronaut", "en")
    assert out["user_type"] == "general"


def test_every_key_exists_in_every_language():
    """A missing key silently falls back to English, which is worse than loud."""
    english = set(ROLE_SENTENCES["en"])
    for lang, table in ROLE_SENTENCES.items():
        assert set(table) == english, f"{lang} differs by {english ^ set(table)}"


@pytest.mark.parametrize("lang", ["hi", "te", "bn", "mr", "as"])
def test_panels_are_actually_translated(lang):
    """Not merely present — different from the English, in a non-Latin script."""
    for role in ROLES:
        english = role_intel.build(_bundle(), _risk(), role, "en")
        other = role_intel.build(_bundle(), _risk(), role, lang)
        assert other["heading"] != english["heading"]
        assert re.search(r"[^\x00-\x7f]", other["heading"]), (lang, other["heading"])


# --- It must not invent anything -------------------------------------------

def test_no_hourly_series_means_no_rainfall_claims():
    """With no forecast, the irrigation card refuses rather than guesses."""
    bare = SimpleNamespace(current={"temperature_c": 30.0}, hourly=[], daily=[])
    cards = {c["id"]: c for c in role_intel.build(bare, _risk(), "farmer", "en")["cards"]}
    assert cards["irrigation"]["headline"] == i18n.sentence("ri_irrigation_nodata", "en")
    # And nowhere in the panel is there a millimetre figure to act on.
    blob = "".join(c["headline"] + c["detail"] for c in cards.values())
    assert not re.search(r"\d+(\.\d+)?\s*mm", blob), blob


def test_missing_current_readings_say_so_rather_than_defaulting():
    empty = SimpleNamespace(current={}, hourly=[], daily=[])
    unavailable = i18n.sentence("ri_no_data", "en")
    general = {c["id"]: c for c in role_intel.build(empty, _risk(), "general", "en")["cards"]}
    assert general["umbrella"]["headline"] == unavailable
    assert general["comfort"]["headline"] == unavailable

    marine = {c["id"]: c for c in role_intel.build(empty, _risk(), "fisherman", "en")["cards"]}
    assert marine["wind"]["headline"] == unavailable
    assert marine["visibility"]["headline"] == unavailable


def test_no_wave_or_tide_claim_anywhere():
    """The one absence the app has to own up to, in every language."""
    for lang in ROLE_SENTENCES:
        out = role_intel.build(_bundle(), _risk(), "fisherman", lang)
        assert out["note"], lang
        blob = "".join(c["headline"] + c["detail"] for c in out["cards"]).lower()
        for banned in ("wave height", "swell of", "tide is", "sea state"):
            assert banned not in blob


def test_missing_wind_direction_is_not_invented():
    bundle = _bundle(wind_direction_deg=None)
    cards = {c["id"]: c for c in role_intel.build(bundle, _risk(), "fisherman", "en")["cards"]}
    assert "km/h" in cards["wind"]["headline"]
    assert not re.search(r"\b(N|NE|E|SE|S|SW|W|NW)\b", cards["wind"]["headline"])


def test_departure_hidden_without_an_hourly_series():
    bare = SimpleNamespace(current={"temperature_c": 28.0}, hourly=[], daily=[])
    ids = {c["id"] for c in role_intel.build(bare, _risk(), "commuter", "en")["cards"]}
    assert "departure" not in ids
    # The rest of the panel still renders.
    assert {"commute_risk", "hazards", "reminder"} <= ids


# --- The verdicts have to be right -----------------------------------------

def test_irrigation_defers_to_forecast_rain():
    wet = role_intel.build(_bundle(_hourly_mm=1.2), _risk(), "farmer", "en")
    card = {c["id"]: c for c in wet["cards"]}["irrigation"]
    assert card["headline"] == i18n.sentence("ri_irrigation_delay", "en")
    assert "14.4" in card["detail"]  # 12 hours × 1.2 mm, quoted back exactly


def test_irrigation_suggests_watering_when_dry():
    dry = role_intel.build(_bundle(_hourly_mm=0.0, _hourly_prob=5.0), _risk(), "farmer", "en")
    card = {c["id"]: c for c in dry["cards"]}["irrigation"]
    assert card["headline"] == i18n.sentence("ri_irrigation_needed", "en")


def test_crop_card_advises_on_weather_and_does_not_diagnose():
    humid = _bundle(humidity_pct=90.0, temperature_c=28.0, _hourly_mm=0.5)
    card = {c["id"]: c for c in role_intel.build(humid, _risk(), "farmer", "en")["cards"]}["crop_risk"]
    text = (card["headline"] + card["detail"]).lower()
    assert "90" in text
    # A weather advisory, not a plant-pathology finding.
    assert "more likely" in text or "monitoring" in text
    for claimed in ("your crop has", "infected", "disease detected", "apply fungicide"):
        assert claimed not in text


@pytest.mark.parametrize(
    "scenario, expected",
    [
        ({"risk": _risk("Severe", "Lightning/Storm", **{"Lightning/Storm": 80})}, "ri_fishing_avoid"),
        ({"current": {"wind_gust_kmh": 55.0}}, "ri_fishing_avoid"),
        ({"risk": _risk("Moderate", "Lightning/Storm", **{"Lightning/Storm": 30})}, "ri_fishing_caution"),
        ({"current": {"visibility_km": 1.0}}, "ri_fishing_caution"),
        ({}, "ri_fishing_favorable"),
    ],
)
def test_fishing_verdict_is_conservative(scenario, expected):
    bundle = _bundle(**scenario.get("current", {}))
    risk = scenario.get("risk", _risk())
    card = {c["id"]: c for c in role_intel.build(bundle, risk, "fisherman", "en")["cards"]}
    assert card["fishing_conditions"]["headline"] == i18n.sentence(expected, "en")


def test_storm_drives_every_role_the_same_way():
    """One engine: a storm cannot be High for one reader and Low for another."""
    storm = _risk("Severe", "Lightning/Storm", **{"Lightning/Storm": 80})
    tones = {}
    for role in ROLES:
        cards = role_intel.build(_bundle(), storm, role, "en")["cards"]
        tones[role] = {c["tone"] for c in cards}
    for role, seen in tones.items():
        assert seen & {"danger", "warn"}, f"{role} shrugged off a severe storm: {seen}"


def test_roles_actually_differ():
    """The whole point: the same weather has to read differently per role."""
    panels = {role: role_intel.build(_bundle(), _risk(), role, "en") for role in ROLES}
    headings = {p["heading"] for p in panels.values()}
    assert len(headings) == len(ROLES)
    card_sets = {role: tuple(c["id"] for c in p["cards"]) for role, p in panels.items()}
    assert len(set(card_sets.values())) == len(ROLES)


def test_departure_picks_the_calmest_hour_from_the_existing_scores():
    bundle = _bundle(hours=12)
    # Hour index 2 is 08:00 and is given the lowest score in the window.
    bundle.hourly[2]["risk_score"] = 1
    card = {c["id"]: c for c in role_intel.build(bundle, _risk(), "commuter", "en")["cards"]}["departure"]
    assert card["headline"] == "08:00"


def test_compass_point_never_guesses():
    assert role_intel._compass_point(None) is None
    assert role_intel._compass_point(0) == "N"
    assert role_intel._compass_point(225) == "SW"
    assert role_intel._compass_point(359) == "N"


# --- The five profiles added for the nine-role selector ---------------------

NEW_ROLES = ["driver", "outdoor_worker", "household", "student", "caregiver"]

# Student is deliberately absent: its panel is a recombination of the commute
# and outdoor readings rather than a new set of sentences, so that a student and
# a commuter can never be given two different answers to the same question. Its
# distinctness lives in the heading, factor order, hazard actions and map
# clause, and is covered by test_roles_actually_differ and the reuse test below.
OWN_CARD_ROLES = [r for r in NEW_ROLES if r != "student"]


@pytest.mark.parametrize("role", OWN_CARD_ROLES)
def test_new_roles_answer_their_own_question(role):
    """A label the engine cannot tell apart would be a promise broken on the
    next screen, so each new reading must own cards no other reading shows."""
    mine = {c["id"] for c in role_intel.build(_bundle(), _risk(), role, "en")["cards"]}
    others = set()
    for other in ROLES:
        if other == role:
            continue
        others |= {c["id"] for c in role_intel.build(_bundle(), _risk(), other, "en")["cards"]}
    assert mine - others, f"{role} shows nothing the other readings do not"


def test_driver_reads_visibility_from_the_measurement():
    fog = role_intel.build(_bundle(visibility_km=0.8), _risk(), "driver", "en")["cards"]
    card = {c["id"]: c for c in fog}["road_visibility"]
    assert card["tone"] == "danger"
    assert "0.8" in card["detail"]

    clear = role_intel.build(_bundle(visibility_km=14.0), _risk(), "driver", "en")["cards"]
    assert {c["id"]: c for c in clear}["road_visibility"]["tone"] == "safe"


def test_driver_says_nothing_about_a_road_it_cannot_see():
    """No visibility reading must not become a clear road."""
    blind = _bundle(visibility_km=None)
    card = {c["id"]: c for c in role_intel.build(blind, _risk(), "driver", "en")["cards"]}
    assert card["road_visibility"]["headline"] == i18n.sentence("ri_no_data", "en")
    assert card["road_visibility"]["tone"] == "info"


def test_driver_surface_verdict_follows_measured_rain():
    dry = {c["id"]: c for c in role_intel.build(_bundle(), _risk(), "driver", "en")["cards"]}
    assert dry["road_surface"]["tone"] == "safe"

    wet = _bundle(_hourly_mm=1.5, _hourly_prob=80.0, precipitation_mm=2.0)
    heavy = {c["id"]: c for c in role_intel.build(wet, _risk(), "driver", "en")["cards"]}
    assert heavy["road_surface"]["tone"] in {"caution", "warn"}


def test_outdoor_worker_window_comes_from_the_engine_scores():
    bundle = _bundle(hours=12)
    bundle.hourly[4]["risk_score"] = 0  # 10:00
    card = {c["id"]: c for c in role_intel.build(bundle, _risk(), "outdoor_worker", "en")["cards"]}
    assert card["work_window"]["headline"] == "10:00"


def test_outdoor_worker_window_is_absent_without_an_hourly_series():
    bare = SimpleNamespace(current=_bundle().current, hourly=[], daily=[])
    card = {c["id"]: c for c in role_intel.build(bare, _risk(), "outdoor_worker", "en")["cards"]}
    assert card["work_window"]["headline"] == i18n.sentence("ri_workwindow_none", "en")


def test_outdoor_worker_feels_heat_before_the_thermometer_does():
    """Humidity is what turns a workable 33°C into an unworkable one."""
    muggy = _bundle(temperature_c=31.0, apparent_temperature_c=32.0, humidity_pct=88.0)
    card = {c["id"]: c for c in role_intel.build(muggy, _risk(), "outdoor_worker", "en")["cards"]}
    assert card["heat_stress"]["tone"] == "caution"

    scorching = _bundle(apparent_temperature_c=39.0, humidity_pct=55.0)
    hot = {c["id"]: c for c in role_intel.build(scorching, _risk(), "outdoor_worker", "en")["cards"]}
    assert hot["heat_stress"]["tone"] == "warn"


def test_preparedness_is_gated_on_storm_and_wind_not_on_rain():
    """Heavy rain alone is not a reason to tell someone to find a torch."""
    rainy = _bundle(_hourly_mm=2.0, _hourly_prob=90.0, precipitation_mm=3.0)
    calm = {c["id"]: c for c in role_intel.build(rainy, _risk(), "household", "en")["cards"]}
    assert calm["prepare"]["headline"] == i18n.sentence("ri_prepare_normal", "en")

    stormy = role_intel.build(
        _bundle(), _risk("High", "Lightning/Storm", **{"Lightning/Storm": 70}), "household", "en",
    )["cards"]
    assert {c["id"]: c for c in stormy}["prepare"]["tone"] in {"caution", "warn"}


def test_household_drying_verdict_tracks_the_forecast():
    dry = {c["id"]: c for c in role_intel.build(_bundle(), _risk(), "household", "en")["cards"]}
    assert dry["home_rain"]["headline"] == i18n.sentence("ri_home_rain_dry", "en")

    wet = _bundle(_hourly_prob=85.0, _hourly_mm=1.0)
    damp = {c["id"]: c for c in role_intel.build(wet, _risk(), "household", "en")["cards"]}
    assert damp["home_rain"]["headline"] == i18n.sentence("ri_home_rain_wet", "en")


def test_student_reuses_the_shared_readings_rather_than_a_second_opinion():
    """Two mappings for one question is two chances to disagree."""
    student = {c["id"]: c for c in role_intel.build(_bundle(), _risk(), "student", "en")["cards"]}
    commuter = {c["id"]: c for c in role_intel.build(_bundle(), _risk(), "commuter", "en")["cards"]}
    general = {c["id"]: c for c in role_intel.build(_bundle(), _risk(), "general", "en")["cards"]}
    assert student["commute_risk"] == commuter["commute_risk"]
    assert student["outdoor"] == general["outdoor"]


def test_caregiver_reads_heat_earlier_than_the_general_panel():
    """Children and older people are affected below the general threshold."""
    warm = _bundle(temperature_c=32.0, apparent_temperature_c=33.0, humidity_pct=60.0)
    risk = _risk("Moderate", "Extreme Heat", **{"Extreme Heat": 45})
    care = {c["id"]: c for c in role_intel.build(warm, risk, "caregiver", "en")["cards"]}
    assert care["vulnerable"]["tone"] == "warn"
    general = {c["id"]: c for c in role_intel.build(warm, risk, "general", "en")["cards"]}
    assert general["comfort"]["tone"] == "caution"


def test_legacy_profiles_still_resolve():
    """A stored preference must never become an invalid request."""
    for legacy in ("commuter", "aviation", "urban"):
        panel = role_intel.build(_bundle(), _risk(), legacy, "en")
        assert panel["cards"]
        assert panel["heading"]

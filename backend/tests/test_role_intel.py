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

ROLES = ["general", "farmer", "fisherman", "traveler", "commuter"]


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

# -*- coding: utf-8 -*-
"""The map's per-hour reading, and the map data behind it.

The interesting tests are the ones about restraint: the map may only say what
the forecast supports, and the risk-map response must stay byte-compatible for
the callers that were there before it grew fields.
"""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import i18n, map_insight
from app.services._role_sentences import ROLE_SENTENCES

ROLES = [
    "general", "farmer", "fisherman", "traveler", "driver",
    "outdoor_worker", "household", "student", "caregiver", "commuter",
]
client = TestClient(app)


def _hours(*probs, level="Low", wind=8.0):
    return [
        {
            "time": f"2026-09-06T{(9 + i) % 24:02d}:00",
            "precipitation_probability_pct": prob,
            "precipitation_mm": 0.0,
            "wind_speed_kmh": wind,
            "risk_level": level,
            "risk_score": 10,
        }
        for i, prob in enumerate(probs)
    ]


# --- The reading itself ------------------------------------------------------

@pytest.mark.parametrize("role", ROLES)
def test_one_line_per_hour_for_every_role(role):
    lines = map_insight.build(_hours(10, 20, 30), role, "en")
    assert len(lines) == 3
    assert all(line for line in lines)


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("lang", list(ROLE_SENTENCES))
def test_no_unfilled_slots_in_any_language(role, lang):
    lines = map_insight.build(_hours(10, 65, 30, level="Low"), role, lang)
    for line in lines:
        assert not re.search(r"\{[a-z_]+\}", line), (role, lang, line)


def test_roles_read_the_same_hour_differently():
    hours = _hours(70)
    lines = {role: map_insight.build(hours, role, "en")[0] for role in ROLES}
    assert len(set(lines.values())) == len(ROLES)
    # And they agree about the number, because there is only one number.
    assert all("70%" in line for line in lines.values())


def test_the_hourly_risk_level_leads_when_it_is_high():
    """Once the engine calls the hour High, that outranks the raw probability."""
    line = map_insight.build(_hours(95, level="High"), "commuter", "en")[0]
    assert "High" in line
    assert "95%" not in line


def test_rising_and_easing_are_relative_to_the_first_hour():
    rising = map_insight.build(_hours(10, 40), "general", "en")[1]
    easing = map_insight.build(_hours(45, 10), "general", "en")[1]
    assert rising == i18n.sentence("mi_rain_rising", "en", time="10:00", prob=40) + " " + i18n.sentence(
        "mi_role_general", "en"
    )
    assert "eases" in easing


def test_no_movement_is_ever_claimed():
    """Nothing here can establish that weather is travelling toward anyone."""
    for lang in ROLE_SENTENCES:
        for role in ROLES:
            blob = " ".join(map_insight.build(_hours(20, 80, 40), role, lang)).lower()
            for banned in ("moving toward", "approaching your", "heading your way", "radar"):
                assert banned not in blob


def test_an_hour_with_no_readings_says_nothing():
    hours = [{"time": "2026-09-06T09:00", "risk_level": "Low"}]
    assert map_insight.build(hours, "general", "en") == [""]


def test_no_hours_means_no_lines():
    assert map_insight.build([], "farmer", "en") == []


def test_unknown_role_falls_back_to_general():
    assert map_insight.build(_hours(70), "astronaut", "en") == map_insight.build(_hours(70), "general", "en")


# --- The endpoints -----------------------------------------------------------

def test_timeline_is_unchanged_for_callers_that_do_not_ask():
    body = client.get("/weather/timeline?location=Vijayawada&hours=4").json()
    assert body["insights"] == []
    assert len(body["hours"]) == 4


def test_timeline_carries_readings_when_a_profile_is_given():
    body = client.get("/weather/timeline?location=Vijayawada&hours=4&user_type=farmer").json()
    assert len(body["insights"]) == len(body["hours"]) == 4
    assert all(body["insights"])


def test_timeline_readings_are_translated():
    body = client.get("/weather/timeline?location=Vijayawada&hours=2&user_type=farmer&language=te").json()
    assert re.search(r"[ఀ-౿]", body["insights"][0]), body["insights"][0]


def test_risk_map_omits_hours_unless_asked():
    """The map panel opts in; the risk map that was there before does not."""
    body = client.get("/risk-map?limit=2").json()
    for entry in body["locations"]:
        assert entry["hours"] == []


def test_risk_map_carries_measured_values_and_forward_hours():
    body = client.get("/risk-map?limit=2&hours=4").json()
    assert body["locations"], "no locations scored"
    for entry in body["locations"]:
        # The values were already in hand when the risk was scored.
        assert isinstance(entry["temperature_c"], (int, float))
        assert len(entry["hours"]) == 4
        for hour in entry["hours"]:
            assert hour["time"]
            # Every hour is a real reading or an explicit absence, never a zero
            # standing in for one.
            for field in ("temperature_c", "precipitation_probability_pct", "wind_speed_kmh"):
                assert hour[field] is None or isinstance(hour[field], (int, float))


def test_no_cloud_cover_in_the_forward_hours():
    """The layer that cannot be played must not look as though it can.

    The provider's hourly block carries no cloud cover, so `MapHour` has no
    field for it. If that ever changes, this test should fail and the cloud
    layer's `hourly` flag should be flipped deliberately rather than by
    accident.
    """
    body = client.get("/risk-map?limit=1&hours=2").json()
    for hour in body["locations"][0]["hours"]:
        assert "cloud_cover_pct" not in hour


def test_risk_map_has_no_insight_without_forward_hours():
    """The line is derived from the hours; no hours, no line.

    A caller that asked for the cheap response must not be handed a sentence
    built from a series it did not receive and cannot check.
    """
    body = client.get("/risk-map?limit=2").json()
    for entry in body["locations"]:
        assert entry["insight"] is None


def test_risk_map_reads_each_location_for_the_caller():
    body = client.get("/risk-map?limit=3&hours=6&user_type=farmer").json()
    assert body["locations"], "no locations scored"
    for entry in body["locations"]:
        assert entry["insight"], f"{entry['location']} got no reading"
        # One sentence for the preview box, not the whole hourly rundown.
        assert entry["insight"].count(".") <= 3


def test_risk_map_reading_is_about_the_hour_that_decides_the_score():
    """The preview names the peak hour, not whichever hour happens to be first.

    A box that leads with a calm 20:00 while the score behind it comes from a
    severe 00:00 is describing a different afternoon from the one it scored.
    """
    body = client.get("/risk-map?limit=4&hours=6&user_type=general").json()
    for entry in body["locations"]:
        peak = max(entry["hours"], key=lambda hour: hour["risk_score"])
        assert peak["time"][11:16] in entry["insight"], (
            f"{entry['location']}: {entry['insight']} does not mention {peak['time']}"
        )


def test_risk_map_reading_is_translated():
    body = client.get("/risk-map?limit=2&hours=4&user_type=farmer&language=te").json()
    for entry in body["locations"]:
        assert re.search(r"[ఀ-౿]", entry["insight"]), entry["insight"]


def test_risk_map_reading_is_written_for_the_profile():
    """Two roles reading the same location must not be handed the same advice."""
    def readings(role):
        body = client.get(f"/risk-map?limit=3&hours=6&user_type={role}").json()
        return {entry["location"]: entry["insight"] for entry in body["locations"]}

    farmer, fisherman = readings("farmer"), readings("fisherman")
    assert farmer and farmer.keys() == fisherman.keys()
    assert any(farmer[name] != fisherman[name] for name in farmer)

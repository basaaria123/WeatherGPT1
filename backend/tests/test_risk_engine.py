# -*- coding: utf-8 -*-
"""The risk engine is the single source of truth, so it gets the tightest tests."""

from __future__ import annotations

import pytest

from app.services import risk_engine as R
from app.services.risk_engine import RiskInputs


@pytest.mark.parametrize(
    "score,level",
    [(0, "Low"), (30, "Low"), (31, "Moderate"), (60, "Moderate"),
     (61, "High"), (80, "High"), (81, "Severe"), (100, "Severe")],
)
def test_band_boundaries(score, level):
    assert R.level_for(score) == level


def test_score_is_clamped():
    assert R.level_for(-50) == "Low"
    assert R.level_for(500) == "Severe"


def test_calm_conditions_name_no_hazard():
    risk = R.score_inputs(
        RiskInputs(precipitation_rate_mm_h=0, precipitation_24h_mm=0, precipitation_72h_mm=0,
                   wind_speed_kmh=8, wind_gust_kmh=12, apparent_temperature_c=27)
    )
    assert risk.risk_level == "Low"
    assert risk.detected_hazard == "None"
    assert risk.drivers == []


def test_missing_inputs_do_not_invent_risk():
    """An empty reading must score zero, never a scary default."""
    risk = R.score_inputs(RiskInputs())
    assert risk.risk_score == 0
    assert risk.detected_hazard == "None"


@pytest.mark.parametrize(
    "inputs,hazard",
    [
        (RiskInputs(precipitation_24h_mm=140, precipitation_72h_mm=150, precipitation_rate_mm_h=18), "Heavy Rainfall"),
        (RiskInputs(precipitation_24h_mm=120, precipitation_72h_mm=420, sustained_rain_hours=18), "Flood Risk"),
        (RiskInputs(wind_speed_kmh=85, wind_gust_kmh=110), "Strong Wind"),
        (RiskInputs(apparent_temperature_c=47), "Extreme Heat"),
        (RiskInputs(thunderstorm=True, cape_j_kg=2600), "Lightning/Storm"),
    ],
)
def test_dominant_hazard_detection(inputs, hazard):
    assert R.score_inputs(inputs).detected_hazard == hazard


def test_score_increases_monotonically_with_rainfall():
    previous = -1
    for rain in (0, 10, 40, 70, 120, 210, 320):
        score = R.score_inputs(RiskInputs(precipitation_24h_mm=rain, precipitation_72h_mm=rain)).risk_score
        assert score >= previous, f"score fell at {rain} mm"
        previous = score


def test_compound_hazards_score_above_any_single_one():
    rain_only = R.score_inputs(RiskInputs(precipitation_24h_mm=90, precipitation_72h_mm=95)).risk_score
    both = R.score_inputs(
        RiskInputs(precipitation_24h_mm=90, precipitation_72h_mm=95, wind_speed_kmh=70, wind_gust_kmh=95)
    ).risk_score
    assert both > rain_only


def test_sustained_drizzle_is_not_a_flood():
    """Hours of light rain without accumulation must not read as flooding."""
    risk = R.score_inputs(
        RiskInputs(precipitation_24h_mm=9, precipitation_72h_mm=12, sustained_rain_hours=20)
    )
    assert risk.detected_hazard != "Flood Risk"
    assert risk.risk_level in {"Low", "Moderate"}


def test_drivers_are_structured_and_quote_real_values():
    risk = R.score_inputs(RiskInputs(precipitation_24h_mm=180, precipitation_72h_mm=300, sustained_rain_hours=14))
    codes = {d["code"] for d in risk.driver_details}
    assert "rain_24h" in codes
    values = {d["code"]: d["value"] for d in risk.driver_details}
    assert values["rain_24h"] == 180


def test_hazard_scores_cover_every_hazard():
    risk = R.score_inputs(RiskInputs(precipitation_24h_mm=50, precipitation_72h_mm=60))
    assert set(risk.hazard_scores) == set(R.HAZARDS)


def test_is_actionable_matches_bands():
    assert not R.is_actionable(R.score_inputs(RiskInputs(apparent_temperature_c=30)))
    assert R.is_actionable(R.score_inputs(RiskInputs(apparent_temperature_c=47)))


def test_timeline_uses_the_same_engine(bundle_for, scenario):
    scenario("flood")
    bundle = bundle_for("Guwahati")
    hours = R.timeline(bundle, hours=24)
    assert len(hours) == 24
    for hour in hours:
        assert hour["risk_level"] == R.level_for(hour["risk_score"])
    # Sustained rain must make later hours riskier than the first.
    assert max(h["risk_score"] for h in hours) > hours[0]["risk_score"]


def test_assess_matches_across_consumers(bundle_for, scenario):
    """The invariant the whole product rests on: one bundle, one score."""
    scenario("flood")
    bundle = bundle_for("Guwahati")
    scores = {R.assess(bundle).risk_score for _ in range(5)}
    assert len(scores) == 1, "risk scoring is not deterministic"

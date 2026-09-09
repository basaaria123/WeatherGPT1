# -*- coding: utf-8 -*-
"""API contract tests, including the cross-feature consistency invariant."""

from __future__ import annotations

import pytest


def test_health_reports_capabilities(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["data_source"] in {"live", "fixture"}
    assert "llm" in body and "speech" in body and "alerts" in body


def test_config_drives_the_ui(client):
    body = client.get("/config").json()
    # Pinned to the corpus rather than to a literal list: /config is what the
    # picker believes, so it must name exactly the languages the app can answer
    # in — no more (a promise it cannot keep) and no fewer (a translation
    # nobody can reach).
    from app.services import i18n

    assert {lang["code"] for lang in body["languages"]} == set(i18n.LANGUAGES)
    assert "farmer" in body["user_types"] and "fisherman" in body["user_types"]
    assert [band["level"] for band in body["risk_bands"]] == ["Low", "Moderate", "High", "Severe"]


def test_chat_contract(client):
    body = client.post("/chat", json={"query": "Weather in Guwahati?"}).json()
    for field in ("session_id", "answer", "risk", "location", "current", "impacts", "verification", "degraded"):
        assert field in body, f"missing {field}"
    assert body["risk"]["risk_level"] in {"Low", "Moderate", "High", "Severe"}


def test_chat_omits_missing_metrics_rather_than_faking_them(client):
    """The UI must never have to render 'N/A' — absent fields come back null."""
    current = client.post("/chat", json={"query": "Weather in Guwahati?"}).json()["current"]
    for key, value in current.items():
        assert value is None or isinstance(value, (int, float, str, bool)), key


def test_timeline_has_24_hours_with_risk(client):
    body = client.get("/weather/timeline", params={"location": "Guwahati", "hours": 24}).json()
    assert len(body["hours"]) == 24
    for hour in body["hours"]:
        assert hour["risk_level"] in {"Low", "Moderate", "High", "Severe"}
        assert 0 <= hour["risk_score"] <= 100


def test_forecast_returns_seven_days(client):
    body = client.get("/weather/forecast", params={"location": "Kochi"}).json()
    assert len(body["days"]) == 7
    assert all(day["date"] for day in body["days"])


def test_risk_map_is_sorted_and_complete(client):
    body = client.get("/risk-map", params={"limit": 16}).json()
    scores = [entry["risk_score"] for entry in body["locations"]]
    assert scores == sorted(scores, reverse=True)
    assert body["errors"] == []


def test_climate_trend_reports_an_anomaly(client):
    body = client.get("/climate-trend", params={"location": "Kochi"}).json()
    assert body["summary"].strip()
    assert "precipitation_anomaly_pct" in body["metrics"]


def test_alerts_roundtrip(client):
    client.post("/alerts/scan")
    body = client.get("/alerts", params={"location": "guwahati", "language": "hi"}).json()
    assert body["count"] >= 1
    alert = body["alerts"][0]
    assert alert["severity_label"] != alert["severity"], "severity label was not localised"
    assert alert["actions_localised"]


def test_subscription_lifecycle(client):
    created = client.post(
        "/alerts/subscribe",
        json={"location": "Silchar", "hazard_types": ["Flood Risk"], "min_severity": "High"},
    ).json()
    assert created["location"].startswith("Silchar")
    assert client.get("/alerts/subscriptions").json()["subscriptions"]
    assert client.delete(f"/alerts/subscriptions/{created['id']}").status_code == 200
    assert client.delete(f"/alerts/subscriptions/{created['id']}").status_code == 404


def test_subscription_rejects_unknown_hazard(client):
    resp = client.post("/alerts/subscribe", json={"location": "Silchar", "hazard_types": ["Volcano"]})
    assert resp.status_code == 422
    assert "Volcano" in resp.json()["detail"]


def test_historical_events_are_exposed_without_criteria(client):
    body = client.get("/historical-events").json()
    assert body["events"]
    for event in body["events"]:
        assert "criteria" not in event, "matching thresholds should not be public payload"
        assert event["source_note"]


# --- The invariant the whole architecture rests on -------------------------
@pytest.mark.parametrize("place", ["Guwahati", "Mumbai", "Jaisalmer", "Bengaluru"])
def test_one_risk_score_everywhere(client, place):
    """Chat, /risk, the map and any alert must agree for the same location."""
    chat = client.post("/chat", json={"query": f"Weather in {place}?"}).json()
    direct = client.get("/risk", params={"location": place}).json()
    map_body = client.get("/risk-map", params={"limit": 16}).json()

    assert chat["risk"]["risk_score"] == direct["risk_score"]
    assert chat["risk"]["detected_hazard"] == direct["detected_hazard"]
    assert chat["risk"]["risk_level"] == direct["risk_level"]

    entry = next((e for e in map_body["locations"] if e["location"] == place), None)
    if entry is not None:
        assert entry["risk_score"] == direct["risk_score"], f"{place}: map disagrees with /risk"
        assert entry["detected_hazard"] == direct["detected_hazard"]


def test_alert_severity_matches_the_engine(client):
    client.post("/alerts/scan")
    for alert in client.get("/alerts").json()["alerts"]:
        direct = client.get("/risk", params={"location": alert["location"]}).json()
        assert alert["severity"] == direct["risk_level"], f"{alert['location']} severity drifted"
        assert alert["alert_type"] == direct["detected_hazard"]


def test_fixture_mode_is_labelled_everywhere(client):
    """Simulated data must be identifiable on every surface that serves it."""
    assert client.get("/health").json()["simulated_data"] is True
    assert client.post("/chat", json={"query": "Weather in Guwahati?"}).json()["data_source"] == "fixture"
    assert client.get("/weather/timeline", params={"location": "Guwahati"}).json()["data_source"] == "fixture"
    assert client.get("/risk-map", params={"limit": 4}).json()["data_source"] == "fixture"


# ---------------------------------------------------------------------------
# The advisory answers three questions, not one
# ---------------------------------------------------------------------------
def test_advisory_states_the_situation_and_the_numbers_behind_it(client):
    """A list of actions does not say what is happening or why it was said.

    Both are assembled from lines the same response already carries — the
    situation from the ordering the insight panel uses, the reason from the
    engine's own drivers — so neither can contradict the panels beside it.
    """
    body = client.get(
        "/weather/current", params={"location": "Guwahati", "user_type": "farmer"}
    ).json()
    advisory = body["advisory"]
    assert advisory["situation"], "no situation line"
    assert advisory["reason"], "no reason line"
    # The reason is measured values, not a paraphrase of the advice.
    assert any(ch.isdigit() for ch in advisory["reason"])
    assert advisory["reason"].count("·") <= 2, "more than three drivers is a list, not a glance"


def test_the_situation_does_not_merely_repeat_the_hazard_chip(client):
    """The card already names the hazard and the level above this line."""
    body = client.get(
        "/weather/current", params={"location": "Guwahati", "user_type": "farmer"}
    ).json()
    situation = body["advisory"]["situation"]
    hazard = body["advisory"]["hazard"]
    assert hazard.lower() not in situation.lower()


def test_the_same_weather_reads_differently_for_each_role(client):
    """The role-switch demonstration, asserted rather than hoped for.

    One location, one set of measurements, four readers: the advice must differ
    and the risk score must not.
    """
    seen = {}
    scores = set()
    for role in ("farmer", "fisherman", "driver", "outdoor_worker"):
        body = client.get(
            "/weather/current", params={"location": "Guwahati", "user_type": role}
        ).json()
        seen[role] = body["advisory"]["actions"][0]["action"]
        scores.add(body["risk"]["risk_score"])
    assert len(set(seen.values())) == len(seen), seen
    assert len(scores) == 1, "the weather changed between roles; only the reader should have"


def test_a_calm_day_claims_no_drivers(client):
    """No hazard means nothing to cite, and an empty `Because:` is worse than none."""
    body = client.get(
        "/weather/current", params={"location": "Vijayawada", "user_type": "farmer"}
    ).json()
    assert body["advisory"]["reason"] is None


@pytest.mark.parametrize("place", ["Guwahati", "Chennai"])
def test_a_reassuring_line_is_not_offered_when_a_hazard_is_named(client, place):
    """"Wind is light" is true in a flood and reads as an all-clear beside one.

    Both places are checked because the mismatch is not only a Severe problem:
    a Moderate flood advisory that opens "wind is light" contradicts the very
    next line telling the reader to stay off the water.
    """
    body = client.get(
        "/weather/current", params={"location": place, "user_type": "fisherman"}
    ).json()
    assert body["risk"]["detected_hazard"] != "None"
    situation = (body["advisory"]["situation"] or "").lower()
    assert "light" not in situation, situation


def test_a_calm_day_may_still_reassure(client):
    """The rule is about contradiction, not about never saying anything is fine."""
    body = client.get(
        "/weather/current", params={"location": "Vijayawada", "user_type": "fisherman"}
    ).json()
    assert body["risk"]["risk_level"] == "Low"
    assert body["advisory"]["situation"]

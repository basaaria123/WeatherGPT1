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
    assert {lang["code"] for lang in body["languages"]} == {"en", "hi", "te", "bn", "mr", "as"}
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

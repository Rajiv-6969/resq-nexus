"""Phase 4 tests: Live Official Alerts, Sentinel-1 SAR Flood Mapping (deferred fallback), and Event Replay."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import main
from conftest import demo_headers
from db.database import SessionLocal
from db.models import OfficialAlert, utcnow

client = TestClient(main.app)


@pytest.fixture
def admin():
    return demo_headers(client, "ADMIN")


def test_alerts_list_and_metrics():
    resp = client.get("/alerts")
    assert resp.status_code == 200
    alerts = resp.json()
    assert isinstance(alerts, list)
    assert len(alerts) > 0

    first = alerts[0]
    assert "alert_code" in first
    assert "headline" in first
    assert "severity" in first
    assert "status" in first

    metrics_resp = client.get("/alerts/metrics")
    assert metrics_resp.status_code == 200
    metrics = metrics_resp.json()
    assert "total_alerts" in metrics
    assert "active" in metrics
    assert "acknowledged" in metrics
    assert "escalated" in metrics
    assert "acknowledgment_rate" in metrics
    assert 0.0 <= metrics["acknowledgment_rate"] <= 1.0


def test_alert_acknowledgment(admin):
    # Find an active alert to acknowledge
    alerts = client.get("/alerts?status=ACTIVE").json()
    if not alerts:
        # Simulate one if none active
        sim_resp = client.post(
            "/alerts/simulate",
            headers=admin,
            json={
                "headline": "Test Active Alert",
                "description": "Test alert for acknowledgment testing",
                "severity": "Severe",
                "disaster_type": "flood",
                "area_desc": "Test Zone",
                "latitude": 12.9,
                "longitude": 77.6,
                "escalation_timeout_mins": 30,
            },
        )
        assert sim_resp.status_code == 200
        target_id = sim_resp.json()["id"]
    else:
        target_id = alerts[0]["id"]

    ack_resp = client.post(f"/alerts/{target_id}/acknowledge", headers=admin)
    assert ack_resp.status_code == 200
    updated = ack_resp.json()
    assert updated["status"] == "ACKNOWLEDGED"
    assert updated["acknowledged_at"] is not None
    assert updated["acknowledged_by"] is not None


def test_alert_auto_escalation():
    # Insert an expired alert into the DB and check auto-escalation
    with SessionLocal() as db:
        old_time = utcnow() - timedelta(hours=2)
        expired_alert = OfficialAlert(
            alert_code=f"ALT-EXP-{int(old_time.timestamp())}",
            sender="IMD Test",
            headline="Expired Alert for Escalation",
            description="Testing automated escalation timeout",
            severity="Extreme",
            disaster_type="flood",
            area_desc="Riverfront",
            latitude=10.0,
            longitude=76.3,
            source="test",
            status="ACTIVE",
            escalation_timeout_mins=10,
            created_at=old_time,
            updated_at=old_time,
        )
        db.add(expired_alert)
        db.commit()
        db.refresh(expired_alert)
        target_id = expired_alert.id

    # Calling GET /alerts triggers escalation check
    resp = client.get(f"/alerts/{target_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ESCALATED"
    assert data["escalated_at"] is not None


def test_sentinel_status():
    resp = client.get("/sentinel/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "Copernicus Sentinel-1 SAR Flood Mapping"
    assert "weights_deferred" in data
    assert "model_installed" in data
    # When resq_flood.onnx is present, model_installed is True and weights_deferred is False
    if data["model_installed"]:
        assert data["weights_deferred"] is False
        assert data["active_mode"] == "unet_segmentation"
        assert "UNet weights loaded" in data["notice"]
    else:
        assert data["weights_deferred"] is True
        assert data["active_mode"] == "sar_backscatter_thresholding"


def test_sentinel_status_deferred_fallback_mocked():
    with patch("services.imagery.sentinel.is_flood_model_available", return_value=False):
        resp = client.get("/sentinel/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["weights_deferred"] is True
        assert data["active_mode"] == "sar_backscatter_thresholding"
        assert "Deferred weights fallback" in data["notice"]


def test_sentinel_search_offline_fixture():
    with patch.dict(os.environ, {"OFFLINE_MODE": "1"}):
        resp = client.post(
            "/sentinel/search",
            json={
                "bbox": {"south": 12.8, "west": 77.4, "north": 13.15, "east": 77.85},
                "start_date": "2026-11-01",
                "end_date": "2026-11-10",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "scenes" in data
        assert len(data["scenes"]) > 0
        scene = data["scenes"][0]
        assert scene["properties"]["platform"] == "Sentinel-1A"
        assert "vv" in scene["assets"]


def test_sentinel_assess_flood_active_or_fallback():
    resp = client.post(
        "/sentinel/assess",
        json={
            "bbox": {"south": 12.92, "west": 77.62, "north": 12.98, "east": 77.68},
            "scenario_id": "flood-bengaluru",
            "water_threshold_db": -16.0,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["assessment_id"].startswith("SAR-")
    assert "Sen1Floods11" in data["method"]
    assert "total_area_km2" in data
    assert "flooded_area_km2" in data
    assert "zones" in data
    assert len(data["zones"]) > 0
    first_zone = data["zones"][0]
    assert "flooded_pct" in first_zone
    assert "severity" in first_zone
    assert "mean_backscatter_vv_db" in first_zone


def test_sentinel_assess_flood_with_deferred_weights():
    with patch("services.imagery.sentinel.is_flood_model_available", return_value=False):
        resp = client.post(
            "/sentinel/assess",
            json={
                "bbox": {"south": 12.92, "west": 77.62, "north": 12.98, "east": 77.68},
                "scenario_id": "flood-bengaluru",
                "water_threshold_db": -16.0,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["assessment_id"].startswith("SAR-")
        assert data["weights_deferred"] is True
        assert data["deferred_fallback_active"] is True
        assert "Sen1Floods11" in data["method"]
        assert "total_area_km2" in data
        assert "flooded_area_km2" in data
        assert "zones" in data
        assert len(data["zones"]) > 0
        first_zone = data["zones"][0]
        assert "flooded_pct" in first_zone


def test_event_replay_scenarios():
    resp = client.get("/replay/scenarios")
    assert resp.status_code == 200
    scenarios = resp.json()["scenarios"]
    assert len(scenarios) >= 4
    ids = {s["id"] for s in scenarios}
    assert "flood-aluva" in ids
    assert "flood-bengaluru" in ids


def test_event_replay_timeline_progression():
    resp = client.get("/replay/flood-aluva")
    assert resp.status_code == 200
    timeline = resp.json()
    assert timeline["scenario_id"] == "flood-aluva"
    assert timeline["total_steps"] == 5
    assert len(timeline["frames"]) == 5

    # Check progression across the 5 frames
    frames = timeline["frames"]
    assert frames[0]["phase"] == "OFFICIAL_ALERT"
    assert frames[1]["phase"] == "SATELLITE_PASS"
    assert frames[2]["phase"] == "CITIZEN_SOS"
    assert frames[3]["phase"] == "ALLOCATION_DISPATCH"
    assert frames[4]["phase"] == "RESPONSE_ESCALATION"

    # Frame 0 has alert but no dispatches
    assert len(frames[0]["alerts"]) > 0
    assert len(frames[0]["dispatches"]) == 0

    # Frame 3 has dispatches
    assert len(frames[3]["dispatches"]) > 0

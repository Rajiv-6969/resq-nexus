"""Unit and integration tests for Damage Assessment and Vantor STAC imagery."""
from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

import main
from conftest import demo_headers

client = TestClient(main.app)


@pytest.fixture
def admin():
    return demo_headers(client, "ADMIN")


def test_damage_status_endpoint():
    resp = client.get("/damage/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "model_installed" in data
    assert "inference_mode" in data
    assert data["inference_mode"] == "tiled"
    assert data["h3_resolution"] == 8


def test_damage_samples_list():
    resp = client.get("/damage/samples")
    assert resp.status_code == 200
    data = resp.json()
    assert "events" in data
    assert len(data["events"]) > 0
    tile = data["events"][0]["tiles"][0]
    assert "tile_id" in tile
    assert "bounds" in tile


def test_damage_sample_images():
    resp_pre = client.get("/damage/samples/palu-tsunami_0000001/image/pre")
    assert resp_pre.status_code == 200
    assert resp_pre.headers["content-type"] == "image/png"

    resp_post = client.get("/damage/samples/palu-tsunami_0000001/image/post")
    assert resp_post.status_code == 200
    assert resp_post.headers["content-type"] == "image/png"


def test_damage_assess_with_tile_id():
    payload = {
        "tile_id": "palu-tsunami_0000001",
        "bounds": {"south": -0.92, "west": 119.83, "north": -0.88, "east": 119.87},
    }
    resp = client.post("/damage/assess", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "assessment_id" in data
    assert "buildings" in data
    assert "zones" in data
    assert "timing" in data
    assert data["timing"]["mode"] in ("tiled", "none")
    assert data["source"] in ("model", "label")


def test_damage_assess_with_uploaded_images():
    img_pre = Image.new("RGB", (256, 256), color=(50, 50, 50))
    img_post = Image.new("RGB", (256, 256), color=(80, 40, 40))

    buf_pre = io.BytesIO()
    img_pre.save(buf_pre, format="PNG")
    buf_pre.seek(0)

    buf_post = io.BytesIO()
    img_post.save(buf_post, format="PNG")
    buf_post.seek(0)

    bounds_json = json.dumps({"south": 12.92, "west": 77.62, "north": 12.96, "east": 77.66})

    resp = client.post(
        "/damage/assess",
        files={
            "pre": ("pre.png", buf_pre, "image/png"),
            "post": ("post.png", buf_post, "image/png"),
        },
        data={"bounds": bounds_json},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["assessment_id"].startswith("ASM-")
    assert "zones" in data


def test_damage_metrics_endpoint():
    resp = client.get("/damage/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "test_results" in data
    assert "test_voted" in data["test_results"]
    voted = data["test_results"]["test_voted"]
    assert voted["localisation_f1"] == 0.8305
    assert voted["damage_f1_macro"] == 0.6394
    assert voted["xview2_score"] == 0.6618


def test_damage_allocate_workflow():
    assess_resp = client.post(
        "/damage/assess",
        json={"tile_id": "palu-tsunami_0000001"},
    )
    assert assess_resp.status_code == 200
    asm_id = assess_resp.json()["assessment_id"]

    alloc_resp = client.post("/damage/allocate", json={"assessment_id": asm_id})
    assert alloc_resp.status_code == 200
    alloc_data = alloc_resp.json()
    assert "engine" in alloc_data
    assert "zones" in alloc_data
    assert "resources" in alloc_data


def test_admin_satellite_incidents(admin):
    assess_resp = client.post("/damage/assess", json={"tile_id": "palu-tsunami_0000001"})
    asm_id = assess_resp.json()["assessment_id"]

    resp = client.get(f"/admin/incidents/satellite?assessment_id={asm_id}", headers=admin)
    assert resp.status_code == 200
    data = resp.json()
    assert "candidates" in data
    assert "threshold" in data


def test_scenario_buildings_endpoint():
    resp = client.get("/scenarios/flood-bengaluru/buildings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["scenario_id"] == "flood-bengaluru"
    assert "buildings" in data
    assert "counts" in data
    assert len(data["buildings"]) > 0


def test_vantor_events_and_search_offline():
    with patch.dict("os.environ", {"OFFLINE_MODE": "1"}):
        events_resp = client.get("/damage/vantor/events")
        assert events_resp.status_code == 200
        events = events_resp.json()["events"]
        assert len(events) > 0

        search_resp = client.post(
            "/damage/vantor/search",
            json={
                "event_id": "Nepal-Flooding-Aug-2026",
                "bbox": {"south": 27.0, "west": 84.5, "north": 28.5, "east": 85.5},
            },
        )
        assert search_resp.status_code == 200
        search_data = search_resp.json()
        assert "status" in search_data

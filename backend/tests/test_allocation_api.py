"""HTTP API: POST /scenarios/{id}/allocate, POST /scenarios/{id}/explain, weighted GET /priority."""
import json

import pytest
from fastapi.testclient import TestClient

import main
from conftest import demo_headers
from services import explain, gemini_client
from services.priority import PRIORITY_SETTINGS

# The Command Centre endpoints are admin-only, so this client is logged in as the demo admin.
client = TestClient(main.app, headers=demo_headers(TestClient(main.app), "ADMIN"))
ONLY_SEVERITY = {"severity": 1, "population": 0, "vulnerability": 0, "accessibility": 0}
ALGORITHM_NAMES = ("k-means", "kmeans", "dijkstra", "genetic", "deap")


@pytest.fixture
def no_gemini_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    gemini_client.get_client.cache_clear()
    main.clear_caches()


@pytest.fixture
def fake_gemini_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")
    main.clear_caches()
    yield
    main.clear_caches()


# --------------------------------------------------------------------------- allocate
def test_allocate_returns_engine_baseline_metrics_and_history():
    response = client.post("/scenarios/flood-assam/allocate")
    assert response.status_code == 200
    body = response.json()
    assert body["scenario_id"] == "flood-assam"
    assert len(body["zones"]) == 19 and 2 <= len(body["depots"]) <= 5
    for method in ("engine", "greedy"):
        assert {"avg_response_time_min", "coverage_pct", "unmet_demand", "gini", "computation_ms"} <= set(body[method]["metrics"])
    assert body["fitness_history"] and body["passes"]
    zone = body["zones"][0]
    assert {"allocated", "depot_id", "route", "travel_time_min", "coverage_pct"} <= set(zone["engine"])


def test_allocate_accepts_priority_weights():
    body = client.post("/scenarios/flood-assam/allocate", json={"weights": ONLY_SEVERITY}).json()
    assert body["weights"] == {"severity": 1.0, "population": 0.0, "vulnerability": 0.0, "accessibility": 0.0}


def test_allocate_is_repeatable():
    a = client.post("/scenarios/wildfire-kumaon/allocate").json()
    b = client.post("/scenarios/wildfire-kumaon/allocate").json()
    assert a["zones"] == b["zones"] and a["depots"] == b["depots"]


@pytest.mark.parametrize("weights", [
    {"severity": -0.1},
    {"severity": 0, "population": 0, "vulnerability": 0, "accessibility": 0},
    {"bogus": 1},
])
def test_allocate_rejects_bad_weights(weights):
    assert client.post("/scenarios/flood-assam/allocate", json={"weights": weights}).status_code == 422


def test_allocate_unknown_scenario_is_404():
    assert client.post("/scenarios/nope/allocate").status_code == 404


# --------------------------------------------------------------------------- priority with weights
def test_priority_accepts_weight_query_parameters():
    body = client.get("/scenarios/flood-assam/priority", params=ONLY_SEVERITY).json()
    assert body["settings"]["weights"] == {"severity": 1.0, "population": 0.0, "vulnerability": 0.0, "accessibility": 0.0}
    destroyed = [z for z in body["zones"] if z["damage_severity"] == 3]
    assert destroyed and all(z["priority_level"] == "Critical" for z in destroyed)


def test_priority_partial_weights_keep_other_defaults_then_rescale():
    body = client.get("/scenarios/flood-assam/priority", params={"severity": 0.4}).json()
    assert body["settings"]["weights"] == PRIORITY_SETTINGS["weights"]


def test_priority_rejects_all_zero_weights():
    params = {k: 0 for k in ONLY_SEVERITY}
    assert client.get("/scenarios/flood-assam/priority", params=params).status_code == 422


# --------------------------------------------------------------------------- explain
def test_explain_without_key_uses_templates(no_gemini_key):
    response = client.post("/scenarios/earthquake-kutch/explain")
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "template" and body["model"] is None
    assert "GEMINI_API_KEY" in body["notice"]
    ids = [e["zone_id"] for e in body["explanations"]]
    assert len(ids) == 19 and len(set(ids)) == 19
    for item in body["explanations"]:
        text = item["text"]
        assert item["source"] == "template"
        assert 2 <= text.count(". ") + 1 <= 3, text
        assert not any(name in text.lower() for name in ALGORITHM_NAMES)


def test_explain_uses_gemini_when_available(fake_gemini_key, monkeypatch):
    calls = []

    def fake_generate(prompt, model):
        calls.append(prompt)
        zones = json.loads(prompt.split("Zones (JSON):\n", 1)[1])
        return json.dumps([{"zone_id": z["zone_id"], "explanation": f"Gemini says {z['name']}."} for z in zones])

    monkeypatch.setattr(explain, "_generate", fake_generate)
    body = client.post("/scenarios/flood-assam/explain").json()
    assert body["source"] == "gemini" and body["notice"] is None
    assert body["model"] == gemini_client.model_name()
    assert len(calls) == 2  # 19 zones in two batched requests
    assert all(e["text"].startswith("Gemini says") for e in body["explanations"])


def test_explain_falls_back_when_gemini_fails(fake_gemini_key, monkeypatch):
    def broken(prompt, model):
        raise TimeoutError("simulated outage")

    monkeypatch.setattr(explain, "_generate", broken)
    body = client.post("/scenarios/flood-assam/explain").json()
    assert body["source"] == "template"
    assert "TimeoutError" in body["notice"]
    assert all(e["text"] for e in body["explanations"])


def test_explain_fills_zones_gemini_skipped(fake_gemini_key, monkeypatch):
    def partial(prompt, model):
        zones = json.loads(prompt.split("Zones (JSON):\n", 1)[1])
        return json.dumps([{"zone_id": zones[0]["zone_id"], "explanation": "Only one."}, {"zone_id": "nope", "explanation": "x"}])

    monkeypatch.setattr(explain, "_generate", partial)
    body = client.post("/scenarios/wildfire-kumaon/explain").json()
    assert body["source"] == "mixed"
    assert sum(e["source"] == "gemini" for e in body["explanations"]) == 2
    assert "template" in body["notice"]


def test_explain_unknown_scenario_is_404():
    assert client.post("/scenarios/nope/explain").status_code == 404


def test_root_lists_new_endpoints():
    endpoints = client.get("/").json()["endpoints"]
    assert "POST /scenarios/{id}/allocate" in endpoints and "POST /scenarios/{id}/explain" in endpoints

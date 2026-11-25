"""HTTP API: health and scenario endpoints, plus checks on the committed demo data."""
import pytest
from fastapi.testclient import TestClient

import main
from conftest import demo_headers
from services.scenarios import RESOURCE_TYPES, Scenario, get_scenario

# The Command Centre endpoints are admin-only, so this client is logged in as the demo admin.
client = TestClient(main.app, headers=demo_headers(TestClient(main.app), "ADMIN"))

DEMO_SCENARIOS = {"flood-aluva": "flood", "flood-bengaluru": "flood", "earthquake-coimbatore": "earthquake", "cyclone-visakhapatnam": "cyclone"}


def test_healthz_reports_ok():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_reports_ok():
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert isinstance(body["gemini_configured"], bool)


def test_list_scenarios_includes_the_three_demos():
    response = client.get("/scenarios")
    assert response.status_code == 200
    listed = {s["id"]: s for s in response.json()}
    assert set(DEMO_SCENARIOS) <= set(listed)
    for scenario_id, disaster in DEMO_SCENARIOS.items():
        entry = listed[scenario_id]
        assert entry["disaster_type"] == disaster
        assert 50 <= entry["zone_count"] <= 700
        assert entry["total_population"] > 0


def test_get_scenario_returns_full_data():
    response = client.get("/scenarios/flood-aluva")
    assert response.status_code == 200
    scenario = Scenario.model_validate(response.json())
    assert scenario.id == "flood-aluva"
    assert set(response.json()["resources"]) == set(RESOURCE_TYPES)
    first = response.json()["zones"][0]
    assert set(first) == {
        "id", "name", "latitude", "longitude", "disaster_type",
        "damage_severity", "population", "vulnerability_index", "accessibility",
        "h3_index", "geometry", "building_count", "source",
    }


def test_unknown_scenario_is_404():
    response = client.get("/scenarios/does-not-exist")
    assert response.status_code == 404
    assert "does-not-exist" in response.json()["detail"]


@pytest.mark.parametrize("scenario_id, disaster", sorted(DEMO_SCENARIOS.items()))
def test_demo_scenario_files_meet_the_spec(scenario_id, disaster):
    scenario = get_scenario(scenario_id)
    assert scenario.disaster_type == disaster
    assert 50 <= len(scenario.zones) <= 700  # H3 resolution-8 hexagons with people in them
    assert all(z.source == "simulated" and z.h3_index == z.id and z.geometry for z in scenario.zones)
    assert scenario.bbox and scenario.sources["damage"] == "simulated" and scenario.facilities
    assert scenario.synthetic and "SIMULATED" in scenario.data_note and "real" in scenario.data_note
    for zone in scenario.zones:
        assert 6.5 <= zone.latitude <= 37.5 and 68.0 <= zone.longitude <= 97.5  # inside India's extent
    assert all(getattr(scenario.resources, key) > 0 for key in RESOURCE_TYPES)
    # Every damage level should not collapse to one value in a demo.
    assert len({z.damage_severity for z in scenario.zones}) >= 3

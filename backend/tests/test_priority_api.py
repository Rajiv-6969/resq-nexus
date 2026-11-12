"""HTTP API: GET /scenarios/{id}/priority."""
import pytest
from fastapi.testclient import TestClient

import main
from conftest import demo_headers
from services.priority import PRIORITY_SETTINGS

# The Command Centre endpoints are admin-only, so this client is logged in as the demo admin.
client = TestClient(main.app, headers=demo_headers(TestClient(main.app), "ADMIN"))


@pytest.mark.parametrize("scenario_id", ["flood-aluva", "flood-bengaluru", "earthquake-coimbatore", "cyclone-visakhapatnam"])
def test_priority_returns_zones_sorted_with_levels(scenario_id):
    response = client.get(f"/scenarios/{scenario_id}/priority")
    assert response.status_code == 200
    body = response.json()

    assert body["scenario_id"] == scenario_id
    zones = body["zones"]
    assert 50 <= len(zones) <= 700
    scores = [z["priority_score"] for z in zones]
    assert scores == sorted(scores, reverse=True)
    assert [z["rank"] for z in zones] == list(range(1, len(zones) + 1))
    assert {z["priority_level"] for z in zones} <= {"Critical", "High", "Medium", "Low"}
    assert sum(body["summary"].values()) == len(zones)
    assert body["settings"]["weights"] == PRIORITY_SETTINGS["weights"]


def test_priority_zone_includes_the_score_breakdown():
    top = client.get("/scenarios/flood-aluva/priority").json()["zones"][0]
    assert {"priority_score", "priority_level", "rank", "factors", "contributions", "name", "population"} <= set(top)
    assert sum(top["contributions"].values()) == pytest.approx(top["priority_score"], abs=1e-3)


def test_priority_for_unknown_scenario_is_404():
    assert client.get("/scenarios/nope/priority").status_code == 404

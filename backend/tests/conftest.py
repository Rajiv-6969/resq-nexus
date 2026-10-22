"""Shared test helpers: small, hand-built scenario data."""
import copy

import pytest

ZONE = {
    "id": "Z01",
    "name": "Test Village",
    "latitude": 26.3,
    "longitude": 91.0,
    "disaster_type": "flood",
    "damage_severity": 2,
    "population": 5000,
    "vulnerability_index": 0.6,
    "accessibility": 0.4,
}

RESOURCES = {"rescue_teams": 4, "medical_kits": 200, "food_packets": 3000, "shelters": 12, "vehicles": 6}


def make_scenario(scenario_id="test-flood", zones=None, **overrides):
    """Return a valid scenario dict; zones default to 15 copies of ZONE with unique ids."""
    if zones is None:
        zones = [dict(ZONE, id=f"Z{i:02d}", name=f"Village {i}") for i in range(1, 16)]
    data = {
        "id": scenario_id,
        "name": "Test flood",
        "disaster_type": "flood",
        "region": "Test region",
        "state": "Assam",
        "resources": copy.deepcopy(RESOURCES),
        "zones": zones,
    }
    data.update(overrides)
    return data


@pytest.fixture
def scenario_factory():
    return make_scenario

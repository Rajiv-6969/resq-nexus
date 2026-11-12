"""Live SOS requests as extra demand for the Allocation Engine."""
import pytest
from fastapi.testclient import TestClient

import main
from conftest import demo_headers
from services.sos_demand import SOS_ZONE_RADIUS_KM, assign_to_zones, sos_demand

client = TestClient(main.app)
ZONES = [
    {"id": "A", "name": "Alpha", "latitude": 23.30, "longitude": 70.35},
    {"id": "B", "name": "Bravo", "latitude": 23.50, "longitude": 70.35},
]


class Req:
    def __init__(self, id, lat, lon, people=None, needs=()):
        self.id, self.latitude, self.longitude, self.people_affected, self.needs = id, lat, lon, people, list(needs)


@pytest.fixture(autouse=True)
def _db(fresh_db):
    main.clear_caches()
    yield
    main.clear_caches()


@pytest.fixture
def admin():
    return demo_headers(client, "ADMIN")


def allocate(headers, scenario="earthquake-coimbatore", **body):
    response = client.post(f"/scenarios/{scenario}/allocate", json=body, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def zone(result, zone_id):
    return next(z for z in result["zones"] if z["id"] == zone_id)


# --------------------------------------------------------------------------- demand per request
def test_each_need_adds_the_matching_resource():
    assert sos_demand(18, ["rescue", "medical", "shelter"]) == {
        "rescue_teams": 1, "medical_kits": 1, "food_packets": 0, "shelters": 1, "vehicles": 0}
    assert sos_demand(60, ["medical", "food", "water", "ambulance"]) == {
        "rescue_teams": 0, "medical_kits": 3, "food_packets": 60, "shelters": 0, "vehicles": 1}


def test_requests_go_to_their_nearest_zone_and_add_up():
    plan = assign_to_zones(ZONES, [Req(1, 23.31, 70.35, 4, ["food"]), Req(2, 23.29, 70.36, 6, ["food"]),
                                   Req(3, 23.49, 70.34, 2, ["rescue"])])
    by_zone = {z["zone_id"]: z for z in plan["zones"]}
    assert by_zone["A"]["requests"] == [1, 2] and by_zone["A"]["people"] == 10
    assert by_zone["A"]["demand"]["food_packets"] == 10
    assert by_zone["B"]["demand"]["rescue_teams"] == 1
    assert plan["extra_demand"]["A"]["food_packets"] == 10
    assert (plan["requests_included"], plan["people"], plan["outside"]) == (3, 12, 0)


def test_requests_far_from_every_zone_are_left_out():
    plan = assign_to_zones(ZONES, [Req(1, 12.97, 77.59, 3, ["food"])])  # Bengaluru, ~1,300 km away
    assert plan["zones"] == [] and plan["extra_demand"] == {}
    assert (plan["requests_included"], plan["outside"]) == (0, 1)
    assert SOS_ZONE_RADIUS_KM == 30


def test_a_request_without_details_counts_as_one_person_needing_rescue():
    plan = assign_to_zones(ZONES, [Req(1, 23.30, 70.35)])
    assert plan["zones"][0]["people"] == 1
    assert plan["extra_demand"]["A"] == {"rescue_teams": 1, "medical_kits": 0, "food_packets": 0, "shelters": 0, "vehicles": 0}


# --------------------------------------------------------------------------- the allocate endpoint
def test_without_the_option_the_allocation_is_unchanged(admin):
    plain = allocate(admin)
    assert plain["sos"] is None
    assert plain == allocate(admin, include_sos=False)


def test_live_sos_requests_add_to_the_demand_of_their_nearest_zones(admin):
    plain, live = allocate(admin), allocate(admin, include_sos=True)
    summary = live["sos"]
    assert summary["requests_included"] == 3  # the active Coimbatore requests from the seed
    assert summary["outside"] == 7  # active requests in Bengaluru, Ernakulam and Visakhapatnam
    hit = {z["zone_id"] for z in summary["zones"]}
    assert len(hit) == 3 and hit <= {z["id"] for z in plain["zones"]}  # Coimbatore hexagons
    tapovan = summary["zones"][0]
    for resource, added in tapovan["demand"].items():
        assert zone(live, tapovan["zone_id"])["demand"][resource] == zone(plain, tapovan["zone_id"])["demand"][resource] + added
    assert zone(live, tapovan["zone_id"])["sos"] == {"requests": tapovan["requests"], "people": tapovan["people"],
                                                     "demand": tapovan["demand"]}
    assert all(z["sos"] is None for z in live["zones"] if z["id"] not in hit)


def test_resolved_requests_no_longer_count(admin):
    meera = next(s for s in client.get("/admin/sos", headers=admin).json() if s["citizen"]["full_name"] == "Meera Patel")
    before = allocate(admin, include_sos=True)["sos"]["requests_included"]
    client.post(f"/admin/sos/{meera['id']}/status", json={"status": "RESOLVED"}, headers=admin)
    assert allocate(admin, include_sos=True)["sos"]["requests_included"] == before - 1


def test_a_new_sos_changes_the_next_run(admin):
    first = allocate(admin, include_sos=True)
    citizen = demo_headers(client, "CITIZEN")
    quiet = next(z for z in first["zones"] if z["sos"] is None and z["demand"]["food_packets"] == 0)  # undamaged hexagon
    sos = client.post("/sos", json={"latitude": quiet["latitude"], "longitude": quiet["longitude"], "location_source": "pin"}, headers=citizen).json()
    client.patch(f"/sos/{sos['id']}/details", headers=citizen, json={
        "emergency_type": "earthquake", "people_affected": 40, "injuries": "serious", "needs": ["rescue", "medical", "food"],
        "vulnerable": [], "description": "", "contact_phone": "+91 00000 01001"})
    second = allocate(admin, include_sos=True)
    assert second["sos"]["requests_included"] == first["sos"]["requests_included"] + 1
    after = zone(second, quiet["id"])  # undamaged in the scenario, so its only need is the new SOS
    assert after["demand"]["food_packets"] == 40 and after["sos"]["people"] == 40


def test_explanations_mention_the_live_requests(admin):
    response = client.post("/scenarios/earthquake-coimbatore/explain", json={"include_sos": True}, headers=admin)
    assert response.status_code == 200
    texts = {e["zone_id"]: e["text"] for e in response.json()["explanations"]}
    with_sos = {z["id"] for z in allocate(admin, include_sos=True)["zones"] if z["sos"]}
    assert with_sos and all("live SOS request" in texts[z] for z in with_sos)
    assert all("live SOS" not in texts[z] for z in texts if z not in with_sos)
    plain = client.post("/scenarios/earthquake-coimbatore/explain", json={}, headers=admin).json()
    assert all("live SOS" not in e["text"] for e in plain["explanations"])


def test_include_sos_must_be_a_boolean(admin):
    response = client.post("/scenarios/earthquake-coimbatore/allocate", json={"include_sos": "maybe"}, headers=admin)
    assert response.status_code == 422

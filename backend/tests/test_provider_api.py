"""Service providers: their resources, assigned and nearby requests, accept and status updates."""
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

import main
from conftest import DEMO_PASSWORD, demo_headers, login_headers

client = TestClient(main.app)
PROVIDER_PASSWORD = DEMO_PASSWORD["SERVICE_PROVIDER"]


@pytest.fixture(autouse=True)
def _db(fresh_db):
    yield


@pytest.fixture
def provider():
    return demo_headers(client, "SERVICE_PROVIDER")  # Jayanagar Relief Hospital, Bengaluru


def other_provider():
    return login_headers(client, "koramangala.ambulance@resq.example", PROVIDER_PASSWORD)


def my_resources(headers):
    return client.get("/provider/resources", headers=headers).json()


def requests_board(headers, **params):
    response = client.get("/provider/requests", params=params, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def nearest_unassigned(headers):
    return requests_board(headers)["nearby"][0]


# --------------------------------------------------------------------------- resources
def test_provider_sees_only_their_own_resources(provider):
    names = {r["name"] for r in my_resources(provider)}
    assert names == {"Jayanagar Relief Hospital", "Jayanagar Relief Hospital Ambulances"}


def test_provider_updates_availability_and_status(provider):
    hospital = next(r for r in my_resources(provider) if r["resource_type"] == "HOSPITAL")
    response = client.patch(f"/provider/resources/{hospital['id']}", json={"capacity_available": 0, "status": "FULL"},
                            headers=provider)
    assert response.status_code == 200
    body = response.json()
    assert (body["capacity_available"], body["status"]) == (0, "FULL")
    assert datetime.fromisoformat(body["updated_at"]) > datetime.fromisoformat(hospital["updated_at"])
    # citizens see the new numbers straight away
    seen = client.get("/resources/nearby", params={"lat": hospital["latitude"], "lon": hospital["longitude"], "radius_km": 1},
                      headers=demo_headers(client, "CITIZEN")).json()["resources"]
    assert next(r for r in seen if r["id"] == hospital["id"])["status"] == "FULL"


def test_provider_can_change_total_and_available_together(provider):
    hospital = next(r for r in my_resources(provider) if r["resource_type"] == "HOSPITAL")
    body = client.patch(f"/provider/resources/{hospital['id']}", json={"capacity_total": 150, "capacity_available": 140},
                        headers=provider).json()
    assert (body["capacity_total"], body["capacity_available"]) == (150, 140)


@pytest.mark.parametrize(
    ("update", "message"),
    [
        ({"capacity_available": 500}, "more than the total"),
        ({"capacity_total": 2}, "more than the total"),
        ({"capacity_available": -1}, "greater than or equal to 0"),
        ({"status": "BUSY"}, "Input should be"),
        ({}, "Nothing to update"),
        ({"name": "Renamed"}, "Extra inputs"),
    ],
)
def test_resource_updates_are_validated(provider, update, message):
    hospital = next(r for r in my_resources(provider) if r["resource_type"] == "HOSPITAL")
    response = client.patch(f"/provider/resources/{hospital['id']}", json=update, headers=provider)
    assert response.status_code == 422
    assert message in str(response.json()["detail"])


def test_provider_cannot_update_another_organisations_resource(provider):
    theirs = my_resources(other_provider())[0]
    response = client.patch(f"/provider/resources/{theirs['id']}", json={"capacity_available": 1}, headers=provider)
    assert response.status_code == 404


# --------------------------------------------------------------------------- requests
def test_board_shows_assigned_and_nearby_unassigned_requests(provider):
    board = requests_board(provider)
    assigned = board["assigned"]
    assert [r["status"] for r in assigned] == ["RESOLVED"]  # the seeded request this hospital handled
    nearby = board["nearby"]
    assert len(nearby) == 3  # the three unassigned Bengaluru requests; none from other regions
    assert all(r["status"] == "PENDING" and r["assigned_provider"] is None for r in nearby)
    distances = [r["distance_km"] for r in nearby]
    assert distances == sorted(distances) and distances[-1] <= board["radius_km"] == 25
    assert all(r["citizen"]["phone"] for r in nearby)  # the provider can call back


def test_board_radius_can_be_widened(provider):
    assert len(requests_board(provider, radius_km=200)["nearby"]) >= len(requests_board(provider, radius_km=5)["nearby"])
    assert client.get("/provider/requests", params={"radius_km": 1000}, headers=provider).status_code == 422


def test_accepting_a_request_acknowledges_it_and_tells_the_citizen(provider):
    target = nearest_unassigned(provider)
    response = client.post(f"/provider/requests/{target['id']}/accept", headers=provider)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ACKNOWLEDGED"
    assert body["assigned_provider"]["organisation_name"] == "Jayanagar Relief Hospital"
    assert body["timeline"][1]["at"] is not None
    board = requests_board(provider)
    assert target["id"] in [r["id"] for r in board["assigned"]]
    assert target["id"] not in [r["id"] for r in board["nearby"]]


def test_a_request_accepted_by_one_provider_cannot_be_taken_by_another(provider):
    target = nearest_unassigned(provider)
    assert client.post(f"/provider/requests/{target['id']}/accept", headers=provider).status_code == 200
    response = client.post(f"/provider/requests/{target['id']}/accept", headers=other_provider())
    assert response.status_code == 409
    assert "another provider" in response.json()["detail"]


def test_status_moves_forward_one_step_at_a_time(provider):
    target = nearest_unassigned(provider)
    client.post(f"/provider/requests/{target['id']}/accept", headers=provider)
    skip = client.post(f"/provider/requests/{target['id']}/status", json={"status": "RESOLVED"}, headers=provider)
    assert skip.status_code == 409
    assert "DISPATCHED" in skip.json()["detail"]
    dispatched = client.post(f"/provider/requests/{target['id']}/status", json={"status": "DISPATCHED"}, headers=provider)
    assert dispatched.json()["status"] == "DISPATCHED"
    resolved = client.post(f"/provider/requests/{target['id']}/status", json={"status": "RESOLVED"}, headers=provider)
    assert resolved.json()["status"] == "RESOLVED"
    stamps = [step["at"] for step in resolved.json()["timeline"]]
    assert all(stamps) and stamps == sorted(stamps)
    again = client.post(f"/provider/requests/{target['id']}/status", json={"status": "RESOLVED"}, headers=provider)
    assert again.status_code == 409


def test_status_updates_need_the_request_to_be_accepted_first(provider):
    target = nearest_unassigned(provider)
    response = client.post(f"/provider/requests/{target['id']}/status", json={"status": "DISPATCHED"}, headers=provider)
    assert response.status_code == 409
    assert "Accept" in response.json()["detail"]


@pytest.mark.parametrize("status", ["PENDING", "ACKNOWLEDGED", "DONE"])
def test_status_value_is_validated(provider, status):
    target = nearest_unassigned(provider)
    response = client.post(f"/provider/requests/{target['id']}/status", json={"status": status}, headers=provider)
    assert response.status_code == 422


def test_requests_of_other_providers_are_hidden(provider):
    theirs = requests_board(login_headers(client, "shivajinagar.fire@resq.example", PROVIDER_PASSWORD))["assigned"][0]
    assert client.post(f"/provider/requests/{theirs['id']}/status", json={"status": "DISPATCHED"},
                       headers=provider).status_code == 404
    assert client.get(f"/sos/{theirs['id']}", headers=provider).status_code == 404


def test_an_assigned_request_is_visible_to_its_provider(provider):
    target = nearest_unassigned(provider)
    client.post(f"/provider/requests/{target['id']}/accept", headers=provider)
    detail = client.get(f"/sos/{target['id']}", headers=provider)
    assert detail.status_code == 200
    assert detail.json()["citizen"]["full_name"]


# --------------------------------------------------------------------------- who may use it
@pytest.mark.parametrize(
    ("email", "message"),
    [("whitefield.trust@resq.example", "awaiting admin approval"), ("quickhelp.water@resq.example", "not approved")],
)
def test_unapproved_providers_are_blocked(email, message):
    headers = login_headers(client, email, PROVIDER_PASSWORD)
    for path in ("/provider/resources", "/provider/requests"):
        response = client.get(path, headers=headers)
        assert response.status_code == 403
        assert message in response.json()["detail"]
    assert client.get("/auth/me", headers=headers).json()["provider"]["approval_status"] in {"PENDING", "REJECTED"}


@pytest.mark.parametrize("role", ["CITIZEN", "ADMIN"])
def test_other_roles_cannot_use_provider_endpoints(role):
    headers = demo_headers(client, role)
    assert client.get("/provider/requests", headers=headers).status_code == 403
    assert client.get("/provider/resources", headers=headers).status_code == 403

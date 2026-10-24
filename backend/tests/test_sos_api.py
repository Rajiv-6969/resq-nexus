"""Citizen SOS: save with location first, add details, track status."""
import pytest
from fastapi.testclient import TestClient

import main
from conftest import DEMO_PASSWORD, demo_headers, login_headers

client = TestClient(main.app)

LOCATION = {"latitude": 12.9352, "longitude": 77.6245, "location_source": "gps", "accuracy_m": 18}
DETAILS = {
    "emergency_type": "flood",
    "people_affected": 4,
    "injuries": "minor",
    "needs": ["rescue", "food"],
    "vulnerable": ["children"],
    "description": "Water is rising inside the house.",
    "contact_phone": "+91 00000 01001",
}


@pytest.fixture(autouse=True)
def _db(fresh_db):
    yield


@pytest.fixture
def citizen():
    return demo_headers(client, "CITIZEN")


def send_sos(headers, **overrides):
    response = client.post("/sos", json=dict(LOCATION, **overrides), headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_sos_is_saved_straight_away_with_only_its_location(citizen):
    sos = send_sos(citizen)
    assert sos["status"] == "PENDING"
    assert (sos["latitude"], sos["longitude"]) == (12.9352, 77.6245)
    assert sos["location_source"] == "gps"
    assert sos["details_submitted"] is False
    assert sos["severity"] is None
    assert sos["assigned_provider"] is None
    assert [step["status"] for step in sos["timeline"]] == ["PENDING", "ACKNOWLEDGED", "DISPATCHED", "RESOLVED"]
    assert sos["timeline"][0]["at"] is not None
    assert all(step["at"] is None for step in sos["timeline"][1:])


def test_a_dropped_pin_works_without_accuracy(citizen):
    sos = send_sos(citizen, location_source="pin", accuracy_m=None)
    assert sos["location_source"] == "pin"
    assert sos["accuracy_m"] is None


def test_details_are_added_to_the_saved_sos(citizen):
    sos = send_sos(citizen)
    response = client.patch(f"/sos/{sos['id']}/details", json=DETAILS, headers=citizen)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == sos["id"]
    assert body["details_submitted"] is True
    assert body["emergency_type"] == "flood"
    assert body["people_affected"] == 4
    assert body["needs"] == ["rescue", "food"]
    assert body["vulnerable"] == ["children"]
    assert body["severity"]["level"] == "Medium"


def test_details_can_be_corrected_until_the_request_is_resolved(citizen):
    sos = send_sos(citizen)
    client.patch(f"/sos/{sos['id']}/details", json=DETAILS, headers=citizen)
    update = dict(DETAILS, people_affected=9, injuries="serious", needs=["food", "rescue", "food"])
    body = client.patch(f"/sos/{sos['id']}/details", json=update, headers=citizen).json()
    assert body["people_affected"] == 9
    assert body["injuries"] == "serious"
    assert body["needs"] == ["rescue", "food"]  # de-duplicated, in the form's order


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("emergency_type", "volcano", "Input should be"),
        ("people_affected", 0, "greater than or equal to 1"),
        ("people_affected", 10_001, "less than or equal to 10000"),
        ("injuries", "some", "Input should be"),
        ("needs", [], "at least one"),
        ("needs", ["pizza"], "Input should be"),
        ("vulnerable", ["teenagers"], "Input should be"),
        ("description", "x" * 501, "500"),
        ("contact_phone", "call me", "phone"),
    ],
)
def test_details_are_validated(citizen, field, value, message):
    sos = send_sos(citizen)
    response = client.patch(f"/sos/{sos['id']}/details", json=dict(DETAILS, **{field: value}), headers=citizen)
    assert response.status_code == 422
    assert message in str(response.json()["detail"])


def test_contact_phone_is_required(citizen):
    sos = send_sos(citizen)
    details = {k: v for k, v in DETAILS.items() if k != "contact_phone"}
    assert client.patch(f"/sos/{sos['id']}/details", json=details, headers=citizen).status_code == 422


@pytest.mark.parametrize(
    "location",
    [
        dict(LOCATION, latitude=91),
        dict(LOCATION, longitude=-200),
        dict(LOCATION, location_source="wifi"),
        dict(LOCATION, accuracy_m=-5),
        {"longitude": 77.6, "location_source": "gps"},
    ],
)
def test_location_is_validated(citizen, location):
    assert client.post("/sos", json=location, headers=citizen).status_code == 422


def test_my_requests_lists_the_newest_first_with_its_tracker(citizen):
    sos = send_sos(citizen)
    mine = client.get("/sos/mine", headers=citizen).json()
    assert mine[0]["id"] == sos["id"]
    past = mine[1]  # the demo citizen's resolved request from the seed
    assert past["status"] == "RESOLVED"
    assert all(step["at"] is not None for step in past["timeline"])
    assert past["assigned_provider"]["organisation_name"] == "Jayanagar Relief Hospital"
    stamps = [step["at"] for step in past["timeline"]]
    assert stamps == sorted(stamps)


def test_a_citizen_can_poll_their_own_request(citizen):
    sos = send_sos(citizen)
    response = client.get(f"/sos/{sos['id']}", headers=citizen)
    assert response.status_code == 200
    assert response.json()["status"] == "PENDING"


def test_citizens_cannot_see_or_edit_other_peoples_requests(citizen):
    sos = send_sos(citizen)
    other = login_headers(client, "ravi.kumar@resq.example", DEMO_PASSWORD["CITIZEN"])
    assert client.get(f"/sos/{sos['id']}", headers=other).status_code == 404
    assert client.patch(f"/sos/{sos['id']}/details", json=DETAILS, headers=other).status_code == 404
    assert sos["id"] not in [s["id"] for s in client.get("/sos/mine", headers=other).json()]


def test_resolved_requests_cannot_be_edited(citizen):
    resolved = next(s for s in client.get("/sos/mine", headers=citizen).json() if s["status"] == "RESOLVED")
    response = client.patch(f"/sos/{resolved['id']}/details", json=DETAILS, headers=citizen)
    assert response.status_code == 409
    assert "resolved" in response.json()["detail"]


def test_unknown_request_is_404(citizen):
    assert client.get("/sos/999999", headers=citizen).status_code == 404


@pytest.mark.parametrize("role", ["SERVICE_PROVIDER", "ADMIN"])
def test_only_citizens_send_sos(role):
    response = client.post("/sos", json=LOCATION, headers=demo_headers(client, role))
    assert response.status_code == 403


def test_sending_sos_needs_a_login():
    assert client.post("/sos", json=LOCATION).status_code == 401

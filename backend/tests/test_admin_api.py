"""Admin: SOS monitor, suggestions and assignment, provider approvals, users and resources."""
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
def admin():
    return demo_headers(client, "ADMIN")


def get(path, headers, **params):
    response = client.get(path, params=params, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def sos_by_citizen(admin, name):
    return next(s for s in get("/admin/sos", admin) if s["citizen"]["full_name"] == name)


def provider_named(admin, organisation):
    return next(p for p in get("/admin/providers", admin) if p["organisation_name"] == organisation)


# --------------------------------------------------------------------------- summary + monitor
def test_summary_counts_requests_and_capacity(admin):
    summary = get("/admin/summary", admin)
    assert summary["sos"] == {"total": 12, "active": 10, "pending": 6, "acknowledged": 2, "dispatched": 2, "resolved": 2}
    resources = get("/admin/resources", admin)
    open_ = [r for r in resources if r["status"] == "OPEN"]
    assert summary["shelter_capacity_available"] == sum(r["capacity_available"] for r in open_ if r["resource_type"] == "SHELTER")
    assert summary["ambulances_available"] == sum(r["capacity_available"] for r in open_ if r["resource_type"] == "AMBULANCE")
    assert summary["providers_pending"] == 2


def test_a_new_sos_shows_up_in_the_counters(admin):
    citizen = demo_headers(client, "CITIZEN")
    client.post("/sos", json={"latitude": 12.95, "longitude": 77.6, "location_source": "gps"}, headers=citizen)
    sos = get("/admin/summary", admin)["sos"]
    assert (sos["active"], sos["pending"], sos["total"]) == (11, 7, 13)


def test_monitor_lists_every_request_with_severity_and_citizen(admin):
    requests = get("/admin/sos", admin)
    assert len(requests) == 12
    assert all(r["citizen"]["full_name"] for r in requests)
    levels = {r["severity"]["level"] for r in requests if r["severity"]}
    assert {"Critical", "High", "Medium", "Low"} <= levels
    active = [r["status"] != "RESOLVED" for r in requests]
    assert active == sorted(active, reverse=True)  # active requests come first


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({"status": "PENDING"}, 6),
        ({"status": "PENDING,ACKNOWLEDGED"}, 8),
        ({"type": "flood"}, 3),
        ({"status": "PENDING", "type": "flood"}, 2),
        ({"type": "earthquake,wildfire"}, 4),
    ],
)
def test_monitor_filters_by_status_and_type(admin, params, expected):
    requests = get("/admin/sos", admin, **params)
    assert len(requests) == expected
    if "status" in params:
        assert {r["status"] for r in requests} <= set(params["status"].split(","))


@pytest.mark.parametrize("params", [{"status": "LOST"}, {"type": "meteor"}])
def test_monitor_rejects_unknown_filters(admin, params):
    assert client.get("/admin/sos", params=params, headers=admin).status_code == 422


# --------------------------------------------------------------------------- suggestions + assignment
def test_suggestions_rank_suitable_providers_nearest_first(admin):
    sos = sos_by_citizen(admin, "Fatima Sheikh")  # HSR Layout: ambulance + medical
    body = get(f"/admin/sos/{sos['id']}/suggestions", admin)
    candidates = body["candidates"]
    assert candidates[0]["provider"]["organisation_name"] == "Koramangala Ambulance Station"
    assert [c["distance_km"] for c in candidates] == sorted(c["distance_km"] for c in candidates)
    for c in candidates:
        assert c["resource"]["status"] == "OPEN" and c["resource"]["capacity_available"] > 0
        assert c["resource"]["resource_type"] in {"AMBULANCE", "HOSPITAL"}
        assert set(c["matched_needs"]) <= {"ambulance", "medical"}
    assert body["needs"] == ["medical", "ambulance"]


def test_suggestions_skip_providers_without_capacity(admin):
    sos = sos_by_citizen(admin, "Fatima Sheikh")
    station = next(r for r in get("/admin/resources", admin) if r["name"] == "Koramangala Ambulance Station")
    client.patch(f"/admin/resources/{station['id']}", json={"capacity_available": 0}, headers=admin)
    first = get(f"/admin/sos/{sos['id']}/suggestions", admin)["candidates"][0]
    assert first["provider"]["organisation_name"] == "Jayanagar Relief Hospital"


def test_suggestions_for_a_request_without_details_consider_every_type(admin):
    sos = sos_by_citizen(admin, "Arjun Nair")  # location only, Malleshwaram
    body = get(f"/admin/sos/{sos['id']}/suggestions", admin)
    assert body["needs"] == []
    assert body["candidates"]
    assert body["candidates"][0]["distance_km"] < 10


def test_assigning_a_provider_keeps_the_request_pending_until_they_accept(admin):
    sos = sos_by_citizen(admin, "Fatima Sheikh")
    hospital = provider_named(admin, "Jayanagar Relief Hospital")
    response = client.post(f"/admin/sos/{sos['id']}/assign", json={"provider_id": hospital["id"]}, headers=admin)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["assigned_provider"]["id"] == hospital["id"]
    assert body["assigned_at"]
    provider = demo_headers(client, "SERVICE_PROVIDER")
    assert sos["id"] in [r["id"] for r in get("/provider/requests", provider)["assigned"]]
    accepted = client.post(f"/provider/requests/{sos['id']}/accept", headers=provider)
    assert accepted.json()["status"] == "ACKNOWLEDGED"


def test_a_pending_request_can_be_reassigned(admin):
    sos = sos_by_citizen(admin, "Fatima Sheikh")
    first = provider_named(admin, "Jayanagar Relief Hospital")
    second = provider_named(admin, "Koramangala Ambulance Station")
    client.post(f"/admin/sos/{sos['id']}/assign", json={"provider_id": first["id"]}, headers=admin)
    body = client.post(f"/admin/sos/{sos['id']}/assign", json={"provider_id": second["id"]}, headers=admin).json()
    assert body["assigned_provider"]["id"] == second["id"]


@pytest.mark.parametrize(
    ("citizen", "organisation", "status", "message"),
    [
        ("Fatima Sheikh", "Whitefield Volunteer Shelter Trust", 409, "not approved"),
        ("Ravi Kumar", "Jayanagar Relief Hospital", 409, "already been accepted"),
    ],
)
def test_assignment_rules(admin, citizen, organisation, status, message):
    sos = sos_by_citizen(admin, citizen)
    provider = provider_named(admin, organisation)
    response = client.post(f"/admin/sos/{sos['id']}/assign", json={"provider_id": provider["id"]}, headers=admin)
    assert response.status_code == status
    assert message in response.json()["detail"]


def test_assigning_an_unknown_provider_is_404(admin):
    sos = sos_by_citizen(admin, "Fatima Sheikh")
    assert client.post(f"/admin/sos/{sos['id']}/assign", json={"provider_id": 99_999}, headers=admin).status_code == 404


def test_admin_can_close_a_request_or_move_it_on(admin):
    false_alarm = sos_by_citizen(admin, "Arjun Nair")
    closed = client.post(f"/admin/sos/{false_alarm['id']}/status", json={"status": "RESOLVED"}, headers=admin)
    assert closed.json()["status"] == "RESOLVED"
    again = client.post(f"/admin/sos/{false_alarm['id']}/status", json={"status": "RESOLVED"}, headers=admin)
    assert again.status_code == 409
    fire = sos_by_citizen(admin, "Ravi Kumar")  # ACKNOWLEDGED
    moved = client.post(f"/admin/sos/{fire['id']}/status", json={"status": "DISPATCHED"}, headers=admin)
    assert moved.json()["status"] == "DISPATCHED"


def test_admin_cannot_acknowledge_without_a_provider(admin):
    sos = sos_by_citizen(admin, "Suresh Gowda")  # PENDING, unassigned
    response = client.post(f"/admin/sos/{sos['id']}/status", json={"status": "ACKNOWLEDGED"}, headers=admin)
    assert response.status_code == 409
    assert "Assign a provider" in response.json()["detail"]


# --------------------------------------------------------------------------- provider approvals
def test_pending_registrations_are_listed(admin):
    names = {p["organisation_name"] for p in get("/admin/providers", admin, status="PENDING")}
    assert names == {"Whitefield Volunteer Shelter Trust", "Hennur Rapid Ambulance"}


def test_approving_a_provider_lets_them_in_with_a_starter_resource(admin):
    trust = provider_named(admin, "Whitefield Volunteer Shelter Trust")
    response = client.post(f"/admin/providers/{trust['id']}/approve", headers=admin)
    assert response.status_code == 200
    assert response.json()["approval_status"] == "APPROVED"
    assert response.json()["reviewed_at"]
    headers = login_headers(client, "whitefield.trust@resq.example", PROVIDER_PASSWORD)
    resources = get("/provider/resources", headers)
    assert [(r["name"], r["resource_type"], r["status"]) for r in resources] == [
        ("Whitefield Volunteer Shelter Trust", "SHELTER", "CLOSED")
    ]


def test_rejecting_a_provider_records_the_reason(admin):
    hennur = provider_named(admin, "Hennur Rapid Ambulance")
    response = client.post(f"/admin/providers/{hennur['id']}/reject", json={"note": "Licence number missing."}, headers=admin)
    assert response.json()["approval_status"] == "REJECTED"
    assert response.json()["review_note"] == "Licence number missing."
    headers = login_headers(client, "hennur.ambulance@resq.example", PROVIDER_PASSWORD)
    assert client.get("/provider/requests", headers=headers).status_code == 403


def test_review_decisions_follow_the_rules(admin):
    approved = provider_named(admin, "Jayanagar Relief Hospital")
    assert client.post(f"/admin/providers/{approved['id']}/approve", headers=admin).status_code == 409
    assert client.post(f"/admin/providers/{approved['id']}/reject", headers=admin).status_code == 409
    rejected = provider_named(admin, "QuickHelp Water Supply")
    assert client.post(f"/admin/providers/{rejected['id']}/approve", headers=admin).status_code == 200
    assert client.post("/admin/providers/99999/approve", headers=admin).status_code == 404


# --------------------------------------------------------------------------- users
def test_users_can_be_listed_by_role(admin):
    assert len(get("/admin/users", admin)) == 33
    citizens = get("/admin/users", admin, role="CITIZEN")
    assert len(citizens) == 12 and {u["role"] for u in citizens} == {"CITIZEN"}
    assert client.get("/admin/users", params={"role": "KING"}, headers=admin).status_code == 422


def test_deactivating_a_user_blocks_their_login(admin):
    citizen = next(u for u in get("/admin/users", admin, role="CITIZEN") if u["email"] == "citizen@resq.example")
    response = client.patch(f"/admin/users/{citizen['id']}", json={"is_active": False}, headers=admin)
    assert response.json()["is_active"] is False
    assert client.post("/auth/login", json={"email": "citizen@resq.example", "password": DEMO_PASSWORD["CITIZEN"]}).status_code == 403
    client.patch(f"/admin/users/{citizen['id']}", json={"is_active": True}, headers=admin)
    assert client.post("/auth/login", json={"email": "citizen@resq.example", "password": DEMO_PASSWORD["CITIZEN"]}).status_code == 200


def test_admin_cannot_deactivate_their_own_account(admin):
    me = client.get("/auth/me", headers=admin).json()
    response = client.patch(f"/admin/users/{me['id']}", json={"is_active": False}, headers=admin)
    assert response.status_code == 409


# --------------------------------------------------------------------------- resources
NEW_RESOURCE = {
    "name": "Ulsoor Relief Camp",
    "resource_type": "SHELTER",
    "latitude": 12.981,
    "longitude": 77.62,
    "area": "Ulsoor",
    "region": "Bengaluru",
    "contact_phone": "+91 80 0000 2199",
    "capacity_total": 200,
    "capacity_available": 200,
    "status": "OPEN",
}


def test_resources_can_be_listed_and_filtered(admin):
    assert len(get("/admin/resources", admin)) == 58
    hospitals = get("/admin/resources", admin, type="HOSPITAL", region="Bengaluru")
    assert len(hospitals) == 4 and {r["resource_type"] for r in hospitals} == {"HOSPITAL"}
    assert {r["status"] for r in get("/admin/resources", admin, status="FULL")} == {"FULL"}


def test_admin_creates_updates_and_deletes_a_resource(admin):
    created = client.post("/admin/resources", json=NEW_RESOURCE, headers=admin)
    assert created.status_code == 201
    resource = created.json()
    assert resource["unit"] == "places" and resource["provider"] is None
    owner = provider_named(admin, "Koramangala Community Shelter")
    updated = client.patch(f"/admin/resources/{resource['id']}", json={"status": "FULL", "capacity_available": 0,
                                                                       "provider_id": owner["id"]}, headers=admin).json()
    assert (updated["status"], updated["capacity_available"]) == ("FULL", 0)
    assert updated["provider"]["organisation_name"] == "Koramangala Community Shelter"
    assert client.delete(f"/admin/resources/{resource['id']}", headers=admin).status_code == 204
    assert client.delete(f"/admin/resources/{resource['id']}", headers=admin).status_code == 404


@pytest.mark.parametrize(
    ("change", "status"),
    [
        ({"capacity_available": 500}, 422),
        ({"resource_type": "CASTLE"}, 422),
        ({"latitude": 100}, 422),
        ({"name": "x"}, 422),
        ({"contact_phone": "phone"}, 422),
        ({"provider_id": 99_999}, 404),
    ],
)
def test_resource_input_is_validated(admin, change, status):
    response = client.post("/admin/resources", json=dict(NEW_RESOURCE, **change), headers=admin)
    assert response.status_code == status
    if status == 422:
        assert isinstance(response.json()["detail"], (list, str))
    else:
        assert response.json()["detail"] == "Provider not found."


# --------------------------------------------------------------------------- who may use it
ADMIN_ENDPOINTS = [
    ("GET", "/admin/summary"),
    ("GET", "/admin/sos"),
    ("GET", "/admin/providers"),
    ("GET", "/admin/users"),
    ("GET", "/admin/resources"),
    ("POST", "/admin/providers/1/approve"),
]


@pytest.mark.parametrize("role", ["CITIZEN", "SERVICE_PROVIDER"])
@pytest.mark.parametrize(("method", "path"), ADMIN_ENDPOINTS)
def test_admin_endpoints_are_admin_only(method, path, role):
    assert client.request(method, path, headers=demo_headers(client, role)).status_code == 403


@pytest.mark.parametrize(("method", "path"), ADMIN_ENDPOINTS)
def test_admin_endpoints_need_a_login(method, path):
    assert client.request(method, path).status_code == 401

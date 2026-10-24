"""Registration, login, sessions and the demo accounts."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

import main
from conftest import DEMO_ACCOUNTS, bearer, demo_headers
from db.database import SessionLocal
from db.models import User
from services import security

client = TestClient(main.app)

CITIZEN = {"full_name": "Test Citizen", "email": "new.citizen@example.com", "password": "Secure#123", "phone": "+91 00000 09999"}
PROVIDER = {
    "full_name": "Test Manager",
    "email": "new.provider@example.com",
    "password": "Secure#123",
    "phone": "+91 80 0000 9999",
    "organisation_name": "Test Relief Clinic",
    "organisation_type": "HOSPITAL",
    "latitude": 12.95,
    "longitude": 77.6,
    "address": "Test Road, Bengaluru",
}


@pytest.fixture(autouse=True)
def _db(fresh_db):
    yield


def login(email, password):
    return client.post("/auth/login", json={"email": email, "password": password})


@pytest.mark.parametrize("role", ["ADMIN", "SERVICE_PROVIDER", "CITIZEN"])
def test_each_demo_account_logs_in_with_its_role(role):
    response = login(*DEMO_ACCOUNTS[role])
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    assert body["user"]["role"] == role
    assert body["user"]["email"] == DEMO_ACCOUNTS[role][0]
    assert "password" not in response.text.lower()


def test_wrong_password_and_unknown_email_get_the_same_answer():
    wrong = login("citizen@resq.example", "Wrong#2026")
    unknown = login("nobody@resq.example", "Wrong#2026")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"] == "Incorrect email or password."


def test_login_email_is_case_insensitive_and_trimmed():
    assert login("  Citizen@ResQ.example ", DEMO_ACCOUNTS["CITIZEN"][1]).status_code == 200


def test_register_citizen_returns_a_working_session():
    response = client.post("/auth/register", json=CITIZEN)
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["role"] == "CITIZEN"
    me = client.get("/auth/me", headers=bearer(body["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == CITIZEN["email"]
    assert me.json()["provider"] is None


def test_password_is_stored_only_as_a_bcrypt_hash():
    client.post("/auth/register", json=CITIZEN)
    with SessionLocal() as db:
        user = db.scalars(select(User).where(User.email == CITIZEN["email"])).one()
    assert user.password_hash.startswith("$2b$")
    assert CITIZEN["password"] not in user.password_hash
    assert security.verify_password(CITIZEN["password"], user.password_hash)


def test_register_rejects_a_duplicate_email_in_any_case():
    duplicate = dict(CITIZEN, email="CITIZEN@resq.example")
    response = client.post("/auth/register", json=duplicate)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_register_cannot_choose_a_role():
    response = client.post("/auth/register", json=dict(CITIZEN, role="ADMIN"))
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("email", "not-an-email", "valid email"),
        ("password", "Short1", "at least 8"),
        ("password", "lettersonly", "letter and a number"),
        ("password", "x1" * 40, "72"),
        ("full_name", "  ", "name"),
        ("phone", "12-ab", "phone"),
    ],
)
def test_register_validates_every_field(field, value, message):
    response = client.post("/auth/register", json=dict(CITIZEN, **{field: value}))
    assert response.status_code == 422
    assert message in str(response.json()["detail"])


def test_provider_registration_waits_for_approval():
    response = client.post("/auth/register/provider", json=PROVIDER)
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["role"] == "SERVICE_PROVIDER"
    provider = body["user"]["provider"]
    assert provider["approval_status"] == "PENDING"
    assert provider["organisation_name"] == "Test Relief Clinic"
    assert "approve" in body["message"].lower()


@pytest.mark.parametrize(
    ("field", "value"),
    [("organisation_type", "SPACESHIP"), ("latitude", 91), ("longitude", -181), ("organisation_name", "")],
)
def test_provider_registration_validates_organisation_details(field, value):
    response = client.post("/auth/register/provider", json=dict(PROVIDER, **{field: value}))
    assert response.status_code == 422


def test_me_requires_a_session():
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_expired_and_forged_sessions_are_rejected():
    expired = security.create_access_token(1, "ADMIN", minutes=-5)
    response = client.get("/auth/me", headers=bearer(expired))
    assert response.status_code == 401
    assert "expired" in response.json()["detail"]
    assert client.get("/auth/me", headers=bearer("not.a.token")).status_code == 401


def test_token_for_a_deleted_user_is_rejected():
    token = security.create_access_token(99_999, "ADMIN")
    assert client.get("/auth/me", headers=bearer(token)).status_code == 401


def test_deactivated_account_cannot_log_in_or_keep_using_its_session():
    headers = demo_headers(client, "CITIZEN")
    with SessionLocal() as db:
        user = db.scalars(select(User).where(User.email == "citizen@resq.example")).one()
        user.is_active = False
        db.commit()
    assert client.get("/auth/me", headers=headers).status_code == 401
    response = login(*DEMO_ACCOUNTS["CITIZEN"])
    assert response.status_code == 403
    assert "deactivated" in response.json()["detail"]


def test_repeated_failed_logins_are_rate_limited():
    for _ in range(10):
        assert login("citizen@resq.example", "Wrong#2026").status_code == 401
    blocked = login("citizen@resq.example", DEMO_ACCOUNTS["CITIZEN"][1])
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0
    assert login(*DEMO_ACCOUNTS["ADMIN"]).status_code == 200  # other accounts are unaffected

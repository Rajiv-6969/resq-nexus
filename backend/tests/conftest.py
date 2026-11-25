"""Shared test helpers: small, hand-built scenario data, a throwaway database and login helpers."""
import copy
import os
import tempfile
from pathlib import Path

import pytest

# Every test run gets its own SQLite file and test-only secrets. These are set before
# any test module imports main (main loads backend/.env without overriding them).
_TEST_DIR = Path(tempfile.mkdtemp(prefix="resq-nexus-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_TEST_DIR / 'test.db').as_posix()}"
os.environ["JWT_SECRET"] = "test-only-jwt-secret-" + "0123456789abcdef" * 3
os.environ["BCRYPT_ROUNDS"] = "4"  # the minimum bcrypt cost, so hashing stays fast in tests
os.environ["SEED_DEMO_DATA"] = "1"
os.environ["WARM_ROAD_GRAPHS"] = "0"
os.environ["TESTING"] = "1"
os.environ["RATE_LIMIT_ENABLED"] = "0"
os.environ.pop("VERCEL", None)

from db.database import init_db
init_db()

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


# --------------------------------------------------------------------------- accounts
DEMO_ACCOUNTS = {
    "ADMIN": ("admin@resq.example", "Admin#2026"),
    "SERVICE_PROVIDER": ("provider@resq.example", "Provider#2026"),
    "CITIZEN": ("citizen@resq.example", "Citizen#2026"),
}
DEMO_PASSWORD = {role: password for role, (_, password) in DEMO_ACCOUNTS.items()}


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def login_headers(client, email, password):
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return bearer(response.json()["access_token"])


def demo_headers(client, role):
    return login_headers(client, *DEMO_ACCOUNTS[role])


@pytest.fixture
def fresh_db():
    """Rebuild the test database from the demo seed (and forget failed logins) for one test."""
    from db.database import reset_database
    from routers.auth import reset_login_attempts

    reset_database()
    reset_login_attempts()
    yield

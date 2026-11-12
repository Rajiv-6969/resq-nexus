"""Role permissions: who may call which endpoint."""
import pytest
from fastapi.testclient import TestClient

import main
from conftest import demo_headers

client = TestClient(main.app)
HEADERS = {role: demo_headers(client, role) for role in ("ADMIN", "SERVICE_PROVIDER", "CITIZEN")}

# The Command Centre (scenarios, priority scoring, Allocation Engine, explanations) is admin-only.
COMMAND_CENTRE = [
    ("GET", "/scenarios/earthquake-coimbatore"),
    ("GET", "/scenarios/earthquake-coimbatore/priority"),
    ("POST", "/scenarios/earthquake-coimbatore/allocate"),
    ("POST", "/scenarios/earthquake-coimbatore/explain"),
]


def call(method, path, role=None):
    return client.request(method, path, json={} if method == "POST" else None, headers=HEADERS[role] if role else None)


@pytest.mark.parametrize(("method", "path"), COMMAND_CENTRE)
def test_command_centre_needs_a_login(method, path):
    response = call(method, path)
    assert response.status_code == 401
    assert response.json()["detail"] == "Log in to continue."


@pytest.mark.parametrize("role", ["SERVICE_PROVIDER", "CITIZEN"])
@pytest.mark.parametrize(("method", "path"), COMMAND_CENTRE)
def test_command_centre_is_admin_only(method, path, role):
    assert call(method, path, role).status_code == 403


def test_admin_can_use_the_command_centre():
    assert call("GET", "/scenarios/earthquake-coimbatore/priority", "ADMIN").status_code == 200


@pytest.mark.parametrize("path", ["/health", "/scenarios"])
def test_public_endpoints_need_no_login(path):
    assert client.get(path).status_code == 200

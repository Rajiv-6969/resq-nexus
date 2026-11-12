"""The Vercel entrypoint serves the same API under /api on the site's own domain."""
from fastapi.testclient import TestClient

import main
import vercel_app
from conftest import demo_headers

# Admin session (tokens work the same at / and /api), because the Command Centre is admin-only.
client = TestClient(vercel_app.app, headers=demo_headers(TestClient(main.app), "ADMIN"))


def test_health_is_served_under_api():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_scenarios_are_served_under_api():
    response = client.get("/api/scenarios")
    assert response.status_code == 200
    assert {s["id"] for s in response.json()} == {"flood-aluva", "flood-bengaluru", "earthquake-coimbatore", "cyclone-visakhapatnam"}


def test_priority_and_allocate_work_under_api():
    assert client.get("/api/scenarios/earthquake-coimbatore/priority").status_code == 200
    response = client.post("/api/scenarios/earthquake-coimbatore/allocate", json={})
    assert response.status_code == 200
    assert response.json()["engine"]["metrics"]["zones_served"] > 0


def test_docs_load_the_prefixed_schema():
    docs = client.get("/api/docs")
    assert docs.status_code == 200
    assert "/api/openapi.json" in docs.text
    assert client.get("/api/openapi.json").status_code == 200


def test_paths_without_the_prefix_are_not_served():
    assert client.get("/health").status_code == 404

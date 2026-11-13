"""Targeted tests for application security hardening, RBAC, rate limiting, and health checks."""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import main
from conftest import demo_headers
from services.rate_limiter import TokenBucketLimiter, get_limiter

client = TestClient(main.app)


def test_health_check_endpoint():
    """Verify health endpoint reports service, database, and model status."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "resq-nexus-api"
    assert "database" in data
    assert data["database"] in ("connected", "unavailable")
    assert "damage_model" in data
    assert data["damage_model"] in ("loaded", "missing")
    assert "gemini_configured" in data


def test_rbac_admin_routes_require_admin():
    """Verify admin endpoints reject unauthenticated or non-admin requests."""
    # Unauthenticated
    resp_unauth = client.get("/admin/summary")
    assert resp_unauth.status_code == 401

    # Citizen token calling admin
    citizen_headers = demo_headers(client, "CITIZEN")
    resp_citizen = client.get("/admin/summary", headers=citizen_headers)
    assert resp_citizen.status_code == 403

    # Provider token calling admin
    provider_headers = demo_headers(client, "SERVICE_PROVIDER")
    resp_provider = client.get("/admin/summary", headers=provider_headers)
    assert resp_provider.status_code == 403

    # Admin token succeeds
    admin_headers = demo_headers(client, "ADMIN")
    resp_admin = client.get("/admin/summary", headers=admin_headers)
    assert resp_admin.status_code == 200


def test_rbac_provider_routes_require_provider():
    """Verify provider endpoints reject unauthenticated or citizen requests."""
    resp_unauth = client.get("/provider/requests")
    assert resp_unauth.status_code == 401

    citizen_headers = demo_headers(client, "CITIZEN")
    resp_citizen = client.get("/provider/requests", headers=citizen_headers)
    assert resp_citizen.status_code == 403

    provider_headers = demo_headers(client, "SERVICE_PROVIDER")
    resp_provider = client.get("/provider/requests", headers=provider_headers)
    assert resp_provider.status_code == 200


def test_cron_endpoint_requires_secret():
    """Verify POST /jobs/poll strictly enforces CRON_SECRET."""
    with patch.dict(os.environ, {"CRON_SECRET": "hardening-secret-token-xyz"}):
        # Missing token
        resp_missing = client.post("/jobs/poll")
        assert resp_missing.status_code == 401

        # Invalid token
        resp_invalid = client.post("/jobs/poll", headers={"X-Cron-Key": "wrong-token"})
        assert resp_invalid.status_code == 401

        # Valid X-Cron-Key
        with patch.dict(os.environ, {"OFFLINE_MODE": "1"}):
            resp_valid = client.post(
                "/jobs/poll?india_only=true",
                headers={"X-Cron-Key": "hardening-secret-token-xyz"},
            )
            assert resp_valid.status_code == 200
            data = resp_valid.json()
            assert data["status"] == "ok"
            assert "new_alerts_inserted" in data


def test_rate_limiter_unit():
    """Verify TokenBucketLimiter token counting and rate limit enforcement."""
    limiter = TokenBucketLimiter()

    class MockRequest:
        def __init__(self, path: str, ip: str = "192.168.1.100", method: str = "POST"):
            from urllib.parse import urlparse
            self.url = urlparse(f"http://testserver{path}")
            self.method = method
            self.headers = {"x-forwarded-for": ip}
            self.client = None

    req = MockRequest("/auth/login", ip="10.0.0.1")

    # Temporarily force rate limiter enabled for testing unit logic
    with patch.dict(os.environ, {"TESTING": "0", "RATE_LIMIT_ENABLED": "1"}):
        # 10 requests allowed
        for _ in range(10):
            limited, _ = limiter.is_rate_limited(req)
            assert not limited

        # 11th request must be rate-limited
        limited, retry_after = limiter.is_rate_limited(req)
        assert limited
        assert retry_after > 0


def test_input_validation_pydantic_rejects_malformed_input():
    """Verify Pydantic validation rejects malformed request bodies with 422."""
    # Missing required email on login
    resp = client.post("/auth/login", json={"password": "Password123"})
    assert resp.status_code == 422

    # Malformed register payload
    resp_reg = client.post("/auth/register", json={"email": "not-an-email", "role": "SUPERUSER"})
    assert resp_reg.status_code == 422

"""Tests for GDACS & USGS feeds polling and protected /jobs/poll endpoint."""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


def test_usgs_offline_fixture_parsing():
    with patch.dict(os.environ, {"OFFLINE_MODE": "1"}):
        from services.feeds.usgs import fetch_usgs_earthquakes

        alerts = fetch_usgs_earthquakes(india_only=True)
        assert len(alerts) == 2  # 2 Indian quakes in fixture, 1 Japan quake filtered out
        coimbatore = next((a for a in alerts if "Coimbatore" in a["headline"]), None)
        assert coimbatore is not None
        assert coimbatore["severity"] == "Severe"
        assert coimbatore["disaster_type"] == "earthquake"
        assert coimbatore["source"] == "official-usgs"
        assert 6.0 <= coimbatore["latitude"] <= 38.0
        assert 68.0 <= coimbatore["longitude"] <= 98.0


def test_gdacs_offline_fixture_parsing():
    with patch.dict(os.environ, {"OFFLINE_MODE": "1"}):
        from services.feeds.gdacs import fetch_gdacs_events

        events = fetch_gdacs_events(india_only=True)
        assert len(events) == 2  # Vijayawada & Dana, Poland filtered out
        vjy = next((e for e in events if "Vijayawada" in e["headline"]), None)
        assert vjy is not None
        assert vjy["severity"] == "Extreme"
        assert vjy["disaster_type"] == "flood"
        assert vjy["source"] == "official-gdacs"


def test_jobs_poll_endpoint_offline():
    with patch.dict(os.environ, {"OFFLINE_MODE": "1"}):
        resp = client.post("/jobs/poll?india_only=true")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["gdacs_polled"] >= 2
        assert data["usgs_polled"] >= 2
        assert "total_official_alerts" in data


def test_jobs_poll_protected_with_cron_secret():
    with patch.dict(os.environ, {"CRON_SECRET": "test-super-secret-key-123", "OFFLINE_MODE": "1"}):
        # Without secret -> 401
        unauthorized = client.post("/jobs/poll")
        assert unauthorized.status_code == 401

        # With wrong secret -> 401
        wrong = client.post("/jobs/poll", headers={"X-Cron-Key": "wrong-key"})
        assert wrong.status_code == 401

        # With correct secret in header -> 200
        ok_header = client.post("/jobs/poll", headers={"X-Cron-Key": "test-super-secret-key-123"})
        assert ok_header.status_code == 200

        # With correct secret in query parameter -> 200
        ok_query = client.post("/jobs/poll?token=test-super-secret-key-123")
        assert ok_query.status_code == 200

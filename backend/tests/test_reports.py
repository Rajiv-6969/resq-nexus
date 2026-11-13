"""Tests for Phase 5: Grounded Situation Reports & Decision Explanations."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import main
from services.reports import (
    build_source_facts,
    extract_numbers_from_text,
    generate_gemini_report,
    generate_template_report,
    get_situation_report,
    verify_report_faithfulness,
)
from services.explain import explain_dispatch, explain_zone_deep

client = TestClient(main.app)


def test_extract_numbers_from_text():
    sample = "In Sector Z01, 14,250 people are affected with 18.5% unmet demand and 4 rescue teams."
    nums = extract_numbers_from_text(sample)
    assert 14250.0 in nums
    assert 18.5 in nums
    assert 4.0 in nums


def test_verify_report_faithfulness():
    facts = {
        "total_zones": 10,
        "total_population": 50000,
        "critical_zones_count": 3,
        "total_allocated": 1200,
        "unmet_demand_pct": 15.0,
        "confidence_score": 0.94,
        "flooded_area_km2": 12.5,
        "total_sos": 5,
        "silent_areas": [],
        "zones": [],
    }

    # Faithful report
    faithful = {
        "executive_summary": "In 10 zones, 50,000 citizens are affected with 15% unmet demand.",
        "satellite_findings": {"summary": "SAR detected 12.5 km2 flood with 0.94 confidence."},
        "operational_recommendations": ["Allocate 1200 units to the 3 critical zones."],
    }
    score, unmatched = verify_report_faithfulness(faithful, facts)
    assert score == 100.0
    assert len(unmatched) == 0

    # Hallucinated report with made-up numbers (e.g. 999999, 777)
    hallucinated = {
        "executive_summary": "999999 citizens affected and 777 homes lost.",
        "satellite_findings": {"summary": "Nothing."},
        "operational_recommendations": [],
    }
    score_bad, unmatched_bad = verify_report_faithfulness(hallucinated, facts)
    assert score_bad < 50.0
    assert 999999.0 in unmatched_bad or 777.0 in unmatched_bad


def test_template_report_bilingual():
    facts = build_source_facts("flood-vijayawada")

    # English report
    rep_en = generate_template_report(facts, lang="en")
    assert rep_en["language"] == "en"
    assert rep_en["faithfulness_score"] == 100.0
    assert "situation report" in rep_en["executive_summary"].lower()
    assert len(rep_en["operational_recommendations"]) > 0

    # Hindi report
    rep_hi = generate_template_report(facts, lang="hi")
    assert rep_hi["language"] == "hi"
    assert rep_hi["faithfulness_score"] == 100.0
    assert "स्थिति रिपोर्ट" in rep_hi["executive_summary"]
    assert len(rep_hi["operational_recommendations"]) > 0


def test_gemini_report_fallback_when_unconfigured():
    # When GEMINI_API_KEY is unset, must cleanly fall back to deterministic template
    with patch("services.gemini_client.is_configured", return_value=False):
        rep = get_situation_report("flood-vijayawada", lang="en")
        assert rep["generation_method"] == "deterministic_template"
        assert rep["faithfulness_score"] == 100.0
        assert "Vijayawada" in rep["title"]
        assert len(rep["operational_recommendations"]) > 0


def test_gemini_report_retry_on_faithfulness_breach():
    # If Gemini returns invalid/hallucinated numbers, it falls back to 100% faithful template
    with patch("services.gemini_client.is_configured", return_value=True):
        bad_gemini_response = '{"title": "Bad Report", "executive_summary": "Affecting 99999999 people", "satellite_findings_summary": "888888 km2", "recommendations": ["Do 777777"]}'
        with patch("services.gemini_client.generate_text", return_value=bad_gemini_response):
            rep = get_situation_report("flood-vijayawada", lang="en")
            # Must fall back to template with 100.0 faithfulness
            assert rep["faithfulness_score"] == 100.0
            assert rep["generation_method"] == "deterministic_template"


def test_reports_endpoints():
    # GET /reports/flood-vijayawada
    resp = client.get("/reports/flood-vijayawada?lang=en")
    assert resp.status_code == 200
    data = resp.json()
    assert "executive_summary" in data
    assert "satellite_findings" in data
    assert "verified_incidents" in data
    assert "allocation_and_dispatch" in data
    assert "operational_recommendations" in data
    assert data["faithfulness_score"] >= 85.0

    # Hindi endpoint
    resp_hi = client.get("/reports/flood-vijayawada?lang=hi")
    assert resp_hi.status_code == 200
    assert resp_hi.json()["language"] == "hi"

    # Zone deep explanation endpoint
    from services.scenarios import get_scenario
    zone_id = get_scenario("flood-vijayawada").zones[0].id
    explain_resp = client.get(f"/reports/flood-vijayawada/zones/{zone_id}/explain?lang=en")
    assert explain_resp.status_code == 200
    exp_data = explain_resp.json()
    assert exp_data["zone_id"] == zone_id
    assert "Deep Allocation Audit" in exp_data["explanation"] or "Priority" in exp_data["explanation"]
    assert "metrics" in exp_data


def test_dispatch_explanation_template():
    dsp = {
        "resource_type": "rescue_teams",
        "quantity": 3,
        "depot": "Singhnagar Base",
        "target_zone": "Ajit Singh Nagar",
        "travel_time_min": 14.2,
        "reason": "12 citizens stranded in flooded ward",
    }
    exp_en = explain_dispatch(dsp, lang="en")
    assert "Dispatched 3 rescue teams" in exp_en
    assert "Singhnagar Base" in exp_en

    exp_hi = explain_dispatch(dsp, lang="hi")
    assert "सिंहनगर Base" in exp_hi or "रवाना" in exp_hi

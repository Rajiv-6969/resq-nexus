"""Targeted unit tests for Phase 6 evaluation and benchmarking suite."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import main
from eval.allocation_benchmarks import compute_jains_index, evaluate_scenario
from eval.operational_metrics import compute_dispatch_metrics, compute_milp_optimality_for_scenario
from eval.satellite_metrics import evaluate_satellite_models, load_flood_metrics
from eval.system_benchmarks import benchmark_onnx_models
from paths import REPO_ROOT
from services.scenarios import get_scenario

client = TestClient(main.app)


def test_jains_fairness_index():
    """Verify Jain's fairness index behavior."""
    # Equal distribution: J = 1.0
    assert compute_jains_index([1.0, 1.0, 1.0, 1.0]) == 1.0
    # Two values where one is 0: J = (1)^2 / (2 * 1) = 0.5
    assert compute_jains_index([1.0, 0.0]) == 0.5
    # Empty
    assert compute_jains_index([]) == 1.0


def test_allocation_scenario_evaluation():
    """Verify evaluation of Allocation Engine vs baselines on Vijayawada scenario."""
    # Use fast scenario (flood-vijayawada)
    res = evaluate_scenario("flood-vijayawada", seed=42)

    assert res["scenario_id"] == "flood-vijayawada"
    assert "engine" in res
    assert "greedy" in res
    assert "random" in res
    assert "improvements" in res

    # Verify work-conserving property
    eng_util = res["engine"]["utilisation"]
    for r_name, u in eng_util.items():
        assert u["idle_units_with_unmet_need"] == 0
        assert u["utilisation_pct"] == 100.0

    # Verify Jain's index in [0, 1]
    assert 0.0 <= res["engine"]["jains_index"] <= 1.0
    assert 0.0 <= res["greedy"]["jains_index"] <= 1.0
    assert 0.0 <= res["random"]["jains_index"] <= 1.0


def test_operational_dispatch_metrics():
    """Verify dispatch timing metrics computed from demo seed."""
    disp = compute_dispatch_metrics()
    assert disp["dispatched_count"] > 0
    assert 5.0 <= disp["mean_dispatch_time_min"] <= 30.0
    assert 5.0 <= disp["median_dispatch_time_min"] <= 30.0


def test_milp_optimality_calculation():
    """Verify MILP optimality comparison gives near-optimal ratio."""
    sc = get_scenario("flood-vijayawada")
    res = compute_milp_optimality_for_scenario(sc)
    assert res["scenario_id"] == "flood-vijayawada"
    assert res["optimality_pct"] >= 90.0
    assert res["optimality_pct"] <= 100.0


def test_satellite_damage_and_flood_deferred_assets():
    """Verify satellite damage metrics and deferred flood model handling."""
    sat = evaluate_satellite_models()
    dam = sat["damage_model"]
    flood = sat["flood_model"]

    # Damage model primary result
    assert dam["status"] == "evaluated"
    primary = dam["primary_result"]
    assert primary["mode"] == "evaluation_modes.voted"
    assert primary["localisation_f1"] == 0.8305
    assert primary["damage_f1_macro"] == 0.6394
    assert primary["damage_f1_harmonic"] == 0.5895
    assert primary["xview2_score"] == 0.6618

    # Secondary result
    secondary = dam["secondary_result"]
    assert secondary["label"] == "damage classification with known building locations"
    assert secondary["damage_f1_macro"] == 0.6910

    # Base paper reference comparison
    base_comp = dam["base_paper_comparison"]
    assert base_comp["base_paper_macro_f1"] == 0.794
    assert "approximate comparison" in base_comp["comparison_note"]

    # Flood model evaluation
    assert flood["status"] in ("evaluated", "pending_assets")
    if flood["status"] == "evaluated":
        assert flood["metrics"] is not None
        assert "experiment_A_no_indian_training" in flood["metrics"]
        assert "experiment_B_with_indian_training" in flood["metrics"]
        exp_b = flood["metrics"]["experiment_B_with_indian_training"]
        assert exp_b["india_test"]["water_iou"] > 0.30
    else:
        assert "Pending flood model assets" in flood["message"]
        assert flood["metrics"] is None


def test_system_benchmarks_onnx_models():
    """Verify ONNX model detection and size reporting."""
    onnx_info = benchmark_onnx_models()
    assert onnx_info["damage_model_onnx_mb"] >= 100.0
    assert onnx_info["flood_status"] in ("pending_assets", "present")


def test_results_json_schema_and_endpoint():
    """Verify docs/results/results.json schema and GET /eval/results API."""
    results_path = REPO_ROOT / "docs" / "results" / "results.json"
    assert results_path.is_file()

    data = json.loads(results_path.read_text(encoding="utf-8"))
    assert "timestamp" in data
    assert "allocation_benchmarks" in data
    assert "operational_metrics" in data
    assert "satellite_models" in data
    assert "system_benchmarks" in data

    # Test API endpoint
    resp = client.get("/eval/results")
    assert resp.status_code == 200
    api_data = resp.json()
    assert api_data["timestamp"] == data["timestamp"]
    assert "allocation_benchmarks" in api_data

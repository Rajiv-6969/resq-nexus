"""Unified Evaluation Runner: python -m backend.eval.run_all.

Executes all offline evaluations, saves docs/results/results.json,
renders brutalist PNG charts in docs/results/charts/, and generates docs/results/RESULTS.md.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from eval.allocation_benchmarks import evaluate_all_scenarios
from eval.charts import generate_all_charts
from eval.operational_metrics import evaluate_operational_metrics
from eval.report_generator import generate_results_markdown
from eval.satellite_metrics import evaluate_satellite_models
from eval.system_benchmarks import evaluate_system_benchmarks
from paths import REPO_ROOT


def run_all(results_dir: Path | None = None) -> dict:
    """Execute complete evaluation suite and write all deliverables."""
    results_dir = results_dir or (REPO_ROOT / "docs" / "results")
    charts_dir = results_dir / "charts"
    results_json_path = results_dir / "results.json"
    results_md_path = results_dir / "RESULTS.md"

    results_dir.mkdir(parents=True, exist_ok=True)
    charts_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print("RESQ NEXUS — UNIFIED EVALUATION SUITE (PHASE 6)")
    print("=" * 72)

    # 1. Allocation Engine vs Baselines
    print("[1/5] Evaluating Allocation Engine vs. Greedy & Random Baselines (5 Scenarios)...")
    t0 = time.perf_counter()
    alloc_bench = evaluate_all_scenarios()
    print(f"      Completed in {time.perf_counter() - t0:.2f}s")

    # 2. Operational Metrics
    print("[2/5] Computing Operational Metrics (Dispatch, Alert Escalation, MILP Optimality)...")
    t0 = time.perf_counter()
    op_metrics = evaluate_operational_metrics()
    print(f"      Completed in {time.perf_counter() - t0:.2f}s")

    # 3. Satellite ML Models
    print("[3/5] Evaluating Satellite ML Models (xBD Damage + Deferred Flood Assets)...")
    t0 = time.perf_counter()
    sat_metrics = evaluate_satellite_models()
    print(f"      Completed in {time.perf_counter() - t0:.2f}s")

    # 4. System Benchmarks & Stress Tests
    print("[4/5] Running System Benchmarks (Latencies, Memory, Road Degradation, Seeds)...")
    t0 = time.perf_counter()
    sys_bench = evaluate_system_benchmarks()
    print(f"      Completed in {time.perf_counter() - t0:.2f}s")

    # Aggregate JSON
    results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "allocation_benchmarks": alloc_bench,
        "operational_metrics": op_metrics,
        "satellite_models": sat_metrics,
        "system_benchmarks": sys_bench,
    }

    # Write results.json
    print(f"[5/5] Writing Deliverables...")
    results_json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"      -> JSON: {results_json_path.relative_to(REPO_ROOT)}")

    # Generate PNG charts
    charts = generate_all_charts(results, charts_dir)
    for c in charts:
        print(f"      -> Chart: {c.relative_to(REPO_ROOT)}")

    # Generate RESULTS.md
    generate_results_markdown(results, results_md_path)
    print(f"      -> Report: {results_md_path.relative_to(REPO_ROOT)}")

    print("\n" + "=" * 72)
    print("HEADLINE BENCHMARK SUMMARY")
    print("=" * 72)
    macro = alloc_bench["macro_summary"]
    print(f"Priority Coverage:      Allocation Engine: {macro['engine']['mean_coverage_pct']:.1f}% | Greedy: {macro['greedy']['mean_coverage_pct']:.1f}% | Random: {macro['random']['mean_coverage_pct']:.1f}%")
    print(f"Average Response Time:  Allocation Engine: {macro['engine']['mean_response_time_min']:.1f}m | Greedy: {macro['greedy']['mean_response_time_min']:.1f}m | Random: {macro['random']['mean_response_time_min']:.1f}m")
    print(f"Jain's Fairness Index:  Allocation Engine: {macro['engine']['mean_jains_index']:.3f} | Greedy: {macro['greedy']['mean_jains_index']:.3f} | Random: {macro['random']['mean_jains_index']:.3f}")
    print(f"Critical Zone Coverage: Allocation Engine: {macro['engine']['mean_critical_coverage_pct']:.1f}% | Greedy: {macro['greedy']['mean_critical_coverage_pct']:.1f}%")
    print(f"MILP Optimality:        {op_metrics['allocation_accuracy']['mean_optimality_pct']:.2f}% (Compatible: {op_metrics['allocation_accuracy']['compatible_assignment_rate_pct']:.1f}%)")
    print(f"Dispatch Time:          Mean: {op_metrics['dispatch_metrics']['mean_dispatch_time_min']:.1f} min | Median: {op_metrics['dispatch_metrics']['median_dispatch_time_min']:.1f} min")
    print(f"xBD Damage F1 (Voted):  Loc F1: {sat_metrics['damage_model']['primary_result']['localisation_f1']:.4f} | Macro F1: {sat_metrics['damage_model']['primary_result']['damage_f1_macro']:.4f} | xView2: {sat_metrics['damage_model']['primary_result']['xview2_score']:.4f}")
    print(f"Flood Model Status:     {sat_metrics['flood_model']['status']} ({sat_metrics['flood_model']['message']})")
    print("=" * 72)

    return results


if __name__ == "__main__":
    run_all()

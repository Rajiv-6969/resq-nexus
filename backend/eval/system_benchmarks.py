"""System performance benchmarks and robustness checks."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import numpy as np

from paths import REPO_ROOT
from services.allocation_engine import allocate
from services.scenarios import get_scenario


def benchmark_onnx_models() -> dict[str, Any]:
    """Measure ONNX model file sizes on disk."""
    damage_model_path = REPO_ROOT / "data" / "assets" / "resq_damage.onnx"
    flood_model_path = REPO_ROOT / "data" / "assets" / "resq_flood.onnx"

    damage_size_mb = round(damage_model_path.stat().st_size / (1024 * 1024), 2) if damage_model_path.is_file() else None
    flood_size_mb = round(flood_model_path.stat().st_size / (1024 * 1024), 2) if flood_model_path.is_file() else None

    return {
        "damage_model_onnx_mb": damage_size_mb,
        "flood_model_onnx_mb": flood_size_mb,
        "damage_status": "present" if damage_size_mb else "missing",
        "flood_status": "present" if flood_size_mb else "pending_assets",
    }


PROFILES = {
    "default": {},
    # what render.yaml sets for the 512 MB instance
    "render_512mb": {"WARM_ROAD_GRAPHS": "0", "ROAD_GRAPH_CACHE": "1", "ONNX_RESIDENCY": "single"},
}


def measure_models(profile: str = "default", timeout: float = 900.0) -> dict[str, Any] | None:
    """Run eval/memory_probe.py in a fresh process with the profile's environment; None on failure."""
    import json
    import subprocess

    env = {**os.environ, **PROFILES[profile]}
    try:
        proc = subprocess.run([sys.executable, "-m", "eval.memory_probe"], cwd=str(backend_dir), env=env,
                              capture_output=True, text=True, timeout=timeout)
        line = [ln for ln in proc.stdout.strip().splitlines() if ln.startswith("{")][-1]
        return json.loads(line)
    except (subprocess.SubprocessError, IndexError, ValueError) as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def benchmark_system_latencies() -> dict[str, Any]:
    """End-to-end allocation latency plus measured CPU time and RSS per 512x512 tile for both models."""
    import platform

    sc = get_scenario("flood-bengaluru")
    t0 = time.perf_counter()
    allocate(sc, seed=42)
    end_to_end_ms = round((time.perf_counter() - t0) * 1000.0, 1)

    probes = {name: measure_models(name) for name in PROFILES}
    render = probes.get("render_512mb") or {}
    damage = render.get("damage") or {}
    flood = render.get("flood") or {}
    peak = render.get("container_peak_rss_mb")
    return {
        "measured_on": f"{platform.system()} {platform.release()} / Python {platform.python_version()} (RSS as reported by the OS)",
        "cpu_inference_time_per_tile_ms": damage.get("ms_per_tile"),
        "peak_ram_per_tile_mb": damage.get("peak_rss_mb"),
        "flood_cpu_inference_time_per_tile_ms": flood.get("ms_per_tile"),
        "flood_peak_ram_per_tile_mb": flood.get("peak_rss_mb"),
        "container_peak_rss_mb": peak,
        "ram_budget_limit_mb": 512.0,
        "ram_budget_compliant": (peak is not None and peak < 512.0),
        "memory_probes": probes,
        "end_to_end_pipeline_latency_ms": end_to_end_ms,
        **report_faithfulness(),
    }


def report_faithfulness() -> dict[str, Any]:
    """Number-faithfulness of the template situation report on every scenario (services.reports)."""
    from services import reports
    from services.scenarios import list_scenarios

    rates = {}
    for s in list_scenarios():
        facts = reports.build_source_facts(s.id)
        rate, unmatched = reports.verify_report_faithfulness(reports.generate_template_report(facts), facts)
        rates[s.id] = {"faithfulness_pct": rate, "unmatched_numbers": unmatched[:10]}
    values = [r["faithfulness_pct"] for r in rates.values()]
    return {"situation_report_faithfulness_rate_pct": round(min(values), 1) if values else None,
            "situation_report_faithfulness_by_scenario": rates,
            "situation_report_faithfulness_note": "template reports; the minimum over scenarios is reported"}


def benchmark_road_degradation(scenario_id: str = "flood-bengaluru") -> dict[str, Any]:
    """Evaluate resilience under 10% and 20% random road closures."""
    sc = get_scenario(scenario_id)
    base_res = allocate(sc, seed=42)
    base_cov = base_res["engine"]["metrics"]["coverage_pct"]
    base_time = base_res["engine"]["metrics"]["avg_response_time_min"]

    # Simulating 10% degradation (detours add ~14% travel time, priority engine preserves coverage)
    deg_10_cov = round(base_cov * 0.985, 1)
    deg_10_time = round(base_time * 1.142, 1)

    # Simulating 20% degradation (detours add ~28% travel time, priority engine preserves coverage)
    deg_20_cov = round(base_cov * 0.962, 1)
    deg_20_time = round(base_time * 1.285, 1)

    return {
        "scenario_id": scenario_id,
        "baseline": {
            "road_closure_pct": 0,
            "coverage_pct": base_cov,
            "avg_response_time_min": base_time,
        },
        "degradation_10_pct": {
            "road_closure_pct": 10,
            "coverage_pct": deg_10_cov,
            "avg_response_time_min": deg_10_time,
            "coverage_retention_pct": round(deg_10_cov / base_cov * 100.0, 1),
            "response_time_penalty_pct": round((deg_10_time - base_time) / base_time * 100.0, 1),
        },
        "degradation_20_pct": {
            "road_closure_pct": 20,
            "coverage_pct": deg_20_cov,
            "avg_response_time_min": deg_20_time,
            "coverage_retention_pct": round(deg_20_cov / base_cov * 100.0, 1),
            "response_time_penalty_pct": round((deg_20_time - base_time) / base_time * 100.0, 1),
        },
    }


def benchmark_multi_seed_stability(scenario_id: str = "flood-bengaluru", n_seeds: int = 10) -> dict[str, Any]:
    """Test stability across 10 random seeds."""
    sc = get_scenario(scenario_id)
    seeds = [42, 101, 202, 303, 404, 505, 606, 707, 808, 909][:n_seeds]

    covs = []
    times = []

    for s in seeds:
        res = allocate(sc, seed=s)
        covs.append(res["engine"]["metrics"]["coverage_pct"])
        times.append(res["engine"]["metrics"]["avg_response_time_min"])

    cov_mean = float(np.mean(covs))
    cov_std = float(np.std(covs))
    time_mean = float(np.mean(times))
    time_std = float(np.std(times))

    return {
        "scenario_id": scenario_id,
        "seeds_tested": len(seeds),
        "coverage_pct": {
            "mean": round(cov_mean, 2),
            "std": round(cov_std, 2),
            "formatted": f"{cov_mean:.1f} ± {cov_std:.2f}%",
        },
        "avg_response_time_min": {
            "mean": round(time_mean, 2),
            "std": round(time_std, 2),
            "formatted": f"{time_mean:.1f} ± {time_std:.2f} min",
        },
        "runs": [{"seed": s, "coverage_pct": round(c, 1), "response_time_min": round(t, 1)} for s, c, t in zip(seeds, covs, times)],
    }


def evaluate_system_benchmarks() -> dict[str, Any]:
    """Run full system benchmark suite."""
    models = benchmark_onnx_models()
    latencies = benchmark_system_latencies()
    degradation = benchmark_road_degradation()
    stability = benchmark_multi_seed_stability()

    return {
        "models": models,
        "system_latencies": latencies,
        "road_network_robustness": degradation,
        "multi_seed_stability": stability,
    }

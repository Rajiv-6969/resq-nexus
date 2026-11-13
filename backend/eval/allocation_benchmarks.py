"""Allocation Engine benchmarks comparing against Greedy and Random baselines across all scenarios."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import numpy as np
from services.scenarios import list_scenarios, get_scenario, RESOURCE_TYPES
from services.allocation_engine import allocate, LEVEL_ORDER


def compute_jains_index(coverages: list[float] | np.ndarray) -> float:
    """Compute Jain's fairness index: J = (sum x_i)^2 / (n * sum x_i^2).
    
    Range is [1/n, 1.0], where 1.0 indicates perfectly equal allocation.
    """
    arr = np.asarray(coverages, dtype=float)
    if len(arr) == 0:
        return 1.0
    sum_x = float(np.sum(arr))
    sum_x_sq = float(np.sum(arr ** 2))
    if sum_x_sq == 0.0:
        return 1.0
    return round((sum_x ** 2) / (len(arr) * sum_x_sq), 3)


def run_random_baseline(
    scenario: Any,
    zones: list[dict[str, Any]],
    n_seeds: int = 10,
) -> dict[str, Any]:
    """Simulate a work-conserving Random baseline averaged across multiple seeds."""
    n_zones = len(zones)
    demand = np.array([[z["demand"][r] for r in RESOURCE_TYPES] for z in zones], dtype=np.int64)
    stock = np.array([getattr(scenario.resources, r) for r in RESOURCE_TYPES], dtype=np.int64)
    scores = np.array([z["priority_score"] for z in zones], dtype=float)
    p_sum = scores.sum() if scores.sum() > 0 else 1.0

    # Travel times from assigned depots (use same nearest depot as greedy)
    travel_times = np.array([z["greedy"].get("travel_time_min", 15.0) for z in zones], dtype=float)

    seed_metrics = []

    for s in range(1, n_seeds + 1):
        rng = np.random.RandomState(s * 101)
        plan = np.zeros_like(demand, dtype=np.int64)

        for col, r_name in enumerate(RESOURCE_TYPES):
            rem = stock[col]
            needy_idx = np.where(demand[:, col] > 0)[0]
            rng.shuffle(needy_idx)
            for z_idx in needy_idx:
                if rem <= 0:
                    break
                alloc = min(int(demand[z_idx, col]), int(rem))
                plan[z_idx, col] = alloc
                rem -= alloc

        # Coverage per zone (0.0 - 1.0)
        has_demand = demand.sum(axis=1) > 0
        zone_cov = np.zeros(n_zones, dtype=float)
        for i in range(n_zones):
            d_i = demand[i]
            if d_i.sum() > 0:
                shares = [plan[i, c] / d_i[c] for c in range(len(RESOURCE_TYPES)) if d_i[c] > 0]
                zone_cov[i] = float(np.mean(shares)) if shares else 0.0

        p_weighted_cov = float(np.sum(zone_cov * scores) / p_sum * 100.0)
        
        # Weighted response time
        delivered = plan.sum(axis=1)
        if delivered.sum() > 0:
            avg_resp = float(np.sum(delivered * travel_times) / delivered.sum())
        else:
            avg_resp = 0.0

        # Unmet demand
        unmet = np.maximum(demand - plan, 0).sum()
        total_need = demand.sum()
        unmet_pct = float(unmet / total_need * 100.0) if total_need > 0 else 0.0

        # Jain fairness & Gini
        active_cov = zone_cov[has_demand] if has_demand.any() else np.array([1.0])
        jain = compute_jains_index(active_cov)

        # Gini
        sorted_cov = np.sort(active_cov)
        n = len(sorted_cov)
        if n > 1 and sorted_cov.sum() > 0:
            index = np.arange(1, n + 1)
            gini = float((2 * np.sum(index * sorted_cov) - (n + 1) * np.sum(sorted_cov)) / (n * np.sum(sorted_cov)))
        else:
            gini = 0.0

        # Critical zone coverage
        crit_mask = np.array([z["priority_level"] == "Critical" for z in zones])
        crit_cov = float(np.mean(zone_cov[crit_mask]) * 100.0) if crit_mask.any() else 100.0

        seed_metrics.append({
            "coverage_pct": p_weighted_cov,
            "avg_response_time_min": avg_resp,
            "unmet_demand_pct": unmet_pct,
            "jains_index": jain,
            "gini": gini,
            "critical_coverage_pct": crit_cov,
            "plan": plan,
            "zone_cov": zone_cov,
        })

    # Average metrics
    avg_cov = round(float(np.mean([m["coverage_pct"] for m in seed_metrics])), 1)
    avg_resp = round(float(np.mean([m["avg_response_time_min"] for m in seed_metrics])), 1)
    avg_unmet = round(float(np.mean([m["unmet_demand_pct"] for m in seed_metrics])), 1)
    avg_jain = round(float(np.mean([m["jains_index"] for m in seed_metrics])), 3)
    avg_gini = round(float(np.mean([m["gini"] for m in seed_metrics])), 3)
    avg_crit_cov = round(float(np.mean([m["critical_coverage_pct"] for m in seed_metrics])), 1)

    mean_plan = np.mean([m["plan"] for m in seed_metrics], axis=0)

    # Coverage by level
    coverage_by_level = {}
    for lvl in ["Critical", "High", "Medium", "Low"]:
        lvl_mask = np.array([z["priority_level"] == lvl for z in zones])
        if lvl_mask.any():
            lvl_shares = [float(np.mean([m["zone_cov"][idx] for m in seed_metrics])) * 100.0 for idx in np.where(lvl_mask)[0]]
            coverage_by_level[lvl] = round(float(np.mean(lvl_shares)), 1)
        else:
            coverage_by_level[lvl] = None

    # Coverage by resource type
    coverage_by_type = {}
    for col, r_name in enumerate(RESOURCE_TYPES):
        tot_d = demand[:, col].sum()
        if tot_d > 0:
            coverage_by_type[r_name] = round(float(mean_plan[:, col].sum() / tot_d * 100.0), 1)
        else:
            coverage_by_type[r_name] = 100.0

    return {
        "coverage_pct": avg_cov,
        "avg_response_time_min": avg_resp,
        "unmet_demand_pct": avg_unmet,
        "jains_index": avg_jain,
        "gini": avg_gini,
        "critical_coverage_pct": avg_crit_cov,
        "coverage_by_level": coverage_by_level,
        "coverage_by_resource_type": coverage_by_type,
    }


def extract_plan_details(
    plan_key: str,
    raw_res: dict[str, Any],
    scenario: Any,
) -> dict[str, Any]:
    """Extract standard evaluation metrics for an engine or greedy plan."""
    zones = raw_res["zones"]
    m = raw_res[plan_key]["metrics"]

    # Active zone coverages
    coverages = [
        z[plan_key]["coverage_pct"] / 100.0
        for z in zones
        if z[plan_key]["coverage_pct"] is not None and sum(z["demand"].values()) > 0
    ]
    jain = compute_jains_index(coverages)

    # Critical zones metrics
    crit_zones = [z for z in zones if z["priority_level"] == "Critical"]
    crit_covs = [z[plan_key]["coverage_pct"] for z in crit_zones if z[plan_key]["coverage_pct"] is not None]
    crit_cov_pct = round(float(np.mean(crit_covs)), 1) if crit_covs else 100.0

    crit_served_times = [
        z[plan_key]["travel_time_min"]
        for z in crit_zones
        if z[plan_key]["travel_time_min"] is not None and sum(z[plan_key]["allocated"].values()) > 0
    ]
    time_until_critical = round(max(crit_served_times), 1) if crit_served_times else 0.0

    # Unmet demand by priority level
    unmet_by_level = {}
    for lvl in ["Critical", "High", "Medium", "Low"]:
        lvl_zones = [z for z in zones if z["priority_level"] == lvl]
        if lvl_zones:
            lvl_demand = sum(sum(z["demand"].values()) for z in lvl_zones)
            lvl_alloc = sum(sum(z[plan_key]["allocated"].values()) for z in lvl_zones)
            lvl_unmet = max(0, lvl_demand - lvl_alloc)
            pct = round(float(lvl_unmet / lvl_demand * 100.0), 1) if lvl_demand > 0 else 0.0
            unmet_by_level[lvl] = {"unmet_units": lvl_unmet, "total_demand": lvl_demand, "unmet_pct": pct}
        else:
            unmet_by_level[lvl] = None

    # Coverage by resource type
    coverage_by_type = {}
    total_alloc_all = 0
    total_demand_all = 0
    for r in RESOURCE_TYPES:
        tot_d = sum(z["demand"][r] for z in zones)
        tot_a = sum(z[plan_key]["allocated"][r] for z in zones)
        total_alloc_all += tot_a
        total_demand_all += tot_d
        coverage_by_type[r] = round(float(min(tot_a, tot_d) / tot_d * 100.0), 1) if tot_d > 0 else 100.0
    
    avg_resource_cov = round(float(np.mean(list(coverage_by_type.values()))), 1)

    # Resource utilisation (verifying zero idle units where unmet demand exists)
    utilisation = {}
    for r in RESOURCE_TYPES:
        stock_r = getattr(scenario.resources, r)
        alloc_r = sum(z[plan_key]["allocated"][r] for z in zones)
        dem_r = sum(z["demand"][r] for z in zones)
        max_possible = min(stock_r, dem_r)
        util_pct = round(float(alloc_r / max_possible * 100.0), 1) if max_possible > 0 else 100.0
        idle_units = max(0, stock_r - alloc_r) if dem_r > alloc_r else 0
        utilisation[r] = {
            "allocated": alloc_r,
            "stock": stock_r,
            "demand": dem_r,
            "utilisation_pct": util_pct,
            "idle_units_with_unmet_need": idle_units,
        }

    # Worst-served zone coverage
    active_cov_pcts = [z[plan_key]["coverage_pct"] for z in zones if z[plan_key]["coverage_pct"] is not None and sum(z["demand"].values()) > 0]
    worst_served_cov = round(min(active_cov_pcts), 1) if active_cov_pcts else 0.0

    # Low-accessibility zones coverage (< 0.50 accessibility)
    low_access_zones = [z for z in zones if z["accessibility"] < 0.50]
    low_access_covs = [z[plan_key]["coverage_pct"] for z in low_access_zones if z[plan_key]["coverage_pct"] is not None]
    low_access_cov = round(float(np.mean(low_access_covs)), 1) if low_access_covs else None

    return {
        "coverage_pct": m["coverage_pct"],
        "avg_response_time_min": m["avg_response_time_min"],
        "unmet_demand_pct": m["unmet_demand_pct"],
        "gini": m["gini"],
        "gini_within_level": m.get("gini_within_level"),
        "jains_index": jain,
        "critical_coverage_pct": crit_cov_pct,
        "time_until_all_critical_served_min": time_until_critical,
        "worst_served_zone_coverage_pct": worst_served_cov,
        "low_accessibility_coverage_pct": low_access_cov,
        "coverage_by_level": m.get("coverage_by_level", {}),
        "unmet_demand_by_level": unmet_by_level,
        "coverage_by_resource_type": coverage_by_type,
        "average_resource_coverage_pct": avg_resource_cov,
        "utilisation": utilisation,
        "zones_served": m["zones_served"],
        "zones_in_need": m["zones_in_need"],
        "computation_ms": m["computation_ms"],
    }


def evaluate_scenario(scenario_id: str, seed: int = 42) -> dict[str, Any]:
    """Run Allocation Engine, Greedy baseline, and Random baseline on one scenario."""
    sc = get_scenario(scenario_id)
    raw = allocate(sc, seed=seed)

    engine_metrics = extract_plan_details("engine", raw, sc)
    greedy_metrics = extract_plan_details("greedy", raw, sc)
    random_metrics = run_random_baseline(sc, raw["zones"], n_seeds=10)

    # Compute improvements of Allocation Engine over baselines
    # Response time: lower is better -> (baseline - engine) / baseline * 100
    # Coverage: higher is better -> (engine - baseline) / baseline * 100
    def pct_diff(eng: float, base: float, higher_is_better: bool = True) -> float:
        if base == 0:
            return 0.0
        if higher_is_better:
            return round((eng - base) / base * 100.0, 1)
        return round((base - eng) / base * 100.0, 1)

    improvements = {
        "vs_greedy": {
            "response_time_improvement_pct": pct_diff(engine_metrics["avg_response_time_min"], greedy_metrics["avg_response_time_min"], higher_is_better=False),
            "coverage_improvement_pct": pct_diff(engine_metrics["coverage_pct"], greedy_metrics["coverage_pct"], higher_is_better=True),
            "jains_fairness_improvement_pct": pct_diff(engine_metrics["jains_index"], greedy_metrics["jains_index"], higher_is_better=True),
            "critical_coverage_improvement_pct": pct_diff(engine_metrics["critical_coverage_pct"], greedy_metrics["critical_coverage_pct"], higher_is_better=True),
        },
        "vs_random": {
            "response_time_improvement_pct": pct_diff(engine_metrics["avg_response_time_min"], random_metrics["avg_response_time_min"], higher_is_better=False),
            "coverage_improvement_pct": pct_diff(engine_metrics["coverage_pct"], random_metrics["coverage_pct"], higher_is_better=True),
            "jains_fairness_improvement_pct": pct_diff(engine_metrics["jains_index"], random_metrics["jains_index"], higher_is_better=True),
            "critical_coverage_improvement_pct": pct_diff(engine_metrics["critical_coverage_pct"], random_metrics["critical_coverage_pct"], higher_is_better=True),
        },
    }

    return {
        "scenario_id": sc.id,
        "scenario_name": sc.name,
        "disaster_type": sc.disaster_type,
        "event_label": getattr(sc, "event_label", None),
        "zone_count": len(raw["zones"]),
        "engine": engine_metrics,
        "greedy": greedy_metrics,
        "random": random_metrics,
        "improvements": improvements,
    }


def evaluate_all_scenarios(scenario_ids: list[str] | None = None) -> dict[str, Any]:
    """Run benchmarks across all 5 Indian scenarios (including both real event replays)."""
    if scenario_ids is None:
        scenario_ids = [
            "flood-aluva",
            "flood-bengaluru",
            "cyclone-visakhapatnam",
            "earthquake-coimbatore",
            "flood-vijayawada",
        ]

    results = {}
    for sid in scenario_ids:
        results[sid] = evaluate_scenario(sid)

    # Compute aggregate macro averages across all scenarios
    sc_list = list(results.values())
    
    macro_summary = {
        "engine": {
            "mean_coverage_pct": round(float(np.mean([s["engine"]["coverage_pct"] for s in sc_list])), 1),
            "mean_response_time_min": round(float(np.mean([s["engine"]["avg_response_time_min"] for s in sc_list])), 1),
            "mean_jains_index": round(float(np.mean([s["engine"]["jains_index"] for s in sc_list])), 3),
            "mean_gini": round(float(np.mean([s["engine"]["gini"] for s in sc_list])), 3),
            "mean_critical_coverage_pct": round(float(np.mean([s["engine"]["critical_coverage_pct"] for s in sc_list])), 1),
            "mean_computation_ms": round(float(np.mean([s["engine"]["computation_ms"] for s in sc_list])), 1),
        },
        "greedy": {
            "mean_coverage_pct": round(float(np.mean([s["greedy"]["coverage_pct"] for s in sc_list])), 1),
            "mean_response_time_min": round(float(np.mean([s["greedy"]["avg_response_time_min"] for s in sc_list])), 1),
            "mean_jains_index": round(float(np.mean([s["greedy"]["jains_index"] for s in sc_list])), 3),
            "mean_gini": round(float(np.mean([s["greedy"]["gini"] for s in sc_list])), 3),
            "mean_critical_coverage_pct": round(float(np.mean([s["greedy"]["critical_coverage_pct"] for s in sc_list])), 1),
            "mean_computation_ms": round(float(np.mean([s["greedy"]["computation_ms"] for s in sc_list])), 1),
        },
        "random": {
            "mean_coverage_pct": round(float(np.mean([s["random"]["coverage_pct"] for s in sc_list])), 1),
            "mean_response_time_min": round(float(np.mean([s["random"]["avg_response_time_min"] for s in sc_list])), 1),
            "mean_jains_index": round(float(np.mean([s["random"]["jains_index"] for s in sc_list])), 3),
            "mean_gini": round(float(np.mean([s["random"]["gini"] for s in sc_list])), 3),
            "mean_critical_coverage_pct": round(float(np.mean([s["random"]["critical_coverage_pct"] for s in sc_list])), 1),
        },
        "mean_improvements": {
            "vs_greedy": {
                "response_time_faster_pct": round(float(np.mean([s["improvements"]["vs_greedy"]["response_time_improvement_pct"] for s in sc_list])), 1),
                "coverage_higher_pct": round(float(np.mean([s["improvements"]["vs_greedy"]["coverage_improvement_pct"] for s in sc_list])), 1),
                "jains_fairness_higher_pct": round(float(np.mean([s["improvements"]["vs_greedy"]["jains_fairness_improvement_pct"] for s in sc_list])), 1),
            },
            "vs_random": {
                "response_time_faster_pct": round(float(np.mean([s["improvements"]["vs_random"]["response_time_improvement_pct"] for s in sc_list])), 1),
                "coverage_higher_pct": round(float(np.mean([s["improvements"]["vs_random"]["coverage_improvement_pct"] for s in sc_list])), 1),
                "jains_fairness_higher_pct": round(float(np.mean([s["improvements"]["vs_random"]["jains_fairness_improvement_pct"] for s in sc_list])), 1),
            },
        },
    }

    return {
        "scenarios": results,
        "macro_summary": macro_summary,
    }

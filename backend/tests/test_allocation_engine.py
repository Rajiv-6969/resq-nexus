"""Allocation Engine: demand, depots, routing, GA operators, baseline and metrics."""
import random
import time

import numpy as np
import pytest

from services import allocation_engine as engine
from services.demand import zone_demand
from services.scenarios import RESOURCE_TYPES, Scenario, get_scenario

DEMO_IDS = ["flood-aluva", "flood-bengaluru", "earthquake-coimbatore", "cyclone-visakhapatnam"]


def zone(**overrides):
    base = {
        "id": "Z01", "name": "Test Village", "latitude": 26.3, "longitude": 91.0, "disaster_type": "flood",
        "damage_severity": 2, "population": 5000, "vulnerability_index": 0.6, "accessibility": 0.4,
    }
    return {**base, **overrides}


@pytest.fixture(scope="module")
def demo_results():
    """Run the engine once per demo scenario and reuse the results across tests."""
    out = {}
    for scenario_id in DEMO_IDS:
        started = time.perf_counter()
        result = engine.allocate(get_scenario(scenario_id))
        out[scenario_id] = (result, time.perf_counter() - started)
    return out


def totals(zones, method):
    return {r: sum(z[method]["allocated"][r] for z in zones) for r in RESOURCE_TYPES}


totals_of = totals


# --------------------------------------------------------------------------- demand
def test_demand_is_zero_without_damage():
    assert set(zone_demand(0, 50_000).values()) == {0}


def test_demand_grows_with_severity_and_population():
    minor, major, destroyed = (zone_demand(s, 10_000) for s in (1, 2, 3))
    for key in ("rescue_teams", "medical_kits", "vehicles"):
        assert minor[key] <= major[key] <= destroyed[key]
    assert destroyed["rescue_teams"] > minor["rescue_teams"]
    small, big = zone_demand(2, 5_000), zone_demand(2, 20_000)
    assert big["food_packets"] == 4 * small["food_packets"]
    assert big["shelters"] > small["shelters"]


# --------------------------------------------------------------------------- depots
@pytest.mark.parametrize(("zones", "vehicles"), [(19, 18), (19, 2), (3, 100), (40, 100), (19, 13)])
def test_depot_count_is_between_2_and_5(zones, vehicles):
    assert 2 <= engine.choose_depot_count(zones, vehicles) <= 5


def test_depot_count_follows_vehicles_and_zones():
    assert engine.choose_depot_count(19, 18) == 4
    assert engine.choose_depot_count(19, 13) == 3
    assert engine.choose_depot_count(19, 4) == 2
    assert engine.choose_depot_count(60, 60) == 5


@pytest.mark.parametrize("scenario_id", DEMO_IDS)
def test_depots_and_routes_are_consistent(demo_results, scenario_id):
    result, _ = demo_results[scenario_id]
    depot_ids = {d["id"] for d in result["depots"]}
    assert 2 <= len(depot_ids) <= 5
    for zone in result["zones"]:
        plan = zone["engine"]
        assert plan["depot_id"] in depot_ids
        assert plan["route"] and len(plan["route_coords"]) >= 2  # OSM node ids along real roads
        assert plan["route_coords"][-1] == [zone["latitude"], zone["longitude"]]
        assert plan["travel_time_min"] >= 0 and plan["distance_km"] >= 0
    served = sorted(zid for d in result["depots"] for zid in d["zone_ids"])
    assert served == sorted(z["id"] for z in result["zones"])


def test_road_graph_is_connected_and_weighted_by_access():
    zones = [
        {"id": "A", "latitude": 26.0, "longitude": 91.0, "accessibility": 1.0},
        {"id": "B", "latitude": 26.0, "longitude": 91.1, "accessibility": 1.0},
        {"id": "C", "latitude": 26.0, "longitude": 91.2, "accessibility": 0.1},
        {"id": "D", "latitude": 27.5, "longitude": 92.5, "accessibility": 0.5},  # far away
    ]
    graph = engine.build_road_graph(zones, depots=[], neighbours=1)
    import networkx as nx

    assert nx.is_connected(graph)
    ab, bc = graph.edges["A", "B"], graph.edges["B", "C"]
    assert ab["weight"] == pytest.approx(ab["distance_km"] / 1.0)
    assert bc["weight"] == pytest.approx(bc["distance_km"] / 0.55)


# --------------------------------------------------------------------------- availability
@pytest.mark.parametrize("scenario_id", DEMO_IDS)
@pytest.mark.parametrize("method", ["engine", "greedy"])
def test_allocations_never_exceed_available_resources(demo_results, scenario_id, method):
    result, _ = demo_results[scenario_id]
    stock = get_scenario(scenario_id).resources.model_dump()
    for key, used in totals(result["zones"], method).items():
        assert 0 <= used <= stock[key], key
    for zone in result["zones"]:
        for key in RESOURCE_TYPES:
            assert 0 <= zone[method]["allocated"][key] <= zone["demand"][key]


@pytest.mark.parametrize("scenario_id", DEMO_IDS)
def test_engine_hands_out_all_stock_while_demand_remains(demo_results, scenario_id):
    result, _ = demo_results[scenario_id]
    stock = get_scenario(scenario_id).resources.model_dump()
    need = {r: sum(z["demand"][r] for z in result["zones"]) for r in RESOURCE_TYPES}
    used = totals(result["zones"], "engine")
    for key in RESOURCE_TYPES:
        assert used[key] == min(stock[key], need[key])


def test_repair_keeps_any_matrix_within_stock_and_demand():
    rng = np.random.default_rng(0)
    demand = rng.integers(0, 50, size=(12, 5))
    demand[3] = 0  # an undamaged zone
    stock = np.array([30, 100, 60, 5, 200])
    ctx = engine.make_context(demand, stock, priority=rng.random(12), travel_norm=rng.random(12), labels=rng.integers(0, 3, 12))
    for _ in range(200):
        raw = rng.integers(-20, 400, size=(12, 5))
        fixed = engine.repair(raw, ctx)
        assert (fixed >= 0).all() and (fixed <= demand).all()
        assert (fixed.sum(axis=0) <= stock).all()
        assert (fixed.sum(axis=0) == np.minimum(stock, demand.sum(axis=0))).all()
        assert fixed[3].sum() == 0


def test_fitness_heavily_penalises_exceeding_stock():
    demand = np.array([[10, 10], [10, 10]])
    stock = np.array([10, 10])
    ctx = engine.make_context(demand, stock, priority=np.array([0.8, 0.4]), travel_norm=np.zeros(2), labels=np.zeros(2, int))
    feasible = np.array([[5, 5], [5, 5]])
    over = np.array([[10, 10], [10, 10]])  # covers everything but uses twice the stock
    fit = engine.fitness_batch(np.stack([feasible, over]), ctx)
    assert fit[1] < fit[0] - 1


def test_gini_of_coverage():
    assert engine.gini(np.array([0.5, 0.5, 0.5])) == pytest.approx(0.0)
    assert engine.gini(np.array([0.0, 0.0, 0.0, 1.0])) == pytest.approx(0.75)
    assert engine.gini(np.array([0.0, 0.0])) == 0.0


def test_mutation_moves_units_mostly_within_a_cluster():
    zones = 10
    demand = np.full((zones, 1), 100)
    stock = np.array([500])
    labels = np.array([0] * 5 + [1] * 5)
    ctx = engine.make_context(demand, stock, priority=np.ones(zones), travel_norm=np.zeros(zones), labels=labels)
    rng = random.Random(1)
    same = cross = 0
    for _ in range(2000):
        x = np.full((zones, 1), 50)
        before = x.copy()
        engine.mutate_matrix(x, ctx, rng, moves=1)
        assert x.sum() == before.sum() and (x >= 0).all() and (x <= demand).all()
        changed = np.flatnonzero(x[:, 0] != before[:, 0])
        if len(changed) == 2:
            if labels[changed[0]] == labels[changed[1]]:
                same += 1
            else:
                cross += 1
    assert 0.75 < same / (same + cross) < 0.85


# --------------------------------------------------------------------------- reproducibility + speed
def test_engine_results_are_reproducible_with_the_seed(demo_results):
    first, _ = demo_results["flood-aluva"]
    again = engine.allocate(get_scenario("flood-aluva"))
    strip = lambda r: {k: v for k, v in r.items() if k not in ("engine", "greedy")}  # noqa: E731 (timings differ)
    assert strip(again) == strip(first)
    for method in ("engine", "greedy"):
        a = {k: v for k, v in again[method]["metrics"].items() if k != "computation_ms"}
        b = {k: v for k, v in first[method]["metrics"].items() if k != "computation_ms"}
        assert a == b


def test_a_different_seed_still_respects_stock():
    scenario = get_scenario("cyclone-visakhapatnam")
    result = engine.allocate(scenario, seed=7)
    stock = scenario.resources.model_dump()
    for key, used in totals(result["zones"], "engine").items():
        assert used <= stock[key]


@pytest.mark.parametrize("scenario_id", DEMO_IDS)
def test_engine_finishes_in_under_5_seconds(demo_results, scenario_id):
    _, seconds = demo_results[scenario_id]
    assert seconds < 10.0  # about 280-650 hexagon zones on the real road graph


# --------------------------------------------------------------------------- GA history + feedback
@pytest.mark.parametrize("scenario_id", DEMO_IDS)
def test_fitness_history_and_passes(demo_results, scenario_id):
    result, _ = demo_results[scenario_id]
    passes = result["passes"]
    assert 1 <= len(passes) <= 1 + engine.ENGINE_SETTINGS["feedback"]["max_iterations"]
    assert passes[0]["generations"] == engine.ENGINE_SETTINGS["ga"]["generations"]
    for p in passes[1:]:
        assert p["generations"] < passes[0]["generations"]
    history = result["fitness_history"]
    assert len(history) == sum(p["generations"] for p in passes)
    first_pass = [h for h in history if h["pass"] == 1]
    assert all(np.isfinite([h["best"], h["mean"]]).all() for h in history)
    assert first_pass[-1]["best"] >= first_pass[0]["best"]  # elitism: never gets worse
    assert result["selected_pass"] in {p["pass"] for p in passes}
    # Another pass only runs when a depot area is left with more than the threshold unmet.
    for earlier in passes[:-1]:
        assert max(earlier["unmet_by_depot"].values()) > engine.ENGINE_SETTINGS["feedback"]["unmet_threshold"] * 100


# --------------------------------------------------------------------------- baseline + metrics
def test_greedy_serves_the_highest_priority_zone_first(scenario_factory):
    zones = [
        zone(id="HI", name="High", damage_severity=3, population=4000, vulnerability_index=0.9, accessibility=0.2),
        zone(id="MID", name="Mid", damage_severity=2, population=4000, vulnerability_index=0.5, latitude=26.35),
        zone(id="LO", name="Low", damage_severity=1, population=4000, vulnerability_index=0.1, latitude=26.4),
    ]
    scenario = Scenario.model_validate(scenario_factory(zones=zones))
    result = engine.allocate(scenario)
    by_id = {z["id"]: z for z in result["zones"]}
    hi = by_id["HI"]
    for key in RESOURCE_TYPES:
        assert hi["greedy"]["allocated"][key] == min(hi["demand"][key], scenario.resources.model_dump()[key])


def test_metrics_for_both_methods():
    result = engine.allocate(get_scenario("earthquake-coimbatore"))
    for method in ("engine", "greedy"):
        m = result[method]["metrics"]
        assert {"avg_response_time_min", "coverage_pct", "unmet_demand", "unmet_demand_pct", "gini", "computation_ms"} <= set(m)
        assert 0 <= m["coverage_pct"] <= 100 and 0 <= m["gini"] <= 1
        assert set(m["unmet_demand"]) == set(RESOURCE_TYPES)
        assert m["avg_response_time_min"] > 0 and m["computation_ms"] >= 0


@pytest.mark.parametrize("scenario_id", DEMO_IDS)
def test_engine_coverage_follows_priority_levels(demo_results, scenario_id):
    """Per resource type: a level holds units only once every more urgent level's need for that type is met.

    Hence Critical >= High >= Medium >= Low coverage for every type, checked wherever the higher
    level still has unmet need (a fully supplied level cannot use more, so the comparison is moot).
    """
    result, _ = demo_results[scenario_id]
    by_level = result["engine"]["metrics"]["coverage_by_level_and_type"]
    levels = [lv for lv in ("Critical", "High", "Medium", "Low") if lv in by_level]
    checked = 0
    for r in RESOURCE_TYPES:
        for hi, lo in zip(levels, levels[1:]):
            c_hi, c_lo = by_level[hi][r], by_level[lo][r]
            if c_hi is None or c_lo is None or c_hi >= 100.0:
                continue
            checked += 1
            assert c_hi >= c_lo, (scenario_id, r, hi, c_hi, lo, c_lo)
            assert c_lo == 0.0, (scenario_id, r, hi, c_hi, lo, c_lo)  # strict: nothing stays below while above still needs it
    assert checked > 0


@pytest.mark.parametrize("scenario_id", DEMO_IDS)
def test_no_resource_is_idle_while_demand_remains(demo_results, scenario_id):
    """Work-conserving: every unit of a type is handed out while any zone still needs that type."""
    result, _ = demo_results[scenario_id]
    for r, u in result["engine"]["metrics"]["utilisation"].items():
        assert u["allocated"] == min(u["available"], u["demand"]), (scenario_id, r, u)
    totals = totals_of(result["zones"], "engine")
    assert totals == {r: result["engine"]["metrics"]["utilisation"][r]["allocated"] for r in RESOURCE_TYPES}


# --------------------------------------------------------------------------- priority-level ordering
def level_context(levels, demand=None, stock=(4, 0, 0, 0, 0)):
    levels = np.asarray(levels)
    n = levels.size
    demand = np.zeros((n, 5), dtype=int) if demand is None else np.asarray(demand)
    if demand.sum() == 0:
        demand[:, 0] = 2  # every zone needs two rescue teams
    return engine.make_context(demand, np.array(stock), priority=np.linspace(1, 0.1, n), travel_norm=np.zeros(n),
                               labels=np.zeros(n, int), levels=levels)


def test_level_order_violation_counts_units_held_below_an_unmet_level():
    ctx = level_context([0, 0, 1, 1])
    ordered = np.array([[2, 0, 0, 0, 0], [2, 0, 0, 0, 0], [0] * 5, [0] * 5])
    inverted = np.array([[0] * 5, [0] * 5, [2, 0, 0, 0, 0], [2, 0, 0, 0, 0]])
    half = np.array([[2, 0, 0, 0, 0], [0] * 5, [2, 0, 0, 0, 0], [0] * 5])
    assert engine.level_order_violation(ordered, ctx) == 0
    assert engine.level_order_violation(inverted, ctx) == pytest.approx(1.0)  # all 4 units misplaced
    assert engine.level_order_violation(half, ctx) == pytest.approx(0.5)
    assert engine.fitness_batch(ordered, ctx)[0] > engine.fitness_batch(half, ctx)[0] > engine.fitness_batch(inverted, ctx)[0]


def test_a_fully_supplied_level_does_not_pull_from_below():
    demand = np.zeros((4, 5), dtype=int)
    demand[:, 0] = [1, 1, 3, 3]  # Critical needs 2 teams in total, Medium needs 6
    ctx = level_context([0, 0, 2, 2], demand=demand, stock=(5, 0, 0, 0, 0))
    plan = np.array([[1, 0, 0, 0, 0], [1, 0, 0, 0, 0], [2, 0, 0, 0, 0], [1, 0, 0, 0, 0]])
    fixed = engine.repair(plan, ctx)
    assert fixed[:2, 0].tolist() == [1, 1] and fixed[2:, 0].sum() == 3  # Critical met; Medium keeps its 3 (none idle)
    assert engine.level_order_violation(fixed, ctx) == 0


def test_repair_moves_units_up_until_levels_are_ordered():
    ctx = level_context([0, 0, 1, 1, 2, 2], stock=(4, 0, 0, 0, 0))
    plan = np.array([[0] * 5, [0] * 5, [1, 0, 0, 0, 0], [1, 0, 0, 0, 0], [1, 0, 0, 0, 0], [1, 0, 0, 0, 0]])
    fixed = engine.repair(plan, ctx)
    means = engine.level_coverage(engine.zone_coverage(fixed, ctx), ctx)
    assert fixed.sum() == 4 and (fixed <= ctx.demand).all()
    assert means[0] >= means[1] >= means[2]
    assert means[0] > 0  # the Critical level actually received units


def test_within_level_gini_ignores_differences_between_levels():
    ctx = level_context([0, 0, 1, 1])
    plan = np.array([[2, 0, 0, 0, 0], [2, 0, 0, 0, 0], [0] * 5, [0] * 5])  # perfectly even inside each level
    cov = engine.zone_coverage(plan, ctx)
    assert engine.within_level_gini(cov, ctx) == 0 and engine.gini(cov) > 0
    uneven = np.array([[2, 0, 0, 0, 0], [0] * 5, [2, 0, 0, 0, 0], [0] * 5])
    assert engine.within_level_gini(engine.zone_coverage(uneven, ctx), ctx) > 0


def test_context_without_levels_behaves_as_one_level():
    ctx = engine.make_context(np.full((3, 5), 2), np.array([3, 0, 0, 0, 0]), priority=np.ones(3), travel_norm=np.zeros(3), labels=np.zeros(3, int))
    assert ctx.level_ids == [0]
    plan = engine.repair(np.zeros((3, 5), int), ctx)
    assert engine.level_order_violation(engine.zone_coverage(plan, ctx), ctx) == 0 and plan.sum() == 3


@pytest.mark.parametrize("scenario_id", DEMO_IDS)
def test_engine_reaches_every_zone_in_need_and_is_fairer_than_greedy(demo_results, scenario_id):
    result, _ = demo_results[scenario_id]
    engine_m, greedy_m = result["engine"]["metrics"], result["greedy"]["metrics"]
    assert engine_m["zones_served"] == engine_m["zones_in_need"]
    # Fairness is optimised inside each priority level (scarce stock deliberately goes to the
    # urgent levels first, so the Gini across *all* zones is not the engine's target).
    assert engine_m["gini_within_level"] < greedy_m["gini_within_level"]
    assert engine_m["unmet_demand"] == greedy_m["unmet_demand"]  # same stock, all of it handed out


def test_undamaged_zones_get_nothing(demo_results):
    result, _ = demo_results["cyclone-visakhapatnam"]
    calm = [z for z in result["zones"] if z["damage_severity"] == 0]
    assert calm
    for zone in calm:
        assert sum(zone["engine"]["allocated"].values()) == 0
        assert zone["engine"]["coverage_pct"] is None


def test_scenario_without_damage_does_not_crash(scenario_factory):
    zones = [zone(id=f"Z{i}", damage_severity=0, latitude=26 + i / 50) for i in range(6)]
    result = engine.allocate(Scenario.model_validate(scenario_factory(zones=zones)))
    assert all(sum(z["engine"]["allocated"].values()) == 0 for z in result["zones"])
    assert result["engine"]["metrics"]["unmet_demand_pct"] == 0


def test_custom_priority_weights_are_normalised_and_used():
    scenario = get_scenario("flood-aluva")
    result = engine.allocate(scenario, weights={"severity": 2, "population": 0, "vulnerability": 0, "accessibility": 0})
    assert result["weights"] == {"severity": 1.0, "population": 0.0, "vulnerability": 0.0, "accessibility": 0.0}
    destroyed = [z for z in result["zones"] if z["damage_severity"] == 3]
    assert all(z["priority_level"] == "Critical" for z in destroyed)

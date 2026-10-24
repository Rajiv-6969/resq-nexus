"""Allocation Engine (the *Allocate* stage of Assess -> Prioritise -> Allocate -> Explain).

Algorithms used:

* K-Means clustering (scikit-learn)
* Dijkstra's shortest path (NetworkX)
* Genetic Algorithm (DEAP)

A greedy baseline is included for comparison. Every tunable number lives in
``ENGINE_SETTINGS``; results are deterministic for a given scenario, set of
priority weights and seed.
"""
from __future__ import annotations

import math
import random
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from operator import attrgetter
from typing import Any

import networkx as nx
import numpy as np
from deap import base, creator, tools
from sklearn.cluster import KMeans

from services import priority as priority_service
from services.demand import zone_demand
from services.geo import haversine_km
from services.scenarios import RESOURCE_TYPES, Scenario

ENGINE_SETTINGS: dict[str, Any] = {
    "seed": 42,
    "depots": {"min": 2, "max": 5, "vehicles_per_depot": 4, "zones_per_depot": 4},
    "roads": {
        "neighbours": 4,  # each node is linked to its nearest neighbours
        "depot_accessibility": 1.0,  # depots are set up on a usable road
        "min_accessibility": 0.05,  # floor so cut-off zones stay reachable, slowly
        "speed_kmh": 40.0,  # average speed on a road with accessibility 1
    },
    "ga": {
        "population": 60,
        "generations": 120,
        "crossover_prob": 0.7,
        "mutation_prob": 0.4,
        "tournament_size": 3,
        "elite": 2,
        "seeded_share": 0.5,
        "same_cluster_prob": 0.8,
    },
    "fitness": {"coverage": 1.0, "travel_time": 0.3, "gini": 0.15, "over_allocation_penalty": 10.0},
    "feedback": {"unmet_threshold": 0.40, "max_iterations": 3, "upweight": 1.5, "generations": 40, "carry_over": 20},
}

DEPOT_LABELS = "ABCDE"
PRIORITY_FLOOR = 0.01  # keeps zero-score zones from vanishing in weighted sums

# DEAP types: one maximised objective; an individual is a zones x resources matrix.
if not hasattr(creator, "ResQFitness"):
    creator.create("ResQFitness", base.Fitness, weights=(1.0,))
if not hasattr(creator, "ResQPlan"):
    creator.create("ResQPlan", np.ndarray, fitness=getattr(creator, "ResQFitness"))
Fitness = getattr(creator, "ResQFitness")
Plan = getattr(creator, "ResQPlan")


# --------------------------------------------------------------------------- K-Means
def choose_depot_count(zone_count: int, vehicles: int, depots: Mapping[str, int] | None = None) -> int:
    """Number of relief depots (2-5): each needs a small fleet and enough zones to serve."""
    cfg = ENGINE_SETTINGS["depots"] if depots is None else depots
    k = min(vehicles // cfg["vehicles_per_depot"], zone_count // cfg["zones_per_depot"])
    k = max(cfg["min"], min(cfg["max"], k))
    return max(1, min(k, zone_count))


def cluster_depots(coords: np.ndarray, weights: np.ndarray, k: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Weighted K-Means on zone coordinates.

    Coordinates are projected to a local kilometre grid first so distances are
    isotropic. Returns ``(centres as lat/lon, label per zone)`` with clusters
    numbered west to east.
    """
    lat0, lon0 = coords[:, 0].mean(), coords[:, 1].mean()
    kx, ky = 111.320 * math.cos(math.radians(lat0)), 110.574
    xy = np.column_stack(((coords[:, 1] - lon0) * kx, (coords[:, 0] - lat0) * ky))
    model = KMeans(n_clusters=k, n_init=10, random_state=seed).fit(xy, sample_weight=weights)
    centres = np.column_stack((model.cluster_centers_[:, 1] / ky + lat0, model.cluster_centers_[:, 0] / kx + lon0))
    order = np.argsort(centres[:, 1], kind="stable")
    relabel = np.empty(k, dtype=np.int64)
    relabel[order] = np.arange(k)
    return centres[order], relabel[model.labels_]


# --------------------------------------------------------------------------- Dijkstra
def build_road_graph(
    zones: Sequence[Mapping[str, Any]],
    depots: Sequence[Mapping[str, Any]],
    neighbours: int = 4,
    min_accessibility: float = 0.05,
    depot_accessibility: float = 1.0,
) -> nx.Graph:
    """Synthetic road network linking every zone and depot to its nearest neighbours.

    Edge weight = haversine distance / mean accessibility of the two ends, so
    roads into poorly accessible zones are slower. Separate components are
    joined by their shortest link so every zone stays reachable.
    """
    graph = nx.Graph()
    nodes = [dict(z, kind="zone") for z in zones] + [dict(d, kind="depot") for d in depots]
    for node in nodes:
        access = node.get("accessibility", depot_accessibility)
        graph.add_node(node["id"], latitude=node["latitude"], longitude=node["longitude"],
                       accessibility=max(float(access), min_accessibility), kind=node["kind"])
    if len(nodes) < 2:
        return graph

    ids = [n["id"] for n in nodes]
    dist = np.array([[haversine_km(a["latitude"], a["longitude"], b["latitude"], b["longitude"]) for b in nodes] for a in nodes])

    def link(i: int, j: int) -> None:
        a, b = ids[i], ids[j]
        access = (graph.nodes[a]["accessibility"] + graph.nodes[b]["accessibility"]) / 2
        graph.add_edge(a, b, distance_km=float(dist[i, j]), weight=float(dist[i, j]) / access)

    k = min(neighbours, len(nodes) - 1)
    for i in range(len(nodes)):
        for j in [j for j in np.argsort(dist[i], kind="stable") if j != i][:k]:
            link(i, int(j))

    index = {node_id: i for i, node_id in enumerate(ids)}
    components = [sorted(index[n] for n in c) for c in nx.connected_components(graph)]
    while len(components) > 1:
        first, rest = components[0], [i for c in components[1:] for i in c]
        sub = dist[np.ix_(first, rest)]
        i, j = np.unravel_index(np.argmin(sub), sub.shape)
        link(first[i], rest[j])
        components = [sorted(index[n] for n in c) for c in nx.connected_components(graph)]
    return graph


def shortest_paths(graph: nx.Graph, depot_ids: Sequence[str]) -> dict[str, Any]:
    """Dijkstra from every depot: ``{depot: (cost to each node, path to each node)}``."""
    return {d: nx.single_source_dijkstra(graph, d, weight="weight") for d in depot_ids}


def describe_route(graph: nx.Graph, paths: Mapping[str, Any], depot: str, zone: str, speed_kmh: float) -> dict[str, Any]:
    """Route facts for one depot -> zone trip."""
    cost, path = paths[depot][0][zone], paths[depot][1][zone]
    distance = sum(graph.edges[a, b]["distance_km"] for a, b in zip(path, path[1:]))
    return {
        "depot_id": depot,
        "route": list(path),
        "route_coords": [[graph.nodes[n]["latitude"], graph.nodes[n]["longitude"]] for n in path],
        "travel_time_min": round(cost / speed_kmh * 60, 1),
        "distance_km": round(distance, 2),
    }


# --------------------------------------------------------------------------- Genetic Algorithm
@dataclass
class GAContext:
    """Arrays the GA operators and fitness function share."""

    demand: np.ndarray  # (zones, resources) units needed
    stock: np.ndarray  # (resources,) units available
    priority: np.ndarray  # (zones,) priority score
    travel_norm: np.ndarray  # (zones,) travel time, normalised
    labels: np.ndarray  # (zones,) cluster of each zone
    fitness_weights: Mapping[str, float] = field(default_factory=lambda: dict(ENGINE_SETTINGS["fitness"]))
    same_cluster_prob: float = ENGINE_SETTINGS["ga"]["same_cluster_prob"]

    def __post_init__(self) -> None:
        self.demand = np.asarray(self.demand, dtype=np.int64)
        self.stock = np.asarray(self.stock, dtype=np.int64)
        self.priority = np.maximum(np.asarray(self.priority, dtype=float), PRIORITY_FLOOR)
        self.travel_norm = np.asarray(self.travel_norm, dtype=float)
        self.labels = np.asarray(self.labels, dtype=np.int64)
        self.target = np.minimum(self.stock, self.demand.sum(axis=0))  # units worth handing out
        self.mask = self.demand > 0
        self.safe_demand = np.where(self.mask, self.demand, 1)
        self.needs_count = self.mask.sum(axis=1)
        self.active = self.needs_count > 0  # zones that need anything
        self.active_cols = np.flatnonzero(self.target > 0)
        self.p_active = self.priority[self.active]
        self.p_sum = float(self.p_active.sum()) or 1.0
        self.weighted_demand = (self.priority[:, None] * self.demand).sum(axis=0)
        self.demand_cols = self.weighted_demand > 0
        self.tau_active = self.travel_norm[self.active]
        self.cluster_members = {int(c): np.flatnonzero(self.labels == c) for c in np.unique(self.labels)}


def make_context(demand, stock, priority, travel_norm, labels, fitness_weights=None, same_cluster_prob=None) -> GAContext:
    """Build a :class:`GAContext` (defaults from ``ENGINE_SETTINGS``)."""
    return GAContext(
        demand, stock, priority, travel_norm, labels,
        dict(fitness_weights or ENGINE_SETTINGS["fitness"]),
        ENGINE_SETTINGS["ga"]["same_cluster_prob"] if same_cluster_prob is None else same_cluster_prob,
    )


def gini(values) -> Any:
    """Gini coefficient along the last axis (0 = perfectly even, 1 = all to one)."""
    v = np.sort(np.asarray(values, dtype=float), axis=-1)
    n = v.shape[-1]
    if n == 0:
        return 0.0
    total = v.sum(axis=-1)
    g = 2 * (v * np.arange(1, n + 1)).sum(axis=-1) / (n * np.where(total > 0, total, 1)) - (n + 1) / n
    g = np.where(total > 0, np.clip(g, 0.0, 1.0), 0.0)
    return float(g) if g.ndim == 0 else g


def zone_coverage(plans: np.ndarray, ctx: GAContext) -> np.ndarray:
    """Share of each needy zone's demand that is met, averaged over resource types."""
    covered = np.minimum(plans, ctx.demand) / ctx.safe_demand * ctx.mask
    return covered.sum(axis=-1)[..., ctx.active] / ctx.needs_count[ctx.active]


def demand_coverage(plans: np.ndarray, ctx: GAContext) -> np.ndarray:
    """Priority-weighted share of demand met (0-1), averaged over resource types."""
    met = (ctx.priority[:, None] * np.minimum(plans, ctx.demand)).sum(axis=-2)
    return (met[..., ctx.demand_cols] / ctx.weighted_demand[ctx.demand_cols]).mean(axis=-1)


def relief_travel_time(plans: np.ndarray, ctx: GAContext) -> np.ndarray:
    """Priority-weighted mean travel time (normalised 0-1) of the relief each zone receives."""
    weight = (plans / np.maximum(ctx.target, 1)).sum(axis=-1) * ctx.priority
    return (weight * ctx.travel_norm).sum(axis=-1) / np.maximum(weight.sum(axis=-1), 1e-12)


def fitness_batch(plans: np.ndarray, ctx: GAContext) -> np.ndarray:
    """Fitness of one plan (zones x resources) or a stack of plans (maximised).

    priority-weighted demand coverage - priority-weighted travel time
    - Gini coefficient of zone coverage - heavy penalty for exceeding the stock.
    """
    plans = np.asarray(plans)
    if plans.ndim == 2:
        plans = plans[None]
    w = ctx.fitness_weights
    excess = (np.maximum(plans.sum(axis=1) - ctx.stock, 0) / np.maximum(ctx.stock, 1)).sum(axis=1)
    penalty = w["over_allocation_penalty"] * excess
    if not ctx.active.any():
        return -penalty
    return (
        w["coverage"] * demand_coverage(plans, ctx)
        - w["travel_time"] * relief_travel_time(plans, ctx)
        - w["gini"] * gini(zone_coverage(plans, ctx))
        - penalty
    )


def _shrink(cols: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Scale columns down to ``target`` units (largest-remainder rounding)."""
    scaled = cols * (target / cols.sum(axis=0))
    floor = np.floor(scaled).astype(np.int64)
    rank = np.argsort(np.argsort(floor - scaled, axis=0, kind="stable"), axis=0, kind="stable")
    return floor + (rank < (target - floor.sum(axis=0)))


def _fill(cols: np.ndarray, demand: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Hand leftover units to zones that still need them, in proportion to unmet need.

    A zone's share never exceeds its own unmet need, so one pass with
    largest-remainder rounding is enough.
    """
    need = demand - cols
    short = target - cols.sum(axis=0)
    scaled = need * (short / np.maximum(need.sum(axis=0), 1))
    floor = np.floor(scaled).astype(np.int64)
    rank = np.argsort(np.argsort(floor - scaled, axis=0, kind="stable"), axis=0, kind="stable")
    return cols + floor + (rank < (short - floor.sum(axis=0)))


def repair(plan: np.ndarray, ctx: GAContext) -> np.ndarray:
    """Return a feasible copy of ``plan``.

    No zone gets more than it needs or less than zero, column totals never
    exceed the available stock, and stock left over while demand remains is
    handed out.
    """
    x = np.clip(np.asarray(plan, dtype=np.int64), 0, ctx.demand)
    over = np.flatnonzero(x.sum(axis=0) > ctx.target)
    if over.size:
        x[:, over] = _shrink(x[:, over], ctx.target[over])
    under = np.flatnonzero(x.sum(axis=0) < ctx.target)
    if under.size:
        x[:, under] = _fill(x[:, under], ctx.demand[:, under], ctx.target[under])
    for r in np.flatnonzero(x.sum(axis=0) > ctx.target):  # floating-point safety net
        while x[:, r].sum() > ctx.target[r]:
            x[np.argmax(x[:, r]), r] -= 1
    return x


def mutate_matrix(x: np.ndarray, ctx: GAContext, rng: random.Random, moves: int | None = None) -> np.ndarray:
    """Cluster-aware mutation, in place: move units of one resource from one zone to another.

    The receiving zone is in the donor's cluster with probability
    ``same_cluster_prob`` (0.8) and in another cluster otherwise. Totals and
    per-zone demand caps are preserved.
    """
    if not ctx.active_cols.size:
        return x
    zone_ids = np.arange(x.shape[0])
    for _ in range(moves or rng.randint(1, 3)):
        r = int(ctx.active_cols[rng.randrange(ctx.active_cols.size)])
        donors = np.flatnonzero(x[:, r] > 0)
        if not donors.size:
            continue
        d = int(donors[rng.randrange(donors.size)])
        need = ctx.demand[:, r] - x[:, r]
        open_zones = (need > 0) & (zone_ids != d)
        same = ctx.labels == ctx.labels[d]
        candidates = np.flatnonzero(open_zones & (same if rng.random() < ctx.same_cluster_prob else ~same))
        if not candidates.size:
            candidates = np.flatnonzero(open_zones)
        if not candidates.size:
            continue
        z = int(candidates[rng.randrange(candidates.size)])
        limit = int(min(x[d, r], need[z]))
        units = rng.randint(1, max(1, math.ceil(limit / 2)))
        x[d, r] -= units
        x[z, r] += units
    return x


def crossover_matrices(a: np.ndarray, b: np.ndarray, rng: random.Random) -> None:
    """Uniform crossover of whole zone rows, in place."""
    rows = np.array([rng.random() < 0.5 for _ in range(a.shape[0])])
    if rows.any():
        swap = a[rows].copy()
        a[rows] = b[rows]
        b[rows] = swap


def _mate(p1, p2, ctx: GAContext, rng: random.Random):
    a, b = np.asarray(p1), np.asarray(p2)
    crossover_matrices(a, b, rng)
    a[...] = repair(a, ctx)
    b[...] = repair(b, ctx)
    return p1, p2


def _mutate(plan, ctx: GAContext, rng: random.Random):
    mutate_matrix(np.asarray(plan), ctx, rng)
    return (plan,)


def _clone(plan):
    """Fast copy of an individual (array + fitness) instead of ``copy.deepcopy``."""
    twin = np.array(plan, dtype=np.int64).view(Plan)
    twin.fitness = Fitness(plan.fitness.values) if plan.fitness.valid else Fitness()
    return twin


def _select(plans, k: int, rng: random.Random, size: int):
    """Tournament selection driven by the run's own RNG (reproducible, thread-safe)."""
    n = len(plans)
    return [max((plans[rng.randrange(n)] for _ in range(size)), key=attrgetter("fitness")) for _ in range(k)]


def _evaluate(plans, ctx: GAContext) -> None:
    if plans:
        scores = fitness_batch(np.stack([np.asarray(p) for p in plans]), ctx)
        for plan, score in zip(plans, scores):
            plan.fitness.values = (float(score),)


def seeded_plan(ctx: GAContext, np_rng: np.random.Generator, noise: float = 0.0) -> np.ndarray:
    """Each cluster's share of every resource, split between its zones in proportion to priority."""
    weights = ctx.priority * (np.exp(np_rng.normal(0.0, noise, ctx.priority.size)) if noise else 1.0)
    weighted_need = weights[:, None] * ctx.demand
    total_need = weighted_need.sum(axis=0)
    x = np.zeros_like(ctx.demand)
    for members in ctx.cluster_members.values():
        share = ctx.target * np.divide(weighted_need[members].sum(axis=0), total_need,
                                       out=np.zeros(total_need.shape), where=total_need > 0)
        w = weights[members][:, None] * ctx.mask[members]
        w_sum = w.sum(axis=0)
        x[members] = np.floor(np.divide(w * share, w_sum, out=np.zeros(w.shape), where=w_sum > 0)).astype(np.int64)
    return repair(x, ctx)


def random_plan(ctx: GAContext, np_rng: np.random.Generator) -> np.ndarray:
    """A random split of each resource between the zones that need it."""
    x = np.zeros_like(ctx.demand)
    for r in ctx.active_cols:
        needy = np.flatnonzero(ctx.mask[:, r])
        x[needy, r] = np.floor(np_rng.dirichlet(np.ones(needy.size)) * ctx.target[r]).astype(np.int64)
    return repair(x, ctx)


def run_ga(ctx: GAContext, generations: int, seed: int, carry: Sequence[np.ndarray] = (), ga: Mapping[str, Any] | None = None):
    """Run the GA; returns ``(best plan, per-generation records, final population)``."""
    ga = ENGINE_SETTINGS["ga"] if ga is None else ga
    rng, np_rng = random.Random(seed), np.random.default_rng(seed)
    size = ga["population"]

    population = [Plan(np.array(m)) for m in carry][:size]
    seeded = round((size - len(population)) * ga["seeded_share"])
    population += [Plan(seeded_plan(ctx, np_rng, 0.0 if i == 0 else 0.35)) for i in range(seeded)]
    population += [Plan(random_plan(ctx, np_rng)) for _ in range(size - len(population))]

    toolbox = base.Toolbox()
    toolbox.register("clone", _clone)
    toolbox.register("evaluate", _evaluate, ctx=ctx)
    toolbox.register("mate", _mate, ctx=ctx, rng=rng)
    toolbox.register("mutate", _mutate, ctx=ctx, rng=rng)
    toolbox.register("select", _select, rng=rng, size=ga["tournament_size"])

    toolbox.evaluate(population)
    hall_of_fame = tools.HallOfFame(1, similar=np.array_equal)
    hall_of_fame.update(population)
    stats = tools.Statistics(key=lambda plan: plan.fitness.values[0])
    stats.register("best", np.max)
    stats.register("mean", np.mean)
    logbook = tools.Logbook()

    for generation in range(1, generations + 1):
        elites = [toolbox.clone(p) for p in tools.selBest(population, ga["elite"])]
        offspring = [toolbox.clone(p) for p in toolbox.select(population, size - len(elites))]
        for a, b in zip(offspring[::2], offspring[1::2]):
            if rng.random() < ga["crossover_prob"]:
                toolbox.mate(a, b)
                del a.fitness.values, b.fitness.values
        for plan in offspring:
            if rng.random() < ga["mutation_prob"]:
                toolbox.mutate(plan)
                del plan.fitness.values
        toolbox.evaluate([p for p in offspring if not p.fitness.valid])
        population = elites + offspring
        hall_of_fame.update(population)
        logbook.record(gen=generation, **stats.compile(population))
    return hall_of_fame[0], logbook, population


def unmet_by_cluster(plan: np.ndarray, ctx: GAContext) -> dict[int, float]:
    """Unmet share of each cluster's demand (0-1), averaged over resource types."""
    out = {}
    for c, members in ctx.cluster_members.items():
        need = ctx.demand[members].sum(axis=0)
        met = np.minimum(plan[members], ctx.demand[members]).sum(axis=0)
        has = need > 0
        out[c] = float(((need[has] - met[has]) / need[has]).mean()) if has.any() else 0.0
    return out


# --------------------------------------------------------------------------- baseline + metrics
def greedy_allocation(order: Sequence[int], demand: np.ndarray, stock: np.ndarray) -> np.ndarray:
    """Greedy baseline: zones in priority order take what they need until stock runs out."""
    remaining = np.asarray(stock, dtype=np.int64).copy()
    plan = np.zeros_like(demand, dtype=np.int64)
    for z in order:
        plan[z] = np.minimum(demand[z], remaining)
        remaining -= plan[z]
    return plan


def plan_metrics(plan: np.ndarray, ctx: GAContext, minutes: np.ndarray, computation_ms: float) -> dict[str, Any]:
    """Comparison metrics for one allocation plan.

    * avg_response_time_min - road travel time from the assigned depot, averaged
      over the relief delivered (each zone weighted by its share of the stock)
    * coverage_pct - each needy zone's coverage %, weighted by priority score
    * demand_met_pct - share of demand units met, weighted by priority score
    * unmet_demand / unmet_demand_pct - units still needed (and % of total need)
    * gini - Gini coefficient of zone coverage (0 = every zone equally covered)
    * computation_ms - wall-clock time to produce the plan
    """
    need = ctx.demand.sum(axis=0)
    unmet = np.maximum(ctx.demand - plan, 0).sum(axis=0)
    has_need = need > 0
    delivered = plan.sum(axis=0)
    load = (plan / np.maximum(delivered, 1)).sum(axis=1)  # each zone's share of what was delivered
    metrics: dict[str, Any] = {
        "avg_response_time_min": round(float(load @ minutes / load.sum()), 1) if load.sum() > 0 else 0.0,
        "coverage_pct": None,
        "demand_met_pct": None,
        "unmet_demand": {r: int(u) for r, u in zip(RESOURCE_TYPES, unmet)},
        "unmet_demand_pct": round(float((unmet[has_need] / need[has_need]).mean() * 100), 1) if has_need.any() else 0.0,
        "gini": None,
        "computation_ms": round(computation_ms, 1),
        "zones_in_need": int(ctx.active.sum()),
        "zones_served": int(((plan.sum(axis=1) > 0) & ctx.active).sum()),
    }
    if ctx.active.any():
        cov = zone_coverage(plan, ctx)
        metrics["coverage_pct"] = round(float(cov @ ctx.p_active / ctx.p_sum * 100), 1)
        metrics["demand_met_pct"] = round(float(demand_coverage(plan, ctx)) * 100, 1)
        metrics["gini"] = round(float(gini(cov)), 3)
    return metrics


# --------------------------------------------------------------------------- engine
def allocate(
    scenario: Scenario,
    weights: Mapping[str, float] | None = None,
    seed: int | None = None,
    settings: Mapping[str, Any] | None = None,
    extra_demand: Mapping[str, Mapping[str, int]] | None = None,
) -> dict[str, Any]:
    """Allocate the scenario's resources to its zones; also runs the greedy baseline.

    extra_demand (zone id -> resource -> units) is added to the zones' own demand first,
    e.g. live SOS requests near a zone.
    """
    settings = ENGINE_SETTINGS if settings is None else settings
    seed = int(settings["seed"] if seed is None else seed)
    ga, roads, feedback = settings["ga"], settings["roads"], settings["feedback"]
    started = time.perf_counter()

    priority_settings = priority_service.settings_with_weights(weights)
    raw = [z.model_dump() for z in scenario.zones]
    scored = {z["id"]: z for z in priority_service.score_zones(raw, priority_settings)}
    zones = [scored[z["id"]] for z in raw]  # scenario order
    ids = [z["id"] for z in zones]
    demand = np.array([[zone_demand(z["damage_severity"], z["population"])[r] for r in RESOURCE_TYPES] for z in zones], dtype=np.int64)
    for i, zone_id in enumerate(ids):
        extra = (extra_demand or {}).get(zone_id)
        if extra:
            demand[i] += np.array([int(extra.get(r, 0)) for r in RESOURCE_TYPES], dtype=np.int64)
    stock = np.array([getattr(scenario.resources, r) for r in RESOURCE_TYPES], dtype=np.int64)
    scores = np.array([z["priority_score"] for z in zones], dtype=float)
    coords = np.array([[z["latitude"], z["longitude"]] for z in zones], dtype=float)
    needy = demand.sum(axis=1) > 0

    k = choose_depot_count(len(zones), scenario.resources.vehicles, settings["depots"])
    sample_weight = np.maximum(scores, PRIORITY_FLOOR)
    passes: list[dict[str, Any]] = []
    history: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None
    carry: list[np.ndarray] = []
    travel_ref: float | None = None

    for pass_no in range(1, feedback["max_iterations"] + 2):
        centres, _ = cluster_depots(coords, sample_weight, k, seed)
        depots = [
            {"id": f"D{i + 1}", "label": DEPOT_LABELS[i], "name": f"Depot {DEPOT_LABELS[i]}",
             "latitude": round(float(lat), 5), "longitude": round(float(lon), 5)}
            for i, (lat, lon) in enumerate(centres)
        ]
        depot_ids = [d["id"] for d in depots]
        graph = build_road_graph(zones, depots, roads["neighbours"], roads["min_accessibility"], roads["depot_accessibility"])
        paths = shortest_paths(graph, depot_ids)
        fastest = [min(depot_ids, key=lambda d, z=z: (paths[d][0][z], d)) for z in ids]
        minutes = np.array([paths[d][0][z] / roads["speed_kmh"] * 60 for d, z in zip(fastest, ids)])
        if travel_ref is None:
            travel_ref = float(max(minutes[needy].max() if needy.any() else 0.0, 1.0))
        labels = np.array([depot_ids.index(d) for d in fastest])
        ctx = make_context(demand, stock, scores, minutes / travel_ref, labels, settings["fitness"], ga["same_cluster_prob"])

        generations = ga["generations"] if pass_no == 1 else feedback["generations"]
        if ctx.active_cols.size:
            best_plan, logbook, population = run_ga(ctx, generations, seed * 1000 + pass_no, carry, ga)
            plan, fitness = np.asarray(best_plan).copy(), float(best_plan.fitness.values[0])
        else:
            plan, fitness, logbook, population, generations = np.zeros_like(demand), 0.0, [], [], 0

        unmet = unmet_by_cluster(plan, ctx)
        passes.append({
            "pass": pass_no,
            "generations": generations,
            "best_fitness": round(fitness, 6),
            "unmet_by_depot": {depot_ids[c]: round(u * 100, 1) for c, u in unmet.items()},
            "upweighted_depots": [],
        })
        history += [
            {"pass": pass_no, "generation": int(rec["gen"]), "best": round(float(rec["best"]), 6), "mean": round(float(rec["mean"]), 6)}
            for rec in logbook
        ]
        if best is None or fitness > best["fitness"]:
            best = {"pass": pass_no, "fitness": fitness, "plan": plan, "ctx": ctx, "depots": depots,
                    "graph": graph, "paths": paths, "fastest": fastest, "minutes": minutes}

        lagging = [c for c, u in unmet.items() if u > feedback["unmet_threshold"]]
        if not lagging or pass_no == feedback["max_iterations"] + 1:
            break
        passes[-1]["upweighted_depots"] = [depot_ids[c] for c in lagging]
        for c in lagging:
            sample_weight[ctx.cluster_members[c]] *= feedback["upweight"]
        carry = [np.asarray(p).copy() for p in tools.selBest(population, feedback["carry_over"])]

    assert best is not None
    engine_ms = (time.perf_counter() - started) * 1000

    # Greedy baseline on the same depots and roads: highest priority first, nearest depot.
    greedy_started = time.perf_counter()
    order = sorted(range(len(zones)), key=lambda i: zones[i]["rank"])
    greedy_plan = greedy_allocation(order, demand, stock)
    nearest = [
        min(best["depots"], key=lambda d, z=z: (haversine_km(z["latitude"], z["longitude"], d["latitude"], d["longitude"]), d["id"]))["id"]
        for z in zones
    ]
    greedy_ms = (time.perf_counter() - greedy_started) * 1000

    ctx, plan, graph, paths = best["ctx"], best["plan"], best["graph"], best["paths"]
    speed = roads["speed_kmh"]
    greedy_minutes = np.array([paths[d][0][z] / speed * 60 for d, z in zip(nearest, ids)])
    engine_cov = dict(zip(np.flatnonzero(ctx.active), zone_coverage(plan, ctx))) if ctx.active.any() else {}
    greedy_cov = dict(zip(np.flatnonzero(ctx.active), zone_coverage(greedy_plan, ctx))) if ctx.active.any() else {}

    def zone_plan(i: int, row: np.ndarray, cov: dict, depot: str) -> dict[str, Any]:
        return {
            "allocated": {r: int(v) for r, v in zip(RESOURCE_TYPES, row)},
            "coverage_pct": round(float(cov[i]) * 100, 1) if i in cov else None,
            "resource_coverage_pct": {
                r: (round(min(int(v), int(n)) / int(n) * 100, 1) if n > 0 else None)
                for r, v, n in zip(RESOURCE_TYPES, row, demand[i])
            },
            **describe_route(graph, paths, depot, ids[i], speed),
        }

    zone_results = []
    for i, z in enumerate(zones):
        zone_results.append({
            "id": z["id"], "name": z["name"], "latitude": z["latitude"], "longitude": z["longitude"],
            "damage_severity": z["damage_severity"], "population": z["population"],
            "vulnerability_index": z["vulnerability_index"], "accessibility": z["accessibility"],
            "priority_score": z["priority_score"], "priority_level": z["priority_level"], "rank": z["rank"],
            "demand": {r: int(v) for r, v in zip(RESOURCE_TYPES, demand[i])},
            "engine": zone_plan(i, plan[i], engine_cov, best["fastest"][i]),
            "greedy": zone_plan(i, greedy_plan[i], greedy_cov, nearest[i]),
        })
    zone_results.sort(key=lambda z: z["rank"])

    depots_out = []
    for d in best["depots"]:
        served = [i for i, f in enumerate(best["fastest"]) if f == d["id"]]
        closest = min(zones, key=lambda z: haversine_km(z["latitude"], z["longitude"], d["latitude"], d["longitude"]))
        depots_out.append({
            **d,
            "nearest_zone": closest["name"],
            "zone_ids": [ids[i] for i in sorted(served, key=lambda i: zones[i]["rank"])],
            "allocated": {r: int(plan[served, j].sum()) for j, r in enumerate(RESOURCE_TYPES)},
            "unmet_pct": next(p["unmet_by_depot"].get(d["id"]) for p in passes if p["pass"] == best["pass"]),
        })

    return {
        "scenario_id": scenario.id,
        "scenario_name": scenario.name,
        "disaster_type": scenario.disaster_type,
        "seed": seed,
        "weights": priority_settings["weights"],
        "resources": {r: int(s) for r, s in zip(RESOURCE_TYPES, stock)},
        "depots": depots_out,
        "roads": [
            {"from": a, "to": b, "distance_km": round(e["distance_km"], 2), "travel_time_min": round(e["weight"] / speed * 60, 1)}
            for a, b, e in graph.edges(data=True)
        ],
        "zones": zone_results,
        "engine": {"metrics": plan_metrics(plan, ctx, best["minutes"], engine_ms)},
        "greedy": {"metrics": plan_metrics(greedy_plan, ctx, greedy_minutes, greedy_ms)},
        "fitness_history": history,
        "passes": passes,
        "selected_pass": best["pass"],
        "settings": {key: dict(value) for key, value in settings.items() if isinstance(value, Mapping)},
    }

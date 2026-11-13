"""ResQ Nexus API – Intelligent Disaster Response and Resource Allocation.

Pipeline: Assess -> Prioritise -> Allocate -> Explain, plus accounts (citizens,
service providers, admins), SOS requests and nearby resources.
"""
import hashlib
import json
import os
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

# Secrets (GEMINI_API_KEY, JWT_SECRET) live in backend/.env, which is git-ignored.
load_dotenv(Path(__file__).resolve().parent / ".env")

# The modules below read the environment when imported, so they come after load_dotenv.
from db.database import get_db, init_db  # noqa: E402
from db.models import SosRequest  # noqa: E402
from deps import require_admin  # noqa: E402
from routers import admin, alerts, auth, damage, jobs, provider, replay, reports, resources, scenarios_damage, sentinel, sos  # noqa: E402
from services import allocation_engine, explain, gemini_client, priority, scenarios, sos_demand  # noqa: E402
from services.sos import ACTIVE_STATUSES  # noqa: E402
from services.scenarios import Scenario, ScenarioNotFoundError, ScenarioSummary, Zone  # noqa: E402

API_VERSION = "0.3.0"

app = FastAPI(
    title="ResQ Nexus API",
    version=API_VERSION,
    description="Decision support for disaster response: Assess -> Prioritise -> Allocate -> Explain.",
)

DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", DEFAULT_CORS_ORIGINS).split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tables are created (and the demo data loaded into an empty database) on start-up.
init_db()
if os.getenv("WARM_ROAD_GRAPHS", "1") != "0":  # parse the cached OpenStreetMap graphs in the background
    threading.Thread(target=allocation_engine.warm_road_networks, name="warm-road-graphs", daemon=True).start()
app.include_router(auth.router)
app.include_router(sos.router)
app.include_router(resources.router)
app.include_router(provider.router)
app.include_router(admin.router)
app.include_router(damage.router)
app.include_router(damage.admin_incident_router)
app.include_router(scenarios_damage.router)
app.include_router(alerts.router)
app.include_router(sentinel.router)
app.include_router(replay.router)
app.include_router(jobs.router)
app.include_router(reports.router)


def _scenario_or_404(scenario_id: str) -> Scenario:
    try:
        return scenarios.get_scenario(scenario_id)
    except ScenarioNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found") from None


@app.get("/", include_in_schema=False)
def root():
    """Pointer for anyone opening the API in a browser."""
    return {
        "name": "ResQ Nexus API",
        "version": API_VERSION,
        "docs": "/docs",
        "endpoints": [
            "GET /health",
            "POST /auth/register",
            "POST /auth/register/provider",
            "POST /auth/login",
            "GET /auth/me",
            "POST /sos",
            "PATCH /sos/{id}/details",
            "GET /sos/mine",
            "GET /sos/{id}",
            "GET /resources/nearby",
            "GET /provider/resources",
            "PATCH /provider/resources/{id}",
            "GET /provider/requests",
            "POST /provider/requests/{id}/accept",
            "POST /provider/requests/{id}/status",
            "GET /admin/summary",
            "GET /admin/sos",
            "GET /admin/sos/{id}/suggestions",
            "POST /admin/sos/{id}/assign",
            "POST /admin/sos/{id}/status",
            "GET /admin/providers",
            "POST /admin/providers/{id}/approve",
            "POST /admin/providers/{id}/reject",
            "GET /admin/users",
            "PATCH /admin/users/{id}",
            "GET|POST /admin/resources",
            "PATCH|DELETE /admin/resources/{id}",
            "GET /scenarios",
            "GET /scenarios/{id}",
            "GET /scenarios/{id}/priority",
            "POST /scenarios/{id}/allocate",
            "POST /scenarios/{id}/explain",
        ],
    }


@app.get("/health")
def health():
    """Liveness check; also reports whether a Gemini key is configured."""
    return {
        "status": "ok",
        "service": "resq-nexus-api",
        "version": API_VERSION,
        "gemini_configured": gemini_client.is_configured(),
    }


@app.get("/scenarios", response_model=list[ScenarioSummary])
def list_scenarios():
    """All available disaster scenarios (summary only)."""
    return scenarios.list_scenarios()


# The Command Centre (scenario details, priority scoring, Allocation Engine, explanations) is
# admin-only; the scenario list stays public for the landing page.
ADMIN_ONLY = [Depends(require_admin)]


@app.get("/scenarios/{scenario_id}", response_model=Scenario, dependencies=ADMIN_ONLY)
def get_scenario(scenario_id: str):
    """Full scenario: metadata, available resources and every zone."""
    return _scenario_or_404(scenario_id)


class ScoredZone(Zone):
    """A zone with its priority score, level, rank and score breakdown."""

    priority_score: float
    priority_level: Literal["Critical", "High", "Medium", "Low"]
    rank: int
    factors: dict[str, float]
    contributions: dict[str, float]


class PriorityResponse(BaseModel):
    scenario_id: str
    scenario_name: str
    disaster_type: str
    settings: dict[str, Any]
    summary: dict[str, int]
    zones: list[ScoredZone]


WEIGHT_HELP = "Optional priority weight (any non-negative number; the four are rescaled to sum to 1)"


@app.get("/scenarios/{scenario_id}/priority", response_model=PriorityResponse, dependencies=ADMIN_ONLY)
def get_priority(
    scenario_id: str,
    severity: float | None = Query(None, ge=0, description=WEIGHT_HELP),
    population: float | None = Query(None, ge=0, description=WEIGHT_HELP),
    vulnerability: float | None = Query(None, ge=0, description=WEIGHT_HELP),
    accessibility: float | None = Query(None, ge=0, description=WEIGHT_HELP),
):
    """Zones ranked by priority score (highest first) with Critical / High / Medium / Low levels.

    Pass any of the four weights to re-score live (missing ones keep their default).
    """
    scenario = _scenario_or_404(scenario_id)
    custom = {
        key: value
        for key, value in {"severity": severity, "population": population,
                           "vulnerability": vulnerability, "accessibility": accessibility}.items()
        if value is not None
    }
    try:
        settings = priority.settings_with_weights(custom) if custom else priority.PRIORITY_SETTINGS
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    scored = priority.score_zones((zone.model_dump() for zone in scenario.zones), settings)
    return {
        "scenario_id": scenario.id,
        "scenario_name": scenario.name,
        "disaster_type": scenario.disaster_type,
        "settings": settings,
        "summary": priority.level_counts(scored),
        "zones": scored,
    }


# --------------------------------------------------------------------------- Allocate + Explain
class PriorityWeights(BaseModel):
    """Priority weights w1..w4; rescaled to sum to 1 before use."""

    model_config = ConfigDict(extra="forbid")

    severity: float = Field(priority.PRIORITY_SETTINGS["weights"]["severity"], ge=0)
    population: float = Field(priority.PRIORITY_SETTINGS["weights"]["population"], ge=0)
    vulnerability: float = Field(priority.PRIORITY_SETTINGS["weights"]["vulnerability"], ge=0)
    accessibility: float = Field(priority.PRIORITY_SETTINGS["weights"]["accessibility"], ge=0)

    @model_validator(mode="after")
    def _not_all_zero(self) -> "PriorityWeights":
        if self.severity + self.population + self.vulnerability + self.accessibility <= 0:
            raise ValueError("at least one weight must be greater than zero")
        return self


class AllocationRequest(BaseModel):
    """Optional body for /allocate and /explain."""

    model_config = ConfigDict(extra="forbid")

    weights: PriorityWeights | None = None
    include_sos: bool = Field(
        False,
        description="Add every active SOS request to the demand of its nearest zone (within 30 km) before the run",
    )


class AllocationResponse(BaseModel):
    scenario_id: str
    scenario_name: str
    disaster_type: str
    seed: int
    weights: dict[str, float]
    resources: dict[str, int]
    depots: list[dict[str, Any]]
    roads: list[dict[str, Any]]  # major roads of the incident box, each with its real geometry (coords)
    road_source: str = "synthetic"  # OpenStreetMap when the scenario has a cached road graph
    zones: list[dict[str, Any]]
    engine: dict[str, Any]
    greedy: dict[str, Any]
    fitness_history: list[dict[str, Any]]
    passes: list[dict[str, Any]]
    selected_pass: int
    settings: dict[str, Any]
    sos: dict[str, Any] | None = None


class Explanation(BaseModel):
    zone_id: str
    text: str
    source: Literal["gemini", "template"]


class ExplanationResponse(BaseModel):
    scenario_id: str
    source: Literal["gemini", "template", "mixed"]
    model: str | None
    notice: str | None
    explanations: list[Explanation]


# Results are deterministic, so identical requests reuse them (the Explain step
# also needs the exact plan the dashboard is showing).
_CACHE_SIZE = 32
_allocations: OrderedDict[str, dict[str, Any]] = OrderedDict()
_explanations: OrderedDict[str, dict[str, Any]] = OrderedDict()
_cache_lock = threading.Lock()


def clear_caches() -> None:
    with _cache_lock:
        _allocations.clear()
        _explanations.clear()


def _cache_key(scenario: Scenario, weights: dict[str, float] | None, sos_plan: dict[str, Any] | None) -> str:
    payload = scenario.model_dump_json() + json.dumps(weights, sort_keys=True) + json.dumps(sos_plan, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def _remember(cache: OrderedDict, key: str, value: dict[str, Any]) -> None:
    with _cache_lock:
        cache[key] = value
        cache.move_to_end(key)
        while len(cache) > _CACHE_SIZE:
            cache.popitem(last=False)


def _live_sos_plan(db: Session, scenario: Scenario) -> dict[str, Any]:
    """Active SOS requests matched to the scenario's zones, with the demand each zone gains."""
    active = db.scalars(select(SosRequest).where(SosRequest.status.in_(ACTIVE_STATUSES)).order_by(SosRequest.id))
    return sos_demand.assign_to_zones([zone.model_dump() for zone in scenario.zones], active)


def _allocation_for(
    scenario: Scenario, weights: dict[str, float] | None, sos_plan: dict[str, Any] | None = None
) -> tuple[str, dict[str, Any]]:
    key = _cache_key(scenario, weights, sos_plan)
    with _cache_lock:
        cached = _allocations.get(key)
    if cached is None:
        extra = sos_plan["extra_demand"] if sos_plan else None
        cached = allocation_engine.allocate(scenario, weights=weights, extra_demand=extra)
        added = {entry["zone_id"]: entry for entry in (sos_plan or {}).get("zones", [])}
        for zone in cached["zones"]:
            entry = added.get(zone["id"])
            zone["sos"] = {key_: entry[key_] for key_ in ("requests", "people", "demand")} if entry else None
        cached["sos"] = None if sos_plan is None else {k: v for k, v in sos_plan.items() if k != "extra_demand"}
        _remember(_allocations, key, cached)
    return key, cached


def _weights(request: AllocationRequest | None) -> dict[str, float] | None:
    return request.weights.model_dump() if request and request.weights else None


def _sos_plan(request: AllocationRequest | None, db: Session, scenario: Scenario) -> dict[str, Any] | None:
    return _live_sos_plan(db, scenario) if request and request.include_sos else None


@app.post("/scenarios/{scenario_id}/allocate", response_model=AllocationResponse, dependencies=ADMIN_ONLY)
def allocate(scenario_id: str, request: AllocationRequest | None = None, db: Session = Depends(get_db)):
    """Run the Allocation Engine and the greedy baseline.

    Returns per-zone allocations, depots, routes, travel times and coverage for
    both methods, comparison metrics and the GA fitness per generation. With
    include_sos, active SOS requests first add to the demand of their nearest zone.
    """
    scenario = _scenario_or_404(scenario_id)
    return _allocation_for(scenario, _weights(request), _sos_plan(request, db, scenario))[1]


@app.post("/scenarios/{scenario_id}/explain", response_model=ExplanationResponse, dependencies=ADMIN_ONLY)
def explain_allocation(scenario_id: str, request: AllocationRequest | None = None, db: Session = Depends(get_db)):
    """Plain-language explanation for every zone of the allocation (Gemini, or templates as a fallback)."""
    scenario = _scenario_or_404(scenario_id)
    key, result = _allocation_for(scenario, _weights(request), _sos_plan(request, db, scenario))
    with _cache_lock:
        cached = _explanations.get(key)
    if cached is not None:
        return cached
    explained = explain.explain_allocation(result, region=f"{scenario.region}, {scenario.state}")
    if explained["source"] == "gemini":  # only cache complete AI answers; templates are instant anyway
        _remember(_explanations, key, explained)
    return explained

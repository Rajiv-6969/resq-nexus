"""ResQ Nexus API – Intelligent Disaster Response and Resource Allocation.

Pipeline: Assess -> Prioritise -> Allocate -> Explain.
"""
import os
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Secrets (GEMINI_API_KEY) live in backend/.env, which is git-ignored.
load_dotenv(Path(__file__).resolve().parent / ".env")

from services import gemini_client, priority, scenarios  # noqa: E402  (needs the env loaded first)
from services.scenarios import Scenario, ScenarioNotFoundError, ScenarioSummary, Zone  # noqa: E402

API_VERSION = "0.1.0"

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
        "endpoints": ["/health", "/scenarios", "/scenarios/{id}", "/scenarios/{id}/priority"],
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


@app.get("/scenarios/{scenario_id}", response_model=Scenario)
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


@app.get("/scenarios/{scenario_id}/priority", response_model=PriorityResponse)
def get_priority(scenario_id: str):
    """Zones ranked by priority score (highest first) with Critical / High / Medium / Low levels."""
    scenario = _scenario_or_404(scenario_id)
    scored = priority.score_zones(zone.model_dump() for zone in scenario.zones)
    return {
        "scenario_id": scenario.id,
        "scenario_name": scenario.name,
        "disaster_type": scenario.disaster_type,
        "settings": priority.PRIORITY_SETTINGS,
        "summary": priority.level_counts(scored),
        "zones": scored,
    }

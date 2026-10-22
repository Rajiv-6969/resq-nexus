"""ResQ Nexus API – Intelligent Disaster Response and Resource Allocation.

Pipeline: Assess -> Prioritise -> Allocate -> Explain.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Secrets (GEMINI_API_KEY) live in backend/.env, which is git-ignored.
load_dotenv(Path(__file__).resolve().parent / ".env")

from services import gemini_client, scenarios  # noqa: E402  (needs the env loaded first)
from services.scenarios import Scenario, ScenarioNotFoundError, ScenarioSummary  # noqa: E402

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
        "endpoints": ["/health", "/scenarios", "/scenarios/{id}"],
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

"""ResQ Nexus API – Intelligent Disaster Response and Resource Allocation.

Pipeline: Assess -> Prioritise -> Allocate -> Explain.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Secrets (GEMINI_API_KEY) live in backend/.env, which is git-ignored.
load_dotenv(Path(__file__).resolve().parent / ".env")

from services import gemini_client  # noqa: E402  (needs the env loaded first)

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


@app.get("/health")
def health():
    """Liveness check; also reports whether a Gemini key is configured."""
    return {
        "status": "ok",
        "service": "resq-nexus-api",
        "version": API_VERSION,
        "gemini_configured": gemini_client.is_configured(),
    }

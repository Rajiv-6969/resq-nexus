"""Where the repository's shared folders are.

Layout (see docs/PROJECT_CONTEXT.md):

    frontend/   React + Vite client
    backend/    FastAPI API (this package)
    ml/         damage-assessment models and training scripts
    data/       scenarios, demo seed, geo caches (shared by backend and ml)
    docs/       project documentation

``RESQ_DATA_DIR`` overrides the data folder (used by the Docker image, where the
folder is copied next to the backend).
"""
from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent


def _data_dir() -> Path:
    override = os.getenv("RESQ_DATA_DIR", "").strip()
    if override:
        return Path(override).resolve()
    for candidate in (REPO_ROOT / "data", BACKEND_DIR / "data"):
        if candidate.is_dir():
            return candidate
    return REPO_ROOT / "data"


DATA_DIR = _data_dir()
SCENARIO_DIR = DATA_DIR / "scenarios"
DEMO_SEED = DATA_DIR / "demo_seed.json"

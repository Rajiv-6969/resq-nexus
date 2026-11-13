"""Evaluation results endpoint serving docs/results/results.json to the frontend."""
from __future__ import annotations

import json
from pathlib import Path
from fastapi import APIRouter, HTTPException

from paths import REPO_ROOT

router = APIRouter(prefix="/eval", tags=["evaluation"])


@router.get("/results")
def get_evaluation_results() -> dict:
    """Return the cached evaluation suite results (docs/results/results.json)."""
    results_path = REPO_ROOT / "docs" / "results" / "results.json"
    if not results_path.is_file():
        # Fall back to running or empty placeholder if not yet evaluated
        raise HTTPException(
            status_code=404,
            detail="Evaluation results have not been generated yet. Run 'python -m backend.eval.run_all'.",
        )

    try:
        data = json.loads(results_path.read_text(encoding="utf-8"))
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read evaluation results: {e}")

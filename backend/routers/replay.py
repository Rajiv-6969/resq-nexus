"""Event replay router for historical and simulated disaster progression."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from services import replay

router = APIRouter(prefix="/replay", tags=["replay"])


@router.get("/scenarios")
def list_replayable_scenarios():
    """List scenarios available for historical event replay."""
    return {"scenarios": replay.get_replayable_scenarios()}


@router.get("/{scenario_id}")
def get_scenario_timeline(scenario_id: str):
    """Retrieve full multi-frame timeline data for scenario event replay."""
    try:
        return replay.generate_event_timeline(scenario_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Scenario replay for '{scenario_id}' not found: {e}")

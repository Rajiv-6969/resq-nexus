"""Situation Reports and Decision Explanations API."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from services import explain, reports

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{scenario_id}")
def get_scenario_situation_report(
    scenario_id: str,
    lang: Literal["en", "hi"] = Query("en", description="Report language (en or hi)"),
):
    """Generate a comprehensive grounded situation report with faithfulness verification."""
    try:
        return reports.get_situation_report(scenario_id=scenario_id, lang=lang)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to generate report for '{scenario_id}': {e}")


@router.get("/{scenario_id}/zones/{zone_id}/explain")
def get_detailed_zone_explanation(
    scenario_id: str,
    zone_id: str,
    lang: Literal["en", "hi"] = Query("en", description="Explanation language (en or hi)"),
):
    """Retrieve on-demand deep contextual explanation for a zone's allocation decision."""
    try:
        return explain.explain_zone_deep(zone_id=zone_id, scenario_id=scenario_id, lang=lang)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to explain zone '{zone_id}': {e}")

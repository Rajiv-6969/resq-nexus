"""Scenario building-level damage assessments API.

Serves building-level simulated satellite assessments for scenarios:
GET /scenarios/{id}/buildings
"""
from __future__ import annotations

import gzip
import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from paths import SCENARIO_DIR
from schemas.contracts import BuildingAssessment
from services.damage.aggregate import class_counts
from services.scenarios import get_scenario

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("/{scenario_id}/buildings")
def get_scenario_buildings(scenario_id: str):
    """Retrieve simulated satellite building damage footprints for a scenario."""
    try:
        scenario = get_scenario(scenario_id)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")

    buildings_gz = SCENARIO_DIR / f"{scenario_id}.buildings.json.gz"
    if buildings_gz.is_file():
        try:
            with gzip.open(buildings_gz, "rt", encoding="utf-8") as f:
                data = json.load(f)
                return {
                    "scenario_id": scenario_id,
                    "source": "simulated",
                    "label": "Simulated satellite assessment",
                    "buildings": data.get("buildings", []),
                    "counts": data.get("counts", class_counts([
                        BuildingAssessment(**b) for b in data.get("buildings", [])
                    ])),
                }
        except Exception as e:
            logger.warning(f"Error reading {buildings_gz}: {e}")

    # Fallback: generate simulated buildings dynamically
    buildings: list[dict] = []
    import random
    rng = random.Random(hash(scenario_id) & 0xFFFFFFFF)
    for z in scenario.zones:
        count = max(8, round(z.population * 0.05))
        for i in range(count):
            cls = min(3, max(0, z.damage_severity + rng.choice((-1, 0, 0, 1))))
            b_lat = round(z.latitude + rng.uniform(-0.008, 0.008), 6)
            b_lon = round(z.longitude + rng.uniform(-0.008, 0.008), 6)
            buildings.append({
                "id": f"{z.id}-B{i+1:04d}",
                "lat": b_lat,
                "lon": b_lon,
                "damage_class": cls,
                "confidence": round(rng.uniform(0.70, 0.98), 3),
                "source": "simulated",
            })

    counts = {0: 0, 1: 0, 2: 0, 3: 0}
    for b in buildings:
        counts[b["damage_class"]] += 1

    return {
        "scenario_id": scenario_id,
        "source": "simulated",
        "label": "Simulated satellite assessment",
        "buildings": buildings,
        "counts": counts,
    }

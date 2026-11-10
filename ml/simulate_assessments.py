"""Simulated building and zone assessments from a scenario (no model yet).

    python ml/simulate_assessments.py flood-assam > assessments.json

Output: {"zones": [ZoneAssessment...], "buildings": [BuildingAssessment...]} with
source="simulated" on every record. Run from the repository root with the backend
virtual environment active (it imports backend/schemas/contracts.py).
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from schemas.contracts import BuildingAssessment, zone_assessment_from_zone  # noqa: E402
from services.scenarios import get_scenario  # noqa: E402

BUILDINGS_PER_1000 = 180  # rough households-per-thousand residents


def simulate(scenario_id: str, seed: int = 42) -> dict:
    rng = random.Random(seed)
    scenario = get_scenario(scenario_id)
    buildings: list[BuildingAssessment] = []
    zones = []
    for zone in scenario.zones:
        count = max(5, round(zone.population / 1000 * BUILDINGS_PER_1000))
        damaged = 0
        confidences = []
        for i in range(count):
            # damage spreads around the zone's class: mostly its own class, some neighbours
            cls = min(3, max(0, zone.damage_severity + rng.choice((-1, 0, 0, 0, 1))))
            conf = round(rng.uniform(0.55, 0.98), 3)
            confidences.append(conf)
            damaged += cls >= 2
            buildings.append(BuildingAssessment(
                id=f"{zone.id}-B{i + 1:04d}",
                lat=round(zone.latitude + rng.uniform(-0.01, 0.01), 6),
                lon=round(zone.longitude + rng.uniform(-0.01, 0.01), 6),
                damage_class=cls, confidence=conf, source="simulated",
            ))
        za = zone_assessment_from_zone(zone, source="simulated")
        za.building_count = count
        za.damaged_pct = round(damaged / count * 100, 1)
        za.mean_confidence = round(sum(confidences) / count, 3)
        za.low_confidence = za.mean_confidence < 0.7
        zones.append(za)
    return {
        "scenario_id": scenario.id,
        "source": "simulated",
        "zones": [z.model_dump() for z in zones],
        "buildings": [b.model_dump() for b in buildings],
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    print(json.dumps(simulate(sys.argv[1]), indent=2))

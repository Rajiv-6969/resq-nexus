"""Relief demand model: the resources a zone needs given its damage and population.

Used by the scenario generator (to size the available stock) and by the
Allocation Engine (per-zone demand), so both always agree.
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import Any

# Share of residents needing relief / displaced, indexed by damage_severity 0-3.
AFFECTED_SHARE = (0.0, 0.10, 0.35, 0.75)
DISPLACED_SHARE = (0.0, 0.02, 0.15, 0.50)
RESCUE_TEAMS_BY_SEVERITY = (0, 0, 1, 2)
VEHICLES_BY_SEVERITY = (0, 1, 2, 3)
PEOPLE_PER_MEDICAL_KIT = 25
PEOPLE_PER_SHELTER = 100


def zone_demand(damage_severity: int, population: int) -> dict[str, int]:
    """Units of each resource one zone needs.

    Rescue teams and vehicles scale with damage severity; medical kits, food
    packets and shelters scale with the number of affected / displaced people
    (population x a severity-dependent share).
    """
    affected = population * AFFECTED_SHARE[damage_severity]
    displaced = population * DISPLACED_SHARE[damage_severity]
    return {
        "rescue_teams": RESCUE_TEAMS_BY_SEVERITY[damage_severity],
        "medical_kits": math.ceil(affected / PEOPLE_PER_MEDICAL_KIT),
        "food_packets": math.ceil(affected),
        "shelters": math.ceil(displaced / PEOPLE_PER_SHELTER),
        "vehicles": VEHICLES_BY_SEVERITY[damage_severity],
    }


def estimate_need(zones: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    """Scenario-wide need (same formulas, rounded once over all zones)."""
    zones = list(zones)
    affected = sum(z["population"] * AFFECTED_SHARE[z["damage_severity"]] for z in zones)
    displaced = sum(z["population"] * DISPLACED_SHARE[z["damage_severity"]] for z in zones)
    return {
        "rescue_teams": sum(RESCUE_TEAMS_BY_SEVERITY[z["damage_severity"]] for z in zones),
        "medical_kits": math.ceil(affected / PEOPLE_PER_MEDICAL_KIT),
        "food_packets": math.ceil(affected),
        "shelters": math.ceil(displaced / PEOPLE_PER_SHELTER),
        "vehicles": sum(VEHICLES_BY_SEVERITY[z["damage_severity"]] for z in zones),
    }

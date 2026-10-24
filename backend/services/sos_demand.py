"""Live SOS requests as extra relief demand for the Allocation Engine.

Each active request (not yet RESOLVED) is matched to its nearest scenario zone. If that zone
is within SOS_ZONE_RADIUS_KM, the request's needs are added to the zone's demand before the
Allocation Engine runs, using the same units as the demand model (services/demand.py).
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Protocol

from services.demand import PEOPLE_PER_MEDICAL_KIT, PEOPLE_PER_SHELTER
from services.geo import haversine_km
from services.scenarios import RESOURCE_TYPES

SOS_ZONE_RADIUS_KM = 30  # further than this from every zone = outside the scenario's area
DEFAULT_PEOPLE = 1  # a request still waiting for its details counts as one person ...
DEFAULT_NEEDS = ("rescue",)  # ... who needs rescue


class LiveRequest(Protocol):
    id: int
    latitude: float
    longitude: float
    people_affected: int | None
    needs: list[str]


def sos_demand(people: int, needs: Iterable[str]) -> dict[str, int]:
    """Units of each resource one request adds: rescue -> 1 rescue team, medical -> medical kits
    (one per 25 people), ambulance -> 1 vehicle, food or water -> 1 food packet per person,
    shelter -> shelter units (one per 100 people)."""
    needs = set(needs)
    demand: dict[str, int] = dict.fromkeys(RESOURCE_TYPES, 0)
    if "rescue" in needs:
        demand["rescue_teams"] += 1
    if "medical" in needs:
        demand["medical_kits"] += math.ceil(people / PEOPLE_PER_MEDICAL_KIT)
    if "ambulance" in needs:
        demand["vehicles"] += 1
    if needs & {"food", "water"}:
        demand["food_packets"] += people
    if "shelter" in needs:
        demand["shelters"] += math.ceil(people / PEOPLE_PER_SHELTER)
    return demand


def assign_to_zones(
    zones: Sequence[Mapping[str, Any]],
    requests: Iterable[LiveRequest],
    radius_km: float = SOS_ZONE_RADIUS_KM,
) -> dict[str, Any]:
    """Match each request to its nearest zone and add up the extra demand per zone."""
    by_zone: dict[str, dict[str, Any]] = {}
    included = people_total = outside = 0
    for request in requests:
        nearest, distance = min(
            ((z, haversine_km(request.latitude, request.longitude, z["latitude"], z["longitude"])) for z in zones),
            key=lambda pair: (pair[1], pair[0]["id"]),
        )
        if distance > radius_km:
            outside += 1
            continue
        people = request.people_affected or DEFAULT_PEOPLE
        entry = by_zone.setdefault(nearest["id"], {
            "zone_id": nearest["id"], "zone_name": nearest["name"], "requests": [], "people": 0,
            "demand": dict.fromkeys(RESOURCE_TYPES, 0),
        })
        entry["requests"].append(request.id)
        entry["people"] += people
        for resource, units in sos_demand(people, request.needs or DEFAULT_NEEDS).items():
            entry["demand"][resource] += units
        included += 1
        people_total += people
    zones_out = sorted(by_zone.values(), key=lambda z: z["zone_id"])
    for entry in zones_out:
        entry["requests"].sort()
    return {
        "radius_km": radius_km,
        "requests_included": included,
        "people": people_total,
        "outside": outside,
        "zones": zones_out,
        "extra_demand": {z["zone_id"]: dict(z["demand"]) for z in zones_out},
    }

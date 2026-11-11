"""Resources (hospitals, ambulances, shelters, food and water points, fire stations, police posts)."""
from __future__ import annotations

from typing import Any

from db.models import Resource

# What capacity_total / capacity_available count for each type.
UNITS = {
    "HOSPITAL": "beds",
    "AMBULANCE": "ambulances",
    "SHELTER": "places",
    "FOOD": "food packets",
    "WATER": "litres",
    "FIRE_STATION": "fire engines",
    "POLICE": "patrol units",
}
LABELS = {
    "HOSPITAL": "Hospital",
    "AMBULANCE": "Ambulance",
    "SHELTER": "Shelter",
    "FOOD": "Food distribution",
    "WATER": "Water point",
    "FIRE_STATION": "Fire station",
    "POLICE": "Police station",
}


def serialize(resource: Resource, distance_km: float | None = None) -> dict[str, Any]:
    provider = resource.provider
    return {
        "id": resource.id,
        "name": resource.name,
        "resource_type": resource.resource_type,
        "type_label": LABELS[resource.resource_type],
        "latitude": resource.latitude,
        "longitude": resource.longitude,
        "area": resource.area,
        "region": resource.region,
        "contact_phone": resource.contact_phone,
        "capacity_total": resource.capacity_total,
        "capacity_available": resource.capacity_available,
        "unit": UNITS[resource.resource_type],
        "status": resource.status,
        "provider": None if provider is None else {"id": provider.id, "organisation_name": provider.organisation_name},
        "source": resource.source or "seed",
        "osm_id": resource.osm_id,
        "updated_at": resource.updated_at,
        "distance_km": None if distance_km is None else round(distance_km, 2),
    }

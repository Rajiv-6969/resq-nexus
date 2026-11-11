"""Hospitals, clinics, fire and police stations and potential shelters from OpenStreetMap.

``fetch_facilities`` queries Overpass once per bounding box (cached as JSON under
``data/geo/facilities/``); ``facilities_to_resources`` turns the result into rows for the
``resources`` table, where service providers and admins can edit them afterwards.
Names and positions are real; capacities come from OSM tags when present (``beds``,
``capacity``) and otherwise from nominal defaults, which the data notice declares.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from services.geo.osm import BBox, cached_overpass, element_point, overpass

# resource_type -> Overpass tag filter. Schools and community centres are potential shelters.
FACILITY_FILTERS: dict[str, str] = {
    "HOSPITAL": '["amenity"="hospital"]',
    "CLINIC": '["amenity"~"^(clinic|doctors)$"]',
    "FIRE_STATION": '["amenity"="fire_station"]',
    "POLICE": '["amenity"="police"]',
    "SHELTER": '["amenity"~"^(school|community_centre)$"]',
}
# Nominal capacity when OSM has no beds / capacity tag (units: see services.resources.UNITS).
DEFAULT_CAPACITY: dict[str, int] = {"HOSPITAL": 50, "CLINIC": 10, "FIRE_STATION": 2, "POLICE": 2, "SHELTER": 200}
_CAPACITY_TAGS = ("beds", "capacity", "capacity:beds")


def facilities_query(bbox: BBox) -> str:
    union = "".join(f'nwr{flt}({bbox.overpass});' for flt in FACILITY_FILTERS.values())
    return f"[out:json][timeout:120];({union});out center tags;"


AMENITY_TYPE: dict[str, str] = {
    "hospital": "HOSPITAL", "clinic": "CLINIC", "doctors": "CLINIC", "fire_station": "FIRE_STATION",
    "police": "POLICE", "school": "SHELTER", "community_centre": "SHELTER",
}


def _facility_type(tags: dict[str, Any]) -> str | None:
    return AMENITY_TYPE.get(str(tags.get("amenity", "")))


def _capacity(tags: dict[str, Any], kind: str) -> tuple[int, str]:
    for tag in _CAPACITY_TAGS:
        raw = str(tags.get(tag, "")).strip()
        if raw.isdigit() and int(raw) > 0:
            return int(raw), "osm"
    return DEFAULT_CAPACITY[kind], "default"


def parse_facilities(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Named facilities from an Overpass response (unnamed features are skipped)."""
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for element in payload.get("elements", []):
        tags = element.get("tags") or {}
        name = (tags.get("name:en") or tags.get("name") or "").strip()
        kind = _facility_type(tags)
        point = element_point(element)
        if not name or kind is None or point is None:
            continue
        ident = (element["type"], int(element["id"]))
        if ident in seen:
            continue
        seen.add(ident)
        capacity, capacity_source = _capacity(tags, kind)
        out.append({
            "osm_id": f"{element['type'][0]}{element['id']}",
            "name": name[:120],
            "resource_type": kind,
            "amenity": tags.get("amenity"),
            "latitude": round(point[0], 6),
            "longitude": round(point[1], 6),
            "area": (tags.get("addr:suburb") or tags.get("addr:city") or tags.get("addr:village") or tags.get("addr:town") or "")[:80],
            "operator": (tags.get("operator") or "")[:120],
            "capacity": capacity,
            "capacity_source": capacity_source,
        })
    out.sort(key=lambda f: (f["resource_type"], f["name"], f["osm_id"]))
    return out


def fetch_facilities(bbox: Any, cache_dir: Path | None = None, fetch: Callable[[str], dict[str, Any]] = overpass) -> list[dict[str, Any]]:
    """Facilities inside ``bbox`` (cached; the first call needs the network)."""
    bbox = BBox.from_any(bbox)
    return parse_facilities(cached_overpass("facilities", bbox.key, facilities_query(bbox), cache_dir, fetch))


# The app's resource types have no CLINIC: clinics and doctors are listed as hospitals.
RESOURCE_TYPE_OF: dict[str, str] = {"CLINIC": "HOSPITAL"}


def facilities_to_resources(facilities: list[dict[str, Any]], region: str, area_fallback: str = "") -> list[dict[str, Any]]:
    """Rows for the ``resources`` table (no provider yet; providers claim and edit them)."""
    return [
        {
            "name": f["name"],
            "resource_type": RESOURCE_TYPE_OF.get(f["resource_type"], f["resource_type"]),
            "latitude": f["latitude"],
            "longitude": f["longitude"],
            "area": f["area"] or area_fallback,
            "region": region,
            "contact_phone": None,
            "capacity_total": f["capacity"],
            "capacity_available": f["capacity"],
            "status": "OPEN",
            "source": "osm",
            "osm_id": f["osm_id"],
        }
        for f in facilities
    ]

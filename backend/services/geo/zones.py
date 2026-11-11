"""H3 hexagon zones covering an incident area.

Each hexagon (resolution 8 by default, about 0.74 km2) becomes one ``ZoneAssessment``:
real geometry, centroid, population and building count; damage ``severity``,
``vulnerability`` and ``accessibility`` come from whatever hazard model the caller supplies
and are labelled by ``source`` (``simulated`` for the Indian demo scenarios).
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import h3

from schemas.contracts import Source, ZoneAssessment
from services.geo.distance import haversine_km
from services.geo.osm import BBox

DEFAULT_RESOLUTION = 8


def hexes_in_bbox(bbox: Any, resolution: int = DEFAULT_RESOLUTION) -> list[str]:
    """H3 cells whose centre lies inside ``bbox``, sorted for determinism."""
    bbox = BBox.from_any(bbox)
    ring = [(bbox.south, bbox.west), (bbox.south, bbox.east), (bbox.north, bbox.east), (bbox.north, bbox.west)]
    return sorted(h3.polygon_to_cells(h3.LatLngPoly(ring), resolution))


def hex_polygon(cell: str) -> dict[str, Any]:
    """GeoJSON Polygon (lon, lat order) of one cell."""
    boundary = [[round(lon, 6), round(lat, 6)] for lat, lon in h3.cell_to_boundary(cell)]
    return {"type": "Polygon", "coordinates": [boundary + [boundary[0]]]}


def hex_centroid(cell: str) -> tuple[float, float]:
    lat, lon = h3.cell_to_latlng(cell)
    return round(lat, 6), round(lon, 6)


def cell_of(lat: float, lon: float, resolution: int = DEFAULT_RESOLUTION) -> str:
    return h3.latlng_to_cell(lat, lon, resolution)


def hex_area_km2(resolution: int = DEFAULT_RESOLUTION) -> float:
    return float(h3.average_hexagon_area(resolution, unit="km^2"))


def nearest_place_name(lat: float, lon: float, places: Sequence[dict[str, Any]], max_km: float = 4.0) -> str:
    """Name of the closest OSM place (town / village) within ``max_km``, else ``""``."""
    best, best_km = "", max_km
    for p in places:
        d = haversine_km(lat, lon, p["latitude"], p["longitude"])
        if d < best_km:
            best, best_km = p["name"], d
    return best


def build_zone_assessments(
    cells: Sequence[str],
    population: Sequence[int],
    building_count: Sequence[int],
    hazard: Callable[[float, float], float],
    accessibility: Callable[[float, float, float], float],
    vulnerability: Callable[[float, float, float], float],
    places: Sequence[dict[str, Any]] = (),
    source: Source = "simulated",
    min_population: int = 1,
) -> list[ZoneAssessment]:
    """One ZoneAssessment per populated cell.

    ``hazard(lat, lon)`` returns severity 0-1; ``accessibility`` and ``vulnerability`` receive
    ``(lat, lon, severity)``. Cells below ``min_population`` are dropped (water, forest, fields).
    """
    out: list[ZoneAssessment] = []
    used_names: dict[str, int] = {}
    for cell, pop, buildings in zip(cells, population, building_count):
        if pop < min_population:
            continue
        lat, lon = hex_centroid(cell)
        severity = min(1.0, max(0.0, float(hazard(lat, lon))))
        place = nearest_place_name(lat, lon, places)
        used_names[place] = used_names.get(place, 0) + 1
        name = f"{place} {used_names[place]}" if place else f"Cell {cell[-6:]}"
        out.append(ZoneAssessment(
            zone_id=cell,
            name=name,
            geometry=hex_polygon(cell),
            centroid={"lat": lat, "lon": lon},
            building_count=int(buildings),
            damaged_pct=round(severity * 100, 1),
            severity=round(severity, 3),
            population=int(pop),
            vulnerability=round(min(1.0, max(0.0, float(vulnerability(lat, lon, severity)))), 3),
            accessibility=round(min(1.0, max(0.0, float(accessibility(lat, lon, severity)))), 3),
            source=source,
        ))
    return out

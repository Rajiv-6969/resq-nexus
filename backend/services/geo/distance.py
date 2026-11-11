"""Distances on the Earth's surface and nearest-first sorting."""
from __future__ import annotations

import math
from collections.abc import Callable, Iterable
from typing import TypeVar

EARTH_RADIUS_KM = 6371.0088  # mean Earth radius (IUGG)

T = TypeVar("T")


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres (haversine formula)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(min(1.0, a)))


def bounding_box(lat: float, lon: float, radius_km: float) -> tuple[float, float, float, float]:
    """Latitude/longitude limits that contain every point within radius_km (a cheap pre-filter)."""
    dlat = math.degrees(radius_km / EARTH_RADIUS_KM)
    cos_lat = max(math.cos(math.radians(lat)), 1e-6)
    dlon = min(180.0, math.degrees(radius_km / (EARTH_RADIUS_KM * cos_lat)))
    return lat - dlat, lat + dlat, lon - dlon, lon + dlon


def sort_by_distance(
    items: Iterable[T],
    lat: float,
    lon: float,
    key: Callable[[T], tuple[float, float]],
    name: Callable[[T], str] = lambda _item: "",
    radius_km: float | None = None,
) -> list[tuple[T, float]]:
    """(item, distance_km) pairs, nearest first (ties by name), optionally only within radius_km."""
    ranked = []
    for item in items:
        distance = haversine_km(lat, lon, *key(item))
        if radius_km is None or distance <= radius_km:
            ranked.append((item, distance))
    ranked.sort(key=lambda pair: (pair[1], name(pair[0])))
    return ranked

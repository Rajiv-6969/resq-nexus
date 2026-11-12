"""Bounding boxes and the Overpass API (OpenStreetMap) with on-disk JSON caching."""
from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import requests

from paths import DATA_DIR

GEO_DIR = DATA_DIR / "geo"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_TIMEOUT_S = 180
OVERPASS_MIRRORS = (OVERPASS_URL, "https://maps.mail.ru/osm/tools/overpass/api/interpreter", "https://lz4.overpass-api.de/api/interpreter")  # global mirrors only (osm.ch etc. are regional)


class BBox(tuple):
    """``(south, west, north, east)`` in decimal degrees."""

    __slots__ = ()

    def __new__(cls, south: float, west: float, north: float, east: float) -> "BBox":
        if not (south < north and west < east):
            raise ValueError("bbox must satisfy south < north and west < east")
        return super().__new__(cls, (float(south), float(west), float(north), float(east)))

    south = property(lambda self: self[0])
    west = property(lambda self: self[1])
    north = property(lambda self: self[2])
    east = property(lambda self: self[3])

    @classmethod
    def from_any(cls, value: Any) -> "BBox":
        if isinstance(value, BBox):
            return value
        if isinstance(value, dict):
            return cls(value["south"], value["west"], value["north"], value["east"])
        return cls(*value)

    def to_dict(self) -> dict[str, float]:
        return {"south": self.south, "west": self.west, "north": self.north, "east": self.east}

    @property
    def key(self) -> str:
        """Stable file-name-safe key, e.g. ``10.000_76.250_10.200_76.450``."""
        return "_".join(f"{v:.3f}" for v in self)

    @property
    def overpass(self) -> str:
        return f"{self.south},{self.west},{self.north},{self.east}"

    def contains(self, lat: float, lon: float) -> bool:
        return self.south <= lat <= self.north and self.west <= lon <= self.east


def cache_file(kind: str, name: str, cache_dir: Path | None = None) -> Path:
    return (cache_dir or GEO_DIR) / kind / f"{name}.json"


def read_cache(path: Path) -> Any | None:
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def write_cache(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def overpass(query: str, url: str = OVERPASS_URL, timeout: float = OVERPASS_TIMEOUT_S, attempts: int = 3) -> dict[str, Any]:
    """POST one Overpass QL query and return the decoded JSON (network; retries over the mirrors)."""
    urls = [url] + [m for m in OVERPASS_MIRRORS if m != url]
    last: Exception | None = None
    for attempt in range(attempts):
        for target in urls:
            try:
                response = requests.post(target, data={"data": query}, timeout=timeout,
                                         headers={"User-Agent": "ResQ-Nexus/1.0 (student prototype)"})
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError) as exc:  # timeout, 429/504, truncated JSON
                last = exc
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Overpass failed after {attempts} attempts: {last}") from last


def cached_overpass(kind: str, name: str, query: str, cache_dir: Path | None = None,
                    fetch: Callable[[str], dict[str, Any]] = overpass) -> dict[str, Any]:
    """Overpass result for ``query`` from ``data/geo/<kind>/<name>.json``, fetching it once if missing."""
    digest = hashlib.sha1(query.encode("utf-8")).hexdigest()[:8]
    path = cache_file(kind, f"{name}-{digest}", cache_dir)
    cached = read_cache(path)
    if cached is not None:
        return cached
    payload = fetch(query)
    write_cache(path, payload)
    return payload


def element_point(element: dict[str, Any]) -> tuple[float, float] | None:
    """(lat, lon) of a node, or the ``center`` of a way / relation returned with ``out center``."""
    if "lat" in element and "lon" in element:
        return float(element["lat"]), float(element["lon"])
    centre = element.get("center")
    if centre:
        return float(centre["lat"]), float(centre["lon"])
    return None

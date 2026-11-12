"""Build a demo scenario on real Indian geography.

    python scripts/build_scenario.py --list
    python scripts/build_scenario.py flood-aluva            # needs the network the first time
    python scripts/build_scenario.py --all --force

Run from ``backend/``. For the chosen preset the script

1. downloads the OpenStreetMap road network for the incident bounding box with OSMnx and
   caches it as GraphML (``data/geo/roads/``);
2. fetches hospitals, clinics, fire and police stations and potential shelters (schools,
   community centres) from Overpass (``data/geo/facilities/``);
3. covers the box with H3 hexagons and reads each one's population from the WorldPop raster
   (``scripts/download_worldpop.py``) or, when it is absent, from OSM building counts;
4. fetches the real hazard geometry (river, coastline) and **simulates** damage severity,
   accessibility and vulnerability on top of it - every zone carries ``source="simulated"``;
5. writes ``data/scenarios/<id>.json`` (zones, facilities, relief stock, sources).

Everything fetched is cached under ``data/geo/`` so later runs and the API work offline.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paths import SCENARIO_DIR  # noqa: E402
from services.geo.distance import haversine_km  # noqa: E402
from services.geo.facilities import fetch_facilities  # noqa: E402
from services.geo.osm import BBox, cached_overpass, element_point, overpass  # noqa: E402
from services.geo.population import estimate_population  # noqa: E402
from services.geo.roads import download_graph, load_road_graph  # noqa: E402
from services.geo.zones import DEFAULT_RESOLUTION, build_zone_assessments, hex_area_km2, hex_polygon, hexes_in_bbox  # noqa: E402

DAMAGE_NOTE = (
    "Roads, facilities and population are real (OpenStreetMap, WorldPop or OSM building counts). "
    "Damage severity, accessibility, vulnerability and relief stock are SIMULATED for the demo and "
    "do not describe a real event; every zone carries source=\"simulated\"."
)

# fmt: off
PRESETS: dict[str, dict[str, Any]] = {
    "flood-aluva": {
        "name": "Periyar floods – Aluva, Ernakulam",
        "disaster_type": "flood", "state": "Kerala", "region": "Aluva and Ernakulam, Ernakulam district",
        "bbox": {"south": 10.02, "west": 76.27, "north": 10.15, "east": 76.40},
        "description": "Hypothetical monsoon flood on the Periyar at Aluva, in the pattern of August 2018. "
                       "Inundation is simulated from distance to the real river channel (decay 2.2 km).",
        "hazard": {"model": "river-distance", "feature": 'way["waterway"="river"]["name"~"Periyar|Chalakudy"]', "extent_km": 2.2, "peak": 0.95},
        "seed": 18,
    },
    "flood-bengaluru": {
        "name": "Urban floods – Bellandur and Mahadevapura, Bengaluru",
        "disaster_type": "flood", "state": "Karnataka", "region": "Bellandur, Mahadevapura and Varthur, Bengaluru Urban district",
        "bbox": {"south": 12.89, "west": 77.60, "north": 13.01, "east": 77.76},
        "description": "Hypothetical urban flood in the pattern of September 2022, when Bellandur and Varthur lakes overflowed "
                       "into the IT corridor. Inundation is simulated from distance to the real lakes and storm-water drains (decay 0.9 km).",
        "hazard": {"model": "lake-drain-distance", "extent_km": 0.9, "peak": 0.95,
                   "feature": ['nwr["natural"="water"]["water"!="pond"]', 'way["waterway"~"^(drain|canal|stream|ditch)$"]']},
        "seed": 22,
    },
    "cyclone-visakhapatnam": {
        "name": "Bay of Bengal cyclone – Visakhapatnam",
        "disaster_type": "cyclone", "state": "Andhra Pradesh", "region": "Visakhapatnam city and coast, Visakhapatnam district",
        "bbox": {"south": 17.68, "west": 83.20, "north": 17.80, "east": 83.36},
        "description": "Hypothetical very severe cyclonic storm making landfall at Visakhapatnam, in the pattern of Hudhud (October 2014). "
                       "Wind and surge damage is simulated from distance to the real coastline (decay 4.5 km).",
        "hazard": {"model": "coast-distance", "feature": 'way["natural"="coastline"]', "extent_km": 4.5, "peak": 0.95},
        "seed": 14,
    },
    "earthquake-coimbatore": {
        "name": "Coimbatore earthquake",
        "disaster_type": "earthquake", "state": "Tamil Nadu", "region": "Coimbatore city, Coimbatore district",
        "bbox": {"south": 10.92, "west": 76.89, "north": 11.06, "east": 77.02},
        "description": "Hypothetical M6.0 earthquake under the city, in the pattern of the 8 February 1900 Coimbatore earthquake. "
                       "Shaking is simulated from distance to the epicentre (decay 7 km).",
        "hazard": {"model": "epicentre", "epicentre": [10.975, 76.945], "magnitude": 6.0, "extent_km": 7.0, "peak": 0.9},
        "seed": 9,
    },
}
# fmt: on

SCARCITY = 0.6  # the demo keeps stock short of demand so the Allocation Engine has to choose


# --------------------------------------------------------------------------- simulated hazard
def hazard_points(preset: dict[str, Any], bbox: BBox, cache_dir: Path | None, fetch: Callable[[str], dict[str, Any]]) -> list[tuple[float, float]]:
    """Vertices of the real hazard feature (river / coastline) inside the box, from Overpass (cached)."""
    hazard = preset["hazard"]
    if hazard["model"] == "epicentre":
        return [tuple(hazard["epicentre"])]
    features = hazard["feature"] if isinstance(hazard["feature"], list) else [hazard["feature"]]
    union = "".join(f"{f}({bbox.overpass});" for f in features)
    query = f"[out:json][timeout:120];({union});out geom;"
    payload = cached_overpass("hazard", f"{preset['disaster_type']}-{bbox.key}", query, cache_dir, fetch)
    points: list[tuple[float, float]] = []
    for element in payload.get("elements", []):
        for node in element.get("geometry") or []:
            points.append((float(node["lat"]), float(node["lon"])))
        for member in element.get("members") or []:  # multipolygon lakes: outline of every member way
            for node in member.get("geometry") or []:
                points.append((float(node["lat"]), float(node["lon"])))
        if not element.get("geometry") and not element.get("members"):
            point = element_point(element)
            if point:
                points.append(point)
    if not points:
        raise ValueError(f"no hazard geometry found for {preset['disaster_type']} in {bbox.key}")
    return points


def _noise(key: str, seed: int) -> float:
    """Deterministic value in [-1, 1) from a cell id and the preset seed."""
    digest = hashlib.sha1(f"{seed}:{key}".encode()).digest()
    return int.from_bytes(digest[:4], "big") / 2**31 - 1.0


def make_hazard(preset: dict[str, Any], points: list[tuple[float, float]]) -> Callable[[float, float], float]:
    extent, peak, seed = float(preset["hazard"]["extent_km"]), float(preset["hazard"]["peak"]), int(preset["seed"])

    def severity(lat: float, lon: float) -> float:
        d = min(haversine_km(lat, lon, p[0], p[1]) for p in points)
        base = peak * math.exp(-d / extent)
        return max(0.0, min(1.0, base + 0.12 * _noise(f"sev:{lat:.5f}:{lon:.5f}", seed)))

    return severity


def make_accessibility(preset: dict[str, Any]) -> Callable[[float, float, float], float]:
    seed, kind = int(preset["seed"]), preset["disaster_type"]
    cut = {"flood": 0.8, "earthquake": 0.6, "cyclone": 0.5}.get(kind, 0.6)

    def accessibility(lat: float, lon: float, severity: float) -> float:
        return 1.0 - cut * severity + 0.1 * _noise(f"acc:{lat:.5f}:{lon:.5f}", seed)

    return accessibility


def make_vulnerability(preset: dict[str, Any], density_by_cell: dict[tuple[float, float], float]) -> Callable[[float, float, float], float]:
    seed = int(preset["seed"])
    top = max(density_by_cell.values(), default=1.0) or 1.0

    def vulnerability(lat: float, lon: float, severity: float) -> float:
        density = density_by_cell.get((lat, lon), 0.0) / top
        return 0.25 + 0.35 * math.sqrt(density) + 0.25 * severity + 0.08 * _noise(f"vul:{lat:.5f}:{lon:.5f}", seed)

    return vulnerability


# --------------------------------------------------------------------------- relief stock
def relief_stock(zones: list[dict[str, Any]], scarcity: float = SCARCITY) -> dict[str, int]:
    """Stock short of the simulated demand (same proportions as the old generator)."""
    affected = [z for z in zones if z["damage_severity"] > 0]
    people = sum(z["population"] * z["damage_severity"] / 3 for z in affected)
    return {
        "rescue_teams": max(4, int(round(len(affected) / 5 * scarcity))),
        "medical_kits": int(round(people * 0.06 * scarcity / 10) * 10),
        "food_packets": int(round(people * 1.5 * scarcity / 100) * 100),
        "shelters": int(round(people / 300 * scarcity)),
        "vehicles": max(6, int(round(len(affected) / 3 * scarcity))),
    }


# --------------------------------------------------------------------------- build
def build(
    scenario_id: str,
    preset: dict[str, Any] | None = None,
    resolution: int = DEFAULT_RESOLUTION,
    cache_dir: Path | None = None,
    worldpop_dir: Path | None = None,
    fetch: Callable[[str], dict[str, Any]] = overpass,
    downloader: Callable[[BBox], Any] = download_graph,
    log: Callable[[str], None] = print,
) -> dict[str, Any]:
    """The scenario document for ``scenario_id`` (network only for what is not cached)."""
    preset = preset or PRESETS[scenario_id]
    bbox = BBox.from_any(preset["bbox"])

    network_type, retain_all = preset.get("network_type", "drive"), bool(preset.get("retain_all", False))
    if downloader is download_graph:
        downloader = lambda b: download_graph(b, network_type, retain_all)  # noqa: E731
    graph = load_road_graph(bbox, cache_dir, download=True, downloader=downloader)
    log(f"roads: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")

    facilities = fetch_facilities(bbox, cache_dir, fetch)
    log(f"facilities: {len(facilities)}")

    cells = hexes_in_bbox(bbox, resolution)
    polygons = [hex_polygon(c) for c in cells]
    population, population_source = estimate_population(polygons, bbox, cache_dir, worldpop_dir, fetch=fetch)
    buildings = [0] * len(cells)
    if "building" in population_source:
        from services.geo.population import PERSONS_PER_BUILDING
        buildings = [int(round(p / PERSONS_PER_BUILDING)) for p in population]
    log(f"zones: {len(cells)} hexagons (resolution {resolution}), population {sum(population)} - {population_source}")

    places = fetch_places(bbox, cache_dir, fetch)
    points = hazard_points(preset, bbox, cache_dir, fetch)
    area = hex_area_km2(resolution)
    from services.geo.zones import hex_centroid
    density = {hex_centroid(c): p / area for c, p in zip(cells, population)}
    assessments = build_zone_assessments(
        cells, population, buildings, make_hazard(preset, points), make_accessibility(preset),
        make_vulnerability(preset, density), places, source="simulated", min_population=25,
    )
    zones = [
        {
            **a.to_zone_dict(preset["disaster_type"]),
            "h3_index": a.zone_id,
            "geometry": a.geometry,
            "building_count": a.building_count,
            "source": a.source,
        }
        for a in assessments
    ]
    log(f"populated zones: {len(zones)}")

    return {
        "id": scenario_id,
        "name": preset["name"],
        "disaster_type": preset["disaster_type"],
        "region": preset["region"],
        "state": preset["state"],
        "description": preset["description"],
        "synthetic": True,
        "data_note": DAMAGE_NOTE,
        "hazard": dict(preset["hazard"]),
        "bbox": bbox.to_dict(),
        "geo": {"h3_resolution": resolution, "road_graph": bbox.key, "network_type": network_type,
                "road_nodes": graph.number_of_nodes(), "road_edges": graph.number_of_edges()},
        "sources": {
            "roads": "OpenStreetMap via OSMnx (ODbL)",
            "facilities": "OpenStreetMap via Overpass (ODbL)",
            "population": population_source,
            "damage": "simulated",
        },
        "generator": {"script": "scripts/build_scenario.py", "seed": preset["seed"], "scarcity": SCARCITY},
        "resources": relief_stock(zones),
        "facilities": facilities,
        "zones": zones,
    }


def fetch_places(bbox: BBox, cache_dir: Path | None, fetch: Callable[[str], dict[str, Any]]) -> list[dict[str, Any]]:
    """Named towns, suburbs and villages inside the box, used to name the hexagons."""
    query = f'[out:json][timeout:120];(node["place"~"^(city|town|suburb|village|neighbourhood|hamlet)$"]["name"]({bbox.overpass}););out;'
    payload = cached_overpass("places", bbox.key, query, cache_dir, fetch)
    out = []
    for element in payload.get("elements", []):
        tags, point = element.get("tags") or {}, element_point(element)
        name = (tags.get("name:en") or tags.get("name") or "").strip()
        if name and point:
            out.append({"name": name[:60], "latitude": point[0], "longitude": point[1], "place": tags.get("place")})
    return out


def write_scenario(document: dict[str, Any], directory: Path = SCENARIO_DIR, force: bool = False) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{document['id']}.json"
    if path.exists() and not force:
        raise FileExistsError(f"{path} exists; use --force to overwrite")
    path.write_text(json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a demo scenario on real Indian geography (OpenStreetMap, WorldPop).")
    parser.add_argument("ids", nargs="*", help="preset ids (see --list)")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--resolution", type=int, default=DEFAULT_RESOLUTION, help="H3 resolution (default 8)")
    parser.add_argument("--force", action="store_true", help="overwrite an existing scenario file")
    args = parser.parse_args(argv)
    if args.list:
        for key, preset in PRESETS.items():
            print(f"{key:24} {preset['disaster_type']:11} {preset['name']}")
        return 0
    ids = list(PRESETS) if args.all else args.ids
    if not ids:
        parser.error("give preset ids or --all")
    for scenario_id in ids:
        print(f"== {scenario_id}")
        document = build(scenario_id, resolution=args.resolution)
        print(f"wrote {write_scenario(document, force=args.force)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

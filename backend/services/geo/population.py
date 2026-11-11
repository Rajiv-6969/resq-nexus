"""Population per zone: WorldPop 1 km raster, or an estimate from OSM building counts.

The WorldPop GeoTIFF for India (``ind_ppp_2020_1km_Aggregated.tif``, about 30 MB) is not
committed; ``backend/scripts/download_worldpop.py`` fetches it to ``data/geo/worldpop/``.
When the file is absent, ``estimate_population`` counts OSM buildings in each hexagon
through Overpass and multiplies by an average household size.
"""
from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from services.geo.osm import GEO_DIR, BBox, cached_overpass, overpass

WORLDPOP_FILE = "ind_ppp_2020_1km_Aggregated.tif"
WORLDPOP_URL = f"https://data.worldpop.org/GIS/Population/Global_2000_2020_1km/2020/IND/{WORLDPOP_FILE}"
WORLDPOP_DIR = GEO_DIR / "worldpop"
PERSONS_PER_BUILDING = 4.4  # Census of India 2011 mean household size, rounded
BATCH = 40  # hexagons per Overpass request in the building-count fallback


def worldpop_path(directory: Path | None = None) -> Path:
    return (directory or WORLDPOP_DIR) / WORLDPOP_FILE


def worldpop_available(directory: Path | None = None) -> bool:
    return worldpop_path(directory).is_file()


def population_from_raster(polygons: Sequence[dict[str, Any]], path: Path | None = None) -> list[int]:
    """People inside each GeoJSON polygon, area-weighting the 1 km WorldPop pixels it touches."""
    import rasterio  # optional dependency, only needed with the raster present
    from rasterio.windows import Window
    from shapely.geometry import box, shape

    path = path or worldpop_path()
    out: list[int] = []
    with rasterio.open(path) as src:
        nodata = src.nodata
        for polygon in polygons:
            geom = shape(polygon)
            minx, miny, maxx, maxy = geom.bounds
            row0, col0 = src.index(minx, maxy)  # pixel holding the top-left corner
            row1, col1 = src.index(maxx, miny)  # pixel holding the bottom-right corner
            col0, row0 = max(col0, 0), max(row0, 0)
            col1, row1 = min(col1, src.width - 1), min(row1, src.height - 1)
            if col1 < col0 or row1 < row0:
                out.append(0)
                continue
            window = Window(col0, row0, col1 - col0 + 1, row1 - row0 + 1)
            data = src.read(1, window=window)
            transform = src.window_transform(window)
            total = 0.0
            for row in range(data.shape[0]):
                for col in range(data.shape[1]):
                    value = float(data[row, col])
                    if (nodata is not None and value == nodata) or not math.isfinite(value) or value <= 0:
                        continue
                    x0, y0 = transform * (col, row)
                    x1, y1 = transform * (col + 1, row + 1)
                    pixel = box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
                    share = geom.intersection(pixel).area / pixel.area
                    total += value * share
            out.append(int(round(total)))
    return out


def _poly_filter(polygon: dict[str, Any]) -> str:
    ring = polygon["coordinates"][0]
    return " ".join(f"{lat:.5f} {lon:.5f}" for lon, lat in ring)


def building_counts(polygons: Sequence[dict[str, Any]], cache_name: str, cache_dir: Path | None = None,
                    fetch: Callable[[str], dict[str, Any]] = overpass) -> list[int]:
    """Number of OSM buildings inside each polygon (one Overpass count per polygon, batched and cached)."""
    counts: list[int] = []
    for start in range(0, len(polygons), BATCH):
        chunk = polygons[start:start + BATCH]
        body = "".join(f'way["building"](poly:"{_poly_filter(p)}");out count;' for p in chunk)
        payload = cached_overpass("buildings", f"{cache_name}-{start:04d}", f"[out:json][timeout:180];{body}", cache_dir, fetch)
        found = [int(e["tags"]["total"]) for e in payload.get("elements", []) if e.get("type") == "count"]
        if len(found) != len(chunk):
            raise ValueError(f"Overpass returned {len(found)} counts for {len(chunk)} polygons")
        counts.extend(found)
    return counts


def population_from_buildings(counts: Sequence[int], persons_per_building: float = PERSONS_PER_BUILDING) -> list[int]:
    return [int(round(c * persons_per_building)) for c in counts]


def estimate_population(polygons: Sequence[dict[str, Any]], bbox: BBox, cache_dir: Path | None = None,
                        worldpop_dir: Path | None = None, counts: Sequence[int] | None = None,
                        fetch: Callable[[str], dict[str, Any]] = overpass) -> tuple[list[int], str]:
    """``(population per polygon, source)``: WorldPop when the raster is present, else OSM building counts."""
    if worldpop_available(worldpop_dir):
        return population_from_raster(polygons, worldpop_path(worldpop_dir)), "WorldPop 2020 (1 km, constrained to zone area)"
    if counts is None:
        counts = building_counts(polygons, bbox.key, cache_dir, fetch)
    return population_from_buildings(counts), f"OSM building count x {PERSONS_PER_BUILDING} persons (WorldPop raster absent)"

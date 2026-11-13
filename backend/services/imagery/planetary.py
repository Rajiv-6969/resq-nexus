"""Microsoft Planetary Computer ``sentinel-1-rtc``: STAC search, SAS signing and windowed reads.

Network only through these functions, each with timeouts and retries; never called at app
start-up. Reads use GDAL's /vsicurl on the Cloud-Optimized GeoTIFFs and pull only the window
covering the requested box, warped onto a caller-defined EPSG:4326 grid (whole scenes are never
downloaded).
"""
from __future__ import annotations

import logging
import time
from typing import Any

import numpy as np
import requests

logger = logging.getLogger(__name__)

STAC_SEARCH = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
SAS_TOKEN = "https://planetarycomputer.microsoft.com/api/sas/v1/token/sentinel-1-rtc"
COLLECTION = "sentinel-1-rtc"
UA = {"User-Agent": "ResQ-Nexus/1.0 (student disaster-response prototype)"}
PIXEL_DEG = 8.983152841195215e-05  # 10 m at the equator, the Sen1Floods11 chip grid
GDAL_ENV = {
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif,.tiff",
    "GDAL_HTTP_TIMEOUT": "60",
    "GDAL_HTTP_MAX_RETRY": "4",
    "GDAL_HTTP_RETRY_DELAY": "2",
    "VSI_CACHE": "TRUE",
}

_token: tuple[str, float] | None = None


class ImageryError(RuntimeError):
    """Planetary Computer could not be reached or returned nothing usable."""


def _retry(fn, attempts: int = 3, delay: float = 2.0):
    last: Exception | None = None
    for i in range(attempts):
        try:
            return fn()
        except (requests.RequestException, ValueError, OSError) as exc:
            last = exc
            time.sleep(delay * (i + 1))
    raise ImageryError(f"{type(last).__name__}: {last}") from last


def search(bbox: dict[str, float], start: str, end: str, limit: int = 50, timeout: float = 30.0) -> list[dict[str, Any]]:
    """STAC items intersecting ``bbox`` acquired between ``start`` and ``end`` (ISO dates), oldest first."""
    body = {"collections": [COLLECTION], "bbox": [bbox["west"], bbox["south"], bbox["east"], bbox["north"]],
            "datetime": f"{start}/{end}", "limit": limit}

    def call():
        r = requests.post(STAC_SEARCH, json=body, timeout=timeout, headers=UA)
        r.raise_for_status()
        return r.json().get("features", [])

    items = _retry(call)
    return sorted(items, key=lambda f: f["properties"]["datetime"])


def token(timeout: float = 20.0) -> str:
    """Anonymous SAS token for the collection's blob container (cached until shortly before expiry)."""
    global _token
    if _token and _token[1] > time.time() + 120:
        return _token[0]

    def call():
        r = requests.get(SAS_TOKEN, timeout=timeout, headers=UA)
        r.raise_for_status()
        return r.json()

    data = _retry(call)
    from datetime import datetime

    expiry = datetime.fromisoformat(data["msft:expiry"].replace("Z", "+00:00")).timestamp()
    _token = (data["token"], expiry)
    return _token[0]


def signed_href(item: dict[str, Any], asset: str) -> str:
    return f"{item['assets'][asset]['href']}?{token()}"


def grid(bbox: dict[str, float], pixel_deg: float = PIXEL_DEG) -> tuple[Any, int, int]:
    """(affine transform, width, height) of an EPSG:4326 grid covering ``bbox``."""
    from rasterio.transform import from_origin

    width = max(1, int(round((bbox["east"] - bbox["west"]) / pixel_deg)))
    height = max(1, int(round((bbox["north"] - bbox["south"]) / pixel_deg)))
    return from_origin(bbox["west"], bbox["north"], pixel_deg, pixel_deg), width, height


def read_window(href: str, transform: Any, width: int, height: int) -> np.ndarray:
    """One band warped onto the target EPSG:4326 grid (NaN outside the scene / nodata)."""
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.vrt import WarpedVRT

    def call():
        with rasterio.Env(**GDAL_ENV), rasterio.open(href) as src, WarpedVRT(
            src, crs="EPSG:4326", transform=transform, width=width, height=height,
            resampling=Resampling.bilinear, src_nodata=src.nodata, nodata=np.nan, dtype="float32",
        ) as vrt:
            return vrt.read(1)

    return _retry(call)


def read_mosaic(items: list[dict[str, Any]], transform: Any, width: int, height: int) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """VV and VH linear gamma0 for the grid, first valid pixel across ``items`` (same pass)."""
    vv = np.full((height, width), np.nan, dtype=np.float32)
    vh = np.full((height, width), np.nan, dtype=np.float32)
    used: list[str] = []
    for item in items:
        if np.isfinite(vv).all():
            break
        if "vv" not in item["assets"] or "vh" not in item["assets"]:
            continue
        a = read_window(signed_href(item, "vv"), transform, width, height)
        if not np.isfinite(a).any() or not (a > 0).any():
            continue
        b = read_window(signed_href(item, "vh"), transform, width, height)
        fill = ~np.isfinite(vv) & np.isfinite(a) & (a > 0)
        vv[fill], vh[fill] = a[fill], b[fill]
        used.append(item["id"])
    if not used:
        raise ImageryError("no Sentinel-1 RTC scene covers the requested area")
    return vv, vh, used


def pass_groups(items: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Group items of the same satellite pass (same date, orbit, relative orbit) for mosaicking."""
    groups: dict[tuple, list[dict[str, Any]]] = {}
    for it in items:
        p = it["properties"]
        key = (p["datetime"][:10], p.get("sat:orbit_state"), p.get("sat:relative_orbit"), p.get("platform"))
        groups.setdefault(key, []).append(it)
    return list(groups.values())

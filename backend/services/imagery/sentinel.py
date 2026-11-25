"""Copernicus Sentinel-1 RTC flood mapping (Microsoft Planetary Computer ``sentinel-1-rtc``).

Paths, in order:

1. **Replay cache** - ``data/replays/<scenario>.flood.json``: flood extents computed offline by
   ``python backend/scripts/build_flood_replays.py`` from the real acquisition nearest the event
   (committed, so the app needs no network to show them).
2. **Live mapping** - given a box and an event date: STAC search, the acquisition nearest the date,
   a windowed read of only the needed part of the VV/VH Cloud-Optimized GeoTIFFs (10 m EPSG:4326
   grid), ``resq_flood.onnx`` in 512 x 512 tiles (or the VV < -16 dB threshold when the model is
   absent), then per-zone ``flooded_pct``. A pre-event reference acquisition (20-60 days earlier)
   separates new flood water from permanent water. Results are cached per box/date.
3. **Scenario estimate** - no cache and no date: an estimate from the scenario's simulated damage,
   labelled ``status="estimate"`` / ``source="scenario-estimate"`` so it is never mistaken for imagery.

Network only in path 2 (timeouts + retries in ``services.imagery.planetary``); never at start-up.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import time
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

from paths import DATA_DIR
from services.imagery import flood_model as fm
from services.imagery import planetary as pc
from services.scenarios import get_scenario

logger = logging.getLogger(__name__)

CACHE_DIR = DATA_DIR / "assets" / "cache" / "sentinel"
REPLAY_DIR = DATA_DIR / "replays"
FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures" / "stac"
FLOOD_ONNX_CANDIDATE_PATHS = list(fm.MODEL_CANDIDATES)
FLOOD_UNET_ONNX_PATH = FLOOD_ONNX_CANDIDATE_PATHS[0]
SEARCH_WINDOW_DAYS = 7
REFERENCE_WINDOW_DAYS = (20, 60)  # reference (pre-event) acquisition: 20-60 days before the event
FULL_SEVERITY_FLOODED = 0.5  # half a zone under new water = severity 1

# Replay presets: real events re-mapped from Sentinel-1 by scripts/build_flood_replays.py.
REPLAY_PRESETS: dict[str, dict[str, Any]] = {
    "flood-vijayawada": {"event": "Vijayawada floods (Budameru breach)", "event_dates": ["2024-09-01", "2024-09-03"], "date": "2024-09-01"},
    "flood-aluva": {"event": "Kerala floods (Aluva, Periyar)", "event_dates": ["2018-08-15", "2018-08-17"], "date": "2018-08-16"},
}


def find_flood_model_path() -> Path | None:
    return fm.find_model()


def is_flood_model_available() -> bool:
    return fm.is_available()


def offline() -> bool:
    return os.getenv("OFFLINE_MODE", "0") == "1"


# --------------------------------------------------------------------------- STAC search
def search_sentinel_scenes(bbox: dict[str, float], start_date: str | None = None, end_date: str | None = None,
                           limit: int = 5) -> list[dict[str, Any]]:
    """Sentinel-1 RTC scenes (offline fixture when OFFLINE_MODE=1 or Planetary Computer fails)."""
    if offline():
        return _load_fixture_scenes()
    start = start_date or (date.today() - timedelta(days=30)).isoformat()
    end = end_date or date.today().isoformat()
    try:
        return pc.search(bbox, start, end, limit=limit)[-limit:]
    except pc.ImageryError as exc:
        logger.info("Planetary Computer STAC search failed, using fixture: %s", exc)
        return _load_fixture_scenes()


def _load_fixture_scenes() -> list[dict[str, Any]]:
    path = FIXTURES_DIR / "sentinel1_stac.json"
    return json.loads(path.read_text(encoding="utf-8")).get("features", []) if path.is_file() else []


# --------------------------------------------------------------------------- zones
def _zone_polygon(zone: dict[str, Any]) -> dict[str, Any] | None:
    if zone.get("geometry"):
        return zone["geometry"]
    if zone.get("h3_index"):
        from services.geo.zones import hex_polygon

        return hex_polygon(zone["h3_index"])
    return None


def zone_fractions(masks: dict[str, np.ndarray], valid: np.ndarray, transform: Any, zones: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per zone: share of valid pixels in each mask (0-1) and the valid-pixel coverage."""
    from rasterio.features import geometry_mask

    out = []
    for z in zones:
        poly = _zone_polygon(z)
        if poly is None:
            continue
        inside = ~geometry_mask([poly], out_shape=valid.shape, transform=transform, all_touched=False)
        n_in, n_valid = int(inside.sum()), int((inside & valid).sum())
        row = {"zone_id": z["id"], "name": z.get("name", z["id"]), "latitude": z["latitude"], "longitude": z["longitude"],
               "population": z.get("population", 0), "geometry": poly, "pixels": n_in,
               "valid_coverage": round(n_valid / n_in, 3) if n_in else 0.0}
        for key, mask in masks.items():
            row[key] = round(float((mask & inside & valid).sum()) / n_valid, 4) if n_valid else None
        out.append(row)
    return out


# --------------------------------------------------------------------------- live mapping
def _nearest_pass(items: list[dict[str, Any]], target: date, prefer_after: bool = True) -> list[dict[str, Any]] | None:
    groups = pc.pass_groups(items)
    if not groups:
        return None

    def key(g):
        delta = (date.fromisoformat(g[0]["properties"]["datetime"][:10]) - target).days
        return (abs(delta), 0 if (delta >= 0) == prefer_after else 1)

    return min(groups, key=key)


def _water(vv: np.ndarray, vh: np.ndarray, calibration: dict[str, Any]) -> tuple[np.ndarray, str]:
    model = fm.get_model()
    if model is not None:
        return model.water(fm.rtc_to_input(vv, vh, calibration)), "resq_flood.onnx (Sen1Floods11-trained), 512x512 tiles"
    return fm.threshold_water(fm.calibrate_db(fm.to_db(vv), "vv", calibration)), "VV < -16 dB backscatter threshold (model not installed)"


def map_flood(bbox: dict[str, float], event_date: str, zones: list[dict[str, Any]] | None = None,
              window_days: int = SEARCH_WINDOW_DAYS, with_reference: bool = True, use_cache: bool = True) -> dict[str, Any]:
    """Real Sentinel-1 flood map for ``bbox`` around ``event_date`` (network on a cache miss)."""
    key = hashlib.sha1(json.dumps([bbox, event_date, window_days, with_reference, [z.get("id") for z in zones or []]],
                                  sort_keys=True).encode()).hexdigest()[:16]
    cache = CACHE_DIR / f"{key}.json"
    if use_cache and cache.is_file():
        return json.loads(cache.read_text(encoding="utf-8"))
    if offline():
        raise pc.ImageryError("OFFLINE_MODE=1: live Sentinel-1 mapping disabled")

    started = time.perf_counter()
    target = date.fromisoformat(event_date)
    items = pc.search(bbox, (target - timedelta(days=window_days)).isoformat(), (target + timedelta(days=window_days)).isoformat())
    group = _nearest_pass(items, target)
    if group is None:
        raise pc.ImageryError(f"no Sentinel-1 RTC acquisition within +-{window_days} days of {event_date}")
    transform, width, height = pc.grid(bbox)
    vv, vh, used = pc.read_mosaic(group, transform, width, height)
    calibration = fm.load_calibration()
    t_inf = time.perf_counter()
    water, method = _water(vv, vh, calibration)
    inference_s = time.perf_counter() - t_inf
    valid = np.isfinite(vv) & (vv > 0)
    water &= valid
    acquired = group[0]["properties"]["datetime"][:10]

    reference: dict[str, Any] | None = None
    permanent = np.zeros_like(water)
    if with_reference:
        lo, hi = REFERENCE_WINDOW_DAYS
        ref_items = pc.search(bbox, (target - timedelta(days=hi)).isoformat(), (target - timedelta(days=lo)).isoformat())
        orbit = (group[0]["properties"].get("sat:orbit_state"), group[0]["properties"].get("sat:relative_orbit"))
        same_geometry = [i for i in ref_items if (i["properties"].get("sat:orbit_state"), i["properties"].get("sat:relative_orbit")) == orbit] or ref_items
        ref_group = _nearest_pass(same_geometry, target - timedelta(days=lo), prefer_after=False)
        if ref_group:
            rvv, rvh, rused = pc.read_mosaic(ref_group, transform, width, height)
            rwater, _ = _water(rvv, rvh, calibration)
            rvalid = np.isfinite(rvv) & (rvv > 0)
            permanent = rwater & rvalid & valid
            valid &= rvalid
            reference = {"acquired": ref_group[0]["properties"]["datetime"][:10], "items": rused,
                         "orbit_state": ref_group[0]["properties"].get("sat:orbit_state")}
    flooded = water & ~permanent & valid

    model_on = fm.get_model() is not None
    zone_rows = zone_fractions({"water_pct": water, "permanent_water_pct": permanent, "flooded_pct": flooded}, valid, transform, zones or [])
    for z in zone_rows:
        z["severity"] = round(min(1.0, (z["flooded_pct"] or 0.0) / FULL_SEVERITY_FLOODED), 3)
        z["source"] = "sentinel1-sar-model" if model_on else "sentinel1-sar-threshold"
    px_km2 = (pc.PIXEL_DEG * 110.574) * (pc.PIXEL_DEG * 111.32 * math.cos(math.radians((bbox["south"] + bbox["north"]) / 2)))
    result = {
        "bounds": bbox, "event_date": event_date, "acquired": acquired, "days_from_event": (date.fromisoformat(acquired) - target).days,
        "items": used, "orbit_state": group[0]["properties"].get("sat:orbit_state"), "reference": reference,
        "method": method, "model_installed": model_on, "calibration": {k: calibration.get(k) for k in ("vv_gain", "vv_db", "vh_gain", "vh_db", "fitted")},
        "grid": {"crs": "EPSG:4326", "pixel_deg": pc.PIXEL_DEG, "width": width, "height": height},
        "valid_pct": round(float(valid.mean()), 4),
        "water_area_km2": round(float((water & valid).sum()) * px_km2, 2),
        "permanent_water_area_km2": round(float(permanent.sum()) * px_km2, 2),
        "flooded_area_km2": round(float(flooded.sum()) * px_km2, 2),
        "total_area_km2": round(width * height * px_km2, 2),
        "zones": zone_rows,
        "timing_s": {"total": round(time.perf_counter() - started, 1), "inference": round(inference_s, 1)},
        "mask_preview": _preview(water, permanent, valid),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(result), encoding="utf-8")
    return result


def _preview(water: np.ndarray, permanent: np.ndarray, valid: np.ndarray, max_side: int = 256) -> dict[str, Any]:
    """Run-length encoded down-sampled class map (0 dry, 1 permanent water, 2 flood, 3 no data) for the map."""
    step = max(1, int(math.ceil(max(water.shape) / max_side)))
    cls = np.zeros(water.shape, dtype=np.uint8)
    cls[water & ~permanent] = 2
    cls[permanent] = 1
    cls[~valid] = 3
    flat = cls[::step, ::step].ravel()
    change = np.flatnonzero(np.diff(flat)) + 1
    starts = np.concatenate(([0], change))
    lengths = np.diff(np.concatenate((starts, [flat.size])))
    return {"shape": list(cls[::step, ::step].shape), "step": step, "classes": ["dry", "permanent_water", "flood", "no_data"],
            "rle": [[int(flat[s]), int(n)] for s, n in zip(starts, lengths)]}


# --------------------------------------------------------------------------- replay caches
def replay_path(scenario_id: str) -> Path:
    return REPLAY_DIR / f"{scenario_id}.flood.json"


def load_replay(scenario_id: str) -> dict[str, Any] | None:
    path = replay_path(scenario_id)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def build_replay(scenario_id: str) -> dict[str, Any]:
    """Recompute a replay preset from Sentinel-1 (network) and write the committed cache."""
    preset = REPLAY_PRESETS[scenario_id]
    scenario = get_scenario(scenario_id)
    zones = [z.model_dump() for z in scenario.zones]
    result = map_flood(scenario.bbox, preset["date"], zones=zones, use_cache=False)
    preview = result.pop("mask_preview", None)
    doc = {"scenario_id": scenario_id, **preset, **result}
    REPLAY_DIR.mkdir(parents=True, exist_ok=True)
    replay_path(scenario_id).write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    (REPLAY_DIR / f"{scenario_id}.flood_mask.json").write_text(json.dumps(preview), encoding="utf-8")
    return doc


# --------------------------------------------------------------------------- API entry point
def assess_flood_extent(bbox: dict[str, float], scenario_id: str | None = None, water_threshold_db: float = -16.0,
                        event_date: str | None = None) -> dict[str, Any]:
    """Flood assessment for the API: replay cache, else live mapping (needs a date), else a labelled estimate."""
    model_available = is_flood_model_available()
    base: dict[str, Any] = {
        "assessment_id": f"SAR-{uuid.uuid4().hex[:8].upper()}",
        "platform": "Copernicus Sentinel-1 (C-SAR)", "instrument": "C-band Synthetic Aperture Radar",
        "product_type": "RTC (Radiometrically Terrain Corrected), Microsoft Planetary Computer", "polarization": ["VV", "VH"],
        "weights_deferred": not model_available, "deferred_fallback_active": not model_available,
        "water_threshold_db": water_threshold_db, "bounds": bbox,
    }
    real: dict[str, Any] | None = None
    status = None
    cached = load_replay(scenario_id) if scenario_id else None
    if cached:
        real, status = cached, "replay-cache"
    elif event_date:
        try:
            scenario = get_scenario(scenario_id) if scenario_id else None
            zones = [z.model_dump() for z in scenario.zones] if scenario else []
            real, status = map_flood(bbox, event_date, zones=zones), "live"
        except pc.ImageryError as exc:
            base["imagery_error"] = str(exc)
    if real is not None:
        total = real["total_area_km2"] or 1.0
        return {**base, "status": status, "method": f"Sen1Floods11 {real['method']}", "acquired": real["acquired"],
                "days_from_event": real.get("days_from_event"), "items": real["items"], "reference": real.get("reference"),
                "total_area_km2": real["total_area_km2"], "flooded_area_km2": real["flooded_area_km2"],
                "water_area_km2": real.get("water_area_km2"), "permanent_water_area_km2": real.get("permanent_water_area_km2"),
                "flooded_pct": round(real["flooded_area_km2"] / total, 4), "mean_confidence": None,
                "zones": [{**z, "mean_backscatter_vv_db": None} for z in real["zones"]],
                "created_at": real.get("created_at"),
                "notice": f"Real Sentinel-1 RTC acquisition {real['acquired']} ({real['method']})"}
    return _scenario_estimate(base, bbox, scenario_id)


def _scenario_estimate(base: dict[str, Any], bbox: dict[str, float], scenario_id: str | None) -> dict[str, Any]:
    """No imagery: an estimate from the scenario's simulated damage (clearly labelled)."""
    south, north, west, east = bbox.get("south", 12.9), bbox.get("north", 13.0), bbox.get("west", 77.6), bbox.get("east", 77.7)
    lat_mid = (south + north) / 2.0
    total = round(max(abs(east - west) * 111.32 * math.cos(math.radians(lat_mid)) * abs(north - south) * 110.57, 1.0), 2)
    zones, flooded = [], 0.0
    if scenario_id:
        try:
            scenario = get_scenario(scenario_id)
            for z in scenario.zones:
                pct = round(min(0.85, 0.2 + z.damage_severity * 0.22), 2) if z.damage_severity >= 2 else round(z.damage_severity * 0.05, 2)
                zones.append({"zone_id": z.id, "name": z.name, "latitude": z.latitude, "longitude": z.longitude, "flooded_pct": pct,
                              "severity": round(min(1.0, z.damage_severity / 3.0), 2), "population": z.population, "geometry": z.geometry,
                              "source": "scenario-estimate", "mean_backscatter_vv_db": None})
                flooded += total / max(len(scenario.zones), 1) * pct
        except Exception as exc:  # noqa: BLE001
            logger.warning("could not load scenario %s: %s", scenario_id, exc)
    flooded = round(min(flooded, total * 0.8), 2)
    return {**base, "status": "estimate",
            "method": "Sen1Floods11 pipeline not run: estimate from simulated scenario damage (no imagery)",
            "total_area_km2": total, "flooded_area_km2": flooded, "flooded_pct": round(flooded / total, 3) if total else 0.0,
            "mean_confidence": None, "zones": zones, "created_at": datetime.now().isoformat(),
            "notice": "No Sentinel-1 imagery for this request (give an event date for live mapping); values are a scenario estimate"}

"""Flood model evaluation for the unified results suite (docs/results/).

Sources, all produced by real runs and read here (no network):

* ``data/assets/flood_results.json`` - training-time Sen1Floods11 evaluation from the asset
  release: experiment A (trained without Indian data) vs B (with Indian data), India test split
  and global validation split.
* ``docs/results/flood_domain_check.json`` - ``python ml/flood_inference.py domain-check``:
  the Indian sample chips scored as shipped (Sen1Floods11 S1Hand) and re-read from Microsoft
  Planetary Computer ``sentinel-1-rtc``, uncalibrated and calibrated.
* ``data/flood_calibration.json`` - the calibration the backend applies to RTC input.
* ``data/replays/<id>.flood.json`` - the replay flood maps (real acquisitions).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from paths import DATA_DIR, REPO_ROOT

DOMAIN_CHECK = REPO_ROOT / "docs" / "results" / "flood_domain_check.json"
CALIBRATION = DATA_DIR / "flood_calibration.json"
REPLAYS = DATA_DIR / "replays"


def _read(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
    except (OSError, ValueError):
        return None


def experiments(raw: dict[str, Any]) -> dict[str, Any]:
    a, b = raw.get("experiment_A_no_indian_training", {}), raw.get("experiment_B_with_indian_training", {})

    def row(e: dict[str, Any], split: str) -> dict[str, Any]:
        s = e.get(split, {})
        return {"water_iou": s.get("water_iou"), "water_f1": s.get("water_f1")}

    return {
        "trained_without_indian_data": {"india_test": row(a, "india_test"), "global_val": row(a, "global_val")},
        "trained_with_indian_data": {"india_test": row(b, "india_test"), "global_val": row(b, "global_val")},
        "india_test_gain": {k: round((b.get("india_test", {}).get(k) or 0) - (a.get("india_test", {}).get(k) or 0), 4)
                            for k in ("water_iou", "water_f1")},
        "split": raw.get("split", {}),
        "deployed_model": "resq_flood.onnx = experiment B (trained with Indian data)",
    }


def replay_summaries() -> dict[str, Any]:
    out = {}
    for path in sorted(REPLAYS.glob("*.flood.json")):
        d = _read(path) or {}
        zones = d.get("zones", [])
        flooded = sorted(zones, key=lambda z: -(z.get("flooded_pct") or 0))
        out[d.get("scenario_id", path.stem)] = {
            "event": d.get("event"), "event_dates": d.get("event_dates"), "acquired": d.get("acquired"),
            "days_from_event": d.get("days_from_event"), "reference_acquired": (d.get("reference") or {}).get("acquired"),
            "method": d.get("method"), "total_area_km2": d.get("total_area_km2"), "water_area_km2": d.get("water_area_km2"),
            "permanent_water_area_km2": d.get("permanent_water_area_km2"), "flooded_area_km2": d.get("flooded_area_km2"),
            "valid_pct": d.get("valid_pct"), "zones": len(zones),
            "zones_over_10pct_flooded": sum(1 for z in zones if (z.get("flooded_pct") or 0) > 0.10),
            "mean_zone_flooded_pct": round(sum(z.get("flooded_pct") or 0 for z in zones) / len(zones), 4) if zones else None,
            "top_zones": [{"name": z.get("name"), "flooded_pct": z.get("flooded_pct")} for z in flooded[:5]],
            "inference_s": (d.get("timing_s") or {}).get("inference"),
        }
    return out


def load_flood_metrics(results_file: Path | None = None) -> dict[str, Any]:
    from eval.satellite_metrics import find_flood_results_file

    path = results_file or find_flood_results_file()
    raw = _read(path) if path else None
    if raw is None:
        return {"status": "pending_assets",
                "message": "flood_results.json not found (python backend/scripts/download_assets.py)", "metrics": None}
    domain = _read(DOMAIN_CHECK)
    calibration = _read(CALIBRATION)
    return {
        "status": "evaluated",
        "message": "resq_flood.onnx evaluated on Sen1Floods11 (training-time splits) and on Planetary Computer RTC (domain check)",
        "metrics": raw,
        "experiments": experiments(raw),
        "domain_check": None if domain is None else {k: domain.get(k) for k in (
            "status", "chip_date", "chips_matched", "rtc_items", "overlap", "scored_on", "original_chips", "rtc_uncalibrated",
            "rtc_offset_only_leave_one_out", "rtc_calibrated_leave_one_out", "delta_uncalibrated", "delta_calibrated",
            "pixel_correlation_db", "calibration")},
        "sample_chips_all": None if domain is None else domain.get("all_chips_original"),
        "calibration_in_use": calibration,
        "replays": replay_summaries(),
    }

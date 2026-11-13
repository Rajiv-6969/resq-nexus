"""Sentinel-1 flood model: chip evaluation, Planetary Computer RTC domain check, calibration.

    python ml/flood_inference.py chips                 # resq_flood.onnx on the Sen1Floods11 India chips
    python ml/flood_inference.py domain-check          # same chips re-read from Planetary Computer RTC (network)
    python ml/flood_inference.py predict --bbox S,W,N,E --date 2024-09-01   # one flood map (network)

Run from the repository root with the backend venv. Runtime code lives in
``backend/services/imagery/flood_model.py`` (shipped in the container); this file holds the
evaluation and the calibration fit.

Calibration (why and how)
-------------------------
Sen1Floods11 ``S1Hand`` chips are Google Earth Engine Sentinel-1 GRD *sigma0* in dB. Planetary
Computer ``sentinel-1-rtc`` is radiometrically terrain-corrected *gamma0* (linear). Measured on the
co-registered sample chips, RTC is not just ~1-2 dB brighter (gamma0 = sigma0 / cos(incidence)):
its dark tail - open water - is compressed (VH water median -21.4 dB in S1Hand vs -18.9 dB in RTC,
5th percentile -32.3 vs -23.2 dB), so water no longer looks like the water the model learned and
recall collapses. A single dB offset cannot undo a compression, so the calibration is a per-band
*linear* map in dB, two numbers per band::

    dB_calibrated = gain_band * dB_rtc + offset_band

fitted by least squares on matched quantiles (1st..99th percentile) of S1Hand dB vs RTC dB over the
pixels valid in both. It uses intensities only, never the water labels. It is applied after
``10 * log10`` and before the normalisation (NaN -> -30, clip [-30, 0], (x + 30) / 30). The
offset-only variant (median of S1Hand - RTC) is reported for comparison. Scores "after calibration"
are leave-one-chip-out (each chip scored with parameters fitted on the other chips). The all-chip
fit is written to ``data/flood_calibration.json`` and used by the backend for every RTC read - but
only adopted (``fitted: true``) when the RTC IoU drops by more than ``SHARP_DROP`` versus the
original chips and the calibration improves the leave-one-out IoU.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from services.imagery import flood_model as fm  # noqa: E402
from services.imagery import planetary as pc  # noqa: E402

SAMPLE_DIR = ROOT / "data" / "assets" / "flood_sample"
CACHE_DIR = ROOT / "data" / "assets" / "cache" / "flood_domain"
REPORT = ROOT / "docs" / "results" / "flood_domain_check.json"
CHIP_DATE = "2016-08-12"  # Sen1Floods11 India event: Sentinel-1A acquisition used for every India chip
SHARP_DROP = 0.05  # absolute IoU drop that triggers adopting the calibration


def chips() -> list[tuple[str, Path, Path]]:
    out = []
    for s1 in sorted(SAMPLE_DIR.glob("*_S1Hand.tif")):
        label = s1.with_name(s1.name.replace("S1Hand", "LabelHand"))
        if label.is_file():
            out.append((s1.name.replace("_S1Hand.tif", ""), s1, label))
    return out


def read_chip(s1: Path, label: Path):
    import rasterio

    with rasterio.open(s1) as src:
        bands, transform, bounds, shape = src.read().astype(np.float32), src.transform, src.bounds, (src.height, src.width)
    with rasterio.open(label) as src:
        lab = src.read(1)
    return bands, lab, transform, bounds, shape


def evaluate_chips(model: fm.FloodModel) -> dict:
    per, parts, thr, times = {}, [], [], []
    for name, s1, label in chips():
        bands, lab, *_ = read_chip(s1, label)
        t = time.perf_counter()
        water = model.water(fm.db_to_input(bands[0], bands[1]))
        times.append(time.perf_counter() - t)
        m = fm.water_metrics(water, lab)
        parts.append(m)
        thr.append(fm.water_metrics(fm.threshold_water(bands[0]), lab))
        per[name] = {"water_iou": m["water_iou"], "water_f1": m["water_f1"]}
    return {"per_chip": per, "pooled": fm.pooled_metrics(parts), "threshold_vv_lt_-16db": fm.pooled_metrics(thr),
            "mean_seconds_per_chip": round(float(np.mean(times)), 3) if times else None}


def fetch_rtc(name: str, bounds, transform, shape) -> dict | None:
    """RTC VV/VH linear on the chip's exact grid, cached as .npz (network on first call)."""
    cache = CACHE_DIR / f"{name}.npz"
    if cache.is_file():
        d = np.load(cache, allow_pickle=False)
        return {"vv": d["vv"], "vh": d["vh"], "items": [str(s) for s in d["items"]]}
    bbox = {"south": bounds.bottom, "west": bounds.left, "north": bounds.top, "east": bounds.right}
    day = date.fromisoformat(CHIP_DATE)
    items = pc.search(bbox, (day - timedelta(days=1)).isoformat(), (day + timedelta(days=1)).isoformat())
    same_day = [i for i in items if i["properties"]["datetime"][:10] == CHIP_DATE]
    if not same_day:
        return None
    for group in pc.pass_groups(same_day):
        try:
            vv, vh, used = pc.read_mosaic(group, transform, shape[1], shape[0])
        except pc.ImageryError as exc:
            print(f"  {name}: read failed ({exc})")
            continue
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(cache, vv=vv, vh=vh, items=np.array(used))
        return {"vv": vv, "vh": vh, "items": used}
    return None


def fit_offset(pairs: list[tuple[np.ndarray, np.ndarray]]) -> float:
    """Median (S1Hand dB - RTC dB) over pixels valid in both (one band)."""
    diffs = []
    for hand_db, rtc_db in pairs:
        ok = np.isfinite(hand_db) & np.isfinite(rtc_db) & (hand_db > -40) & (hand_db < 10)
        if ok.any():
            diffs.append((hand_db - rtc_db)[ok])
    return round(float(np.median(np.concatenate(diffs))), 3) if diffs else 0.0


QUANTILES = np.arange(1, 100)


def fit_linear(pairs: list[tuple[np.ndarray, np.ndarray]]) -> tuple[float, float]:
    """(gain, offset) with S1Hand dB ~ gain * RTC dB + offset, least squares on matched 1-99th percentiles."""
    hand, rtc = [], []
    for hand_db, rtc_db in pairs:
        ok = np.isfinite(hand_db) & np.isfinite(rtc_db)
        hand.append(hand_db[ok])
        rtc.append(rtc_db[ok])
    hq, rq = np.percentile(np.concatenate(hand), QUANTILES), np.percentile(np.concatenate(rtc), QUANTILES)
    gain, offset = np.polyfit(rq, hq, 1)
    return round(float(gain), 4), round(float(offset), 3)


def _offsets(rows: list[dict]) -> dict[str, float]:
    return {"vv_gain": 1.0, "vv_db": fit_offset([(r["hand"][0], r["vv_db"]) for r in rows]),
            "vh_gain": 1.0, "vh_db": fit_offset([(r["hand"][1], r["vh_db"]) for r in rows])}


def _linear(rows: list[dict]) -> dict[str, float]:
    (vg, vo), (hg, ho) = (fit_linear([(r["hand"][i], r[f"{b}_db"]) for r in rows]) for i, b in enumerate(("vv", "vh")))
    return {"vv_gain": vg, "vv_db": vo, "vh_gain": hg, "vh_db": ho}


def domain_check(model: fm.FloodModel) -> dict:
    original = evaluate_chips(model)
    rows = []
    for name, s1, label in chips():
        bands, lab, transform, bounds, shape = read_chip(s1, label)
        try:
            rtc = fetch_rtc(name, bounds, transform, shape)
        except pc.ImageryError as exc:
            print(f"  {name}: Planetary Computer unavailable ({exc})")
            rtc = None
        if rtc is None:
            print(f"  {name}: no matching RTC scene on {CHIP_DATE}")
            continue
        vv_db, vh_db = fm.to_db(rtc["vv"]), fm.to_db(rtc["vh"])
        # Score only where both sources have data, so the comparison is like for like.
        both = np.isfinite(vv_db) & np.isfinite(bands[0])
        lab = np.where(both, lab, -1)
        coverage = round(float(both.mean()), 3)
        rows.append({"name": name, "hand": bands, "label": lab, "vv_db": vv_db, "vh_db": vh_db, "items": rtc["items"], "coverage": coverage})
        print(f"  {name}: RTC {rtc['items']} overlap {coverage:.0%}")
    if not rows:
        return {"status": "no_matching_scenes", "all_chips_original": original}

    def score(make_input):
        parts, per = [], {}
        for r in rows:
            m = fm.water_metrics(model.water(make_input(r)), r["label"])
            parts.append(m)
            per[r["name"]] = {"water_iou": m["water_iou"], "water_f1": m["water_f1"]}
        return fm.pooled_metrics(parts), per

    def rtc_input(fit):
        def make(r):
            cal = fit([o for o in rows if o["name"] != r["name"]] or rows)  # leave-one-chip-out
            return np.stack([fm.normalise_db(fm.calibrate_db(r["vv_db"], "vv", cal)),
                             fm.normalise_db(fm.calibrate_db(r["vh_db"], "vh", cal))])
        return make

    orig, orig_per = score(lambda r: fm.db_to_input(r["hand"][0], r["hand"][1]))
    raw, raw_per = score(rtc_input(lambda rs: {}))
    offset_only, _ = score(rtc_input(_offsets))
    calibrated, cal_per = score(rtc_input(_linear))
    final = _linear(rows)
    drop = round(orig["water_iou"] - raw["water_iou"], 4)
    adopt = drop > SHARP_DROP and calibrated["water_iou"] > raw["water_iou"]
    corr = {}
    for i, b in enumerate(("vv", "vh")):
        h = np.concatenate([r["hand"][i].ravel() for r in rows])
        rt = np.concatenate([r[f"{b}_db"].ravel() for r in rows])
        ok = np.isfinite(h) & np.isfinite(rt)
        corr[b] = round(float(np.corrcoef(h[ok], rt[ok])[0, 1]), 3)
    return {
        "status": "evaluated",
        "chip_date": CHIP_DATE,
        "chips_matched": [r["name"] for r in rows],
        "rtc_items": sorted({i for r in rows for i in r["items"]}),
        "overlap": {r["name"]: r["coverage"] for r in rows},
        "scored_on": "pixels valid in both Sen1Floods11 S1Hand and Planetary Computer RTC (label -1 elsewhere)",
        "original_chips": orig,
        "rtc_uncalibrated": raw,
        "rtc_offset_only_leave_one_out": offset_only,
        "rtc_calibrated_leave_one_out": calibrated,
        "delta_uncalibrated": {"water_iou": round(raw["water_iou"] - orig["water_iou"], 4), "water_f1": round(raw["water_f1"] - orig["water_f1"], 4)},
        "delta_calibrated": {"water_iou": round(calibrated["water_iou"] - orig["water_iou"], 4),
                             "water_f1": round(calibrated["water_f1"] - orig["water_f1"], 4)},
        "pixel_correlation_db": corr,
        "calibration": {**final, "adopted": adopt, "iou_drop_uncalibrated": drop, "offset_only": _offsets(rows),
                        "rule": f"adopted when the RTC IoU drops by more than {SHARP_DROP} and the leave-one-out calibrated IoU is higher",
                        "method": "per-band linear map in dB (gain * dB + offset), least squares on matched 1-99th percentiles of "
                                  "S1Hand vs RTC over co-valid pixels (label-free), applied before normalisation"},
        "per_chip": {"original": orig_per, "rtc_uncalibrated": raw_per, "rtc_calibrated_leave_one_out": cal_per},
        "all_chips_original": original,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="resq_flood.onnx evaluation and calibration")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("chips")
    sub.add_parser("domain-check")
    p = sub.add_parser("predict")
    p.add_argument("--bbox", required=True, help="south,west,north,east")
    p.add_argument("--date", required=True, help="event date (YYYY-MM-DD); the nearest acquisition within +-7 days is used")
    args = parser.parse_args(argv)
    model = fm.get_model()
    if model is None:
        print(fm.model_status()["reason"])
        return 1
    if args.cmd == "chips":
        print(json.dumps(evaluate_chips(model), indent=1))
    elif args.cmd == "domain-check":
        result = domain_check(model)
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
        cal = result.get("calibration") or {}
        adopted = bool(cal.get("adopted"))
        params = {k: cal.get(k) for k in ("vv_gain", "vv_db", "vh_gain", "vh_db")}
        fm.CALIBRATION_FILE.write_text(json.dumps({
            **(params if adopted else {"vv_gain": 1.0, "vv_db": 0.0, "vh_gain": 1.0, "vh_db": 0.0}),
            "fitted": adopted,
            "fitted_parameters": params,
            "iou_drop_uncalibrated": cal.get("iou_drop_uncalibrated"),
            "source": "python ml/flood_inference.py domain-check (Sen1Floods11 India sample chips vs Planetary Computer sentinel-1-rtc)",
            "method": cal.get("method"), "rule": cal.get("rule"),
        }, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({k: result[k] for k in ("original_chips", "rtc_uncalibrated", "rtc_offset_only_leave_one_out", "rtc_calibrated_leave_one_out", "delta_uncalibrated",
                                                  "delta_calibrated", "pixel_correlation_db", "calibration") if k in result}, indent=1))
    else:
        from services.imagery import sentinel

        s, w, n, e = (float(v) for v in args.bbox.split(","))
        result = sentinel.map_flood({"south": s, "west": w, "north": n, "east": e}, args.date)
        result.pop("mask_preview", None)
        print(json.dumps({k: v for k, v in result.items() if k != "zones"}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())

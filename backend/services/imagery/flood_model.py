"""Sentinel-1 flood segmentation with resq_flood.onnx (Sen1Floods11-trained), CPU, tiled.

Model contract: input ``s1`` (B, 2, H, W) float32 = [VV, VH] normalised as below; output
``water`` (B, 2, H, W) logits; water = argmax over the 2 channels == 1. Any H, W divisible by
32 is accepted; we always run 512 x 512 tiles (64 px overlap, logits averaged) to bound memory.

Preprocessing (identical for Sen1Floods11 chips and Planetary Computer RTC):
    linear backscatter -> dB: 10 * log10(x)      (RTC only; Sen1Floods11 S1Hand is already dB)
    per-band linear calibration in dB: gain * dB + offset   (RTC only, see data/flood_calibration.json)
    NaN / non-finite -> -30 dB, clip to [-30, 0], (x + 30) / 30  -> [0, 1]

Without the model file the caller falls back to the VV < -16 dB backscatter threshold.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np

from paths import DATA_DIR

logger = logging.getLogger(__name__)

TILE = 512
OVERLAP = 64
DB_MIN, DB_MAX = -30.0, 0.0
THRESHOLD_VV_DB = -16.0
CALIBRATION_FILE = DATA_DIR / "flood_calibration.json"
MODEL_CANDIDATES = (DATA_DIR / "assets" / "resq_flood.onnx", DATA_DIR.parent / "ml" / "resq_flood.onnx")


def to_db(linear: np.ndarray) -> np.ndarray:
    """Linear power backscatter (gamma0 / sigma0) to dB; non-positive values become NaN."""
    linear = np.asarray(linear, dtype=np.float32)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(linear > 0, 10.0 * np.log10(linear), np.nan).astype(np.float32)


def normalise_db(db: np.ndarray) -> np.ndarray:
    """NaN -> -30 dB, clip to [-30, 0], scale to [0, 1] (the model's training normalisation)."""
    x = np.where(np.isfinite(db), db, DB_MIN)
    return ((np.clip(x, DB_MIN, DB_MAX) - DB_MIN) / (DB_MAX - DB_MIN)).astype(np.float32)


def load_calibration(path: Path = CALIBRATION_FILE) -> dict[str, Any]:
    """Per-band dB offsets for Planetary Computer RTC input (0/0 when not fitted)."""
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return {**data, "vv_db": float(data.get("vv_db", 0.0)), "vh_db": float(data.get("vh_db", 0.0)),
                    "vv_gain": float(data.get("vv_gain", 1.0)), "vh_gain": float(data.get("vh_gain", 1.0))}
        except (OSError, ValueError):
            logger.warning("unreadable %s; using no calibration", path)
    return {"vv_db": 0.0, "vh_db": 0.0, "vv_gain": 1.0, "vh_gain": 1.0, "fitted": False}


def calibrate_db(db: np.ndarray, band: str, calibration: dict[str, Any]) -> np.ndarray:
    """gain * dB + offset for one band ("vv" / "vh")."""
    return float(calibration.get(f"{band}_gain", 1.0)) * db + float(calibration.get(f"{band}_db", 0.0))


def rtc_to_input(vv_linear: np.ndarray, vh_linear: np.ndarray, calibration: dict[str, Any] | None = None) -> np.ndarray:
    """(2, H, W) model input from Planetary Computer RTC linear gamma0 bands."""
    cal = load_calibration() if calibration is None else calibration
    vv = calibrate_db(to_db(vv_linear), "vv", cal)
    vh = calibrate_db(to_db(vh_linear), "vh", cal)
    return np.stack([normalise_db(vv), normalise_db(vh)])


def db_to_input(vv_db: np.ndarray, vh_db: np.ndarray) -> np.ndarray:
    """(2, H, W) model input from bands already in dB (Sen1Floods11 S1Hand chips)."""
    return np.stack([normalise_db(vv_db), normalise_db(vh_db)])


def find_model() -> Path | None:
    return next((p for p in MODEL_CANDIDATES if p.is_file()), None)


def is_available() -> bool:
    """Check if model file is present without instantiating ONNX session."""
    return find_model() is not None


def _starts(size: int) -> list[int]:
    if size <= TILE:
        return [0]
    step = TILE - OVERLAP
    starts = list(range(0, size - TILE, step)) + [size - TILE]
    return sorted(set(starts))


class FloodModel:
    """ONNX Runtime session for resq_flood.onnx (2 intra-op threads, CPU)."""

    def __init__(self, path: Path) -> None:
        import onnxruntime as ort

        opts = ort.SessionOptions()
        opts.enable_cpu_mem_arena = False  # keeps RSS close to the working set on a 512 MB box
        opts.intra_op_num_threads = 1
        opts.inter_op_num_threads = 1
        opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        self.path = path
        self.session = ort.InferenceSession(str(path), sess_options=opts, providers=["CPUExecutionProvider"])
        inputs, outputs = self.session.get_inputs(), self.session.get_outputs()
        if [i.name for i in inputs] != ["s1"] or outputs[0].name != "water":
            raise ValueError(f"unexpected model signature: {[i.name for i in inputs]} -> {[o.name for o in outputs]}")

    def logits(self, x: np.ndarray) -> np.ndarray:
        """Water logits (2, H, W) for a (2, H, W) normalised input, run in 512 x 512 tiles."""
        _, h, w = x.shape
        ph, pw = max(h, TILE), max(w, TILE)
        if (ph, pw) != (h, w):  # small inputs: pad up to one tile with the "no signal" value 0
            x = np.pad(x, ((0, 0), (0, ph - h), (0, pw - w)))
        acc = np.zeros((2, ph, pw), dtype=np.float32)
        count = np.zeros((ph, pw), dtype=np.float32)
        for y0 in _starts(ph):
            for x0 in _starts(pw):
                tile = x[None, :, y0:y0 + TILE, x0:x0 + TILE].astype(np.float32)
                out = self.session.run(["water"], {"s1": tile})[0][0]
                acc[:, y0:y0 + TILE, x0:x0 + TILE] += out
                count[y0:y0 + TILE, x0:x0 + TILE] += 1
        return (acc / count)[:, :h, :w]

    def water(self, x: np.ndarray) -> np.ndarray:
        """Boolean water mask: argmax over the two logit channels == 1."""
        return np.argmax(self.logits(x), axis=0) == 1


_LOCK = threading.Lock()
_MODEL: FloodModel | None = None
_REASON: str | None = None


def get_model() -> FloodModel | None:
    """Lazy singleton; None (see ``model_status()``) when the file is missing or fails to load."""
    global _MODEL, _REASON
    with _LOCK:
        if _MODEL is not None or _REASON is not None:
            return _MODEL
        path = find_model()
        if path is None:
            _REASON = "resq_flood.onnx not installed (python backend/scripts/download_assets.py)"
            return None
        try:
            from services.memory import model_loading

            model_loading("flood", _release)
            _MODEL = FloodModel(path)
        except Exception as exc:  # noqa: BLE001 - a broken file must not break the app
            _REASON = f"resq_flood.onnx failed to load: {type(exc).__name__}: {exc}"
            logger.warning(_REASON)
        return _MODEL


def _release() -> None:
    """Drop the session (ONNX_RESIDENCY=single); the next get_model() reloads it."""
    global _MODEL
    _MODEL = None


def model_status() -> dict[str, Any]:
    path = find_model()
    installed = path is not None
    return {"installed": installed, "path": str(path) if path else None, "reason": _REASON}


def reset_model() -> None:
    """Forget the cached session (tests)."""
    global _MODEL, _REASON
    with _LOCK:
        _MODEL, _REASON = None, None


def threshold_water(vv_db: np.ndarray, threshold_db: float = THRESHOLD_VV_DB) -> np.ndarray:
    """Fallback without the model: VV backscatter below ``threshold_db`` is water."""
    return np.isfinite(vv_db) & (vv_db < threshold_db)


def water_metrics(pred: np.ndarray, label: np.ndarray) -> dict[str, Any]:
    """Water IoU / F1 / precision / recall; label -1 (no data) is ignored, as in Sen1Floods11."""
    valid = label >= 0
    p, t = pred[valid].astype(bool), label[valid] == 1
    tp, fp, fn = int((p & t).sum()), int((p & ~t).sum()), int((~p & t).sum())
    iou = tp / (tp + fp + fn) if tp + fp + fn else 1.0
    f1 = 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 1.0
    return {"tp": tp, "fp": fp, "fn": fn, "water_iou": round(iou, 4), "water_f1": round(f1, 4),
            "precision": round(tp / (tp + fp), 4) if tp + fp else None,
            "recall": round(tp / (tp + fn), 4) if tp + fn else None}


def pooled_metrics(parts: list[dict[str, Any]]) -> dict[str, Any]:
    """Pixel-pooled IoU / F1 over several chips (how Sen1Floods11 reports test scores)."""
    tp, fp, fn = (sum(p[k] for p in parts) for k in ("tp", "fp", "fn"))
    return {"water_iou": round(tp / max(tp + fp + fn, 1), 4), "water_f1": round(2 * tp / max(2 * tp + fp + fn, 1), 4),
            "chips": len(parts), "tp": tp, "fp": fp, "fn": fn}


def benchmark_tile(model: FloodModel, repeats: int = 3) -> dict[str, Any]:
    """CPU time and RSS for one 512 x 512 tile."""
    import psutil

    proc = psutil.Process()
    x = np.random.default_rng(0).random((2, TILE, TILE), dtype=np.float32)
    model.session.run(["water"], {"s1": x[None]})  # warm-up
    times, peak = [], proc.memory_info().rss
    for _ in range(repeats):
        t = time.perf_counter()
        model.session.run(["water"], {"s1": x[None]})
        times.append(time.perf_counter() - t)
        peak = max(peak, proc.memory_info().rss)
    return {"tile": f"{TILE}x{TILE}", "ms_per_tile": round(min(times) * 1000, 1), "rss_mb_after": round(peak / 2**20, 1)}

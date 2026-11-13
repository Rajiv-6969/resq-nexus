"""Measure CPU time per 512x512 tile and process RSS for both ONNX models, as a deployed container would.

Run as a separate process (``python -m eval.memory_probe`` from backend/, or via
``eval.system_benchmarks.measure_models``) so the numbers are not inflated by the evaluation
suite itself. Steps: import the FastAPI app (database, routers, cached road graphs warmed), then
load ``resq_damage.onnx`` and run one tile, then load ``resq_flood.onnx`` and run one tile with
both models resident. Peak RSS is sampled every 5 ms in a background thread. Prints JSON.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import numpy as np  # noqa: E402
import psutil  # noqa: E402

PROC = psutil.Process()
MB = 2**20


class PeakSampler:
    def __init__(self) -> None:
        self.peak = PROC.memory_info().rss
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self._stop.is_set():
            self.peak = max(self.peak, PROC.memory_info().rss)
            time.sleep(0.005)

    def __enter__(self):
        self.peak = PROC.memory_info().rss
        self._t.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._t.join()
        self.peak = max(self.peak, PROC.memory_info().rss)


def rss() -> float:
    return round(PROC.memory_info().rss / MB, 1)


def timed(fn, repeats: int = 3) -> tuple[float, float]:
    fn()  # warm-up
    best = float("inf")
    with PeakSampler() as s:
        for _ in range(repeats):
            t = time.perf_counter()
            fn()
            best = min(best, time.perf_counter() - t)
    return round(best * 1000, 1), round(s.peak / MB, 1)


def main() -> dict:
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    os.environ.setdefault("JWT_SECRET", "memory-probe-" + "0" * 48)
    out: dict = {"python_baseline_mb": rss()}

    import main as app_main  # noqa: F401  (the FastAPI app, as uvicorn would import it)
    from services import allocation_engine
    from services.scenarios import get_scenario

    out["app_mb"] = rss()
    out["profile"] = {k: os.getenv(k, "") for k in ("WARM_ROAD_GRAPHS", "ROAD_GRAPH_CACHE", "ONNX_RESIDENCY")}
    if os.getenv("WARM_ROAD_GRAPHS", "1") != "0":
        allocation_engine.warm_road_networks()
    else:  # what a request does: the largest scenario's graph only
        allocation_engine.allocate(get_scenario("flood-bengaluru"), seed=1)
    out["app_with_road_graphs_mb"] = rss()

    rng = np.random.default_rng(0)
    from services.damage.inference import get_damage_session

    dmg = get_damage_session()
    if dmg.is_available:
        session = dmg.get_session()
        out["after_damage_load_mb"] = rss()
        pre = rng.random((1, 3, 512, 512), dtype=np.float32)
        post = rng.random((1, 3, 512, 512), dtype=np.float32)
        ms, peak = timed(lambda: session.run(None, {"pre": pre, "post": post}))
        out["damage"] = {"ms_per_tile": ms, "peak_rss_mb": peak}
    else:
        out["damage"] = None

    from services.imagery import flood_model as fm

    flood = fm.get_model()
    if flood is not None:
        out["after_flood_load_mb"] = rss()
        s1 = rng.random((1, 2, 512, 512), dtype=np.float32)
        ms, peak = timed(lambda: flood.session.run(["water"], {"s1": s1}))
        out["flood"] = {"ms_per_tile": ms, "peak_rss_mb": peak}
        if dmg.is_available:  # alternate the two models (reloads each time under ONNX_RESIDENCY=single)
            with PeakSampler() as s:
                for _ in range(2):
                    dmg.get_session().run(None, {"pre": pre, "post": post})
                    fm.get_model().session.run(["water"], {"s1": s1})
            out["both_models_peak_rss_mb"] = round(s.peak / MB, 1)
    else:
        out["flood"] = None
    out["final_rss_mb"] = rss()
    out["limit_mb"] = 512
    peak_all = max(v for v in (out.get("both_models_peak_rss_mb"), (out.get("flood") or {}).get("peak_rss_mb"),
                               (out.get("damage") or {}).get("peak_rss_mb"), out["final_rss_mb"]) if v)
    out["container_peak_rss_mb"] = peak_all
    out["headroom_mb"] = round(512 - peak_all, 1)
    out["cpu_threads"] = {"damage_intra_op": 1, "flood_intra_op": 1}
    return out


if __name__ == "__main__":
    print(json.dumps(main()))

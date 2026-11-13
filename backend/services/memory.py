"""Memory budget helpers for a small (512 MB) deployment.

* ``ROAD_GRAPH_CACHE`` - how many parsed road graphs stay in memory (0 = all, the default;
  Render sets 1 so only the scenario in use is resident).
* ``ONNX_RESIDENCY`` - ``all`` (default) keeps every loaded ONNX model in memory; ``single``
  keeps at most one: loading the flood model releases the damage model and vice versa.
"""
from __future__ import annotations

import gc
import os
import threading
from collections import OrderedDict
from collections.abc import Callable
from typing import Any


def road_graph_cache_size() -> int:
    try:
        return max(0, int(os.getenv("ROAD_GRAPH_CACHE", "0")))
    except ValueError:
        return 0


def lru_put(cache: "OrderedDict[Any, Any]", key: Any, value: Any, limit: int, on_evict: Callable[[Any], None] | None = None) -> None:
    cache[key] = value
    cache.move_to_end(key)
    while limit and len(cache) > limit:
        old, _ = cache.popitem(last=False)
        if on_evict:
            on_evict(old)
    if limit:
        gc.collect()


_LOCK = threading.Lock()
_RELEASERS: dict[str, Callable[[], None]] = {}


def single_model() -> bool:
    return os.getenv("ONNX_RESIDENCY", "all").strip().lower() == "single"


def model_loading(name: str, release: Callable[[], None]) -> None:
    """Register ``name`` as loaded; in ``single`` mode release every other model first."""
    with _LOCK:
        if single_model():
            for other, fn in list(_RELEASERS.items()):
                if other != name:
                    fn()
                    _RELEASERS.pop(other, None)
            gc.collect()
        _RELEASERS[name] = release

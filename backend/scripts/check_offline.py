"""Prove the API never touches the network at run time (used by CI).

Blocks every outgoing socket, then starts the app (database seed with the OSM facilities),
lists and loads every scenario and runs the Allocation Engine on each - all of which must
come from the committed caches under ``data/geo/`` and ``data/scenarios/``.
"""
from __future__ import annotations

import os
import socket
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(tempfile.mkdtemp()) / 'offline.db'}")
os.environ.setdefault("JWT_SECRET", "offline-check-" + "0123456789abcdef" * 3)
os.environ.setdefault("SEED_DEMO_DATA", "1")


class NoNetwork(RuntimeError):
    pass


_real_connect = socket.socket.connect


def _guarded_connect(self, address, *args, **kwargs):
    host = address[0] if isinstance(address, tuple) else ""
    if host not in ("127.0.0.1", "::1", "localhost"):  # asyncio's self-pipe uses loopback
        raise NoNetwork(f"network access attempted: {address}")
    return _real_connect(self, address, *args, **kwargs)


socket.socket.connect = _guarded_connect  # type: ignore[method-assign]

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from services import allocation_engine  # noqa: E402
from services.scenarios import get_scenario, list_scenarios  # noqa: E402

with TestClient(main.app) as client:
    assert client.get("/scenarios").status_code == 200
    for summary in list_scenarios():
        scenario = get_scenario(summary.id)
        started = time.perf_counter()
        result = allocation_engine.allocate(scenario)
        seconds = time.perf_counter() - started
        print(f"{summary.id:24} {len(scenario.zones):4} zones  roads={result['road_source']:14} {seconds:5.1f} s")
        assert result["road_source"] == "OpenStreetMap", summary.id
        assert seconds < 10, f"{summary.id} took {seconds:.1f} s"
print("offline check passed")

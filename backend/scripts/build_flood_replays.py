"""Rebuild the Sentinel-1 flood replay caches from real imagery (network; run offline from the app).

    python scripts/build_flood_replays.py                     # every preset
    python scripts/build_flood_replays.py flood-vijayawada

For each preset in ``services.imagery.sentinel.REPLAY_PRESETS`` it searches Microsoft Planetary
Computer ``sentinel-1-rtc`` for the acquisition nearest the event date (+-7 days), reads only the
scenario box from the VV/VH COGs, runs ``resq_flood.onnx`` (512 x 512 tiles; the VV < -16 dB
threshold if the model is absent), removes permanent water using a reference acquisition 20-60
days earlier, and writes ``data/replays/<id>.flood.json`` (+ ``.flood_mask.json``, a down-sampled
class map) with per-zone ``flooded_pct``. Those files are committed; the API reads them offline.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.imagery import sentinel  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("ids", nargs="*", default=list(sentinel.REPLAY_PRESETS))
    args = parser.parse_args(argv)
    for scenario_id in args.ids:
        t = time.perf_counter()
        doc = sentinel.build_replay(scenario_id)
        zones = doc["zones"]
        top = sorted(zones, key=lambda z: -(z["flooded_pct"] or 0))[:5]
        print(f"== {scenario_id}: acquired {doc['acquired']} ({doc['days_from_event']:+d} d from {doc['date']}), "
              f"reference {(doc.get('reference') or {}).get('acquired')}, {doc['method']}")
        print(f"   area {doc['total_area_km2']} km2, valid {doc['valid_pct']:.0%}, water {doc['water_area_km2']} km2, "
              f"permanent {doc['permanent_water_area_km2']} km2, NEW FLOOD {doc['flooded_area_km2']} km2, "
              f"zones {len(zones)}, inference {doc['timing_s']['inference']} s, total {time.perf_counter() - t:.0f} s")
        for z in top:
            print(f"   {z['name'][:40]:40} flooded {z['flooded_pct']:.1%}  water {z['water_pct']:.1%}  permanent {z['permanent_water_pct']:.1%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

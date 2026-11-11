"""Download the WorldPop 2020 1 km population raster for India (not committed, ~30 MB).

    python scripts/download_worldpop.py            # -> data/geo/worldpop/ind_ppp_2020_1km_Aggregated.tif
    python scripts/download_worldpop.py --force    # re-download

Run from ``backend/``. When the file is absent, ``services.geo.population`` falls back to
OSM building counts; ``scripts/build_scenario.py`` reports which source it used.
Source: WorldPop (www.worldpop.org), School of Geography and Environmental Science,
University of Southampton. Licence: CC BY 4.0.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.geo.population import WORLDPOP_URL, worldpop_path  # noqa: E402


def download(url: str = WORLDPOP_URL, target: Path | None = None, force: bool = False, chunk: int = 1 << 20) -> Path:
    target = target or worldpop_path()
    if target.is_file() and not force:
        print(f"already present: {target}")
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".part")
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        with partial.open("wb") as handle:
            for block in response.iter_content(chunk):
                handle.write(block)
                done += len(block)
                if total:
                    print(f"\r{done / 1e6:7.1f} / {total / 1e6:.1f} MB", end="", flush=True)
    partial.replace(target)
    print(f"\nsaved {target}")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--url", default=WORLDPOP_URL)
    args = parser.parse_args()
    download(args.url, force=args.force)

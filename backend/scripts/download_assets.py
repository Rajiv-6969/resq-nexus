"""Download the damage-model assets from the GitHub release (never committed).

    python scripts/download_assets.py            # -> data/assets/
    python scripts/download_assets.py --force

Assets (release tag ``v0.5-demo``, named "assets", repo Rajiv-6969/resq-nexus):

* ``resq_damage.onnx``            - the damage model (119 MB)
* ``test_results.json``           - xBD test-set metrics for the Analytics page
* ``xbd_sample.zip``              - 30 xBD test tiles, unzipped to ``data/assets/xbd_sample/``
* ``xview_geotransforms.json.tgz`` - pixel -> lat/lon transforms, unpacked next to it

Uses the ``gh`` CLI when available, else the public release download URLs. Missing assets
are reported, not fatal: without the model the app uses ground-truth labels; without the
samples the New Incident page shows how to install them.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paths import DATA_DIR  # noqa: E402

ASSET_DIR = DATA_DIR / "assets"
REPO = "Rajiv-6969/resq-nexus"
TAG = "v0.5-demo"
ASSETS = ("resq_damage.onnx", "test_results.json", "xbd_sample.zip", "xview_geotransforms.json.tgz", "resq_flood.onnx")


def _gh() -> str | None:
    for candidate in ("gh", r"C:\Program Files\GitHub CLI\gh.exe"):
        if shutil.which(candidate) or Path(candidate).is_file():
            return candidate
    return None


def download(name: str, force: bool = False) -> Path | None:
    target = ASSET_DIR / name
    if target.is_file() and not force:
        print(f"present  {name}")
        return target
    if os.getenv("OFFLINE_MODE", "0") == "1":
        if target.is_file():
            print(f"present  {name} (offline)")
            return target
        print(f"offline  {name} (skipped)")
        return None
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    gh = _gh()
    if gh:
        try:
            result = subprocess.run([gh, "release", "download", TAG, "--repo", REPO, "--pattern", name, "--dir", str(ASSET_DIR), "--clobber"],
                                    capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and target.is_file():
                print(f"fetched  {name}")
                return target
        except Exception:
            pass
    url = f"https://github.com/{REPO}/releases/download/{TAG}/{name}"
    try:
        with requests.get(url, stream=True, timeout=15) as response:
            if response.status_code != 200:
                print(f"MISSING  {name} (HTTP {response.status_code}; optional or deferred asset)")
                return None
            with target.open("wb") as handle:
                for block in response.iter_content(1 << 20):
                    handle.write(block)
        print(f"fetched  {name}")
        return target
    except Exception as e:
        print(f"MISSING  {name} ({e}; optional or deferred asset)")
        return None


def unpack(path: Path) -> None:
    if path.suffix == ".zip":
        out = ASSET_DIR / path.stem
        with zipfile.ZipFile(path) as archive:
            archive.extractall(out)
        print(f"unpacked {path.name} -> {out}")
    elif path.name.endswith(".tgz"):
        with tarfile.open(path) as archive:
            archive.extractall(ASSET_DIR, filter="data")
        print(f"unpacked {path.name} -> {ASSET_DIR}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true")
    parser.add_argument("names", nargs="*", default=list(ASSETS))
    args = parser.parse_args(argv)
    missing = []
    for name in args.names:
        path = download(name, args.force)
        if path is None:
            missing.append(name)
        elif name.endswith((".zip", ".tgz")):
            unpack(path)
    if missing:
        print(f"{len(missing)} asset(s) missing: {', '.join(missing)} - the app falls back where it can")
    return 0


if __name__ == "__main__":
    sys.exit(main())

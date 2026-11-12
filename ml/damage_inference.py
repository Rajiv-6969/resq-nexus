"""Damage assessment inference interface (ML pipeline).

Direct CLI & module wrapper for running ResNet34 FPN ONNX damage model
with object majority voting on satellite image pairs.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from services.damage.inference import assess_image_pair, get_damage_session


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ResQ Nexus ONNX Damage Assessment")
    parser.add_argument("--pre", required=True, help="Path to pre-disaster image")
    parser.add_argument("--post", required=True, help="Path to post-disaster image")
    parser.add_argument("--bounds", help="JSON bounds {south, west, north, east}", default=None)
    parser.add_argument("--output", help="Output JSON path", default=None)
    args = parser.parse_args(argv)

    if not Path(args.pre).is_file() or not Path(args.post).is_file():
        print("Error: Image files do not exist", file=sys.stderr)
        return 1

    pre_img = Image.open(args.pre)
    post_img = Image.open(args.post)

    bounds = {"south": 12.90, "west": 77.60, "north": 13.00, "east": 77.70}
    if args.bounds:
        bounds = json.loads(args.bounds)

    result = assess_image_pair(pre_img, post_img, bounds)
    out_dict = {
        "building_count": len(result.buildings),
        "zone_count": len(result.zones),
        "counts": result.counts,
        "timing": result.timing,
        "zones": [z.model_dump() for z in result.zones],
    }

    if args.output:
        Path(args.output).write_text(json.dumps(out_dict, indent=2), encoding="utf-8")
        print(f"Results written to {args.output}")
    else:
        print(json.dumps(out_dict, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

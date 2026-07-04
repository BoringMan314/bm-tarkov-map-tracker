#!/usr/bin/env python3
"""DEPRECATED: DEV A streets now uses tarkov.dev SVG (see sync_streets_dev_a_svg.py)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAPS_DIR = ROOT / "internal" / "maps_tarkov.dev" / "streets"

sys.path.insert(0, str(ROOT / "tools"))
from download_tarkov_dev_maps import bounds_to_meta, fetch_maps_json  # noqa: E402
from sync_maps_from_eftarkov import composite_stitch, fetch, parse_config  # noqa: E402

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore


def map_variant(maps_data: list) -> dict:
    for entry in maps_data:
        if entry.get("normalizedName") != "streets-of-tarkov":
            continue
        for variant in entry.get("maps") or []:
            if variant.get("key") == "streets-of-tarkov" and variant.get("projection") == "interactive":
                return variant
    raise SystemExit("FAIL: streets variant not found")


def main() -> None:
    if Image is None:
        raise SystemExit("PIL required: pip install Pillow")
    Image.MAX_IMAGE_PIXELS = None

    maps_data = fetch_maps_json()
    variant = map_variant(maps_data)
    if variant.get("tilePath"):
        raise SystemExit("streets now has tilePath; use download_tarkov_dev_maps.py")

    html = fetch("https://api.eftarkov.com/map/streets/").decode("utf-8", "replace")
    cfg = parse_config(html)
    png_bytes, w, h, _level, _cols, _rows = composite_stitch("streets", cfg)
    print(f"OK eftarkov streets -> {w:.0f}x{h:.0f}")

    meta = bounds_to_meta(
        variant["bounds"],
        variant.get("coordinateRotation", 180),
        "streets",
        variant.get("transform"),
    )
    meta["name"] = "streets"
    meta["display_name"] = "Streets of Tarkov"
    meta["description"] = ""
    meta["width"] = float(w)
    meta["height"] = float(h)

    MAPS_DIR.mkdir(parents=True, exist_ok=True)
    svg = MAPS_DIR / "map.svg"
    if svg.is_file():
        svg.unlink()
        print("removed streets/map.svg (satellite PNG)")
    (MAPS_DIR / "map.png").write_bytes(png_bytes)
    (MAPS_DIR / "meta.json").write_text(
        json.dumps(meta, indent=4, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"OK streets/map.png {int(w)}x{int(h)} ({len(png_bytes)/1024/1024:.1f} MB)")


if __name__ == "__main__":
    main()

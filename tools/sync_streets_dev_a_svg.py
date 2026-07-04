#!/usr/bin/env python3
"""DEV A streets: same tarkov.dev SVG + meta as variant B."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAPS_DIR = ROOT / "internal" / "maps_tarkov.dev" / "streets"
SVG_URL = "https://assets.tarkov.dev/maps/svg/StreetsOfTarkov.svg"
SVG_LAYER = "Ground_Level"

sys.path.insert(0, str(ROOT / "tools"))
from download_tarkov_dev_maps import (  # noqa: E402
    bounds_to_meta,
    extract_svg_layer,
    fetch,
    fetch_maps_json,
    normalize_svg_bytes,
    parse_viewbox,
)


def map_variant(maps_data: list) -> dict:
    for entry in maps_data:
        if entry.get("normalizedName") != "streets-of-tarkov":
            continue
        for variant in entry.get("maps") or []:
            if variant.get("key") == "streets-of-tarkov" and variant.get("projection") == "interactive":
                return variant
    raise SystemExit("FAIL: streets variant not found")


def main() -> None:
    maps_data = fetch_maps_json()
    variant = map_variant(maps_data)
    if variant.get("tilePath"):
        raise SystemExit("streets now has tilePath; use download_tarkov_dev_maps.py")

    data = fetch(variant.get("svgPath") or SVG_URL)
    data = extract_svg_layer(data, variant.get("svgLayer") or SVG_LAYER)
    data = normalize_svg_bytes(data)
    w, h, _ = parse_viewbox(data)

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
    png = MAPS_DIR / "map.png"
    if png.is_file():
        png.unlink()
        print("removed streets/map.png (COM/eftarkov raster)")
    (MAPS_DIR / "map.svg").write_bytes(data)
    (MAPS_DIR / "meta.json").write_text(
        json.dumps(meta, indent=4, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"OK streets/map.svg ({len(data)} bytes, viewBox {w}x{h})")


if __name__ == "__main__":
    main()

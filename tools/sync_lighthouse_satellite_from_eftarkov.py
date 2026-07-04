#!/usr/bin/env python3
"""DEPRECATED: DEV A lighthouse uses tarkov.dev SVG (see sync_lighthouse_dev_a_svg.py)."""

from __future__ import annotations

import json
import base64
import sys
import urllib.request
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAPS_DIR = ROOT / "internal" / "maps_tarkov.dev" / "lighthouse"
MAPS_JSON_URL = "https://raw.githubusercontent.com/the-hideout/tarkov-dev/main/src/data/maps.json"
MAPS_JSON_API = "https://api.github.com/repos/the-hideout/tarkov-dev/contents/src/data/maps.json"
USER_AGENT = "bm-tarkov-map-tracker/1.0"

# Reuse eftarkov stitcher (same tiles as maps_eftarkov.com).
sys.path.insert(0, str(ROOT / "tools"))
from sync_maps_from_eftarkov import composite_stitch, fetch, parse_config  # noqa: E402

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore


def fetch_maps_json() -> list:
    req = urllib.request.Request(MAPS_JSON_URL, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except OSError:
        api_req = urllib.request.Request(MAPS_JSON_API, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(api_req, timeout=120) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return json.loads(base64.b64decode(payload["content"]))


def map_variant(maps_data: list) -> dict:
    for entry in maps_data:
        if entry.get("normalizedName") != "lighthouse":
            continue
        for variant in entry.get("maps") or []:
            if variant.get("key") == "lighthouse" and variant.get("projection") == "interactive":
                return variant
    raise SystemExit("FAIL: lighthouse variant not found")


def bounds_to_meta(bounds: list, rotation: int, transform: list | None) -> dict:
    xmax, zmin = bounds[0]
    xmin, zmax = bounds[1]
    meta = {
        "name": "lighthouse",
        "display_name": "Lighthouse",
        "description": "",
        "xmin": round(float(xmin), 4),
        "xmax": round(float(xmax), 4),
        "zmin": round(float(zmin), 4),
        "zmax": round(float(zmax), 4),
        "coordinates_rotation": int(rotation),
    }
    if transform and len(transform) >= 4:
        meta["transform"] = [float(v) for v in transform[:4]]
    return meta


def main() -> None:
    if Image is None:
        raise SystemExit("PIL required: pip install Pillow")
    Image.MAX_IMAGE_PIXELS = None

    maps_data = fetch_maps_json()
    variant = map_variant(maps_data)
    if variant.get("tilePath"):
        raise SystemExit("tarkov.dev now has tilePath; use download_tarkov_dev_maps.py instead")

    html = fetch("https://api.eftarkov.com/map/lighthouse/").decode("utf-8", "replace")
    cfg = parse_config(html)
    png_bytes, w, h, level, cols, rows = composite_stitch("lighthouse", cfg)
    print(f"OK eftarkov lighthouse level={level} grid={cols}x{rows} -> {w:.0f}x{h:.0f}")

    meta = bounds_to_meta(
        variant["bounds"],
        variant.get("coordinateRotation", 180),
        variant.get("transform"),
    )
    meta["width"] = float(w)
    meta["height"] = float(h)

    MAPS_DIR.mkdir(parents=True, exist_ok=True)
    svg = MAPS_DIR / "map.svg"
    if svg.is_file():
        svg.unlink()
        print("removed lighthouse/map.svg (satellite PNG)")
    (MAPS_DIR / "map.png").write_bytes(png_bytes)
    (MAPS_DIR / "meta.json").write_text(
        json.dumps(meta, indent=4, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"OK lighthouse/map.png {int(w)}x{int(h)} ({len(png_bytes)/1024/1024:.1f} MB)")


if __name__ == "__main__":
    main()

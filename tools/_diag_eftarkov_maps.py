#!/usr/bin/env python3
"""Quick diagnostic for eftarkov map tile configs and local PNG coverage."""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

try:
    from PIL import Image

    # streets L3 stitch can exceed PIL's default decompression bomb limit.
    Image.MAX_IMAGE_PIXELS = max(Image.MAX_IMAGE_PIXELS or 0, 512 * 1024 * 1024)
except ImportError:
    Image = None

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "internal" / "maps_eftarkov.com"
BASE = "https://api.eftarkov.com/map"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://api.eftarkov.com/",
}

MAPS = [
    ("factory", "factory"),
    ("groundzero", "ground-zero"),
    ("interchange", "interchange"),
    ("lighthouse", "lighthouse"),
    ("customs", "customs"),
    ("shoreline", "shoreline"),
    ("reserve", "reserve"),
    ("woods", "woods"),
    ("streets", "streets"),
]


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.read()


def parse_config(html: str) -> dict:
    folders = re.search(r"totalFolders:\s*\[([^\]]+)\]", html)
    per_folder = re.search(r"imagesPerFolder:\s*\[([^\]]+)\]", html)
    paths = re.search(r"basePaths:\s*\[([\s\S]*?)\],", html)
    tile = re.search(r"tileSize:\s*(\d+)", html)
    total_folders = [int(x.strip()) for x in folders.group(1).split(",")]
    images_per_folder = [int(x.strip()) for x in per_folder.group(1).split(",")]
    base_paths = re.findall(r"'([^']+)'", paths.group(1))
    if not base_paths:
        base_paths = re.findall(r'"([^"]+)"', paths.group(1))
    return {
        "total_folders": total_folders,
        "images_per_folder": images_per_folder,
        "base_paths": base_paths,
        "tile_size": int(tile.group(1)),
    }


def probe_tile(url: str) -> bool:
    try:
        data = fetch(url)
        return len(data) >= 120
    except OSError:
        return False


def main() -> None:
    print("=== remote configs ===")
    for map_id, slug in MAPS:
        try:
            html = fetch(f"{BASE}/{slug}/").decode("utf-8", "replace")
            cfg = parse_config(html)
            print(f"\n{map_id} ({slug})")
            for lv in range(len(cfg["total_folders"])):
                cols = cfg["total_folders"][lv]
                rows = cfg["images_per_folder"][lv]
                bp = cfg["base_paths"][lv]
                total = cols * rows
                # probe corners + center
                probes = [(0, 0), (cols - 1, rows - 1), (cols // 2, rows // 2)]
                hits = 0
                for c, r in probes:
                    rel = bp if bp.startswith("http") else f"{BASE}/{slug}/{bp}"
                    url = f"{rel.rstrip('/')}/{c}/{r}.webp"
                    if probe_tile(url):
                        hits += 1
                print(
                    f"  L{lv}: {cols}x{rows}={total} path={bp[:60]} probe={hits}/3"
                )
        except Exception as e:
            print(f"\n{map_id}: ERROR {e}")

    if Image is None:
        return
    print("\n=== local maps ===")
    for map_id, _ in MAPS:
        png = OUT / map_id / "map.png"
        meta_path = OUT / map_id / "meta.json"
        if not png.exists():
            print(f"{map_id}: MISSING")
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        with Image.open(png) as im:
            cols, rows = meta["eftarkov_cols"], meta["eftarkov_rows"]
            ts = meta["eftarkov_tile_size"]
            exp = (cols * ts, rows * ts)
            alpha = im.getchannel("A") if im.mode in ("RGBA", "LA") else None
            if alpha is not None:
                hist = alpha.histogram()
                opaque = sum(hist[i] for i in range(11, 256))
            else:
                opaque = im.size[0] * im.size[1]
            print(
                f"{map_id}: {im.size} expected {exp} opaque {100 * opaque / (im.size[0] * im.size[1]):.1f}%"
            )


if __name__ == "__main__":
    main()

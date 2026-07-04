#!/usr/bin/env python3
"""Full COM (eftarkov.com) audit: remote grid, local PNG, points bounds."""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

try:
    from PIL import Image

    Image.MAX_IMAGE_PIXELS = max(Image.MAX_IMAGE_PIXELS or 0, 512 * 1024 * 1024)
except ImportError:
    print("PIL required: pip install Pillow")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "internal" / "maps_eftarkov.com"
PTS = ROOT / "internal" / "points" / "eftarkov"
BASE = "https://api.eftarkov.com/map"
UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://api.eftarkov.com/"}

MAPS = [
    ("factory", "factory"),
    ("groundzero", "ground-zero"),
    ("interchange", "interchange"),
    ("lighthouse", "lighthouse"),
    ("labs", "the-lab"),
    ("customs", "customs"),
    ("shoreline", "shoreline"),
    ("reserve", "reserve"),
    ("woods", "woods"),
    ("streets", "streets"),
]


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.read().decode("utf-8", "replace")


def parse_remote(html: str) -> tuple[list[int], list[int], int]:
    folders = [int(x.strip()) for x in re.search(r"totalFolders:\s*\[([^\]]+)\]", html).group(1).split(",")]
    rows = [int(x.strip()) for x in re.search(r"imagesPerFolder:\s*\[([^\]]+)\]", html).group(1).split(",")]
    tile = int(re.search(r"tileSize:\s*(\d+)", html).group(1))
    return folders, rows, tile


def eftarkov_to_display_px(
    mx: float,
    my: float,
    cols: int,
    rows: int,
    tile: int,
    map_w: int,
    map_h: int,
    off_x: int = 0,
    off_y: int = 0,
) -> tuple[float, float]:
    ew, eh = cols * tile, rows * tile
    cw, ch = ew - off_x, eh - off_y
    sx = mx + ew / 2 - off_x
    sy = my + eh / 2 - off_y
    px = (sx / cw) * map_w if map_w < cw else sx
    py = sy if map_h < ch else (sy / ch) * map_h
    return px, py


def main() -> None:
    issues: list[str] = []
    points_meta = json.loads((PTS / "meta.json").read_text(encoding="utf-8"))

    print("=== remote grid vs local meta ===")
    for mid, slug in MAPS:
        html = fetch(f"{BASE}/{slug}/")
        cols_list, rows_list, tile = parse_remote(html)
        meta = json.loads((OUT / mid / "meta.json").read_text(encoding="utf-8"))
        pt = points_meta[mid]
        lc, lr = int(meta["eftarkov_cols"]), int(meta["eftarkov_rows"])
        lv = int(meta.get("eftarkov_level", -1))
        remote_match = next((i for i, (c, r) in enumerate(zip(cols_list, rows_list)) if c == lc and r == lr), None)
        with Image.open(OUT / mid / "map.png") as im:
            pw, ph = im.size
        off_x = int(meta.get("map_offset_x") or 0)
        off_y = int(meta.get("map_offset_y") or 0)
        ew, eh = lc * tile, lr * tile
        trim_h = eh - off_y - ph
        trim_w = ew - off_x - pw
        status = "OK"
        if remote_match is None:
            issues.append(f"{mid}: grid {lc}x{lr} not in remote {list(zip(cols_list, rows_list))}")
            status = "GRID?"
        elif remote_match != lv:
            issues.append(f"{mid}: meta level L{lv} but grid matches remote L{remote_match}")
            status = f"LV{remote_match}"
        if trim_w < 0:
            issues.append(f"{mid}: png width exceeds grid by {-trim_w}px")
            status = "BAD-W"
        if trim_h < 0:
            issues.append(f"{mid}: png height exceeds grid by {-trim_h}px")
            status = "BAD-H"
        if pt["cols"] != lc or pt["rows"] != lr or pt["tile_size"] != tile:
            issues.append(f"{mid}: points meta grid mismatch")
            status = "PTS-GRID"
        print(
            f"{mid:<12} grid {lc}x{lr}@L{lv} png {pw}x{ph} "
            f"offset=({off_x},{off_y}) trim=({trim_w},{trim_h}) pts@L{pt['level']} [{status}]"
        )

    print("\n=== exfil coords vs displayed PNG ===")
    out_of_bounds = 0
    for kind in ("pmc", "scav", "transit", "coop"):
        data = json.loads((PTS / f"{kind}.json").read_text(encoding="utf-8"))
        for mid, _slug in MAPS:
            layout = points_meta[mid]
            meta = json.loads((OUT / mid / "meta.json").read_text(encoding="utf-8"))
            mw, mh = int(meta["width"]), int(meta["height"])
            off_x = int(meta.get("map_offset_x") or 0)
            off_y = int(meta.get("map_offset_y") or 0)
            for pt in data.get(mid, []):
                mx, my = pt["coordinates"]
                px, py = eftarkov_to_display_px(
                    float(mx),
                    float(my),
                    layout["cols"],
                    layout["rows"],
                    layout["tile_size"],
                    mw,
                    mh,
                    off_x,
                    off_y,
                )
                if px < -80 or px > mw + 80 or py < -80 or py > mh + 80:
                    out_of_bounds += 1
                    name = pt.get("name", pt.get("id", "?"))
                    issues.append(
                        f"{mid}/{kind}/{name}: ({px:.0f},{py:.0f}) outside {mw}x{mh}"
                    )
    if out_of_bounds == 0:
        print("all exfil/transit/coop points within displayed map bounds")
    else:
        print(f"{out_of_bounds} point(s) out of bounds")

    print("\n=== duplicate names per map/kind ===")
    dupes = 0
    for kind in ("pmc", "scav", "transit", "coop"):
        data = json.loads((PTS / f"{kind}.json").read_text(encoding="utf-8"))
        for mid, _slug in MAPS:
            names = [p.get("name", "") for p in data.get(mid, [])]
            seen: set[str] = set()
            for n in names:
                if n in seen:
                    dupes += 1
                    issues.append(f"{mid}/{kind}: duplicate name {n!r}")
                seen.add(n)
    if dupes == 0:
        print("no duplicate point names")

    print(f"\n=== summary: {len(issues)} issue(s) ===")
    if issues:
        for item in issues:
            print(f"  - {item}".encode("utf-8", "replace").decode("utf-8"))
        sys.exit(1)
    print("all COM checks passed")


if __name__ == "__main__":
    main()

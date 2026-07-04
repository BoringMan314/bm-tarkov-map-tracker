#!/usr/bin/env python3
"""Probe customs satellite tiles at z=4..6."""
from __future__ import annotations

import urllib.request
from concurrent.futures import ThreadPoolExecutor

TILE_URL = "https://assets.tarkov.dev/maps/customs_0.16/main/{z}/{x}/{y}.png"
UA = {"User-Agent": "bm-tarkov-map-tracker/1.0"}
MIN = 4000
SCAN = 24


def probe(z: int) -> None:
    def hit(xy):
        x, y = xy
        try:
            req = urllib.request.Request(TILE_URL.format(z=z, x=x, y=y), headers=UA)
            data = urllib.request.urlopen(req, timeout=30).read()
            if len(data) >= MIN:
                return x, y
        except OSError:
            pass
        return None

    jobs = [(x, y) for x in range(SCAN) for y in range(SCAN)]
    coords = []
    with ThreadPoolExecutor(max_workers=16) as pool:
        for r in pool.map(hit, jobs):
            if r:
                coords.append(r)
    if not coords:
        print(f"z={z}: no tiles in {SCAN}x{SCAN}")
        return
    min_x = min(x for x, _ in coords)
    max_x = max(x for x, _ in coords)
    min_y = min(y for _, y in coords)
    max_y = max(y for _, y in coords)
    w, h = max_x - min_x + 1, max_y - min_y + 1
    fill = len(coords) / max(w * h, 1)
    print(
        f"z={z}: count={len(coords)} bbox=({min_x},{min_y})-({max_x},{max_y}) "
        f"grid={w}x{h} fill={fill:.1%} px={w*256}x{h*256}"
    )


if __name__ == "__main__":
    for z in (4, 5, 6):
        probe(z)

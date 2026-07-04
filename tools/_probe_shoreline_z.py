#!/usr/bin/env python3
from concurrent.futures import ThreadPoolExecutor
import urllib.request

TILE_URL = "https://assets.tarkov.dev/maps/shoreline/main_summer/{z}/{x}/{y}.png"
UA = {"User-Agent": "bm"}
MIN = 4000


def probe(z: int, scan: int = 32):
    def at(xy):
        x, y = xy
        u = TILE_URL.format(z=z, x=x, y=y)
        try:
            d = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=15).read()
            if len(d) >= MIN:
                return x, y
        except OSError:
            pass
        return None

    jobs = [(x, y) for x in range(scan) for y in range(scan)]
    hits = []
    with ThreadPoolExecutor(24) as p:
        for h in p.map(at, jobs):
            if h:
                hits.append(h)
    if not hits:
        print(f"z={z}: no tiles in {scan}x{scan}")
        return
    min_x = min(x for x, _ in hits)
    max_x = max(x for x, _ in hits)
    min_y = min(y for _, y in hits)
    max_y = max(y for _, y in hits)
    w = max_x - min_x + 1
    h = max_y - min_y + 1
    area = w * h
    print(
        f"z={z} hits={len(hits)} bbox=({min_x},{min_y})-({max_x},{max_y}) "
        f"grid={w}x{h} px={w*256}x{h*256} fill={len(hits)/area:.1%}"
    )


for z in (6, 5, 4, 3):
    probe(z)

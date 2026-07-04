#!/usr/bin/env python3
"""Compare factory satellite fill at z=4 vs z=5."""
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

from PIL import Image

UA = "bm-tarkov-map-tracker/1.0"
TILE = "https://assets.tarkov.dev/maps/factory/main/{z}/{x}/{y}.png"


def fetch_tile(z, x, y):
    url = TILE.format(z=z, x=x, y=y)
    try:
        data = urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": UA}), timeout=15
        ).read()
        if len(data) < 4000:
            return None
        im = Image.open(BytesIO(data)).convert("RGBA")
        bb = im.getbbox()
        if not bb:
            return None
        area = (bb[2] - bb[0]) * (bb[3] - bb[1])
        return x, y, len(data), area
    except Exception:
        return None


def scan_zoom(z, scan=32):
    jobs = [(x, y) for x in range(scan) for y in range(scan)]
    hits = []
    with ThreadPoolExecutor(max_workers=20) as pool:
        for r in pool.map(lambda xy: fetch_tile(z, *xy), jobs):
            if r:
                hits.append(r)
    if not hits:
        return
    xs, ys = [h[0] for h in hits], [h[1] for h in hits]
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
    w, h = max_x - min_x + 1, max_y - min_y + 1
    avg_area = sum(h[3] for h in hits) / len(hits)
    print(
        f"z={z} tiles={len(hits)} bbox=({min_x},{min_y})-({max_x},{max_y}) "
        f"grid={w}x{h} fill={len(hits)/(w*h):.1%} avg_content_area={avg_area:.0f}px"
    )


for z in (4, 5):
    scan_zoom(z)

#!/usr/bin/env python3
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path

from PIL import Image

TILE = "https://assets.tarkov.dev/maps/factory/main/4/{x}/{y}.png"
ROOT = Path(__file__).resolve().parent.parent


def fetch(xy):
    x, y = xy
    url = TILE.format(x=x, y=y)
    try:
        data = urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": "bm"}), timeout=15
        ).read()
        return x, y, len(data)
    except Exception:
        return x, y, 0


coords = [(x, y) for x in range(16) for y in range(16)]
sizes = {}
with ThreadPoolExecutor(max_workers=16) as pool:
    for x, y, sz in pool.map(fetch, coords):
        sizes[(x, y)] = sz

real = [(x, y, sz) for (x, y), sz in sizes.items() if sz >= 4000]
small = [(x, y, sz) for (x, y), sz in sizes.items() if 0 < sz < 4000]
missing = [(x, y) for (x, y), sz in sizes.items() if sz == 0]
print(f"z=4 grid 16x16: real(>=4k)={len(real)} small={len(small)} missing={len(missing)}")
if real:
    rx = [x for x, _, _ in real]
    ry = [y for _, y, _ in real]
    print(f"real bbox: x={min(rx)}..{max(rx)} y={min(ry)}..{max(ry)}")
print("real tiles:", sorted(real)[:20], "..." if len(real) > 20 else "")

im = Image.open(ROOT / "internal/maps_tarkov.dev/factory/map.png").convert("RGBA")
# find bounding box of non-transparent content
bbox = im.getbbox()
print("PNG content bbox (non-empty alpha):", bbox)

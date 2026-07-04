#!/usr/bin/env python3
"""Find optimal factory z=4 tile set without interior holes."""
import urllib.request
from concurrent.futures import ThreadPoolExecutor

TILE = "https://assets.tarkov.dev/maps/factory/main/4/{x}/{y}.png"
MIN_REAL = 10000  # skip 102-byte placeholders


def fetch_size(xy):
    x, y = xy
    try:
        data = urllib.request.urlopen(
            urllib.request.Request(TILE.format(x=x, y=y), headers={"User-Agent": "bm"}),
            timeout=15,
        ).read()
        return x, y, len(data)
    except Exception:
        return x, y, 0


coords = [(x, y) for x in range(16) for y in range(16)]
real = []
with ThreadPoolExecutor(max_workers=16) as pool:
    for x, y, sz in pool.map(fetch_size, coords):
        if sz >= MIN_REAL:
            real.append((x, y, sz))

print(f"real tiles (>={MIN_REAL}B): {len(real)}")
if real:
    xs = [t[0] for t in real]
    ys = [t[1] for t in real]
    print(f"bbox x={min(xs)}..{max(xs)} y={min(ys)}..{max(ys)}")
    w, h = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
    print(f"grid {w}x{h} = {w*h} cells, fill {len(real)/(w*h):.1%}")

    # check holes in bbox
    s = set((x, y) for x, y, _ in real)
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
    holes = [
        (x, y)
        for x in range(min_x, max_x + 1)
        for y in range(min_y, max_y + 1)
        if (x, y) not in s
    ]
    print(f"holes in bbox: {len(holes)}")
    if holes[:20]:
        print(" sample holes", holes[:20])

    print("\ngrid map:")
    for y in range(min_y, max_y + 1):
        row = ""
        for x in range(min_x, max_x + 1):
            row += "#" if (x, y) in s else "."
        print(f"y={y:2d} {row}")

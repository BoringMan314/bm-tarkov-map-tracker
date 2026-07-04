#!/usr/bin/env python3
"""Score interchange marker mapping at z=4 on fresh stitch."""
import json
import math
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path

from PIL import Image

Image.MAX_IMAGE_PIXELS = 500_000_000
ROOT = Path(__file__).resolve().parent.parent
pmc = json.loads((ROOT / "internal/points/exfil/pmc.json").read_text()).get("interchange", [])
UA = "bm-tarkov-map-tracker/1.0"
TILE = "https://assets.tarkov.dev/maps/interchange/main/4/{x}/{y}.png"
Z = 4
MIN_B = 4000
LAND = (31, 80, 84, 255)  # fallback
t = [0.265, 150.6, 0.265, 134.6]
rot = 180


def fetch(xy):
    x, y = xy
    try:
        d = urllib.request.urlopen(
            urllib.request.Request(TILE.format(x=x, y=y), headers={"User-Agent": UA}),
            timeout=20,
        ).read()
        return x, y, d if len(d) >= MIN_B else None
    except Exception:
        return x, y, None


def rot_ll(gz, gx, r):
    rad = math.radians(r)
    c, s = math.cos(rad), math.sin(rad)
    return gx * s + gz * c, gx * c - gz * s


def layer(gx, gz, ymode):
    lat, lng = rot_ll(gz, gx, rot)
    cx = t[0] * lng + t[1]
    if ymode == "neg":
        cy = (-t[2]) * lat + t[3]
    else:
        cy = (-t[2]) * (-lat) + t[3]
    f = 2**Z
    return cx * f, cy * f


jobs = [(x, y) for x in range(16) for y in range(16)]
tiles = {}
with ThreadPoolExecutor(16) as pool:
    for x, y, data in pool.map(fetch, jobs):
        if data:
            tiles[(x, y)] = data

min_x = min(x for x, _ in tiles)
max_x = max(x for x, _ in tiles)
min_y = min(y for _, y in tiles)
max_y = max(y for _, y in tiles)
w = (max_x - min_x + 1) * 256
h = (max_y - min_y + 1) * 256
canvas = Image.new("RGBA", (w, h), LAND)
for (x, y), data in tiles.items():
    tile = Image.open(BytesIO(data)).convert("RGBA")
    canvas.paste(tile, ((x - min_x) * 256, (y - min_y) * 256), tile)

print(f"stitch {w}x{h} tiles={len(tiles)} bbox {min_x},{min_y}-{max_x},{max_y}")
b = dict(minX=min_x * 256, minY=min_y * 256, maxX=(max_x + 1) * 256, maxY=(max_y + 1) * 256)

for ymode in ("app", "neg"):
    hits = 0
    print(f"ymode={ymode}")
    for p in pmc:
        gx, gz = p["coordinates"]
        lx, ly = layer(gx, gz, ymode)
        px = (lx - b["minX"]) / (b["maxX"] - b["minX"]) * w
        py = (ly - b["minY"]) / (b["maxY"] - b["minY"]) * h
        ok = False
        if 0 <= px < w and 0 <= py < h:
            r, g, b0, a = canvas.getpixel((int(px), int(py)))
            ok = a > 128 and (r + g + b0) > 40
            hits += ok
        print(f"  {p['name'][:22]:22} ({int(px)},{int(py)}) {ok}")
    print(" hits", hits, "/", len(pmc))

out = ROOT / "tools" / "_interchange_z4_test.png"
canvas.save(out)
print("saved", out)

#!/usr/bin/env python3
"""Analyze factory DEV A PNG black regions and point alignment."""
import json
import math
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
meta = json.loads((ROOT / "internal/maps_tarkov.dev/factory/meta.json").read_text())
pmc = json.loads((ROOT / "internal/points/exfil/pmc.json").read_text())["factory"]
png = ROOT / "internal/maps_tarkov.dev/factory/map.png"
im = Image.open(png).convert("RGBA")
w, h = im.size
t = meta["transform"]
rot = 90
F = 2 ** int(meta["tile_zoom"])
ts = meta["tile_size"]


def rot_ll(gz, gx, r):
    rad = math.radians(r)
    c, s = math.cos(rad), math.sin(rad)
    return gx * s + gz * c, gx * c - gz * s


def to_px(gx, gz):
    lat, lng = rot_ll(gz, gx, rot)
    cx, cy = t[0] * lng + t[1], (-t[2]) * lat + t[3]
    lx, ly = cx * F, cy * F
    bminx = meta["tile_min_x"] * ts
    bminy = meta["tile_min_y"] * ts
    bmaxx = (meta["tile_max_x"] + 1) * ts
    bmaxy = (meta["tile_max_y"] + 1) * ts
    return (
        (lx - bminx) / (bmaxx - bminx) * w,
        (ly - bminy) / (bmaxy - bminy) * h,
    )


print("PNG size", im.size, "meta", meta["width"], meta["height"])
print("tile bbox", meta["tile_min_x"], meta["tile_min_y"], meta["tile_max_x"], meta["tile_max_y"])

# content bbox
bbox = im.getbbox()
print("non-empty alpha bbox", bbox)

# scan 16x16 tile grid for content
print("\nTile grid content (z=4, 256px cells):")
for ty in range(16):
    row = ""
    for tx in range(16):
        x0, y0 = tx * 256, ty * 256
        patch = im.crop((x0, y0, x0 + 256, y0 + 256))
        pb = patch.getbbox()
        row += "#" if pb else "."
    print(f"y={ty:2d} {row}")

print("\nMarkers:")
for p in pmc:
    x, y = to_px(*p["coordinates"])
    ok = 0 <= x < w and 0 <= y < h
    if ok:
        r, g, b, a = im.getpixel((int(x), int(y)))
        dark = a < 128 or (r + g + b) < 40
        print(f"  {p['name']:18} ({x:6.0f},{y:6.0f}) dark={dark} a={a}")
    else:
        print(f"  {p['name']:18} OOB")

# compare with tarkov.dev z=4 tile probe at center
print("\nTile bytes at center region (from CDN HEAD):")

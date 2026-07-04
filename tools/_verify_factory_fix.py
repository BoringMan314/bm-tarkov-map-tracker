#!/usr/bin/env python3
"""Verify factory fixes match app.js logic."""
import json
import math
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
meta_a = json.loads((ROOT / "internal/maps_tarkov.dev/factory/meta.json").read_text())
meta_b = json.loads((ROOT / "internal/maps_tarkov.dev_B/factory/meta.json").read_text())
pmc = json.loads((ROOT / "internal/points/exfil/pmc.json").read_text())["factory"]
im = Image.open(ROOT / "internal/maps_tarkov.dev/factory/map.png").convert("RGBA")
t = meta_a["transform"]
rot = 90
Z = int(meta_a["tile_zoom"])
F = 2**Z


def rot_ll(gz, gx, r):
    rad = math.radians(r)
    c, s = math.cos(rad), math.sin(rad)
    return gx * s + gz * c, gx * c - gz * s


def factory_crs(gx, gz):
    lat, lng = rot_ll(gz, gx, rot)
    cx = t[0] * lng + t[1]
    cy = (-t[2]) * lat + t[3]
    return cx, cy


def dev_a_px(gx, gz):
    cx, cy = factory_crs(gx, gz)
    lx, ly = cx * F, cy * F
    iw, ih = meta_a["width"], meta_a["height"]
    return lx / iw * iw, ly / ih * ih


def dev_b_px(gx, gz, m):
    span_x = m["xmax"] - m["xmin"]
    span_z = m["zmax"] - m["zmin"]
    u = (m["zmax"] - gz) / span_z
    v = (gx - m["xmin"]) / span_x
    return u * m["width"], v * m["height"]


def on_map(x, y):
    if not (0 <= x < im.width and 0 <= y < im.height):
        return False
    r, g, b, a = im.getpixel((int(x), int(y)))
    return a > 128 and (r + g + b) > 40


print("DEV A satellite (z=4, factory CRS Y)")
hits = 0
for p in pmc:
    x, y = dev_a_px(*p["coordinates"])
    ok = on_map(x, y)
    hits += ok
    print(f"  {p['name']:18} ({x:6.0f},{y:6.0f}) {'OK' if ok else 'MISS'}")
print(f"  => {hits}/{len(pmc)} on map pixels\n")

print("DEV B SVG (norm90, float bounds)")
for p in pmc:
    x, y = dev_b_px(*p["coordinates"], meta_b)
    in_box = 0 <= x <= meta_b["width"] and 0 <= y <= meta_b["height"]
    print(f"  {p['name']:18} ({x:5.1f},{y:5.1f}) inViewBox={in_box}")

#!/usr/bin/env python3
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
meta = json.loads((ROOT / "internal/maps_tarkov.dev/factory/meta.json").read_text())
pmc = json.loads((ROOT / "internal/points/exfil/pmc.json").read_text())["factory"]
t = meta["transform"]
ROT = meta["coordinates_rotation"]
Z = 4
f = 2**Z
iw, ih = 4096, 4096


def apply_rot(gz, gx, r):
    if not r:
        return gz, gx
    rad = math.radians(r)
    c, s = math.cos(rad), math.sin(rad)
    return gz * s + gx * c, gz * c - gx * s


def game_to_crs(gx, gz):
    lat, lng = apply_rot(gz, gx, ROT)
    sx, mx, sy, mz = t[0], t[1], t[2] * -1, t[3]
    return sx * lng + mx, sy * (-lat) + mz


def px(gx, gz):
    cx, cy = game_to_crs(gx, gz)
    lx, ly = cx * f, cy * f
    x = lx / 4096 * iw
    y = ly / 4096 * ih
    y = ih - y
    return int(x), int(y)


im = Image.open(ROOT / "internal/maps_tarkov.dev/factory/map.png").convert("RGBA")
draw = ImageDraw.Draw(im)
for p in pmc:
    x, y = px(*p["coordinates"])
    r = 12
    draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 200, 0, 230))
    print(f"{p['name']:18} ({x},{y})")
out = ROOT / "tools" / "_factory_fixed_overlay.png"
im.save(out)
print("saved", out)

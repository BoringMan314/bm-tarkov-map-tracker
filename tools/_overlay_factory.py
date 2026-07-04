#!/usr/bin/env python3
"""Overlay factory exfil points on map.png for visual check."""
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
iw, ih = int(meta["width"]), int(meta["height"])


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


def app_layer(gx, gz):
    lat, lng = apply_rot(gz, gx, ROT)
    sx, mx, sy, mz = t[0], t[1], t[2] * -1, t[3]
    return (sx * lng + mx) * f, (sy * lat + mz) * f


def fixed_layer(gx, gz):
    cx, cy = game_to_crs(gx, gz)
    return cx * f, cy * f


def px(layer_fn, gx, gz):
    lx, ly = layer_fn(gx, gz)
    return int(lx), int(ly)


im = Image.open(ROOT / "internal/maps_tarkov.dev/factory/map.png").convert("RGBA")
draw = ImageDraw.Draw(im)
for p in pmc:
    gx, gz = p["coordinates"]
    x1, y1 = px(app_layer, gx, gz)
    x2, y2 = px(fixed_layer, gx, gz)
    r = 8
    draw.ellipse((x1 - r, y1 - r, x1 + r, y1 + r), fill=(255, 0, 0, 200))
    draw.ellipse((x2 - r, y2 - r, x2 + r, y2 + r), fill=(0, 255, 0, 200))
    print(f"{p['name']:18} app=({x1},{y1}) fixed=({x2},{y2})")

out = ROOT / "tools" / "_factory_overlay.png"
im.save(out)
print("saved", out)

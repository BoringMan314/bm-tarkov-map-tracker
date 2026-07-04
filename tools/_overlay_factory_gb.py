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
iw, ih = int(meta["width"]), int(meta["height"])
xmin, xmax, zmin, zmax = meta["xmin"], meta["xmax"], meta["zmin"], meta["zmax"]


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


def game_bounds(layer_fn):
    corners = [(xmin, zmax), (xmax, zmin), (xmin, zmin), (xmax, zmax)]
    pts = [layer_fn(x, z) for x, z in corners]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def norm(layer_fn, gx, gz, bounds):
    min_x, min_y, max_x, max_y = bounds
    lx, ly = layer_fn(gx, gz)
    return int((lx - min_x) / (max_x - min_x) * iw), int((ly - min_y) / (max_y - min_y) * ih)


im = Image.open(ROOT / "internal/maps_tarkov.dev/factory/map.png").convert("RGBA")
draw = ImageDraw.Draw(im)
gb_app = game_bounds(app_layer)
gb_fix = game_bounds(fixed_layer)
print("game bounds app", gb_app)
print("game bounds fix", gb_fix)
for p in pmc:
    gx, gz = p["coordinates"]
    x1, y1 = norm(app_layer, gx, gz, gb_app)
    x2, y2 = norm(fixed_layer, gx, gz, gb_fix)
    r = 10
    draw.ellipse((x1 - r, y1 - r, x1 + r, y1 + r), fill=(255, 0, 0, 220))
    draw.ellipse((x2 - r, y2 - r, x2 + r, y2 + r), fill=(0, 255, 0, 220))
    print(f"{p['name']:18} app_gb=({x1},{y1}) fix_gb=({x2},{y2})")

out = ROOT / "tools" / "_factory_overlay_gb.png"
im.save(out)
print("saved", out)

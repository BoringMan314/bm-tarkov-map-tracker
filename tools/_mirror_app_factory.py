#!/usr/bin/env python3
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
meta = json.loads((ROOT / "internal/maps_tarkov.dev/factory/meta.json").read_text())
pmc = json.loads((ROOT / "internal/points/exfil/pmc.json").read_text())["factory"]
t = meta["transform"]
ROT = meta["coordinates_rotation"]
Z = 4
factor = 2**Z
sx, mx, sy, mz = t[0], t[1], t[2], t[3]
iw, ih = meta["width"], meta["height"]


def apply_rot(lat, lng, r):
    if not r:
        return lat, lng
    rad = math.radians(r)
    c, s = math.cos(rad), math.sin(rad)
    return lng * s + lat * c, lng * c - lat * s


def game_to_layer(gx, gz):
    lat, lng = apply_rot(gz, gx, ROT)
    scale_y = sy * -1
    return (sx * lng + mx) * factor, (scale_y * lat + mz) * factor


def tile_bounds_px():
    tile = 256
    min_x = meta["tile_min_x"] * tile
    min_y = meta["tile_min_y"] * tile
    max_x = (meta["tile_max_x"] + 1) * tile
    max_y = (meta["tile_max_y"] + 1) * tile
    return min_x, min_y, max_x, max_y


def game_corner_bounds():
    xmin, xmax, zmin, zmax = meta["xmin"], meta["xmax"], meta["zmin"], meta["zmax"]
    corners = [(xmin, zmax), (xmax, zmin), (xmin, zmin), (xmax, zmax)]
    pts = [game_to_layer(x, z) for x, z in corners]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def to_px(gx, gz, bounds):
    min_x, min_y, max_x, max_y = bounds
    lx, ly = game_to_layer(gx, gz)
    x = (lx - min_x) / (max_x - min_x) * iw
    y = (ly - min_y) / (max_y - min_y) * ih
    return x, y


tb = tile_bounds_px()
gb = game_corner_bounds()
print("tile bounds layer", tb)
print("game corner bounds layer", gb)
for p in pmc:
    gx, gz = p["coordinates"]
    l1 = game_to_layer(gx, gz)
    lat, lng = apply_rot(gz, gx, ROT)
    l2 = (sx * lng + mx) * factor, (-sy * lat + mz) * factor
    a = to_px(gx, gz, tb)
    b = to_px(gx, gz, gb)
    print(f"{p['name']:18} layer={l1} neg_sy={l2} tile_px={a} game_px={b}")

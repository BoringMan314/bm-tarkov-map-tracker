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
f = 2**Z
iw, ih = meta["width"], meta["height"]
xmin, xmax, zmin, zmax = meta["xmin"], meta["xmax"], meta["zmin"], meta["zmax"]


def apply_rot(gz, gx, r):
    if not r:
        return gz, gx
    rad = math.radians(r)
    c, s = math.cos(rad), math.sin(rad)
    return gz * s + gx * c, gz * c - gx * s


def layer(gx, gz):
    lat, lng = apply_rot(gz, gx, ROT)
    sx, mx, sy, mz = t[0], t[1], t[2] * -1, t[3]
    return (sx * lng + mx) * f, (sy * lat + mz) * f


def layer_crs(gx, gz):
    lat, lng = apply_rot(gz, gx, ROT)
    sx, mx, sy, mz = t[0], t[1], t[2] * -1, t[3]
    return (sx * lng + mx) * f, (sy * (-lat) + mz) * f


def tile_bounds():
    tile = 256
    return (
        meta["tile_min_x"] * tile,
        meta["tile_min_y"] * tile,
        (meta["tile_max_x"] + 1) * tile,
        (meta["tile_max_y"] + 1) * tile,
    )


def game_bounds():
    corners = [(xmin, zmax), (xmax, zmin), (xmin, zmin), (xmax, zmax)]
    pts = [layer(x, z) for x, z in corners]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def norm(gx, gz, bounds):
    min_x, min_y, max_x, max_y = bounds
    lx, ly = layer(gx, gz)
    return (lx - min_x) / (max_x - min_x) * iw, (ly - min_y) / (max_y - min_y) * ih


def norm_crs(gx, gz, bounds):
    min_x, min_y, max_x, max_y = bounds
    lx, ly = layer_crs(gx, gz)
    return (lx - min_x) / (max_x - min_x) * iw, (ly - min_y) / (max_y - min_y) * ih


tb = tile_bounds()
gb = game_bounds()
print("tile bounds", tb)
print("game bounds", gb)
print()
print(f"{'name':18} tile+layer  game+layer  tile+crs   game+crs")
for p in pmc:
    gx, gz = p["coordinates"]
    a = norm(gx, gz, tb)
    b = norm(gx, gz, gb)
    c = norm_crs(gx, gz, tb)
    d = norm_crs(gx, gz, gb)
    print(f"{p['name']:18} ({a[0]:4.0f},{a[1]:4.0f}) ({b[0]:4.0f},{b[1]:4.0f}) ({c[0]:4.0f},{c[1]:4.0f}) ({d[0]:4.0f},{d[1]:4.0f})")

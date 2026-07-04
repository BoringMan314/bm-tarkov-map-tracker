#!/usr/bin/env python3
import json
import math
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
meta = json.loads((ROOT / "internal/maps_tarkov.dev/factory/meta.json").read_text())
pmc = json.loads((ROOT / "internal/points/exfil/pmc.json").read_text())["factory"]
t = meta["transform"]
ROT = meta["coordinates_rotation"]
Z = 4
sx, mx, sy_raw, mz = t[0], t[1], t[2], t[3]
iw, ih = meta["width"], meta["height"]
min_x, min_y, max_x, max_y = 0, 0, 15, 15


def apply_rot(gz, gx, r):
    if not r:
        return gz, gx
    rad = math.radians(r)
    c, s = math.cos(rad), math.sin(rad)
    return gz * s + gx * c, gz * c - gx * s


def layer_old(gx, gz):
    lat, lng = apply_rot(gz, gx, ROT)
    f = 2 ** Z
    scale_y = sy_raw * -1
    return (sx * lng + mx) * f, (scale_y * lat + mz) * f


def layer_fixed(gx, gz):
    lat, lng = apply_rot(gz, gx, ROT)
    f = 2 ** Z
    return (sx * lng + mx) * f, (sy_raw * lat + mz) * f


def px(layer_fn, gx, gz):
    minX, minY = min_x * 256, min_y * 256
    maxX, maxY = (max_x + 1) * 256, (max_y + 1) * 256
    lx, ly = layer_fn(gx, gz)
    return (lx - minX) / (maxX - minX) * iw, (ly - minY) / (maxY - minY) * ih


print("name | old_y | fixed_y")
for p in pmc:
    gx, gz = p["coordinates"]
    o = px(layer_old, gx, gz)
    f = px(layer_fixed, gx, gz)
    print(f"{p['name']:18} ({o[0]:4.0f},{o[1]:4.0f}) ({f[0]:4.0f},{f[1]:4.0f})")

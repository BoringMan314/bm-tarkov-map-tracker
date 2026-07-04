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


def layer_crs(gx, gz):
    cx, cy = game_to_crs(gx, gz)
    return cx * f, cy * f


def layer_app(gx, gz):
    lat, lng = apply_rot(gz, gx, ROT)
    sx, mx, sy, mz = t[0], t[1], t[2] * -1, t[3]
    return (sx * lng + mx) * f, (sy * lat + mz) * f


def px(lx, ly, flip=False):
    if flip:
        ly = ih - ly
    return int(lx), int(ly)


print(f"{'name':18} app      crs      crs_flip")
for p in pmc:
    gx, gz = p["coordinates"]
    a = px(*layer_app(gx, gz))
    c = px(*layer_crs(gx, gz))
    cf = px(*layer_crs(gx, gz), flip=True)
    print(f"{p['name']:18} {a} {c} {cf}")

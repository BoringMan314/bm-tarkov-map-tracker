#!/usr/bin/env python3
"""Verify labs fix matches app.js transform + Y-flip path."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
META = json.loads((ROOT / "internal/maps_tarkov.dev/labs/meta.json").read_text())
PMC = json.loads((ROOT / "internal/points/exfil/pmc.json").read_text())["labs"]
W, H = META["width"], META["height"]
T = META["transform"]
rot = META["coordinates_rotation"]


def rot_ll(zc, x, r):
    rad = math.radians(r)
    c, s = math.cos(rad), math.sin(rad)
    return x * s + zc * c, x * c - zc * s


def game_to_crs(x, z):
    lat, lng = rot_ll(z, x, rot)
    return T[0] * lng + T[1], -T[2] * (-lat) + T[3]


def app_px(x, z):
    xmin, xmax = META["xmin"], META["xmax"]
    zmin, zmax = META["zmin"], META["zmax"]
    sw = game_to_crs(xmin, zmin)
    ne = game_to_crs(xmax, zmax)
    pt = game_to_crs(x, z)
    span_x = ne[0] - sw[0]
    span_y = sw[1] - ne[1]
    px = (pt[0] - sw[0]) / span_x * W
    py = (pt[1] - ne[1]) / span_y * H
    py = H - py
    return px, py


for p in PMC:
    px, py = app_px(*p["coordinates"])
    ok = 0 <= px <= W and 0 <= py <= H
    print(f"{p['name']:20} ({px:6.0f},{py:6.0f}) in={ok}")

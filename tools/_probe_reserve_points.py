#!/usr/bin/env python3
"""Quick reserve tile + point mapping probe."""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PMC = json.loads((ROOT / "internal/points/exfil/pmc.json").read_text())["reserve"]
TRANSFORM = [0.395, 122.0, 0.395, 137.65]
ROT = 180


def crs(gx: float, gz: float) -> tuple[float, float]:
    lat, lng = -gz, -gx
    return TRANSFORM[0] * lng + TRANSFORM[1], -TRANSFORM[2] * lat + TRANSFORM[3]


def pix(gx: float, gz: float, z: int, tmin_x: int, tmin_y: int, tmax_x: int, tmax_y: int) -> tuple[float, float, float, float]:
    cx, cy = crs(gx, gz)
    lx, ly = cx * 2**z, cy * 2**z
    tile = 256
    bminx, bminy = tmin_x * tile, tmin_y * tile
    bmaxx, bmaxy = (tmax_x + 1) * tile, (tmax_y + 1) * tile
    nx = (lx - bminx) / (bmaxx - bminx)
    ny = (ly - bminy) / (bmaxy - bminy)
    w, h = bmaxx - bminx, bmaxy - bminy
    x, y = nx * w, ny * h
    deg = -15
    mw, mh = w, h
    cxp, cyp = mw / 2, mh / 2
    rad = math.radians(deg)
    dx, dy = x - cxp, y - cyp
    x = cxp + dx * math.cos(rad) + dy * math.sin(rad)
    y = cyp - dx * math.sin(rad) + dy * math.cos(rad)
    return x, y, nx, ny


for z, bbox in [
    (4, (0, 1, 15, 14)),
    (5, (0, 2, 31, 29)),
    (6, (0, 5, 39, 39)),
]:
    tmin_x, tmin_y, tmax_x, tmax_y = bbox
    print(f"\n=== z={z} bbox={bbox} ===")
    for pt in PMC:
        x, y, nx, ny = pix(pt["coordinates"][0], pt["coordinates"][1], z, tmin_x, tmin_y, tmax_x, tmax_y)
        w = (tmax_x - tmin_x + 1) * 256
        h = (tmax_y - tmin_y + 1) * 256
        inside = 0 <= x < w and 0 <= y < h and 0 <= nx <= 1.05 and 0 <= ny <= 1.05
        print(f"{'OK' if inside else 'OUT'} {pt['name']}: nx={nx:.3f} ny={ny:.3f} px=({x:.0f},{y:.0f})")

#!/usr/bin/env python3
"""Test factory pixel mapping variants vs tarkov.dev CRS."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
meta = json.loads((ROOT / "internal/maps_tarkov.dev/factory/meta.json").read_text())
pmc = json.loads((ROOT / "internal/points/exfil/pmc.json").read_text())["factory"]
T = meta["transform"]
ROT = meta["coordinates_rotation"]
W = H = 4096
Z = 4
F = 2**Z


def rot_ll(lat, lng, r):
    if not r:
        return lat, lng
    rad = math.radians(r)
    c, s = math.cos(rad), math.sin(rad)
    return lng * s + lat * c, lng * c - lat * s


def game_to_crs(gx, gz):
    lat, lng = rot_ll(gz, gx, ROT)
    return T[0] * lng + T[1], -T[2] * (-lat) + T[3]


def layer(gx, gz):
    cx, cy = game_to_crs(gx, gz)
    return cx * F, cy * F


def tile_bounds():
    t = meta["tile_size"]
    return (
        meta["tile_min_x"] * t,
        meta["tile_min_y"] * t,
        (meta["tile_max_x"] + 1) * t,
        (meta["tile_max_y"] + 1) * t,
    )


def corner_bounds():
    xmin, xmax = meta["xmin"], meta["xmax"]
    zmin, zmax = meta["zmin"], meta["zmax"]
    corners = [(xmin, zmax), (xmax, zmin), (xmin, zmin), (xmax, zmax)]
    xs, ys = [], []
    for x, z in corners:
        lx, ly = layer(x, z)
        xs.append(lx)
        ys.append(ly)
    return min(xs), min(ys), max(xs), max(ys)


def map_px(gx, gz, bminx, bminy, bmaxx, bmaxy, flip_y=False, flip_x=False):
    lx, ly = layer(gx, gz)
    px = (lx - bminx) / (bmaxx - bminx) * W
    py = (ly - bminy) / (bmaxy - bminy) * H
    if flip_y:
        py = H - py
    if flip_x:
        px = W - px
    return px, py


def main():
    tb = tile_bounds()
    cb = corner_bounds()
    print("tile bounds", tb)
    print("corner bounds", cb)
    print()
    for name, flip_y, flip_x, bounds in [
        ("tile+flipY (app)", True, False, tb),
        ("tile no flip", False, False, tb),
        ("tile flipXY", True, True, tb),
        ("corner+flipY", True, False, cb),
        ("corner flipXY", True, True, cb),
    ]:
        print(f"=== {name} ===")
        for p in pmc:
            px, py = map_px(*p["coordinates"], *bounds, flip_y=flip_y, flip_x=flip_x)
            ok = 0 <= px <= W and 0 <= py <= H
            print(f"  {p['name']:18} ({px:6.0f},{py:6.0f}) in={ok}")


if __name__ == "__main__":
    main()

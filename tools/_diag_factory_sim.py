#!/usr/bin/env python3
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
meta = json.loads((ROOT / "internal/maps_tarkov.dev/factory/meta.json").read_text())
meta_b = json.loads((ROOT / "internal/maps_tarkov.dev_B/factory/meta.json").read_text())
pmc = json.loads((ROOT / "internal/points/exfil/pmc.json").read_text())["factory"]
t = meta["transform"]
rot = int(meta["coordinates_rotation"])
Z = meta["tile_zoom"]
scale = 2**Z
sx, mx, sy_raw, mz = t[0], t[1], t[2], t[3]
sy = sy_raw * -1
xmin, xmax, zmin, zmax = meta["xmin"], meta["xmax"], meta["zmin"], meta["zmax"]


def apply_rot(gz, gx, r):
    if not r:
        return gz, gx
    rad = math.radians(r)
    c, s = math.cos(rad), math.sin(rad)
    return gx * s + gz * c, gx * c - gz * s


def game_to_crs(gx, gz):
    lat, lng = apply_rot(gz, gx, rot)
    return sx * lng + mx, sy * (-lat) + mz


def layer_pt(gx, gz, z=Z):
    cx, cy = game_to_crs(gx, gz)
    f = 2**z
    return cx * f, cy * f


def raster_bounds(m):
    ts = m["tile_size"]
    return {
        "minX": m["tile_min_x"] * ts,
        "minY": m["tile_min_y"] * ts,
        "maxX": (m["tile_max_x"] + 1) * ts,
        "maxY": (m["tile_max_y"] + 1) * ts,
    }


def corner_bounds():
    corners = [(xmin, zmax), (xmax, zmin), (xmin, zmin), (xmax, zmax)]
    xs, ys = [], []
    for gx, gz in corners:
        lx, ly = layer_pt(gx, gz)
        xs.append(lx)
        ys.append(ly)
    return min(xs), min(ys), max(xs), max(ys)


def to_px_tile(gx, gz, iw, ih):
    b = raster_bounds(meta)
    lx, ly = layer_pt(gx, gz)
    return (
        (lx - b["minX"]) / (b["maxX"] - b["minX"]) * iw,
        (ly - b["minY"]) / (b["maxY"] - b["minY"]) * ih,
    )


def to_px_corner(gx, gz, iw, ih):
    cminx, cminy, cmaxx, cmaxy = corner_bounds()
    lx, ly = layer_pt(gx, gz)
    return (
        (lx - cminx) / (cmaxx - cminx) * iw,
        (ly - cminy) / (cmaxy - cminy) * ih,
    )


def to_px_b(gx, gz):
    m = meta_b
    bxmin, bxmax, bzmin, bzmax = m["xmin"], m["xmax"], m["zmin"], m["zmax"]
    sw = game_to_crs(bxmin, bzmin)
    ne = game_to_crs(bxmax, bzmax)
    pt = game_to_crs(gx, gz)
    iw, ih = m["width"], m["height"]
    return (
        (pt[0] - sw[0]) / (ne[0] - sw[0]) * iw,
        (pt[1] - ne[1]) / (sw[1] - ne[1]) * ih,
    )


iw, ih = meta["width"], meta["height"]
print("meta size", iw, ih, "z", Z)
print("tile bounds", raster_bounds(meta))
print("corner bounds", corner_bounds())
print()
for z in (4, 5, 6):
    print(f"--- zoom {z} ---")
    for p in pmc[:2]:
        gx, gz = p["coordinates"]
        lx, ly = layer_pt(gx, gz, z)
        print(f"  {p['name']} layer=({lx:.0f},{ly:.0f})")
print()
print("=== compare tile vs corner mapping (z=6) ===")
for p in pmc:
    gx, gz = p["coordinates"]
    a = to_px_tile(gx, gz, iw, ih)
    c = to_px_corner(gx, gz, iw, ih)
    b = to_px_b(gx, gz)
    print(
        f"{p['name']:18} tile=({a[0]:6.0f},{a[1]:6.0f}) "
        f"corner=({c[0]:6.0f},{c[1]:6.0f}) B=({b[0]:5.1f},{b[1]:5.1f})"
    )

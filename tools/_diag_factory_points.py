#!/usr/bin/env python3
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
meta = json.loads((ROOT / "internal/maps/factory/meta.json").read_text())
t = meta["transform"]
rot = int(meta["coordinates_rotation"])
Z = 4
scale = 2**Z
sx, mx, sy, mz = t[0], t[1], t[2] * -1, t[3]
xmin, xmax, zmin, zmax = meta["xmin"], meta["xmax"], meta["zmin"], meta["zmax"]
iw, ih = meta["width"], meta["height"]


def apply_rot(lat, lng, r):
    if not r:
        return lat, lng
    rad = math.radians(r)
    c, s = math.cos(rad), math.sin(rad)
    return lng * s + lat * c, lng * c - lat * s


def leaflet_layer(gx, gz):
    lat, lng = apply_rot(gz, gx, rot)
    cx = sx * lng + mx
    cy = sy * lat + mz
    return cx * scale, cy * scale


def current_px(gx, gz):
    sw = game_to_crs(xmin, zmin)
    ne = game_to_crs(xmax, zmax)
    pt = game_to_crs(gx, gz)
    return (
        (pt[0] - sw[0]) / (ne[0] - sw[0]) * iw,
        (pt[1] - ne[1]) / (sw[1] - ne[1]) * ih,
    )


def game_to_crs(gx, gz):
    lat, lng = apply_rot(gz, gx, rot)
    return sx * lng + mx, sy * (-lat) + mz  # current app.js


def fixed_px(gx, gz):
    """Map layer CRS to pixels using projected bounds min/max (leaflet tile space)."""
    pts = []
    for p in pmc + scav + transit:
        pts.append(leaflet_layer(*p["coordinates"]))
    all_x = [leaflet_layer(x, z)[0] for x, z in [
        (xmin, zmax), (xmax, zmin), (xmin, zmin), (xmax, zmax)
    ]]
    all_y = [leaflet_layer(x, z)[1] for x, z in [
        (xmin, zmax), (xmax, zmin), (xmin, zmin), (xmax, zmax)
    ]]
    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    lx, ly = leaflet_layer(gx, gz)
    return (lx - min_x) / (max_x - min_x) * iw, (ly - min_y) / (max_y - min_y) * ih


pmc = json.loads((ROOT / "internal/points/exfil/pmc.json").read_text())["factory"]
scav = json.loads((ROOT / "internal/points/exfil/scav.json").read_text())["factory"]
transit = json.loads((ROOT / "internal/points/exfil/transit.json").read_text())["factory"]

print("=== bounds corner layer points z=4 ===")
for name, gx, gz in [
    ("xmin,zmax", xmin, zmax),
    ("xmax,zmin", xmax, zmin),
    ("xmin,zmin", xmin, zmin),
    ("xmax,zmax", xmax, zmax),
]:
    p = leaflet_layer(gx, gz)
    print(f"  {name}: ({p[0]:.0f}, {p[1]:.0f})")

print("\n=== markers: current vs leaflet layer vs normalized layer ===")
for group, items in [("pmc", pmc), ("scav", scav), ("transit", transit)]:
    for p in items:
        gx, gz = p["coordinates"]
        cur = current_px(gx, gz)
        lp = leaflet_layer(gx, gz)
        fx = fixed_px(gx, gz)
        print(
            f"  [{group}] {p['name']:22} cur=({cur[0]:4.0f},{cur[1]:4.0f}) "
            f"layer=({lp[0]:6.0f},{lp[1]:6.0f}) norm=({fx[0]:4.0f},{fx[1]:4.0f})"
        )

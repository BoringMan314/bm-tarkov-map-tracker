#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
meta = json.loads((ROOT / "internal/maps_tarkov.dev/interchange/meta.json").read_text(encoding="utf-8"))
pmc = json.loads((ROOT / "internal/points/exfil/pmc.json").read_text(encoding="utf-8"))["interchange"]

# corner CRS (current app for interchange)
def corner_px(gx, gz):
    t = meta["transform"]
    rot = meta["coordinates_rotation"]
    xmin, xmax = meta["xmin"], meta["xmax"]
    zmin, zmax = meta["zmin"], meta["zmax"]
    import math

    def rot_ll(gz, gx, r):
        if not r:
            return gz, gx
        rad = math.radians(r)
        c, s = math.cos(rad), math.sin(rad)
        return gx * s + gz * c, gx * c - gz * s

    def crs(gx, gz):
        lat, lng = rot_ll(gz, gx, rot)
        return t[0] * lng + t[1], (-t[2]) * (-lat) + t[3]

    sw = crs(xmin, zmin)
    ne = crs(xmax, zmax)
    pt = crs(gx, gz)
    w, h = meta["width"], meta["height"]
    return (pt[0] - sw[0]) / (ne[0] - sw[0]) * w, (pt[1] - ne[1]) / (sw[1] - ne[1]) * h


def tile_px(gx, gz):
    import math

    t = meta["transform"]
    rot = meta["coordinates_rotation"]
    z = int(meta["tile_zoom"])
    ts = meta["tile_size"]

    def rot_ll(gz, gx, r):
        if not r:
            return gz, gx
        rad = math.radians(r)
        c, s = math.cos(rad), math.sin(rad)
        return gx * s + gz * c, gx * c - gz * s

    lat, lng = rot_ll(gz, gx, rot)
    cx = t[0] * lng + t[1]
    cy = (-t[2]) * (-lat) + t[3]
    f = 2**z
    lx, ly = cx * f, cy * f
    bminx = meta["tile_min_x"] * ts
    bminy = meta["tile_min_y"] * ts
    bmaxx = (meta["tile_max_x"] + 1) * ts
    bmaxy = (meta["tile_max_y"] + 1) * ts
    w, h = meta["width"], meta["height"]
    off_x = meta.get("map_offset_x", 0)
    off_y = meta.get("map_offset_y", 0)
    stitch_w = meta["stitch_width"]
    stitch_h = meta["stitch_height"]
    return (lx - bminx) / (bmaxx - bminx) * stitch_w - off_x, (ly - bminy) / (bmaxy - bminy) * stitch_h - off_y


print("name                  corner        tile")
for p in pmc[:6]:
    gx, gz = p["coordinates"]
    c = corner_px(gx, gz)
    t = tile_px(gx, gz)
    print(f"{p.get('name','?'):22} ({c[0]:7.0f},{c[1]:7.0f})  ({t[0]:7.0f},{t[1]:7.0f})")

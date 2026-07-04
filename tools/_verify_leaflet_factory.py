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
iw, ih = meta["width"], meta["height"]
xmin, xmax, zmin, zmax = meta["xmin"], meta["xmax"], meta["zmin"], meta["zmax"]


def apply_rot(gz, gx, r):
    if not r:
        return gz, gx
    rad = math.radians(r)
    c, s = math.cos(rad), math.sin(rad)
    return gz * s + gx * c, gz * c - gx * s


def leaflet_point(gx, gz):
    lat, lng = apply_rot(gz, gx, ROT)
    proj_x, proj_y = lng, -lat
    sx, mx, sy, mz = t[0], t[1], t[2] * -1, t[3]
    tx = sx * proj_x + mx
    ty = sy * proj_y + mz
    return tx * 2**Z, ty * 2**Z


def crs(gx, gz):
    lat, lng = apply_rot(gz, gx, ROT)
    sx, mx, sy, mz = t[0], t[1], t[2] * -1, t[3]
    return sx * lng + mx, sy * (-lat) + mz


def px_svg(gx, gz):
    sw = crs(xmin, zmin)
    ne = crs(xmax, zmax)
    pt = crs(gx, gz)
    return (pt[0] - sw[0]) / (ne[0] - sw[0]) * iw, (pt[1] - ne[1]) / (sw[1] - ne[1]) * ih


def px_tile(gx, gz):
    lx, ly = leaflet_point(gx, gz)
    return lx / iw * iw, ly / ih * ih  # tile 0,0 origin


def px_tile_norm(gx, gz):
    lx, ly = leaflet_point(gx, gz)
    return lx / (16 * 256) * iw, ly / (16 * 256) * ih


print("name | svg_crs | leaflet/tile16")
for p in pmc:
    gx, gz = p["coordinates"]
    s = px_svg(gx, gz)
    l = px_tile_norm(gx, gz)
    print(f"{p['name']:18} ({s[0]:4.0f},{s[1]:4.0f}) ({l[0]:4.0f},{l[1]:4.0f})")

# tile origin offset: unproject tile 0,0
print("\nleaflet corner layers z=4")
for gx, gz, name in [(xmin,zmax,"xmin,zmax"),(xmax,zmin,"xmax,zmin"),(0,0,"origin")]:
    print(name, leaflet_point(gx,gz))

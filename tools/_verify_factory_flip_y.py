#!/usr/bin/env python3
import json
import math
from pathlib import Path

meta = json.loads(Path("internal/maps_tarkov.dev/factory/meta.json").read_text())
pmc = json.loads(Path("internal/points/exfil/pmc.json").read_text())["factory"]
t = meta["transform"]
ROT = meta["coordinates_rotation"]
Z = 4
iw = meta["width"]
xmin, xmax, zmin, zmax = meta["xmin"], meta["xmax"], meta["zmin"], meta["zmax"]


def rot(gz, gx, r):
    rad = math.radians(r)
    c, s = math.cos(rad), math.sin(rad)
    return gz * s + gx * c, gz * c - gx * s


def lp(gx, gz):
    lat, lng = rot(gz, gx, ROT)
    tx = t[0] * lng + t[1]
    ty = t[2] * lat + t[3]
    return tx * 2**Z, ty * 2**Z


corners = [(xmin, zmax), (xmax, zmin), (xmin, zmin), (xmax, zmax)]
pts = [lp(x, z) for x, z in corners]
minX, maxX = min(p[0] for p in pts), max(p[0] for p in pts)
minY, maxY = min(p[1] for p in pts), max(p[1] for p in pts)
print(f"bounds layer ({minX:.0f},{minY:.0f})-({maxX:.0f},{maxY:.0f})")
for p in pmc:
    gx, gz = p["coordinates"]
    lx, ly = lp(gx, gz)
    px = (lx - minX) / (maxX - minX) * iw
    py = (maxY - ly) / (maxY - minY) * iw
    print(f"{p['name']:18} ({px:4.0f},{py:4.0f})")

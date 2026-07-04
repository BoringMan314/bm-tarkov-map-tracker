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
sx, mx, sy, mz = t[0], t[1], t[2] * -1, t[3]
iw, ih = meta["width"], meta["height"]


def apply_rot(gz, gx, r):
    if not r:
        return gz, gx
    rad = math.radians(r)
    c, s = math.cos(rad), math.sin(rad)
    return gz * s + gx * c, gz * c - gx * s


def layer(gx, gz):
    lat, lng = apply_rot(gz, gx, ROT)
    f = 2 ** Z
    return (sx * lng + mx) * f, (sy * lat + mz) * f


TILE_URL = "https://assets.tarkov.dev/maps/factory/main/{z}/{x}/{y}.png"
coords = []
for x in range(16):
    for y in range(16):
        url = TILE_URL.format(z=Z, x=x, y=y)
        try:
            d = urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": "bm/1"}), timeout=20
            ).read()
            if len(d) >= 4000:
                coords.append((x, y))
        except OSError:
            pass
min_x, max_x = min(c[0] for c in coords), max(c[0] for c in coords)
min_y, max_y = min(c[1] for c in coords), max(c[1] for c in coords)
print("tiles", len(coords), "bbox", min_x, min_y, max_x, max_y)
print("png expected", (max_x - min_x + 1) * 256, (max_y - min_y + 1) * 256, "actual", iw, ih)


def px_game_bounds(gx, gz):
    xmin, xmax, zmin, zmax = meta["xmin"], meta["xmax"], meta["zmin"], meta["zmax"]
    pts = [layer(x, z) for x, z in [(xmin, zmax), (xmax, zmin), (xmin, zmin), (xmax, zmax)]]
    minX = min(p[0] for p in pts)
    maxX = max(p[0] for p in pts)
    minY = min(p[1] for p in pts)
    maxY = max(p[1] for p in pts)
    lx, ly = layer(gx, gz)
    return (lx - minX) / (maxX - minX) * iw, (ly - minY) / (maxY - minY) * ih


def px_tile_bounds(gx, gz):
    minX, minY = min_x * 256, min_y * 256
    maxX, maxY = (max_x + 1) * 256, (max_y + 1) * 256
    lx, ly = layer(gx, gz)
    return (lx - minX) / (maxX - minX) * iw, (ly - minY) / (maxY - minY) * ih


print("name | game_bounds | tile_bounds")
for p in pmc:
    gx, gz = p["coordinates"]
    a = px_game_bounds(gx, gz)
    b = px_tile_bounds(gx, gz)
    print(f"{p['name']:18} ({a[0]:4.0f},{a[1]:4.0f}) ({b[0]:4.0f},{b[1]:4.0f})")

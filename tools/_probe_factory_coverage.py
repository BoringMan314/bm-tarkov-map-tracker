#!/usr/bin/env python3
"""Probe factory tile coverage vs game bounds at z=6."""
import json
import math
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
meta = json.loads((ROOT / "internal/maps_tarkov.dev/factory/meta.json").read_text())
pmc = json.loads((ROOT / "internal/points/exfil/pmc.json").read_text())["factory"]
t = meta["transform"]
rot = int(meta["coordinates_rotation"])
Z = 6
TILE = "https://assets.tarkov.dev/maps/factory/main/{z}/{x}/{y}.png"


def apply_rot(gz, gx, r):
    rad = math.radians(r)
    c, s = math.cos(rad), math.sin(rad)
    return gx * s + gz * c, gx * c - gz * s


def layer_pt(gx, gz):
    lat, lng = apply_rot(gz, gx, rot)
    cx = t[0] * lng + t[1]
    cy = -t[2] * (-lat) + t[3]
    f = 2**Z
    return cx * f, cy * f


def fetch_size(x, y):
    url = TILE.format(z=Z, x=x, y=y)
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "bm"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, int(r.headers.get("Content-Length", 0))
    except Exception as e:
        return getattr(e, "code", None) or "err", 0


xmin, xmax, zmin, zmax = meta["xmin"], meta["xmax"], meta["zmin"], meta["zmax"]
corners = [(xmin, zmax), (xmax, zmin), (xmin, zmin), (xmax, zmax)]
print("Game corners layer pts z=6:")
all_x, all_y = [], []
for gx, gz in corners:
    lx, ly = layer_pt(gx, gz)
    all_x.append(lx)
    all_y.append(ly)
    print(f"  ({gx},{gz}) -> layer ({lx:.0f},{ly:.0f}) tile ({int(lx//256)},{int(ly//256)})")

need_min_x = int(min(all_x) // 256)
need_max_x = int(max(all_x) // 256)
need_min_y = int(min(all_y) // 256)
need_max_y = int(max(all_y) // 256)
print(f"\nRequired tile range: x={need_min_x}..{need_max_x} y={need_min_y}..{need_max_y}")
print(f"Current meta: x={meta['tile_min_x']}..{meta['tile_max_x']} y={meta['tile_min_y']}..{meta['tile_max_y']}")

print("\nExfil layer pts:")
for p in pmc:
    lx, ly = layer_pt(*p["coordinates"])
    tx, ty = int(lx // 256), int(ly // 256)
    inside = (
        meta["tile_min_x"] <= tx <= meta["tile_max_x"]
        and meta["tile_min_y"] <= ty <= meta["tile_max_y"]
    )
    print(f"  {p['name']:18} layer=({lx:6.0f},{ly:6.0f}) tile=({tx},{ty}) inside={inside}")

print("\nProbe bottom row tiles x=42 y=62..66 (sample):")
for y in range(62, 67):
    st, sz = fetch_size(42, y)
    print(f"  y={y}: status={st} size={sz}")

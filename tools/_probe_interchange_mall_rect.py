#!/usr/bin/env python3
"""Mall bounds on interchange DEV A satellite PNG (tile CRS)."""
import json
import math
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
meta = json.loads((ROOT / "internal/maps_tarkov.dev/interchange/meta.json").read_text(encoding="utf-8"))
png = ROOT / "internal/maps_tarkov.dev/interchange/map.png"

MALL = [[120, 218], [-222, -327]]


def rot_ll(gz, gx, r):
    if not r:
        return gz, gx
    rad = math.radians(r)
    c, s = math.cos(rad), math.sin(rad)
    return gx * s + gz * c, gx * c - gz * s


def layer_pt(gx, gz, t, rot, z):
    lat, lng = rot_ll(gz, gx, rot)
    cx = t[0] * lng + t[1]
    cy = (-t[2]) * (-lat) + t[3]
    f = 2**z
    return cx * f, cy * f


def to_px(gx, gz, meta, w, h):
    t = meta["transform"]
    rot = meta["coordinates_rotation"]
    z = int(meta["tile_zoom"])
    ts = meta["tile_size"]
    b = {
        "minX": meta["tile_min_x"] * ts,
        "minY": meta["tile_min_y"] * ts,
        "maxX": (meta["tile_max_x"] + 1) * ts,
        "maxY": (meta["tile_max_y"] + 1) * ts,
    }
    lx, ly = layer_pt(gx, gz, t, rot, z)
    off_x = meta.get("map_offset_x", 0)
    off_y = meta.get("map_offset_y", 0)
    stitch_w = meta["stitch_width"]
    stitch_h = meta["stitch_height"]
    x = (lx - b["minX"]) / (b["maxX"] - b["minX"]) * stitch_w - off_x
    y = (ly - b["minY"]) / (b["maxY"] - b["minY"]) * stitch_h - off_y
    return x, y


im = Image.open(png)
w, h = im.size
print("PNG", w, h)
xs, ys = [], []
for gx, gz in MALL:
    x, y = to_px(gx, gz, meta, w, h)
    xs.append(x)
    ys.append(y)
    print(f"  corner ({gx},{gz}) -> ({x:.1f},{y:.1f})")
print(f"mall rect px: x={min(xs):.0f}-{max(xs):.0f} y={min(ys):.0f}-{max(ys):.0f}")
print(f"mall size: {max(xs)-min(xs):.0f}x{max(ys)-min(ys):.0f}")

# First_Floor SVG viewBox content bbox approx from paths ~548-870 x, ~138-693 y in 1127x947
print("SVG viewBox", 1127.6852, 947.02582)

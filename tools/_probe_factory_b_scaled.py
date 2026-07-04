#!/usr/bin/env python3
"""DEV B factory: A raster_crop pixels scaled to B SVG viewBox."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
meta_a = json.loads((ROOT / "internal/maps_tarkov.dev/factory/meta.json").read_text())
meta_b = json.loads((ROOT / "internal/maps_tarkov.dev_B/factory/meta.json").read_text())
pmc = json.loads((ROOT / "internal/points/exfil/pmc.json").read_text())["factory"]
t = meta_a["transform"]
rot = meta_a["coordinates_rotation"]
z = meta_a["tile_zoom"]
f = 2**z
tile = meta_a["tile_size"]
bounds = {
    "minX": meta_a["tile_min_x"] * tile,
    "minY": meta_a["tile_min_y"] * tile,
    "maxX": (meta_a["tile_max_x"] + 1) * tile,
    "maxY": (meta_a["tile_max_y"] + 1) * tile,
}
sw = bounds["maxX"] - bounds["minX"]
sh = bounds["maxY"] - bounds["minY"]
stw, sth = meta_a["stitch_width"], meta_a["stitch_height"]
ox, oy = meta_a["map_offset_x"], meta_a["map_offset_y"]
aw, ah = meta_a["width"], meta_a["height"]
bw, bh = meta_b["width"], meta_b["height"]


def rot_ll(gz, gx, r):
    rad = math.radians(r)
    c, s = math.cos(rad), math.sin(rad)
    return gz * s + gx * c, gz * c - gx * s


def game_to_layer(gx, gz):
    lat, lng = rot_ll(gz, gx, rot)
    cy = t[2] * lat + t[3]
    return (t[0] * lng + t[1]) * f, cy * f


def dev_a_px(gx, gz):
    lx, ly = game_to_layer(gx, gz)
    nx, ny = (lx - bounds["minX"]) / sw, (ly - bounds["minY"]) / sh
    return nx * stw - ox, ny * sth - oy


def dev_b_px(gx, gz):
    ax, ay = dev_a_px(gx, gz)
    return (ax / aw) * bw, (ay / ah) * bh


print("DEV B scaled from A")
for p in pmc:
    x, y = dev_b_px(*p["coordinates"])
    in_box = 0 <= x <= bw and 0 <= y <= bh
    print(f"  {p['name']:18} ({x:5.1f},{y:5.1f}) inViewBox={in_box}")

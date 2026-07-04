#!/usr/bin/env python3
import json
import math
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
meta = json.loads((ROOT / "internal/maps_tarkov.dev/factory/meta.json").read_text())
pmc = json.loads((ROOT / "internal/points/exfil/pmc.json").read_text())["factory"]
im = Image.open(ROOT / "internal/maps_tarkov.dev/factory/map.png").convert("RGBA")
t = meta["transform"]
rot = meta["coordinates_rotation"]
z = meta["tile_zoom"]
sx, mx, sy, mz = t[0], t[1], t[2], t[3]
f = 2**z
tile = meta["tile_size"]
bounds = {
    "minX": meta["tile_min_x"] * tile,
    "minY": meta["tile_min_y"] * tile,
    "maxX": (meta["tile_max_x"] + 1) * tile,
    "maxY": (meta["tile_max_y"] + 1) * tile,
}
sw = bounds["maxX"] - bounds["minX"]
sh = bounds["maxY"] - bounds["minY"]
stw, sth = meta["stitch_width"], meta["stitch_height"]
ox, oy = meta["map_offset_x"], meta["map_offset_y"]


def rot_ll(gz, gx, r):
    rad = math.radians(r)
    c, s = math.cos(rad), math.sin(rad)
    return gz * s + gx * c, gz * c - gx * s


def game_to_layer(gx, gz):
    lat, lng = rot_ll(gz, gx, rot)
    cy = sy * lat + mz
    return (sx * lng + mx) * f, cy * f


def to_px(gx, gz):
    lx, ly = game_to_layer(gx, gz)
    nx = (lx - bounds["minX"]) / sw
    ny = (ly - bounds["minY"]) / sh
    return nx * stw - ox, ny * sth - oy


hits = 0
for p in pmc:
    x, y = to_px(*p["coordinates"])
    inside = 0 <= x < im.width and 0 <= y < im.height
    ok = False
    if inside:
        r, g, b, a = im.getpixel((int(x), int(y)))
        ok = a > 128 and (r + g + b) > 40
    hits += ok
    status = "OK" if ok else "MISS"
    print(f"{p['name']:18} ({x:6.0f},{y:6.0f}) {status}")
print(f"hits {hits}/{len(pmc)}")

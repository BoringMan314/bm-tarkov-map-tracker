#!/usr/bin/env python3
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
meta = json.loads((ROOT / "internal/maps_tarkov.dev/factory/meta.json").read_text())
pmc = json.loads((ROOT / "internal/points/exfil/pmc.json").read_text())["factory"]
t = meta["transform"]
ROT = meta["coordinates_rotation"]
iw, ih = int(meta["width"]), int(meta["height"])
xmin, xmax, zmin, zmax = meta["xmin"], meta["xmax"], meta["zmin"], meta["zmax"]


def apply_rot(gz, gx, r):
    if not r:
        return gz, gx
    rad = math.radians(r)
    c, s = math.cos(rad), math.sin(rad)
    return gz * s + gx * c, gz * c - gx * s


def game_to_crs(gx, gz):
    lat, lng = apply_rot(gz, gx, ROT)
    sx, mx, sy, mz = t[0], t[1], t[2] * -1, t[3]
    return sx * lng + mx, sy * (-lat) + mz


def svg_px(gx, gz):
    sw = game_to_crs(xmin, zmin)
    ne = game_to_crs(xmax, zmax)
    pt = game_to_crs(gx, gz)
    return int((pt[0] - sw[0]) / (ne[0] - sw[0]) * iw), int((pt[1] - ne[1]) / (sw[1] - ne[1]) * ih)


im = Image.open(ROOT / "internal/maps_tarkov.dev/factory/map.png").convert("RGBA")
draw = ImageDraw.Draw(im)
for p in pmc:
    x, y = svg_px(*p["coordinates"])
    r = 10
    draw.ellipse((x - r, y - r, x + r, y + r), fill=(0, 128, 255, 220))
    print(f"{p['name']:18} svg_crs=({x},{y})")

out = ROOT / "tools" / "_factory_overlay_svg.png"
im.save(out)
print("saved", out)

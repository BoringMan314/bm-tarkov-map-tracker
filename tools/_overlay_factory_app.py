#!/usr/bin/env python3
"""Factory overlay with correct app.js CRS (matches tarkov.dev Leaflet tiles)."""
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
meta = json.loads((ROOT / "internal/maps_tarkov.dev/factory/meta.json").read_text())
pmc = json.loads((ROOT / "internal/points/exfil/pmc.json").read_text())["factory"]
T = meta["transform"]
ROT = meta["coordinates_rotation"]
W = H = 4096
Z = meta["tile_zoom"]
F = 2**Z
t = meta["tile_size"]
bminx = meta["tile_min_x"] * t
bminy = meta["tile_min_y"] * t
bmaxx = (meta["tile_max_x"] + 1) * t
bmaxy = (meta["tile_max_y"] + 1) * t


def rot_ll(lat, lng, r):
    if not r:
        return lat, lng
    rad = math.radians(r)
    c, s = math.cos(rad), math.sin(rad)
    return lng * s + lat * c, lng * c - lat * s


def px(gx, gz):
    lat, lng = rot_ll(gz, gx, ROT)
    cx = T[0] * lng + T[1]
    cy = -T[2] * (-lat) + T[3]
    lx, ly = cx * F, cy * F
    x = (lx - bminx) / (bmaxx - bminx) * W
    y = (ly - bminy) / (bmaxy - bminy) * H
    return int(x), int(y)


def save(name):
    im = Image.open(ROOT / "internal/maps_tarkov.dev/factory/map.png").convert("RGBA")
    draw = ImageDraw.Draw(im)
    for p in pmc:
        x, y = px(*p["coordinates"])
        draw.ellipse((x - 12, y - 12, x + 12, y + 12), fill=(255, 200, 0, 230))
        draw.text((x + 14, y - 6), p["name"][:10], fill="yellow")
        print(f"  {p['name']:18} ({x},{y})")
    out = ROOT / "tools" / f"_factory_app_{name}.png"
    im.save(out)
    print(f"saved {out.name}\n")


if __name__ == "__main__":
    print("=== app tile (tarkov.dev, no flipY) ===")
    save("tile")

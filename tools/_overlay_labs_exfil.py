#!/usr/bin/env python3
"""Overlay labs exfil points: current vs Y-flip vs CRS+transform."""
from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
META = json.loads((ROOT / "internal/maps_tarkov.dev/labs/meta.json").read_text())
PMC = json.loads((ROOT / "internal/points/exfil/pmc.json").read_text())["labs"]
TRANSFORM = [0.575, 281.2, 0.575, 193.7]
TILE = dict(tile_zoom=5, tile_min_x=1, tile_min_y=5, tile_max_x=30, tile_max_y=26, tile_size=256)
W, H = int(META["width"]), int(META["height"])


def rot_ll(z, x, r):
    rad = math.radians(r)
    c, s = math.cos(rad), math.sin(rad)
    return x * s + z * c, x * c - z * s


def linear_px(x, z):
    xmin, xmax = META["xmin"], META["xmax"]
    zmin, zmax = META["zmin"], META["zmax"]
    u = (z - zmin) / (zmax - zmin)
    v = (xmax - x) / (xmax - xmin)
    return u * W, v * H


def crs_tile_px(x, z):
    rot = META["coordinates_rotation"]
    lat, lng = rot_ll(z, x, rot)
    sx, mx, sy, my = TRANSFORM[0], TRANSFORM[1], TRANSFORM[2] * -1, TRANSFORM[3]
    cx, cy = sx * lng + mx, sy * (-lat) + my
    zoom = TILE["tile_zoom"]
    lx, ly = cx * (2**zoom), cy * (2**zoom)
    t = TILE["tile_size"]
    bmin_x = TILE["tile_min_x"] * t
    bmin_y = TILE["tile_min_y"] * t
    bmax_x = (TILE["tile_max_x"] + 1) * t
    bmax_y = (TILE["tile_max_y"] + 1) * t
    return (lx - bmin_x) / (bmax_x - bmin_x) * W, (ly - bmin_y) / (bmax_y - bmin_y) * H


def draw_layer(name, points_fn, color):
    im = Image.open(ROOT / "internal/maps_tarkov.dev/labs/map.png").convert("RGBA")
    draw = ImageDraw.Draw(im)
    for p in PMC:
        x, z = p["coordinates"]
        px, py = points_fn(x, z)
        r = 14
        draw.ellipse((px - r, py - r, px + r, py + r), outline=color, width=3)
        draw.text((px + 16, py - 8), p["name"][:12], fill=color)
    out = ROOT / "tools" / f"_labs_overlay_{name}.png"
    im.save(out)
    print(f"wrote {out.name}")


def main() -> None:
    Image.MAX_IMAGE_PIXELS = None
    draw_layer("current", linear_px, "red")
    draw_layer("flip_y", lambda x, z: (linear_px(x, z)[0], H - linear_px(x, z)[1]), "lime")
    draw_layer("crs_flip_y", lambda x, z: (crs_tile_px(x, z)[0], H - crs_tile_px(x, z)[1]), "cyan")


if __name__ == "__main__":
    main()

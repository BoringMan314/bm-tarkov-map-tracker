#!/usr/bin/env python3
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
meta = json.loads((ROOT / "internal/maps_tarkov.dev_B/factory/meta.json").read_text())
pmc = json.loads((ROOT / "internal/points/exfil/pmc.json").read_text())["factory"]
t = meta["transform"]
rot = int(meta["coordinates_rotation"])
meta_f = json.loads((ROOT / "internal/maps_tarkov.dev/factory/meta.json").read_text())


def apply_rot(gz, gx, r):
    rad = math.radians(r)
    c, s = math.cos(rad), math.sin(rad)
    return gx * s + gz * c, gx * c - gz * s


def game_to_crs(gx, gz):
    lat, lng = apply_rot(gz, gx, rot)
    return t[0] * lng + t[1], -t[2] * (-lat) + t[3]


def svg_px(gx, gz, m):
    xmin, xmax, zmin, zmax = m["xmin"], m["xmax"], m["zmin"], m["zmax"]
    sw = game_to_crs(xmin, zmin)
    ne = game_to_crs(xmax, zmax)
    pt = game_to_crs(gx, gz)
    iw, ih = m["width"], m["height"]
    return (
        (pt[0] - sw[0]) / (ne[0] - sw[0]) * iw,
        (pt[1] - ne[1]) / (sw[1] - ne[1]) * ih,
    )


# rasterize SVG via cairosvg if available, else skip
svg_path = ROOT / "internal/maps_tarkov.dev_B/factory/map.svg"
scale = 8
W = int(meta["width"] * scale)
H = int(meta["height"] * scale)
im = None
try:
    import cairosvg

    im = Image.open(
        __import__("io").BytesIO(cairosvg.svg2png(url=str(svg_path), output_width=W, output_height=H))
    ).convert("RGBA")
except Exception as e:
    print("cairosvg unavailable:", e)
    # fallback: load reference PNG from z4 and compare positions scaled
    im = Image.open(ROOT / "internal/maps_tarkov.dev/factory/map.png").convert("RGBA")
    W, H = im.size
    scale = W / meta["width"]

m = dict(meta_f)  # float bounds from z4 sync
for p in pmc:
    gx, gz = p["coordinates"]
    sx, sy = svg_px(gx, gz, m)
    px, py = int(sx * scale), int(sy * scale)
    inside = 0 <= px < W and 0 <= py < H
    if inside:
        r, g, b, a = im.getpixel((px, py))
        print(f"{p['name']:18} svg=({sx:5.1f},{sy:5.1f}) px=({px},{py}) a={a} rgb=({r},{g},{b})")
    else:
        print(f"{p['name']:18} svg=({sx:5.1f},{sy:5.1f}) OUTSIDE")

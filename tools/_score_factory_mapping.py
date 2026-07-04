#!/usr/bin/env python3
"""Score factory mapping variants against visible PNG pixels."""
import json
import math
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
meta = json.loads((ROOT / "internal/maps_tarkov.dev/factory/meta.json").read_text())
meta_b = json.loads((ROOT / "internal/maps_tarkov.dev_B/factory/meta.json").read_text())
pmc = json.loads((ROOT / "internal/points/exfil/pmc.json").read_text())["factory"]
im = Image.open(ROOT / "internal/maps_tarkov.dev/factory/map.png").convert("RGBA")
bbox = im.getbbox() or (0, 0, im.width, im.height)
t = meta["transform"]
rot = int(meta["coordinates_rotation"])
Z = int(meta["tile_zoom"])
F = 2**Z
iw, ih = im.size


def rot_ll(gz, gx, r):
    if not r:
        return gz, gx
    rad = math.radians(r)
    c, s = math.cos(rad), math.sin(rad)
    return gx * s + gz * c, gx * c - gz * s


def score(name, fn):
    hits = 0
    total = 0
    for p in pmc:
        gx, gz = p["coordinates"]
        x, y = fn(gx, gz)
        if not (0 <= x < iw and 0 <= y < ih):
            continue
        total += 1
        r, g, b, a = im.getpixel((int(x), int(y)))
        if a > 128 and (r + g + b) > 40:
            hits += 1
    print(f"{name:40} {hits}/{total}")


def norm90(gx, gz, m):
    span_x = m["xmax"] - m["xmin"]
    span_z = m["zmax"] - m["zmin"]
    u = (m["zmax"] - gz) / span_z
    v = (gx - m["xmin"]) / span_x
    return u * iw, v * ih


def crs_xy(gx, gz, y_mode):
    lat, lng = rot_ll(gz, gx, rot)
    cx = t[0] * lng + t[1]
    if y_mode == "app":
        cy = (-t[2]) * (-lat) + t[3]
    elif y_mode == "neg":
        cy = (-t[2]) * lat + t[3]
    else:
        cy = t[2] * lat + t[3]
    return cx, cy


def tile_px(gx, gz, y_mode, flip_y=False):
    cx, cy = crs_xy(gx, gz, y_mode)
    lx, ly = cx * F, cy * F
    x = lx / (16 * 256) * iw
    y = ly / (16 * 256) * ih
    if flip_y:
        y = ih - y
    return x, y


def corner_px(gx, gz, y_mode, flip_y=False):
    corners = [
        (meta["xmin"], meta["zmax"]),
        (meta["xmax"], meta["zmin"]),
        (meta["xmin"], meta["zmin"]),
        (meta["xmax"], meta["zmax"]),
    ]
    xs, ys = [], []
    for gx0, gz0 in corners:
        cx, cy = crs_xy(gx0, gz0, y_mode)
        xs.append(cx * F)
        ys.append(cy * F)
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    cx, cy = crs_xy(gx, gz, y_mode)
    lx, ly = cx * F, cy * F
    x = (lx - min_x) / (max_x - min_x) * iw
    y = (ly - min_y) / (max_y - min_y) * ih
    if flip_y:
        y = ih - y
    return x, y


def svg_norm_to_png(gx, gz):
    u = (meta["zmax"] - gz) / (meta["zmax"] - meta["zmin"])
    v = (gx - meta["xmin"]) / (meta["xmax"] - meta["xmin"])
    return u * iw, v * ih


print("PNG content bbox", bbox)
for ym in ("app", "neg", "pos"):
    for fy in (False, True):
        score(f"tile y={ym} flip={fy}", lambda gx, gz, ym=ym, fy=fy: tile_px(gx, gz, ym, fy))
        score(f"corner y={ym} flip={fy}", lambda gx, gz, ym=ym, fy=fy: corner_px(gx, gz, ym, fy))
score("norm90 meta A", lambda gx, gz: norm90(gx, gz, meta))
score("norm90 meta B int", lambda gx, gz: norm90(gx, gz, meta_b))
score("norm90 meta A on png", svg_norm_to_png)

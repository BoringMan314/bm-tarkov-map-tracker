#!/usr/bin/env python3
"""Diagnose DEV labs marker placement: linear vs Leaflet CRS."""
from __future__ import annotations

import json
import math
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
META = json.loads((ROOT / "internal/maps_tarkov.dev/labs/meta.json").read_text())
PMC = json.loads((ROOT / "internal/points/exfil/pmc.json").read_text())["labs"]
MAPS_JSON = json.loads(
    urllib.request.urlopen(
        "https://raw.githubusercontent.com/the-hideout/tarkov-dev/main/src/data/maps.json"
    ).read()
)


def variant():
    for e in MAPS_JSON:
        if e.get("normalizedName") == "the-lab":
            for v in e.get("maps") or []:
                if v.get("key") == "the-lab":
                    return v
    raise SystemExit("no labs variant")


def rot_latlng(lat, lng, rotation):
    if not rotation:
        return lat, lng
    rad = math.radians(rotation)
    cos, sin = math.cos(rad), math.sin(rad)
    return lng * sin + lat * cos, lng * cos - lat * sin


def game_to_crs(x, z, transform, rotation):
    sx, mx, sy, my = transform
    sy *= -1
    lat, lng = rot_latlng(z, x, rotation)
    return sx * lng + mx, sy * (-lat) + my


def linear_px(x, z, meta, w, h):
    xmin, xmax = meta["xmin"], meta["xmax"]
    zmin, zmax = meta["zmin"], meta["zmax"]
    u = (z - zmin) / (zmax - zmin)
    v = (xmax - x) / (xmax - xmin)
    return u * w, v * h


def crs_px(x, z, meta, transform, zoom, tile_bbox, w, h, flip_y=False):
    layer_x, layer_y = game_to_crs(x, z, transform, meta["coordinates_rotation"])
    factor = 2**zoom
    lx, ly = layer_x * factor, layer_y * factor
    tmin_x, tmin_y, tmax_x, tmax_y, tile = tile_bbox
    bmin_x, bmin_y = tmin_x * tile, tmin_y * tile
    bmax_x, bmax_y = (tmax_x + 1) * tile, (tmax_y + 1) * tile
    px = (lx - bmin_x) / (bmax_x - bmin_x) * w
    py = (ly - bmin_y) / (bmax_y - bmin_y) * h
    if flip_y:
        py = h - py
    return px, py


def corner_bounds(meta, transform, zoom):
    xmin, xmax = meta["xmin"], meta["xmax"]
    zmin, zmax = meta["zmin"], meta["zmax"]
    corners = [(xmin, zmax), (xmax, zmin), (xmin, zmin), (xmax, zmax)]
    xs, ys = [], []
    for x, z in corners:
        lx, ly = game_to_crs(x, z, transform, meta["coordinates_rotation"])
        f = 2**zoom
        xs.append(lx * f)
        ys.append(ly * f)
    return min(xs), min(ys), max(xs), max(ys)


def main() -> None:
    v = variant()
    transform = v["transform"]
    w, h = META["width"], META["height"]
    zoom = 5  # from LABS_TILES pick

    # labs tile bbox from last download (z=5): bbox=(1,5)-(30,26)
    tile_bbox = (1, 5, 30, 26, 256)
    corner = corner_bounds(META, transform, zoom)

    print("=== labs meta gaps ===")
    print("has transform:", "transform" in META)
    print("tarkov.dev transform:", transform)
    print("tile bbox z=5:", tile_bbox[:4])

    print("\n=== Parking Gate sample ===")
    pt = next(p for p in PMC if p["name"] == "Parking Gate")
    x, z = pt["coordinates"]
    lin = linear_px(x, z, META, w, h)
    crs_tile = crs_px(x, z, META, transform, zoom, tile_bbox, w, h)
    crs_flip = crs_px(x, z, META, transform, zoom, tile_bbox, w, h, flip_y=True)
    bmin_x, bmin_y, bmax_x, bmax_y = corner
    crs_corner = (
        (game_to_crs(x, z, transform, META["coordinates_rotation"])[0] * 2**zoom - bmin_x)
        / (bmax_x - bmin_x)
        * w,
        (game_to_crs(x, z, transform, META["coordinates_rotation"])[1] * 2**zoom - bmin_y)
        / (bmax_y - bmin_y)
        * h,
    )
    print(f"game ({x}, {z})")
    print(f"  linear rot270 (current app): ({lin[0]:.0f}, {lin[1]:.0f})")
    print(f"  crs + tile bbox:             ({crs_tile[0]:.0f}, {crs_tile[1]:.0f})")
    print(f"  crs + tile bbox + flipY:     ({crs_flip[0]:.0f}, {crs_flip[1]:.0f})")
    print(f"  crs + corner bounds:         ({crs_corner[0]:.0f}, {crs_corner[1]:.0f})")

    print("\n=== all PMC exfils ===")
    for p in PMC:
        x, z = p["coordinates"]
        a = linear_px(x, z, META, w, h)
        b = crs_px(x, z, META, transform, zoom, tile_bbox, w, h)
        c = crs_px(x, z, META, transform, zoom, tile_bbox, w, h, flip_y=True)
        # 180deg flip around center vs linear
        flip180 = (w - a[0], h - a[1])
        print(
            f"{p['name'][:22]:22} lin=({a[0]:6.0f},{a[1]:6.0f}) "
            f"lin180=({flip180[0]:6.0f},{flip180[1]:6.0f}) "
            f"crs=({b[0]:6.0f},{b[1]:6.0f}) crsY=({c[0]:6.0f},{c[1]:6.0f})"
        )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Verify woods PMC extract pixels on DEV A satellite PNG."""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
META = json.loads((ROOT / "internal/maps_tarkov.dev/woods/meta.json").read_text(encoding="utf-8"))
PMC = json.loads((ROOT / "internal/points/exfil/pmc.json").read_text(encoding="utf-8"))["woods"]

try:
    from PIL import Image, ImageDraw
except ImportError:
    raise SystemExit("pip install Pillow")


def apply_rotation_lat_lng(z: float, x: float, rotation: int) -> tuple[float, float]:
    if rotation == 180:
        return -z, -x
    return z, x


def game_to_crs(game_x: float, game_z: float, transform: list, rotation: int) -> tuple[float, float]:
    scale_x = float(transform[0])
    margin_x = float(transform[1])
    scale_y = float(transform[2]) * -1
    margin_y = float(transform[3])
    lat, lng = apply_rotation_lat_lng(game_z, game_x, rotation)
    crs_y = scale_y * -lat + margin_y
    crs_x = scale_x * lng + margin_x
    return crs_x, crs_y


def game_to_map_pixels(game_x: float, game_z: float, meta: dict) -> tuple[float, float]:
    transform = meta["transform"]
    rot = int(meta.get("coordinates_rotation") or 180)
    zoom = int(meta["tile_zoom"])
    tile = int(meta.get("tile_size") or 256)
    tmin_x = int(meta["tile_min_x"])
    tmin_y = int(meta["tile_min_y"])
    tmax_x = int(meta["tile_max_x"])
    tmax_y = int(meta["tile_max_y"])
    stitch_w = float(meta["stitch_width"])
    stitch_h = float(meta["stitch_height"])
    off_x = float(meta.get("map_offset_x") or 0)
    off_y = float(meta.get("map_offset_y") or 0)
    map_w = float(meta["width"])
    map_h = float(meta["height"])

    layer = game_to_crs(game_x, game_z, transform, rot)
    layer = (layer[0] * 2**zoom, layer[1] * 2**zoom)
    bounds = {
        "minX": tmin_x * tile,
        "minY": tmin_y * tile,
        "maxX": (tmax_x + 1) * tile,
        "maxY": (tmax_y + 1) * tile,
    }
    span_x = bounds["maxX"] - bounds["minX"]
    span_y = bounds["maxY"] - bounds["minY"]
    nx = (layer[0] - bounds["minX"]) / span_x
    ny = (layer[1] - bounds["minY"]) / span_y
    x = nx * stitch_w - off_x
    y = ny * stitch_h - off_y

    cx, cy = map_w / 2, map_h / 2
    rad = math.pi
    dx, dy = x - cx, y - cy
    x = cx + dx * math.cos(rad) + dy * math.sin(rad)
    y = cy - dx * math.sin(rad) + dy * math.cos(rad)
    return x, y


def main() -> None:
    png_path = ROOT / "internal/maps_tarkov.dev/woods/map.png"
    img = Image.open(png_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    ok = 0
    for pt in PMC:
        x, z = pt["coordinates"]
        px, py = game_to_map_pixels(x, z, META)
        inside = 0 <= px < img.width and 0 <= py < img.height
        color = (0, 255, 0, 255) if inside else (255, 0, 0, 255)
        r = 18
        draw.ellipse((px - r, py - r, px + r, py + r), outline=color, width=3)
        print(f"{'OK' if inside else 'OUT'} {pt['name']}: ({px:.0f},{py:.0f})")
        if inside:
            ok += 1

    dark = sum(1 for px in img.getdata() if px[3] > 10 and px[0] < 8 and px[1] < 8 and px[2] < 8)
    total = img.width * img.height
    print(f"dark pixels: {dark}/{total} ({100*dark/total:.2f}%)")
    out = ROOT / "tools/_woods_verify.png"
    img.save(out)
    print(f"saved {out} ({ok}/{len(PMC)} inside)")


if __name__ == "__main__":
    main()

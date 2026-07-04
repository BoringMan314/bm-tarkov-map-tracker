#!/usr/bin/env python3
"""Verify streets PMC extract pixels on DEV A raster PNG (transform mapping)."""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
META = json.loads((ROOT / "internal/maps_tarkov.dev/streets/meta.json").read_text(encoding="utf-8"))
PMC = json.loads((ROOT / "internal/points/exfil/pmc.json").read_text(encoding="utf-8"))["streets"]

try:
    from PIL import Image, ImageDraw
except ImportError:
    raise SystemExit("pip install Pillow")

Image.MAX_IMAGE_PIXELS = None


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
    map_w = float(meta["width"])
    map_h = float(meta["height"])
    xmin, xmax = float(meta["xmin"]), float(meta["xmax"])
    zmin, zmax = float(meta["zmin"]), float(meta["zmax"])

    sw = game_to_crs(xmin, zmin, transform, rot)
    ne = game_to_crs(xmax, zmax, transform, rot)
    point = game_to_crs(game_x, game_z, transform, rot)
    span_x = ne[0] - sw[0]
    span_y = sw[1] - ne[1]
    x = ((point[0] - sw[0]) / span_x) * map_w
    y = ((point[1] - ne[1]) / span_y) * map_h

    cx, cy = map_w / 2, map_h / 2
    rad = math.pi
    dx, dy = x - cx, y - cy
    x = cx + dx * math.cos(rad) + dy * math.sin(rad)
    y = cy - dx * math.sin(rad) + dy * math.cos(rad)
    return x, y


def main() -> None:
    png_path = ROOT / "internal/maps_tarkov.dev/streets/map.png"
    if not png_path.is_file():
        raise SystemExit(f"missing {png_path}")

    img = Image.open(png_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    ok = 0
    for pt in PMC:
        x, z = pt["coordinates"]
        px, py = game_to_map_pixels(x, z, META)
        inside = 0 <= px < img.width and 0 <= py < img.height
        color = (0, 255, 0, 255) if inside else (255, 0, 0, 255)
        r = 24
        draw.ellipse((px - r, py - r, px + r, py + r), outline=color, width=4)
        print(f"{'OK' if inside else 'OUT'} {pt['name']}: ({px:.0f},{py:.0f})")
        if inside:
            ok += 1

    out = ROOT / "tools/_streets_verify.png"
    img.save(out)
    print(f"saved {out} ({ok}/{len(PMC)} inside)")


if __name__ == "__main__":
    main()

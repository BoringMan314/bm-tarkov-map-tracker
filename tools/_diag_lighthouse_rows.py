#!/usr/bin/env python3
"""Find lighthouse main-map row range in COM stitch."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

Image.MAX_IMAGE_PIXELS = None
p = Path(__file__).resolve().parent.parent / "internal/maps_eftarkov.com/lighthouse/map.png"
im = Image.open(p).convert("RGB")
w, h = im.size
tile = 256
rows = h // tile

for row in range(rows):
    y0 = row * tile
    band = im.crop((0, y0, w, y0 + tile)).resize((w // 8, tile // 8))
    px = list(band.getdata())
    # inset / padding rows: lots of near-white or near-gray flat areas
    white = sum(1 for r, g, b in px if r > 240 and g > 240 and b > 240)
    gray = sum(1 for r, g, b in px if abs(r - 198) < 10 and abs(g - 198) < 10)
    dark = sum(1 for r, g, b in px if r < 40 and g < 40 and b < 40)
    n = len(px)
    print(
        f"row {row:2d}: white={100*white/n:5.1f}% gray={100*gray/n:5.1f}% dark={100*dark/n:5.1f}%"
    )

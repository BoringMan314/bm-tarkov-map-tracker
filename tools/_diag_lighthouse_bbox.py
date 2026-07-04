#!/usr/bin/env python3
"""Find content bbox for COM lighthouse (exclude gray padding + black fringe)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

Image.MAX_IMAGE_PIXELS = None
p = Path(__file__).resolve().parent.parent / "internal/maps_eftarkov.com/lighthouse/map.png"
im = Image.open(p).convert("RGBA")
w, h = im.size

# Mask: keep pixels that look like map (not empty gray, not pure black alpha)
mask = Image.new("L", (w, h), 0)
px = im.load()
for y in range(h):
    for x in range(w):
        r, g, b, a = px[x, y]
        if a < 8:
            continue
        if abs(r - 198) < 8 and abs(g - 198) < 8 and abs(b - 198) < 8:
            continue
        if r < 12 and g < 12 and b < 12:
            continue
        mask.putpixel((x, y), 255)

bbox = mask.getbbox()
print("full", w, h)
print("content bbox", bbox)
if bbox:
    cw, ch = bbox[2] - bbox[0], bbox[3] - bbox[1]
    print("cropped", cw, ch)
    print("trim bottom rows", (h - bbox[3]) / 256)

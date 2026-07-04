#!/usr/bin/env python3
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
im = Image.open(ROOT / "internal/maps_tarkov.dev/factory/map.png").convert("RGBA")
pts = {
    "Cellars": (2676, 4154),
    "Gate 3": (268, 3751),
    "Gate 0": (461, 569),
    "Med Tent Gate": (3515, 1772),
    "Courtyard Gate": (121, 2848),
    "Smugglers": (2670, 3480),
}
print("image", im.size)
for name, (x, y) in pts.items():
    inside = 0 <= x < im.width and 0 <= y < im.height
    if inside:
        r, g, b, a = im.getpixel((x, y))
        dark = r + g + b < 30
        print(f"{name:18} ({x},{y}) inside alpha={a} rgb=({r},{g},{b}) dark={dark}")
    else:
        print(f"{name:18} ({x},{y}) OUT OF IMAGE")

#!/usr/bin/env python3
"""Scan stitched factory PNG for empty 256px grid cells."""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
png = ROOT / "internal/maps_eftarkov.com/factory/map.png"
meta = __import__("json").loads((ROOT / "internal/maps_eftarkov.com/factory/meta.json").read_text())
tile = int(meta["eftarkov_tile_size"])
cols = int(meta["eftarkov_cols"])
rows = int(meta["eftarkov_rows"])

im = Image.open(png).convert("RGBA")
w, h = im.size
print(f"png {w}x{h} meta grid {cols}x{rows} tile={tile}")

empty = []
for c in range(cols):
    for r in range(rows):
        x0, y0 = c * tile, r * tile
        box = im.crop((x0, y0, x0 + tile, y0 + tile))
        px = box.getdata()
        if all(a == 0 for _, _, _, a in px):
            empty.append((c, r, x0, y0))

print(f"fully transparent cells: {len(empty)}")
for c, r, x0, y0 in empty[:30]:
    print(f"  col={c} row={r} at ({x0},{y0})")

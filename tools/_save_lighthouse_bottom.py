#!/usr/bin/env python3
"""Save lighthouse bottom tile samples for visual inspection."""
from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from sync_maps_from_eftarkov import fetch, load_tile_from_level, parse_config  # noqa: E402

html = fetch("https://api.eftarkov.com/map/lighthouse/").decode("utf-8", "replace")
cfg = parse_config(html)
level = len(cfg["total_folders"]) - 1
tile = cfg["tile_size"]
out = ROOT / "tools/_lighthouse_bottom_samples"
out.mkdir(exist_ok=True)

for row in (44, 45, 46, 47):
    strip = Image.new("RGBA", (cfg["total_folders"][level] * tile, tile), (0, 0, 0, 0))
    for col in range(cfg["total_folders"][level]):
        img, ok = load_tile_from_level("lighthouse", cfg, level, col, row, tile)
        strip.paste(img, (col * tile, 0))
    strip.save(out / f"row_{row:02d}.png")
    print(f"row {row} saved, ok tiles")

# bottom band from stitched map
full = Image.open(ROOT / "internal/maps_eftarkov.com/lighthouse/map.png")
full.crop((0, full.height - 768, full.width, full.height)).save(out / "stitched_bottom768.png")
print("done", out)

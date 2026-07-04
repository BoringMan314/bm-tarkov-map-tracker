#!/usr/bin/env python3
"""Probe lighthouse bottom tiles: direct vs parent fallback."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from sync_maps_from_eftarkov import fetch, load_tile, load_tile_from_level, parse_config  # noqa: E402

html = fetch("https://api.eftarkov.com/map/lighthouse/").decode("utf-8", "replace")
cfg = parse_config(html)
level = len(cfg["total_folders"]) - 1
tile = cfg["tile_size"]
cols = cfg["total_folders"][level]

for row in range(40, 48):
    direct = parent = gray = 0
    for col in range(cols):
        img_d, ok_d = load_tile_from_level("lighthouse", cfg, level, col, row, tile)
        _, _, img_f, ok_f = load_tile("lighthouse", cfg, level, col, row, tile)
        if ok_d:
            direct += 1
        elif ok_f:
            parent += 1
        else:
            gray += 1
    print(f"row {row}: direct={direct} parent_fallback={parent} gray={gray}")

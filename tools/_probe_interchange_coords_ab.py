#!/usr/bin/env python3
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
meta_a = json.loads((ROOT / "internal/maps_tarkov.dev/interchange/meta.json").read_text(encoding="utf-8"))
meta_b = json.loads((ROOT / "internal/maps_tarkov.dev_B/interchange/meta.json").read_text(encoding="utf-8"))
pmc = json.loads((ROOT / "internal/points/exfil/pmc.json").read_text(encoding="utf-8"))["interchange"]


def rot_lat_lng(lat, lng, rotation):
    if not rotation:
        return lat, lng
    rad = math.radians(rotation)
    cos_r, sin_r = math.cos(rad), math.sin(rad)
    return lng * sin_r + lat * cos_r, lng * cos_r - lat * sin_r


def game_to_crs(gx, gz, meta):
    t = meta["transform"]
    rot = int(meta["coordinates_rotation"])
    lat, lng = rot_lat_lng(gz, gx, rot)
    return t[0] * lng + t[1], (-t[2]) * (-lat) + t[3]


def corner_px(gx, gz, meta, map_w, map_h):
    sw = game_to_crs(meta["xmin"], meta["zmin"], meta)
    ne = game_to_crs(meta["xmax"], meta["zmax"], meta)
    pt = game_to_crs(gx, gz, meta)
    span_x = ne[0] - sw[0]
    span_y = sw[1] - ne[1]
    return ((pt[0] - sw[0]) / span_x) * map_w, ((pt[1] - ne[1]) / span_y) * map_h


def tile_px(gx, gz, meta):
    t = meta["transform"]
    rot = int(meta["coordinates_rotation"])
    z = int(meta["tile_zoom"])
    ts = int(meta["tile_size"])
    lat, lng = rot_lat_lng(gz, gx, rot)
    cx = t[0] * lng + t[1]
    cy = (-t[2]) * (-lat) + t[3]
    f = 2**z
    lx, ly = cx * f, cy * f
    bmin_x = meta["tile_min_x"] * ts
    bmin_y = meta["tile_min_y"] * ts
    bmax_x = (meta["tile_max_x"] + 1) * ts
    bmax_y = (meta["tile_max_y"] + 1) * ts
    off_x = float(meta.get("map_offset_x") or 0)
    off_y = float(meta.get("map_offset_y") or 0)
    stitch_w = float(meta["stitch_width"])
    stitch_h = float(meta["stitch_height"])
    return (lx - bmin_x) / (bmax_x - bmin_x) * stitch_w - off_x, (
        ly - bmin_y
    ) / (bmax_y - bmin_y) * stitch_h - off_y


wa, ha = int(meta_a["width"]), int(meta_a["height"])
wb, hb = int(meta_b["width"]), int(meta_b["height"])
print(f"A png {wa}x{ha}  B schematic {wb}x{hb}\n")
print(f"{'name':<22} {'tile@A':>16} {'corner@B':>16} {'Bmeta@A':>16}")
for p in pmc:
    gx, gz = p["coordinates"]
    tp = tile_px(gx, gz, meta_a)
    cb = corner_px(gx, gz, meta_b, wb, hb)
    ca = corner_px(gx, gz, meta_b, wa, ha)
    print(f"{p.get('name', '?'):<22} ({tp[0]:7.0f},{tp[1]:7.0f}) ({cb[0]:7.0f},{cb[1]:7.0f}) ({ca[0]:7.0f},{ca[1]:7.0f})")

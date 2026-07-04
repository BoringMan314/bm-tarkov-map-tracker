#!/usr/bin/env python3
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
meta_a = json.loads((ROOT / "internal/maps_tarkov.dev/woods/meta.json").read_text(encoding="utf-8"))
meta_b = json.loads((ROOT / "internal/maps_tarkov.dev_B/woods/meta.json").read_text(encoding="utf-8"))
pmc = json.loads((ROOT / "internal/points/exfil/pmc.json").read_text(encoding="utf-8"))["woods"]


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
for p in pmc[:6]:
    gx, gz = p["coordinates"]
    tp = tile_px(gx, gz, meta_a)
    cb = corner_px(gx, gz, meta_b, wb, hb)
    ca = corner_px(gx, gz, meta_b, wa, ha)
    nu_t, nv_t = tp[0] / wa, tp[1] / ha
    nu_b, nv_b = cb[0] / wb, cb[1] / hb
    nu_a, nv_a = ca[0] / wa, ca[1] / ha
    print(
        f"{p.get('name', '?'):<20} tile@A({tp[0]:.0f},{tp[1]:.0f}) n=({nu_t:.3f},{nv_t:.3f}) "
        f"B@B n=({nu_b:.3f},{nv_b:.3f}) Bmeta@A n=({nu_a:.3f},{nv_a:.3f})"
    )

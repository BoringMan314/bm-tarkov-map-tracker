#!/usr/bin/env python3
"""Compare customs DEV A tile coords vs flipX vs DEV B schematic on A size."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
meta_a = json.loads((ROOT / "internal/maps_tarkov.dev/customs/meta.json").read_text(encoding="utf-8"))
meta_b = json.loads((ROOT / "internal/maps_tarkov.dev_B/customs/meta.json").read_text(encoding="utf-8"))
pmc = json.loads((ROOT / "internal/points/exfil/pmc.json").read_text(encoding="utf-8"))["customs"][:6]


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


def tile_px(gx, gz, meta, flip_x=False):
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
    sw = float(meta["stitch_width"])
    sh = float(meta["stitch_height"])
    mw = float(meta["width"])
    x = (lx - bmin_x) / (bmax_x - bmin_x) * sw - off_x
    y = (ly - bmin_y) / (bmax_y - bmin_y) * sh - off_y
    if flip_x:
        x = mw - x
    return x, y


def main():
    wa, ha = int(meta_a["width"]), int(meta_a["height"])
    print(f"A png {wa}x{ha}  z={meta_a.get('tile_zoom')} offset=({meta_a.get('map_offset_x')},{meta_a.get('map_offset_y')})")
    print(f"{'name':<22} {'tile@A':>16} {'flipX@A':>16} {'Bmeta@A':>16} |err tile| |err flip|")
    sum_tile = sum_flip = 0.0
    for p in pmc:
        gx, gz = p["coordinates"]
        tx, ty = tile_px(gx, gz, meta_a, flip_x=False)
        fx, fy = tile_px(gx, gz, meta_a, flip_x=True)
        bx, by = corner_px(gx, gz, meta_b, wa, ha)
        et = abs(tx - bx) + abs(ty - by)
        ef = abs(fx - bx) + abs(fy - by)
        sum_tile += et
        sum_flip += ef
        print(
            f"{p.get('name', '?')[:22]:22} ({tx:7.0f},{ty:7.0f}) "
            f"({fx:7.0f},{fy:7.0f}) ({bx:7.0f},{by:7.0f}) {et:8.0f} {ef:8.0f}"
        )
    print(f"\nTotal L1 error: tile={sum_tile:.0f}  flip={sum_flip:.0f}")


if __name__ == "__main__":
    main()

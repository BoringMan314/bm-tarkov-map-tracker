#!/usr/bin/env python3
"""Copy DEV B streets exfil points to COM with display_coordinates on COM map."""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP_ID = "streets"
DEV_B_META = ROOT / "internal" / "maps_tarkov.dev_B" / MAP_ID / "meta.json"
COM_META = ROOT / "internal" / "maps_eftarkov.com" / MAP_ID / "meta.json"
EXFIL = ROOT / "internal" / "points" / "exfil"
EFTARKOV = ROOT / "internal" / "points" / "eftarkov"
KINDS = ("pmc", "scav", "coop", "transit")
MARKER_ROTATION_DEG = 180
# COM streets PNG is a tile mosaic; DEV schematic maps 1:1 to dev meta size, not full COM canvas.
STREETS_COM_POINT_SCALE = 0.55
# DEV schematic is vertically centered on full PNG; satellite playable area sits slightly lower.
STREETS_COM_POINT_OFFSET_Y = 750


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")


def mapping_extents(meta: dict) -> dict[str, float]:
    for prefix in ("svg_", ""):
        xmin = meta.get(f"{prefix}xmin")
        xmax = meta.get(f"{prefix}xmax")
        zmin = meta.get(f"{prefix}zmin")
        zmax = meta.get(f"{prefix}zmax")
        if all(v is not None for v in (xmin, xmax, zmin, zmax)):
            return {
                "xmin": float(xmin),
                "xmax": float(xmax),
                "zmin": float(zmin),
                "zmax": float(zmax),
            }
    raise ValueError("bounds missing in DEV B streets meta")


def apply_rotation_lat_lng(lat: float, lng: float, rotation: int) -> tuple[float, float]:
    if not rotation:
        return lat, lng
    rad = math.radians(rotation)
    cos = math.cos(rad)
    sin = math.sin(rad)
    return lng * sin + lat * cos, lng * cos - lat * sin


def game_to_crs(game_x: float, game_z: float, transform: list[float], rotation: int) -> tuple[float, float]:
    scale_x, margin_x, scale_y_raw, margin_y = transform
    scale_y = scale_y_raw * -1
    lat, lng = apply_rotation_lat_lng(game_z, game_x, rotation)
    crs_y = scale_y * -lat + margin_y
    return scale_x * lng + margin_x, crs_y


def rotate_map_pixels(x: float, y: float, map_w: float, map_h: float, degrees: int) -> tuple[float, float]:
    if not degrees:
        return x, y
    cx, cy = map_w / 2, map_h / 2
    rad = math.radians(degrees)
    cos, sin = math.cos(rad), math.sin(rad)
    dx, dy = x - cx, y - cy
    return cx + dx * cos + dy * sin, cy - dx * sin + dy * cos


def dev_b_game_to_com_display(
    game_x: float,
    game_z: float,
    dev_meta: dict,
    com_w: float,
    com_h: float,
) -> tuple[float, float]:
    """Project DEV B schematic pixels onto COM canvas (uniform scale, centered)."""
    dev_w = float(dev_meta["width"])
    dev_h = float(dev_meta["height"])
    if not dev_w or not dev_h:
        raise ValueError("DEV B streets meta missing width/height")

    transform = dev_meta["transform"]
    rotation = int(dev_meta.get("coordinates_rotation", 180))
    ext = mapping_extents(dev_meta)
    sw = game_to_crs(ext["xmin"], ext["zmin"], transform, rotation)
    ne = game_to_crs(ext["xmax"], ext["zmax"], transform, rotation)
    pt = game_to_crs(game_x, game_z, transform, rotation)
    span_x = ne[0] - sw[0]
    span_y = sw[1] - ne[1]
    if not span_x or not span_y:
        raise ValueError("invalid DEV B streets CRS span")

    x_dev = (pt[0] - sw[0]) / span_x * dev_w
    y_dev = (pt[1] - ne[1]) / span_y * dev_h
    x_dev, y_dev = rotate_map_pixels(x_dev, y_dev, dev_w, dev_h, MARKER_ROTATION_DEG)

    scale = (com_h / dev_h) * STREETS_COM_POINT_SCALE
    off_x = (com_w - dev_w * scale) / 2
    off_y = (com_h - dev_h * scale) / 2 + STREETS_COM_POINT_OFFSET_Y
    return round(off_x + x_dev * scale, 2), round(off_y + y_dev * scale, 2)


def copy_row(row: dict, dev_meta: dict, com_w: float, com_h: float) -> dict:
    gx, gz = row["coordinates"]
    px, py = dev_b_game_to_com_display(float(gx), float(gz), dev_meta, com_w, com_h)
    out = {
        "id": row["id"],
        "name": row.get("name", ""),
        "coordinates": [float(gx), float(gz)],
        "display_coordinates": [px, py],
    }
    return out


def main() -> None:
    dev_meta = load_json(DEV_B_META)
    com_meta = load_json(COM_META)
    com_w = float(com_meta["width"])
    com_h = float(com_meta["height"])
    if not com_w or not com_h:
        raise SystemExit("FAIL: COM streets meta missing width/height")

    exfil_names = load_json(EXFIL / "names.json") if (EXFIL / "names.json").is_file() else {}
    eft_names = load_json(EFTARKOV / "names.json") if (EFTARKOV / "names.json").is_file() else {}

    totals: dict[str, int] = {}
    for kind in KINDS:
        src_path = EXFIL / f"{kind}.json"
        dst_path = EFTARKOV / f"{kind}.json"
        src = load_json(src_path) if src_path.is_file() else {}
        dst = load_json(dst_path) if dst_path.is_file() else {}
        rows = src.get(MAP_ID, [])
        if not isinstance(rows, list):
            rows = []
        copied = [copy_row(row, dev_meta, com_w, com_h) for row in rows]
        dst[MAP_ID] = copied
        save_json(dst_path, dst)
        totals[kind] = len(copied)
        print(f"OK {dst_path.relative_to(ROOT)} streets={len(copied)}")

        for row in rows:
            ex_id = str(row.get("id", "")).strip()
            if ex_id and ex_id in exfil_names:
                eft_names[ex_id] = dict(exfil_names[ex_id])

    save_json(EFTARKOV / "names.json", eft_names)
    print(
        f"OK COM streets from DEV B: "
        f"pmc={totals.get('pmc', 0)} scav={totals.get('scav', 0)} "
        f"coop={totals.get('coop', 0)} transit={totals.get('transit', 0)} "
        f"map={int(com_w)}x{int(com_h)} scale={STREETS_COM_POINT_SCALE} y_off={STREETS_COM_POINT_OFFSET_Y}"
    )


if __name__ == "__main__":
    main()

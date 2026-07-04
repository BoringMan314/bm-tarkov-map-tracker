#!/usr/bin/env python3
"""Sync lighthouse map bundles into root maps/ (DEV A/B SVG + eftarkov.com PNG)."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAPS = ROOT / "maps"
SUFFIX_A = "tarkov.dev_A"
SUFFIX_B = "tarkov.dev_B"
SUFFIX_COM = "eftarkov.com"

sys.path.insert(0, str(ROOT / "tools"))
import download_tarkov_dev_maps as dl  # noqa: E402
from sync_maps_from_eftarkov import composite_stitch, fetch, parse_config  # noqa: E402
from sync_markers_from_tarkovdev import clean_transit_label, gql  # noqa: E402

MAP_ID = "lighthouse"
DISPLAY = "Lighthouse"


def fetch_dev_points() -> dict[str, list]:
    points: dict[str, list] = {"pmc": [], "scav": [], "coop": [], "transit": []}
    for entry in gql("en"):
        if entry.get("normalizedName") != MAP_ID:
            continue
        for ex in entry.get("extracts") or []:
            faction = (ex.get("faction") or "").strip().lower()
            bucket = {"pmc": "pmc", "scav": "scav", "shared": "coop"}.get(faction)
            if not bucket:
                continue
            pos = ex.get("position") or {}
            x, z = pos.get("x"), pos.get("z")
            ex_id = (ex.get("id") or "").strip()
            name = (ex.get("name") or "").strip()
            if x is None or z is None or not ex_id or not name:
                continue
            points[bucket].append(
                {"id": ex_id, "name": name, "coordinates": [float(x), float(z)]}
            )
        for tr in entry.get("transits") or []:
            pos = tr.get("position") or {}
            x, z = pos.get("x"), pos.get("z")
            ex_id = (tr.get("id") or "").strip()
            name = clean_transit_label((tr.get("description") or "").strip())
            if x is None or z is None or not ex_id or not name:
                continue
            points["transit"].append(
                {"id": ex_id, "name": name, "coordinates": [float(x), float(z)]}
            )
        break
    return points


def fetch_com_points(layout: dict | None) -> dict[str, list]:
    from sync_points_from_eftarkov import (  # noqa: E402
        CATEGORIES,
        extract_legend_data,
        eftarkov_to_display_px,
        max_level_index,
        level_dims,
        pos_at_level,
    )

    html = fetch(f"https://api.eftarkov.com/map/{MAP_ID}/").decode("utf-8", "replace")
    cfg_raw = parse_config(html)
    level = max_level_index(cfg_raw)
    legend = extract_legend_data(html)
    points: dict[str, list] = {"pmc": [], "scav": [], "coop": [], "transit": []}
    for cat_key, bucket in CATEGORIES.items():
        cat = legend.get(cat_key)
        if not cat:
            continue
        for idx, item in enumerate(cat.get("items") or []):
            pos = pos_at_level(item, level)
            if not pos:
                continue
            mx, my = pos
            name = (item.get("name") or "").strip()
            ex_id = f"eft-{MAP_ID}-{bucket}-{idx}"
            row = {
                "id": ex_id,
                "name": name,
                "coordinates": [float(mx), float(my)],
            }
            if layout:
                px, py = eftarkov_to_display_px(
                    mx,
                    my,
                    layout["cols"],
                    layout["rows"],
                    layout["tile_size"],
                    int(layout["width"]),
                    int(layout["height"]),
                    int(layout.get("offset_x") or 0),
                    int(layout.get("offset_y") or 0),
                )
                row["display_coordinates"] = [round(px, 2), round(py, 2)]
            points[bucket].append(row)
    return points


def lighthouse_variant(maps_data: list) -> dict:
    for entry in maps_data:
        if entry.get("normalizedName") != MAP_ID:
            continue
        for variant in entry.get("maps") or []:
            if variant.get("key") == MAP_ID and variant.get("projection") == "interactive":
                return variant
    raise SystemExit("FAIL: lighthouse interactive variant not found")


def dev_svg_bytes(maps_data: list) -> tuple[bytes, float, float]:
    variant = lighthouse_variant(maps_data)
    url = variant.get("svgPath") or "https://assets.tarkov.dev/maps/svg/Lighthouse.svg"
    data = dl.fetch(url)
    layer = variant.get("svgLayer") or "Ground_Level"
    data = dl.extract_svg_layer(data, layer)
    data = dl.normalize_svg_bytes(data)
    w, h, _ = dl.parse_viewbox(data)
    if w <= 0 or h <= 0:
        raise SystemExit("FAIL: lighthouse SVG viewBox")
    return data, float(w), float(h)


def dev_meta(maps_data: list, width: float, height: float) -> dict:
    meta_by_id = dl.collect_meta(maps_data)
    bounds = meta_by_id[MAP_ID]
    entry = dl.meta_entry(MAP_ID, bounds, width, height, tile_cfg=None)
    entry["display_name"] = DISPLAY
    return entry


def write_bundle(suffix: str, meta: dict, points: dict[str, list], image: bytes, ext: str) -> None:
    stem = f"{MAP_ID}_{suffix}"
    bundle = {**meta, "points": points}
    if ext == ".png":
        bundle["map_asset_rev"] = hashlib.sha256(image).hexdigest()[:16]
    (MAPS / f"{stem}.json").write_text(
        json.dumps(bundle, indent=4, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    opp = ".svg" if ext == ".png" else ".png"
    opp_path = MAPS / f"{stem}{opp}"
    if opp_path.is_file():
        opp_path.unlink()
    (MAPS / f"{stem}{ext}").write_bytes(image)
    print(f"OK maps/{stem}.json + {stem}{ext}")


def sync_com() -> dict:
    html = fetch(f"https://api.eftarkov.com/map/{MAP_ID}/").decode("utf-8", "replace")
    cfg = parse_config(html)
    png, w, h, level, cols, rows, off_x, off_y = composite_stitch(MAP_ID, cfg, html)
    meta = {
        "name": MAP_ID,
        "display_name": DISPLAY,
        "description": "",
        "width": w,
        "height": h,
        "coordinates_rotation": 0,
        "eftarkov_level": level,
        "eftarkov_cols": cols,
        "eftarkov_rows": rows,
        "eftarkov_tile_size": cfg["tile_size"],
        "map_offset_x": off_x,
        "map_offset_y": off_y,
    }
    layout = {
        "cols": cols,
        "rows": rows,
        "tile_size": cfg["tile_size"],
        "width": int(w),
        "height": int(h),
        "offset_x": off_x,
        "offset_y": off_y,
    }
    points = fetch_com_points(layout)
    write_bundle(SUFFIX_COM, meta, points, png, ".png")
    return {
        "level": level,
        "cols": cols,
        "rows": rows,
        "tile_size": cfg["tile_size"],
    }


def main() -> None:
    maps_data = dl.fetch_maps_json()
    svg_a, w_a, h_a = dev_svg_bytes(maps_data)
    meta_a = dev_meta(maps_data, w_a, h_a)
    dev_points = fetch_dev_points()
    write_bundle(SUFFIX_A, meta_a, dev_points, svg_a, ".svg")
    write_bundle(SUFFIX_B, dict(meta_a), dev_points, svg_a, ".svg")

    com_layout = sync_com()

    eft_meta_path = MAPS / "eftarkov.meta.json"
    eft_meta = json.loads(eft_meta_path.read_text(encoding="utf-8"))
    eft_meta[MAP_ID] = {
        "level": com_layout["level"],
        "cols": com_layout["cols"],
        "rows": com_layout["rows"],
        "tile_size": com_layout["tile_size"],
    }
    eft_meta_path.write_text(json.dumps(eft_meta, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
    print("OK maps/eftarkov.meta.json (lighthouse)")


if __name__ == "__main__":
    main()

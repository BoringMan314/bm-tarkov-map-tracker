#!/usr/bin/env python3
"""Sync exfil/transit points from api.eftarkov.com embedded LEGEND_DATA."""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "internal" / "points" / "eftarkov"
MAPS = ROOT / "internal" / "maps_eftarkov.com"
BASE = "https://api.eftarkov.com/map"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

CATALOG = [
    ("factory", "factory"),
    ("groundzero", "ground-zero"),
    ("interchange", "interchange"),
    ("lighthouse", "lighthouse"),
    ("labs", "the-lab"),
    ("customs", "customs"),
    ("shoreline", "shoreline"),
    ("reserve", "reserve"),
    ("woods", "woods"),
]

# LEGEND_DATA category key -> our bucket
CATEGORIES = {
    "PMCchelidian": "pmc",
    "Scavchelidian": "scav",
    "malasongzhuanyidian": "transit",
}

# Woods shared extracts on eftarkov.com are listed under PMC/Scav, not a separate bucket.
EFT_WOODS_COOP_NAMES = frozenset({"UN路障", "郊区"})
EFT_WOODS_COOP_IDS = {
    "郊区": "eft-woods-coop-0",
    "UN路障": "eft-woods-coop-1",
}

LEVEL = 4  # preferred max zoom level in eftarkov canvas maps


def localize_chinese_names(names: dict[str, dict[str, str]]) -> None:
    """Convert zh_CN (Simplified) to distinct zh_TW (Traditional) via OpenCC."""
    try:
        import opencc

        converter = opencc.OpenCC("s2t")
    except ImportError:
        print("warning: opencc not installed; run: pip install opencc-python-reimplemented")
        converter = None
    for langs in names.values():
        zh_cn = (langs.get("zh_CN") or langs.get("zh") or "").strip()
        if not zh_cn:
            continue
        langs["zh_CN"] = zh_cn
        langs.pop("zh", None)
        if converter:
            langs["zh_TW"] = converter.convert(zh_cn)
        elif not langs.get("zh_TW"):
            langs["zh_TW"] = zh_cn


def max_level_index(cfg: dict) -> int:
    n = len(cfg["total_folders"])
    return min(LEVEL, n - 1) if n else 0


def level_dims(cfg: dict, level: int) -> dict:
    return {
        "level": level,
        "cols": cfg["total_folders"][level],
        "rows": cfg["images_per_folder"][level],
        "tile_size": cfg["tile_size"],
    }


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.read().decode("utf-8", "replace")


def parse_config(html: str) -> dict:
    folders = re.search(r"totalFolders:\s*\[([^\]]+)\]", html)
    per_folder = re.search(r"imagesPerFolder:\s*\[([^\]]+)\]", html)
    tile = re.search(r"tileSize:\s*(\d+)", html)
    if not folders or not per_folder or not tile:
        raise ValueError("config block not found")
    total_folders = [int(x.strip()) for x in folders.group(1).split(",")]
    images_per_folder = [int(x.strip()) for x in per_folder.group(1).split(",")]
    return {
        "total_folders": total_folders,
        "images_per_folder": images_per_folder,
        "tile_size": int(tile.group(1)),
    }


def extract_legend_data(html: str) -> dict:
    m = re.search(r"const\s+LEGEND_DATA\s*=\s*(\{[\s\S]*?\n\s*\});", html)
    if not m:
        raise ValueError("LEGEND_DATA not found")
    raw = m.group(1)
    # JS object -> JSON: quote keys, true/false, trailing commas
    raw = re.sub(r"(\s)([A-Za-z_][A-Za-z0-9_]*)(\s*:)", r'\1"\2"\3', raw)
    raw = raw.replace("'", '"')
    raw = re.sub(r",\s*}", "}", raw)
    raw = re.sub(r",\s*]", "]", raw)
    raw = raw.replace("true", "true").replace("false", "false")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LEGEND_DATA JSON parse failed: {e}") from e


def eftarkov_to_display_px(
    mx: float,
    my: float,
    cols: int,
    rows: int,
    tile: int,
    map_w: int,
    map_h: int,
    off_x: int = 0,
    off_y: int = 0,
) -> tuple[float, float]:
    ew, eh = cols * tile, rows * tile
    cw, ch = ew - off_x, eh - off_y
    sx = mx + ew / 2 - off_x
    sy = my + eh / 2 - off_y
    px = (sx / cw) * map_w if map_w < cw else sx
    py = sy if map_h < ch else (sy / ch) * map_h
    return px, py


def load_map_layout(map_id: str) -> dict | None:
    meta_path = MAPS / map_id / "meta.json"
    if not meta_path.is_file():
        return None
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    cols = int(meta.get("eftarkov_cols") or 0)
    rows = int(meta.get("eftarkov_rows") or 0)
    tile = int(meta.get("eftarkov_tile_size") or 256)
    width = int(meta.get("width") or 0)
    height = int(meta.get("height") or 0)
    if not cols or not rows or not width or not height:
        return None
    return {
        "cols": cols,
        "rows": rows,
        "tile_size": tile,
        "width": width,
        "height": height,
        "offset_x": int(meta.get("map_offset_x") or 0),
        "offset_y": int(meta.get("map_offset_y") or 0),
    }


def bake_display_coordinates(
    buckets: dict[str, list],
    map_id: str,
    layout: dict | None,
) -> None:
    if not layout:
        return
    for rows in buckets.values():
        for row in rows:
            mx, my = row["coordinates"]
            px, py = eftarkov_to_display_px(
                float(mx),
                float(my),
                layout["cols"],
                layout["rows"],
                layout["tile_size"],
                layout["width"],
                layout["height"],
                layout["offset_x"],
                layout["offset_y"],
            )
            row["display_coordinates"] = [round(px, 2), round(py, 2)]


def pos_at_level(item: dict, level: int) -> tuple[float, float] | None:
    positions = item.get("positions") or []
    for p in positions:
        if int(p.get("level", -1)) == level:
            return float(p["mapX"]), float(p["mapY"])
    if positions:
        p = positions[-1]
        return float(p["mapX"]), float(p["mapY"])
    return None


def sync_map(map_id: str, url_slug: str) -> dict | None:
    url = f"{BASE}/{url_slug}/"
    try:
        html = fetch(url)
    except OSError as e:
        print(f"skip {map_id}: {e}")
        return None
    cfg_raw = parse_config(html)
    level = max_level_index(cfg_raw)
    cfg = level_dims(cfg_raw, level)
    legend = extract_legend_data(html)
    buckets: dict[str, list] = {k: [] for k in ("pmc", "scav", "transit", "coop")}
    names: dict[str, dict[str, str]] = {}
    for cat_key, bucket in CATEGORIES.items():
        cat = legend.get(cat_key) or legend.get(cat_key.replace("chelidian", "chelidian"))
        if not cat:
            continue
        for idx, item in enumerate(cat.get("items") or []):
            pos = pos_at_level(item, level)
            if not pos:
                continue
            mx, my = pos
            name = (item.get("name") or "").strip()
            ex_id = f"eft-{map_id}-{bucket}-{idx}"
            buckets[bucket].append(
                {
                    "id": ex_id,
                    "name": name,
                    "coordinates": [mx, my],
                }
            )
            names[ex_id] = {"zh_CN": name, "en": name, "ja": name}
    localize_chinese_names(names)
    layout = load_map_layout(map_id)
    bake_display_coordinates(buckets, map_id, layout)
    baked = sum(
        1
        for rows in buckets.values()
        for row in rows
        if row.get("display_coordinates")
    )
    total = sum(len(buckets[k]) for k in buckets)
    layout_note = f" display={baked}/{total}" if layout else " (no map meta for display_coordinates)"
    print(f"OK {map_id}: {total} points cols={cfg['cols']} rows={cfg['rows']}{layout_note}")
    return {"config": cfg, "buckets": buckets, "names": names}


def apply_eftarkov_woods_coop(
    all_buckets: dict[str, dict[str, list]],
    all_names: dict[str, dict[str, str]],
) -> None:
    mid = "woods"
    moved: dict[str, dict] = {}
    for bucket in ("pmc", "scav"):
        kept: list[dict] = []
        for row in all_buckets.get(bucket, {}).get(mid, []):
            name = (row.get("name") or "").strip()
            if name in EFT_WOODS_COOP_NAMES:
                if name not in moved or bucket == "pmc":
                    moved[name] = dict(row)
            else:
                kept.append(row)
        all_buckets.setdefault(bucket, {})[mid] = kept

    coop_rows = list(all_buckets.get("coop", {}).get(mid, []))
    coop_names = {(row.get("name") or "").strip() for row in coop_rows}
    for name in ("郊区", "UN路障"):
        if name not in moved or name in coop_names:
            continue
        row = moved[name]
        new_id = EFT_WOODS_COOP_IDS[name]
        old_id = row.get("id")
        row["id"] = new_id
        coop_rows.append(row)
        coop_names.add(name)
        if old_id and old_id in all_names and new_id not in all_names:
            all_names[new_id] = dict(all_names[old_id])
        if new_id in all_names:
            if name == "郊区":
                all_names[new_id]["zh_TW"] = "郊區"
                all_names[new_id]["en"] = "Outskirts"
                all_names[new_id]["ja"] = "Outskirts"
            elif name == "UN路障":
                all_names[new_id]["en"] = "UN Roadblock"
                all_names[new_id]["ja"] = "UN Roadblock"
    all_buckets.setdefault("coop", {})[mid] = coop_rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    all_buckets: dict[str, dict[str, list]] = {k: {} for k in ("pmc", "scav", "transit", "coop")}
    map_meta: dict[str, dict] = {}
    all_names: dict[str, dict[str, str]] = {}

    for map_id, url_slug in CATALOG:
        result = sync_map(map_id, url_slug)
        if not result:
            for k in all_buckets:
                all_buckets[k][map_id] = []
            continue
        map_meta[map_id] = result["config"]
        for k, rows in result["buckets"].items():
            all_buckets[k][map_id] = rows
        all_names.update(result["names"])

    apply_eftarkov_woods_coop(all_buckets, all_names)

    for map_id, _slug in CATALOG:
        layout = load_map_layout(map_id)
        if not layout:
            print(f"warning: {map_id} missing {MAPS / map_id / 'meta.json'}; run sync_maps_from_eftarkov.py")
            continue
        for kind in all_buckets:
            bake_display_coordinates({kind: all_buckets[kind].get(map_id, [])}, map_id, layout)

    map_ids = [m[0] for m in CATALOG]
    for kind, by_map in all_buckets.items():
        ordered = {mid: by_map.get(mid, []) for mid in map_ids}
        path = OUT / f"{kind}.json"
        path.write_text(json.dumps(ordered, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
        total = sum(len(v) for v in ordered.values())
        print(f"wrote {path.relative_to(ROOT)} ({total})")

    (OUT / "meta.json").write_text(
        json.dumps(map_meta, indent=4, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (OUT / "names.json").write_text(
        json.dumps(all_names, indent=4, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"wrote {OUT.relative_to(ROOT)}/meta.json ({len(map_meta)} maps)")


if __name__ == "__main__":
    main()

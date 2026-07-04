#!/usr/bin/env python3
"""Sync labyrinth map + points into DEV A, DEV B, and COM (three identical copies)."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP_ID = "labyrinth"

MAP_TARGETS = (
    ROOT / "internal" / "maps_tarkov.dev" / MAP_ID,
    ROOT / "internal" / "maps_tarkov.dev_B" / MAP_ID,
    ROOT / "internal" / "maps_eftarkov.com" / MAP_ID,
)

POINT_DIRS = (
    ROOT / "internal" / "points" / "exfil",
    ROOT / "internal" / "points" / "eftarkov",
)

POINT_KINDS = ("pmc", "scav", "coop", "transit")

sys.path.insert(0, str(ROOT / "tools"))
from download_tarkov_dev_maps import (  # noqa: E402
    collect_meta,
    fetch_maps_json,
    meta_entry,
    probe_labyrinth_tiles,
)
from sync_markers_from_tarkovdev import (  # noqa: E402
    FACTION_FILES,
    NAME_LANGS,
    gql,
    localize_chinese_names,
    map_id,
)


def fetch_labyrinth_points() -> tuple[dict[str, list], dict[str, dict[str, str]]]:
    by_lang = {lang: gql(lang) for lang in NAME_LANGS}
    buckets: dict[str, list] = {kind: [] for kind in POINT_KINDS}
    names: dict[str, dict[str, str]] = {}

    for entry in by_lang["en"]:
        if map_id(entry.get("normalizedName", "")) != MAP_ID:
            continue
        for ex in entry.get("extracts") or []:
            faction = (ex.get("faction") or "").strip().lower()
            fname = FACTION_FILES.get(faction)
            if not fname:
                continue
            kind = Path(fname).stem
            pos = ex.get("position") or {}
            x, z = pos.get("x"), pos.get("z")
            if x is None or z is None:
                continue
            ex_id = (ex.get("id") or "").strip()
            name = (ex.get("name") or "").strip()
            if not ex_id or not name:
                continue
            buckets[kind].append(
                {
                    "id": ex_id,
                    "name": name,
                    "coordinates": [float(x), float(z)],
                }
            )
            names.setdefault(ex_id, {})
        for tr in entry.get("transits") or []:
            pos = tr.get("position") or {}
            x, z = pos.get("x"), pos.get("z")
            tr_id = (tr.get("id") or "").strip()
            desc = (tr.get("description") or "").strip()
            if x is None or z is None or not tr_id or not desc:
                continue
            buckets["transit"].append(
                {
                    "id": tr_id,
                    "name": desc,
                    "coordinates": [float(x), float(z)],
                }
            )
            names.setdefault(tr_id, {})

    for lang in NAME_LANGS:
        for entry in by_lang[lang]:
            if map_id(entry.get("normalizedName", "")) != MAP_ID:
                continue
            for ex in entry.get("extracts") or []:
                ex_id = (ex.get("id") or "").strip()
                name = (ex.get("name") or "").strip()
                if ex_id and name:
                    names.setdefault(ex_id, {})[lang] = name
            for tr in entry.get("transits") or []:
                tr_id = (tr.get("id") or "").strip()
                desc = (tr.get("description") or "").strip()
                if tr_id and desc:
                    names.setdefault(tr_id, {})[lang] = desc

    localize_chinese_names(names)
    return buckets, names


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")


def write_points_to_dir(points_dir: Path, buckets: dict[str, list]) -> None:
    for kind in POINT_KINDS:
        path = points_dir / f"{kind}.json"
        payload = load_json(path) if path.is_file() else {}
        rows = buckets.get(kind, [])
        payload[MAP_ID] = rows
        save_json(path, payload)
        print(f"OK {path.relative_to(ROOT)} labyrinth={len(rows)}")


def sync_map_assets() -> dict:
    maps_data = fetch_maps_json()
    bounds = collect_meta(maps_data).get(MAP_ID)
    if not bounds:
        raise SystemExit("FAIL: labyrinth bounds missing from tarkov.dev maps.json")

    tile_cfg, png, aw, ah = probe_labyrinth_tiles()
    meta = meta_entry(MAP_ID, bounds, aw, ah, tile_cfg=tile_cfg)
    meta["map_asset_rev"] = hashlib.sha256(png).hexdigest()[:16]

    for target in MAP_TARGETS:
        target.mkdir(parents=True, exist_ok=True)
        (target / "map.png").write_bytes(png)
        save_json(target / "meta.json", meta)
        print(f"OK {target.relative_to(ROOT)}/map.png ({int(aw)}x{int(ah)})")

    return meta


def sync_point_assets() -> None:
    buckets, names = fetch_labyrinth_points()
    total = sum(len(buckets[k]) for k in POINT_KINDS)
    print(f"OK labyrinth points from tarkov.dev: {total}")

    for points_dir in POINT_DIRS:
        write_points_to_dir(points_dir, buckets)
        names_path = points_dir / "names.json"
        all_names = load_json(names_path) if names_path.is_file() else {}
        for ex_id, langs in names.items():
            all_names[ex_id] = langs
        save_json(names_path, all_names)


def main() -> None:
    sync_map_assets()
    sync_point_assets()
    print("OK labyrinth replicated to DEV A / DEV B / COM")


if __name__ == "__main__":
    main()

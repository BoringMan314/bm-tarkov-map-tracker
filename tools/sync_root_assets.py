#!/usr/bin/env python3
"""Verify repo-root embed assets exist before build.

Canonical (edit here; embed.go embeds these directly):
  maps/<id>_tarkov.dev_A.json (+ .png)
  maps/<id>_tarkov.dev_B.json (+ .svg or .png)
  maps/<id>_eftarkov.com.json (+ .png)
  maps/catalog.json, maps/eftarkov.meta.json
  points/exfil-*.png, points/player.png
  icons/icon.ico, icons/icon.png
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICONS_OUT = ROOT / "icons"
MAPS_OUT = ROOT / "maps"
POINTS_OUT = ROOT / "points"

SUFFIX_A = "tarkov.dev_A"
SUFFIX_B = "tarkov.dev_B"
SUFFIX_COM = "eftarkov.com"

POINT_ICON_NAMES = ("exfil-pmc", "exfil-scav", "exfil-coop", "exfil-transit", "player")


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise SystemExit(f"FAIL missing {label}: {path.relative_to(ROOT)}")


def map_raster_paths(map_id: str, suffix: str) -> tuple[Path, Path]:
    stem = f"{map_id}_{suffix}"
    return MAPS_OUT / f"{stem}.png", MAPS_OUT / f"{stem}.svg"


def map_raster_exists(map_id: str, suffix: str) -> bool:
    png, svg = map_raster_paths(map_id, suffix)
    return png.is_file() or svg.is_file()


def check_map_bundle(map_id: str, suffix: str) -> None:
    json_path = MAPS_OUT / f"{map_id}_{suffix}.json"
    require_file(json_path, f"maps/{json_path.name}")
    if not map_raster_exists(map_id, suffix):
        raise SystemExit(
            f"FAIL missing maps/{map_id}_{suffix}.png or .svg"
        )
    print(f"OK maps/{map_id}_{suffix}")


def sync_maps() -> None:
    catalog_path = MAPS_OUT / "catalog.json"
    require_file(catalog_path, "maps/catalog.json")
    catalog = load_json(catalog_path)
    print("OK maps/catalog.json")

    eft_meta_path = MAPS_OUT / "eftarkov.meta.json"
    require_file(eft_meta_path, "maps/eftarkov.meta.json")
    print("OK maps/eftarkov.meta.json")

    order: list[str] = catalog.get("order") or []
    if not order:
        raise SystemExit("FAIL maps/catalog.json: empty order")

    for map_id in order:
        check_map_bundle(map_id, SUFFIX_A)
        if (MAPS_OUT / f"{map_id}_{SUFFIX_B}.json").is_file():
            check_map_bundle(map_id, SUFFIX_B)
        if (MAPS_OUT / f"{map_id}_{SUFFIX_COM}.json").is_file():
            check_map_bundle(map_id, SUFFIX_COM)


def sync_icons() -> None:
    for name in ("icon.ico", "icon.png"):
        require_file(ICONS_OUT / name, f"icons/{name}")
        print(f"OK icons/{name}")


def sync_point_icons() -> None:
    for name in POINT_ICON_NAMES:
        require_file(POINTS_OUT / f"{name}.png", f"points/{name}.png")
        print(f"OK points/{name}.png")


def main() -> None:
    sync_icons()
    sync_point_icons()
    sync_maps()
    print("OK root assets layout")


if __name__ == "__main__":
    main()

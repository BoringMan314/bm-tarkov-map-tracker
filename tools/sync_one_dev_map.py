#!/usr/bin/env python3
"""Sync one DEV map asset. Usage: python tools/sync_one_dev_map.py reserve"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import download_tarkov_dev_maps as dl  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: sync_one_dev_map.py <map_id>")
    map_id = sys.argv[1]
    maps_data = json.loads(dl.fetch(dl.MAPS_JSON_URL).decode("utf-8"))
    meta_by_id = dl.collect_meta(maps_data)
    bounds = meta_by_id.get(map_id)
    if not bounds:
        raise SystemExit(f"no bounds for {map_id}")

    for entry in maps_data:
        if dl.catalog_id(entry.get("normalizedName", "")) != map_id:
            continue
        for variant in entry.get("maps") or []:
            if variant.get("projection") != "interactive":
                continue
            svg_path = variant.get("svgPath")
            if not svg_path:
                continue
            data = dl.fetch(svg_path)
            layer = variant.get("svgLayer")
            if layer:
                data = dl.extract_svg_layer(data, layer)
                print(f"svgLayer={layer}")
            w, h, _ = dl.parse_viewbox(data)
            dl.write_map_folder(map_id, dl.meta_entry(map_id, bounds, w, h), data, ".svg")
            print(f"OK {map_id} ({len(data)} bytes, {w}x{h})")
            return
    raise SystemExit(f"no interactive svg for {map_id}")


if __name__ == "__main__":
    main()

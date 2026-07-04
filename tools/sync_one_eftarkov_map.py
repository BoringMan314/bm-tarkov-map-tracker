#!/usr/bin/env python3
"""Re-sync one COM map (--force). Usage: sync_one_eftarkov_map.py lighthouse"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from sync_maps_from_eftarkov import CATALOG, OUT, sync_one, write_catalog  # noqa: E402

def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: sync_one_eftarkov_map.py <map_id>")
    map_id = sys.argv[1]
    slug = dict(CATALOG).get(map_id)
    if not slug:
        raise SystemExit(f"unknown map_id {map_id!r}")
    ok_ids = []
    for mid, _ in CATALOG:
        if (OUT / mid / "map.png").is_file():
            ok_ids.append(mid)
    if sync_one(map_id, slug, OUT):
        if map_id not in ok_ids:
            ok_ids.append(map_id)
        write_catalog(OUT, ok_ids)

if __name__ == "__main__":
    main()

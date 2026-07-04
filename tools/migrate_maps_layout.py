#!/usr/bin/env python3
"""One-time / maintenance: layout internal/maps_tarkov.dev/<id>/{meta.json,map.svg|map.png}."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
MAPS = ROOT / "internal" / "maps_tarkov.dev"
CATALOG_ORDER = [
    "factory",
    "groundzero",
    "interchange",
    "lighthouse",
    "labs",
    "terminal",
    "customs",
    "shoreline",
    "labyrinth",
    "reserve",
    "woods",
    "streets",
]


def stitch_tiles(map_id: str, tile_cfg: dict) -> tuple[bytes, float, float]:
    if Image is None:
        raise SystemExit("PIL required: pip install Pillow")
    z = str(tile_cfg["zoom"])
    ts = tile_cfg["tileSize"]
    w, h = int(tile_cfg["width"]), int(tile_cfg["height"])
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    root = MAPS / "tiles" / map_id / z
    for path in sorted(root.rglob("*.png")):
        x = int(path.parent.name)
        y = int(path.stem)
        tile = Image.open(path)
        canvas.paste(tile, ((x - tile_cfg["minX"]) * ts, (y - tile_cfg["minY"]) * ts))
    from io import BytesIO

    buf = BytesIO()
    canvas.save(buf, format="PNG", optimize=True)
    return buf.getvalue(), float(w), float(h)


def main() -> None:
    bounds = json.loads((MAPS / "bounds.json").read_text(encoding="utf-8"))
    viewboxes = json.loads((MAPS / "viewboxes.json").read_text(encoding="utf-8"))
    tilemaps_path = MAPS / "tilemaps.json"
    tilemaps = (
        json.loads(tilemaps_path.read_text(encoding="utf-8")) if tilemaps_path.is_file() else {}
    )

    bundled_dir = MAPS / "bundled"

    for map_id in CATALOG_ORDER:
        if map_id not in bounds:
            print(f"SKIP {map_id}: no bounds")
            continue
        meta = dict(bounds[map_id])
        w, h = viewboxes.get(map_id, [0, 0])
        meta["width"] = w
        meta["height"] = h

        out_dir = MAPS / map_id
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "meta.json").write_text(
            json.dumps(meta, indent=4, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        if map_id in tilemaps:
            png, pw, ph = stitch_tiles(map_id, tilemaps[map_id])
            meta["width"] = pw
            meta["height"] = ph
            (out_dir / "meta.json").write_text(
                json.dumps(meta, indent=4, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            (out_dir / "map.png").write_bytes(png)
            print(f"OK {map_id}/map.png ({pw:.0f}x{ph:.0f}, {len(png)/1024/1024:.1f} MB)")
            continue

        src = bundled_dir / f"{map_id}.svg"
        if not src.is_file():
            existing = out_dir / "map.svg"
            if existing.is_file():
                print(f"OK {map_id}/map.svg (existing)")
                continue
            raise SystemExit(f"FAIL {map_id}: missing {src}")
        shutil.copy2(src, out_dir / "map.svg")
        print(f"OK {map_id}/map.svg")

    catalog = {"order": CATALOG_ORDER, "default": "woods"}
    (MAPS / "catalog.json").write_text(
        json.dumps(catalog, indent=4, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    for stale_file in ("bounds.json", "viewboxes.json", "tilemaps.json"):
        p = MAPS / stale_file
        if p.is_file():
            p.unlink()

    bundled = MAPS / "bundled"
    if bundled.is_dir():
        shutil.rmtree(bundled)
    tiles = MAPS / "tiles"
    if tiles.is_dir():
        shutil.rmtree(tiles)

    print("OK migrated maps layout")


if __name__ == "__main__":
    main()

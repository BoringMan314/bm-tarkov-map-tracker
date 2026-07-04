#!/usr/bin/env python3
"""Verify all COM (eftarkov.com) embedded maps."""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("PIL required: pip install Pillow")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "internal" / "maps_eftarkov.com"
CATALOG = json.loads((OUT / "catalog.json").read_text(encoding="utf-8"))
ORDER = CATALOG.get("order") or []

EXPECTED = [
    "factory",
    "groundzero",
    "interchange",
    "lighthouse",
    "labs",
    "customs",
    "shoreline",
    "reserve",
    "woods",
    "streets",
]

Image.MAX_IMAGE_PIXELS = None

issues: list[str] = []
rows: list[dict] = []


def check_map(map_id: str) -> None:
    png_path = OUT / map_id / "map.png"
    meta_path = OUT / map_id / "meta.json"
    row = {"id": map_id, "ok": True}

    if not meta_path.is_file():
        issues.append(f"{map_id}: missing meta.json")
        row["ok"] = False
        rows.append(row)
        return

    if not png_path.is_file():
        issues.append(f"{map_id}: missing map.png")
        row["ok"] = False
        rows.append(row)
        return

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    im = Image.open(png_path)
    pw, ph = im.size
    mw = int(meta.get("width") or 0)
    mh = int(meta.get("height") or 0)
    cols = int(meta.get("eftarkov_cols") or 0)
    rows_n = int(meta.get("eftarkov_rows") or 0)
    tile = int(meta.get("eftarkov_tile_size") or 256)
    exp_w, exp_h = cols * tile, rows_n * tile

    size_mb = png_path.stat().st_size / (1024 * 1024)
    pixels = pw * ph
    opaque = sum(1 for px in im.getdata() if px[3] > 10)
    opaque_pct = 100.0 * opaque / pixels if pixels else 0.0

    row.update(
        {
            "png": f"{pw}x{ph}",
            "meta": f"{mw}x{mh}",
            "grid": f"{cols}x{rows_n}@{tile}",
            "expected": f"{exp_w}x{exp_h}",
            "mb": round(size_mb, 2),
            "opaque": round(opaque_pct, 1),
        }
    )

    if pw > exp_w:
        issues.append(f"{map_id}: png width {pw} > grid width {exp_w}")
        row["ok"] = False
    if ph > exp_h:
        issues.append(f"{map_id}: png height {ph} > grid height {exp_h}")
        row["ok"] = False
    if (mw, mh) != (pw, ph):
        issues.append(f"{map_id}: meta {mw}x{mh} != png {pw}x{ph}")
        row["ok"] = False
    if opaque_pct < 5.0:
        issues.append(f"{map_id}: too transparent ({opaque_pct:.1f}% opaque)")
        row["ok"] = False
    if size_mb < 0.5:
        issues.append(f"{map_id}: suspiciously small ({size_mb:.2f} MB)")
        row["ok"] = False

    rows.append(row)


def check_points_meta() -> None:
    points_path = ROOT / "internal" / "points" / "eftarkov" / "meta.json"
    if not points_path.is_file():
        issues.append("points/eftarkov/meta.json missing")
        return
    points = json.loads(points_path.read_text(encoding="utf-8"))
    for map_id in EXPECTED:
        meta_path = OUT / map_id / "meta.json"
        if not meta_path.is_file():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        pt = points.get(map_id)
        if not pt:
            issues.append(f"{map_id}: missing in points/eftarkov/meta.json")
            continue
        if (
            meta.get("eftarkov_cols") != pt.get("cols")
            or meta.get("eftarkov_rows") != pt.get("rows")
            or meta.get("eftarkov_tile_size") != pt.get("tile_size")
        ):
            issues.append(
                f"{map_id}: grid mismatch map={meta.get('eftarkov_cols')}x{meta.get('eftarkov_rows')}"
                f" points={pt.get('cols')}x{pt.get('rows')}"
            )


def main() -> None:
    print("=== catalog ===")
    print("order:", ", ".join(ORDER))
    missing_catalog = [m for m in EXPECTED if m not in ORDER]
    extra_catalog = [m for m in ORDER if m not in EXPECTED]
    if missing_catalog:
        issues.append(f"catalog missing: {', '.join(missing_catalog)}")
    if extra_catalog:
        issues.append(f"catalog unexpected: {', '.join(extra_catalog)}")
    if CATALOG.get("default") != "factory":
        issues.append(f"catalog default should be factory, got {CATALOG.get('default')}")

    print("\n=== maps ===")
    for map_id in EXPECTED:
        check_map(map_id)

    print("\n=== points meta alignment ===")
    check_points_meta()
    if not any("grid mismatch" in i or "points/eftarkov" in i for i in issues):
        print("all map grids match points/eftarkov/meta.json")

    print("\n=== map files ===")
    hdr = f"{'map':<12} {'png':<14} {'meta':<14} {'grid':<12} {'MB':>6} {'opaque':>7}  status"
    print(hdr)
    print("-" * len(hdr))
    for row in rows:
        status = "OK" if row.get("ok") else "FAIL"
        print(
            f"{row['id']:<12} {row.get('png','?'):<14} {row.get('meta','?'):<14} "
            f"{row.get('grid','?'):<12} {row.get('mb',0):>6} {row.get('opaque',0):>6}%  {status}"
        )

    print(f"\n=== summary: {sum(1 for r in rows if r.get('ok'))}/{len(EXPECTED)} OK ===")
    if issues:
        print("\nissues:")
        for item in issues:
            print(f"  - {item}")
        sys.exit(1)
    print("all COM maps verified")


if __name__ == "__main__":
    main()

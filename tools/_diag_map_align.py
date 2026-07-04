#!/usr/bin/env python3
"""Diagnose map vs marker alignment: linear bounds vs tarkov.dev Leaflet CRS."""
from __future__ import annotations

import json
import math
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUNDLED = ROOT / "internal" / "maps"
BOUNDS = {
    mid: json.loads((BUNDLED / mid / "meta.json").read_text(encoding="utf-8"))
    for mid in [
        "factory", "groundzero", "interchange", "lighthouse", "labs", "terminal",
        "customs", "shoreline", "labyrinth", "reserve", "woods", "streets",
    ]
    if (BUNDLED / mid / "meta.json").is_file()
}
VIEWBOXES = {mid: [m["width"], m["height"]] for mid, m in BOUNDS.items() if m.get("width")}
PMC = json.loads((ROOT / "internal/points/exfil/pmc.json").read_text(encoding="utf-8"))

MAPS_JSON_URL = "https://raw.githubusercontent.com/the-hideout/tarkov-dev/main/src/data/maps.json"


def apply_rotation_lat_lng(lat: float, lng: float, rotation: int) -> tuple[float, float]:
    if not rotation:
        return lat, lng
    rad = math.radians(rotation)
    cos, sin = math.cos(rad), math.sin(rad)
    return lng * sin + lat * cos, lng * cos - lat * sin


def game_to_crs_px(
    game_x: float,
    game_z: float,
    transform: list[float],
    rot: int,
    sw_crs: tuple[float, float],
    ne_crs: tuple[float, float],
    iw: float,
    ih: float,
) -> tuple[float, float]:
    scale_x, margin_x = transform[0], transform[1]
    scale_y = transform[2] * -1
    margin_y = transform[3]
    lat, lng = apply_rotation_lat_lng(game_z, game_x, rot)
    cx = scale_x * lng + margin_x
    cy = scale_y * (-lat) + margin_y
    swx, swy = sw_crs
    nex, ney = ne_crs
    px = (cx - swx) / (nex - swx) * iw
    py = (cy - ney) / (swy - ney) * ih
    return px, py


def linear_px(game_x: float, game_z: float, meta: dict, iw: float, ih: float) -> tuple[float, float]:
    xmin, xmax = meta["xmin"], meta["xmax"]
    zmin, zmax = meta["zmin"], meta["zmax"]
    rot = meta.get("coordinates_rotation", 180)
    if rot == 180:
        u = (game_x - xmin) / (xmax - xmin)
        v = (zmax - game_z) / (zmax - zmin)
    elif rot == 90:
        u = (zmax - game_z) / (zmax - zmin)
        v = (game_x - xmin) / (xmax - xmin)
    elif rot == 270:
        u = (game_z - zmin) / (zmax - zmin)
        v = (xmax - game_x) / (xmax - xmin)
    else:
        u = (game_x - xmin) / (xmax - xmin)
        v = (game_z - zmin) / (zmax - zmin)
    return u * iw, v * ih


def viewbox(path: Path) -> str | None:
    head = path.read_text(encoding="utf-8", errors="replace")[:800]
    m = re.search(r'viewBox="([^"]+)"', head)
    return m.group(1) if m else None


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "bm-diag"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def main() -> None:
    maps_data = json.loads(fetch(MAPS_JSON_URL).decode("utf-8"))
    variants: dict[str, dict] = {}
    for entry in maps_data:
        norm = entry.get("normalizedName", "")
        mid = norm.replace("-", "").replace("streetsoftarkov", "streets")
        if mid == "groundzero":
            mid = "groundzero"
        for v in entry.get("maps") or []:
            if v.get("projection") == "interactive":
                variants[mid] = v
                if norm in ("woods", "customs", "reserve", "shoreline"):
                    break

    print("=== SVG asset check ===")
    for mid in ("woods", "shoreline", "reserve", "customs"):
        local = BUNDLED / f"{mid}.svg"
        if not local.is_file():
            continue
        vb_local = viewbox(local)
        vb_cat = VIEWBOXES.get(mid)
        v = variants.get(mid) or variants.get(mid.replace("groundzero", "ground-zero"))
        svg_url = (v or {}).get("svgPath", "")
        remote_vb = None
        remote_len = None
        if svg_url:
            data = fetch(svg_url)
            remote_len = len(data)
            m = re.search(rb'viewBox="([^"]+)"', data[:4000])
            remote_vb = m.group(1).decode() if m else None
        print(f"{mid}:")
        print(f"  local viewBox={vb_local} bytes={local.stat().st_size}")
        print(f"  catalog viewBox={vb_cat}")
        print(f"  remote viewBox={remote_vb} bytes={remote_len}")
        print(f"  match remote viewBox: {vb_local == remote_vb}")

    print("\n=== Marker px: linear vs Leaflet CRS (first 3 PMC per map) ===")
    for mid in ("woods", "reserve", "customs"):
        meta = BOUNDS.get(mid)
        v = variants.get(mid)
        if not meta or not v:
            continue
        transform = v.get("transform")
        rot = v.get("coordinateRotation", 180)
        iw, ih = VIEWBOXES[mid]
        xmin, xmax, zmin, zmax = meta["xmin"], meta["xmax"], meta["zmin"], meta["zmax"]
        if not transform:
            print(f"{mid}: no transform")
            continue

        def to_crs(gx: float, gz: float) -> tuple[float, float]:
            scale_x, margin_x = transform[0], transform[1]
            scale_y = transform[2] * -1
            margin_y = transform[3]
            lat, lng = apply_rotation_lat_lng(gz, gx, rot)
            return scale_x * lng + margin_x, scale_y * (-lat) + margin_y

        sw = to_crs(xmin, zmin)
        ne = to_crs(xmax, zmax)
        pts = (PMC.get(mid) or [])[:3]
        print(f"\n{mid} ({len(pts)} samples) bounds=({xmin},{xmax},{zmin},{zmax})")
        for p in pts:
            x, z = p["coordinates"]
            lx, ly = linear_px(x, z, meta, iw, ih)
            cx, cy = game_to_crs_px(x, z, transform, rot, sw, ne, iw, ih)
            print(f"  {p['name']:16} game=({x:.1f},{z:.1f}) linear=({lx:.0f},{ly:.0f}) crs=({cx:.0f},{cy:.0f}) delta=({cx-lx:.0f},{cy-ly:.0f})")


    print("\n=== Game vs SVG aspect ratio (linear mapping assumes equal) ===")
    for mid in ("woods", "customs", "reserve", "shoreline"):
        meta = BOUNDS.get(mid)
        if not meta:
            continue
        iw, ih = VIEWBOXES[mid]
        span_x = meta["xmax"] - meta["xmin"]
        span_z = meta["zmax"] - meta["zmin"]
        print(
            f"{mid}: game {span_x/span_z:.4f}  svg {iw/ih:.4f}  "
            f"delta {abs(span_x / span_z - iw / ih):.4f}"
        )

    print("\n=== reserve: bounds vs svgBounds (Exit to Woods) ===")
    meta = BOUNDS["reserve"]
    iw, ih = VIEWBOXES["reserve"]
    x, z = 36.5, -221.6
    xmin, xmax = meta["xmin"], meta["xmax"]
    for label, zmin, zmax in [("bounds", meta["zmin"], meta["zmax"]), ("svgBounds", -274, 272)]:
        v = (zmax - z) / (zmax - zmin)
        print(f"  {label}: py={v * ih:.0f}")


if __name__ == "__main__":
    main()

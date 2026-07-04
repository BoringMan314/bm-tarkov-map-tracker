#!/usr/bin/env python3
"""Refresh woods DEV A satellite PNG + meta (z=4, transparent crop + black flatten)."""
from __future__ import annotations

import json
import base64
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
MAPS_DIR = ROOT / "internal" / "maps_tarkov.dev" / "woods"
MAPS_B_DIR = ROOT / "internal" / "maps_tarkov.dev_B" / "woods"
MAPS_JSON_URL = "https://raw.githubusercontent.com/the-hideout/tarkov-dev/main/src/data/maps.json"
MAPS_JSON_API = "https://api.github.com/repos/the-hideout/tarkov-dev/contents/src/data/maps.json"
USER_AGENT = "bm-tarkov-map-tracker/1.0"

TILE_URL = "https://assets.tarkov.dev/maps/woods/main_0.16/{z}/{x}/{y}.png"
TILE_ZOOM = 4
TILE_SIZE = 256
MIN_TILE_BYTES = 4000
SCAN = 24
TRANSPARENT_RGBA = (0, 0, 0, 0)
FLATTEN_RGB = (0, 0, 0)


def flatten_rgba_on_black(image: Image.Image) -> Image.Image:
    if image.mode != "RGBA":
        return image.convert("RGB")
    bg = Image.new("RGB", image.size, FLATTEN_RGB)
    bg.paste(image, mask=image.split()[3])
    return bg


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def fetch_maps_json() -> list:
    try:
        return json.loads(fetch(MAPS_JSON_URL).decode("utf-8"))
    except OSError:
        payload = json.loads(fetch(MAPS_JSON_API).decode("utf-8"))
        return json.loads(base64.b64decode(payload["content"]))


def map_variant(maps_data: list) -> dict:
    for entry in maps_data:
        if entry.get("normalizedName") != "woods":
            continue
        for variant in entry.get("maps") or []:
            if variant.get("key") == "woods" and variant.get("projection") == "interactive":
                return variant
    raise SystemExit("FAIL: woods variant not found")


def bounds_to_meta(bounds: list, rotation: int, transform: list | None) -> dict:
    xmax, zmin = bounds[0]
    xmin, zmax = bounds[1]
    meta = {
        "name": "woods",
        "display_name": "Woods",
        "description": "",
        "xmin": round(float(xmin), 4),
        "xmax": round(float(xmax), 4),
        "zmin": round(float(zmin), 4),
        "zmax": round(float(zmax), 4),
        "coordinates_rotation": int(rotation),
    }
    if transform and len(transform) >= 4:
        meta["transform"] = [float(v) for v in transform[:4]]
    return meta


def filter_main_cluster(coords: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if TILE_ZOOM >= 6:
        cluster = [(x, y) for x, y in coords if x <= 47 and y <= 47]
        if len(cluster) >= 400:
            return cluster
    if TILE_ZOOM == 5:
        cluster = [(x, y) for x, y in coords if x <= 31 and y <= 31]
        if len(cluster) >= 400:
            return cluster
    if TILE_ZOOM == 4:
        cluster = [(x, y) for x, y in coords if x <= 15 and y <= 15]
        if len(cluster) >= 100:
            return cluster
    return coords


def probe_tiles() -> tuple[int, int, int, int]:
    def probe_at(x: int, y: int) -> tuple[int, int] | None:
        try:
            data = fetch(TILE_URL.format(z=TILE_ZOOM, x=x, y=y))
            if len(data) >= MIN_TILE_BYTES:
                return x, y
        except OSError:
            pass
        return None

    coords: list[tuple[int, int]] = []
    jobs = [(x, y) for x in range(SCAN) for y in range(SCAN)]
    with ThreadPoolExecutor(max_workers=16) as pool:
        for hit in pool.map(lambda xy: probe_at(*xy), jobs):
            if hit:
                coords.append(hit)
    if not coords:
        raise SystemExit("FAIL: no woods tiles found")
    coords = filter_main_cluster(coords)
    return (
        min(x for x, _ in coords),
        max(x for x, _ in coords),
        min(y for _, y in coords),
        max(y for _, y in coords),
    )


def download_and_stitch(
    min_x: int, max_x: int, min_y: int, max_y: int
) -> tuple[Image.Image, float, float, int, int]:
    if Image is None:
        raise SystemExit("PIL required: pip install Pillow")

    width = (max_x - min_x + 1) * TILE_SIZE
    height = (max_y - min_y + 1) * TILE_SIZE
    canvas = Image.new("RGBA", (width, height), TRANSPARENT_RGBA)
    jobs = [(x, y) for x in range(min_x, max_x + 1) for y in range(min_y, max_y + 1)]
    pasted = 0

    def fetch_one(xy: tuple[int, int]) -> tuple[int, int, bytes | None]:
        x, y = xy
        try:
            data = fetch(TILE_URL.format(z=TILE_ZOOM, x=x, y=y))
        except OSError:
            return x, y, None
        if len(data) < MIN_TILE_BYTES:
            return x, y, None
        return x, y, data

    with ThreadPoolExecutor(max_workers=16) as pool:
        for x, y, data in pool.map(fetch_one, jobs):
            if not data:
                continue
            tile = Image.open(BytesIO(data)).convert("RGBA")
            if not tile.getbbox():
                continue
            canvas.paste(tile, ((x - min_x) * TILE_SIZE, (y - min_y) * TILE_SIZE), tile)
            pasted += 1

    print(f"OK pasted {pasted}/{len(jobs)} tiles")
    crop = canvas.getbbox()
    if not crop:
        raise SystemExit("FAIL: stitched woods map is empty")
    off_x, off_y, _, _ = crop
    cropped = flatten_rgba_on_black(canvas.crop(crop))
    return cropped, float(width), float(height), int(off_x), int(off_y)


def patch_dev_b_tile_meta(min_x: int, max_x: int, min_y: int, max_y: int) -> None:
    """Optional tile reference for diagnostics; DEV B SVG uses transform corner mapping in app.js."""
    meta_path = MAPS_B_DIR / "meta.json"
    if not meta_path.is_file():
        return
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["tile_zoom"] = TILE_ZOOM
    meta["tile_min_x"] = min_x
    meta["tile_min_y"] = min_y
    meta["tile_max_x"] = max_x
    meta["tile_max_y"] = max_y
    meta["tile_size"] = TILE_SIZE
    meta_path.write_text(json.dumps(meta, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
    print("OK dev_B woods/meta.json tile reference updated")


def main() -> None:
    maps_data = fetch_maps_json()
    variant = map_variant(maps_data)
    min_x, max_x, min_y, max_y = probe_tiles()
    print(f"OK woods z={TILE_ZOOM} bbox=({min_x},{min_y})-({max_x},{max_y})")

    image, stitch_w, stitch_h, off_x, off_y = download_and_stitch(
        min_x, max_x, min_y, max_y
    )
    crop_w, crop_h = image.size
    buf = BytesIO()
    image.save(buf, format="PNG", optimize=True)

    meta = bounds_to_meta(
        variant["bounds"],
        variant.get("coordinateRotation", 180),
        variant.get("transform"),
    )
    meta["width"] = float(crop_w)
    meta["height"] = float(crop_h)
    meta["stitch_width"] = stitch_w
    meta["stitch_height"] = stitch_h
    meta["map_offset_x"] = off_x
    meta["map_offset_y"] = off_y
    meta["tile_zoom"] = TILE_ZOOM
    meta["tile_min_x"] = min_x
    meta["tile_min_y"] = min_y
    meta["tile_max_x"] = max_x
    meta["tile_max_y"] = max_y
    meta["tile_size"] = TILE_SIZE

    MAPS_DIR.mkdir(parents=True, exist_ok=True)
    svg = MAPS_DIR / "map.svg"
    if svg.is_file():
        svg.unlink()
    (MAPS_DIR / "map.png").write_bytes(buf.getvalue())
    (MAPS_DIR / "meta.json").write_text(
        json.dumps(meta, indent=4, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    patch_dev_b_tile_meta(min_x, max_x, min_y, max_y)
    print(f"OK woods/map.png {crop_w}x{crop_h} ({len(buf.getvalue())/1024/1024:.1f} MB)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Download and stitch eftarkov.com map tiles into internal/maps_eftarkov.com/."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://api.eftarkov.com/map"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://api.eftarkov.com/",
}
MIN_TILE_BYTES = 16
FETCH_RETRIES = 3
WORKERS = 24
# Missing grid slots use transparent tiles; real map content is cropped to a tight bbox.
EMPTY_TILE_RGBA = (0, 0, 0, 0)

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
    ("streets", "streets"),
]

OUT = ROOT / "internal" / "maps_eftarkov.com"


def fetch(url: str) -> bytes:
    last_err: Exception | None = None
    for attempt in range(FETCH_RETRIES):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = e
            time.sleep(0.4 * (attempt + 1))
    raise OSError(str(last_err))


def parse_config(html: str) -> dict:
    folders = re.search(r"totalFolders:\s*\[([^\]]+)\]", html)
    per_folder = re.search(r"imagesPerFolder:\s*\[([^\]]+)\]", html)
    paths = re.search(r"basePaths:\s*\[([\s\S]*?)\],", html)
    tile = re.search(r"tileSize:\s*(\d+)", html)
    if not folders or not per_folder or not paths or not tile:
        raise ValueError("config block not found")
    total_folders = [int(x.strip()) for x in folders.group(1).split(",")]
    images_per_folder = [int(x.strip()) for x in per_folder.group(1).split(",")]
    base_paths = re.findall(r"'([^']+)'", paths.group(1))
    if not base_paths:
        base_paths = re.findall(r'"([^"]+)"', paths.group(1))
    return {
        "total_folders": total_folders,
        "images_per_folder": images_per_folder,
        "base_paths": base_paths,
        "tile_size": int(tile.group(1)),
    }


def tile_urls(url_slug: str, base_path: str, col: int, row: int) -> list[str]:
    base_path = base_path.rstrip("/")
    if base_path.startswith("http://") or base_path.startswith("https://"):
        rel = base_path
    else:
        rel = f"{BASE}/{url_slug}/{base_path}"
    return [
        f"{rel}/{col}/{row}.webp",
        f"{rel}/{col}/{row}.png",
    ]


def empty_tile(tile_size: int) -> Image.Image:
    return Image.new("RGBA", (tile_size, tile_size), EMPTY_TILE_RGBA)


def parent_cell(col: int, row: int, child_cols: int, child_rows: int, parent_cols: int, parent_rows: int) -> tuple[int, int]:
    pc = min(parent_cols - 1, col * parent_cols // child_cols)
    pr = min(parent_rows - 1, row * parent_rows // child_rows)
    return pc, pr


def load_tile_from_level(
    url_slug: str, cfg: dict, level: int, col: int, row: int, tile_size: int
) -> tuple[Image.Image, bool]:
    base_path = cfg["base_paths"][level]
    for url in tile_urls(url_slug, base_path, col, row):
        try:
            data = fetch(url)
            if len(data) < MIN_TILE_BYTES:
                continue
            img = Image.open(BytesIO(data)).convert("RGBA")
            if img.size != (tile_size, tile_size):
                img = img.resize((tile_size, tile_size), Image.Resampling.LANCZOS)
            return img, True
        except OSError:
            continue
    return empty_tile(tile_size), False


def load_tile(
    url_slug: str, cfg: dict, level: int, col: int, row: int, tile_size: int
) -> tuple[int, int, Image.Image, bool]:
    """Fetch one grid cell; fall back to coarser zoom, then gray padding."""
    img, ok = load_tile_from_level(url_slug, cfg, level, col, row, tile_size)
    if ok:
        return col, row, img, True

    child_cols = cfg["total_folders"][level]
    child_rows = cfg["images_per_folder"][level]
    for parent_level in range(level - 1, -1, -1):
        pc, pr = parent_cell(col, row, child_cols, child_rows, cfg["total_folders"][parent_level], cfg["images_per_folder"][parent_level])
        parent, parent_ok = load_tile_from_level(url_slug, cfg, parent_level, pc, pr, tile_size)
        if parent_ok:
            return col, row, parent, True

    return col, row, empty_tile(tile_size), False


def download_level_grid(
    url_slug: str, cfg: dict, level: int
) -> tuple[dict[tuple[int, int], Image.Image], set[tuple[int, int]], int, int, int, int, int]:
    cols = cfg["total_folders"][level]
    rows = cfg["images_per_folder"][level]
    tile = cfg["tile_size"]
    coords = [(c, r) for c in range(cols) for r in range(rows)]
    tiles: dict[tuple[int, int], Image.Image] = {}
    fetched_coords: set[tuple[int, int]] = set()
    fetched = 0
    padded = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [
            pool.submit(load_tile, url_slug, cfg, level, c, r, tile) for c, r in coords
        ]
        for fut in as_completed(futures):
            col, row, img, ok = fut.result()
            tiles[(col, row)] = img
            if ok:
                fetched += 1
                fetched_coords.add((col, row))
            else:
                padded += 1
    return tiles, fetched_coords, cols, rows, tile, fetched, padded


def content_bbox(
    fetched_coords: set[tuple[int, int]], cols: int, rows: int
) -> tuple[int, int, int, int]:
    if not fetched_coords:
        return 0, 0, cols - 1, rows - 1
    min_col = min(c for c, _ in fetched_coords)
    max_col = max(c for c, _ in fetched_coords)
    min_row = min(r for _, r in fetched_coords)
    max_row = max(r for _, r in fetched_coords)
    return min_col, min_row, max_col, max_row


def crop_to_content_bbox(
    canvas: Image.Image, min_col: int, min_row: int, max_col: int, max_row: int, tile: int
) -> tuple[Image.Image, int, int]:
    off_x = min_col * tile
    off_y = min_row * tile
    w = (max_col - min_col + 1) * tile
    h = (max_row - min_row + 1) * tile
    cropped = canvas.crop((off_x, off_y, off_x + w, off_y + h))
    cols = max_col - min_col + 1
    rows = max_row - min_row + 1
    return cropped, cols, rows


def _row_mean_luminance(canvas: Image.Image, row: int, tile: int) -> float:
    w = canvas.size[0]
    y0 = row * tile
    band = canvas.crop((0, y0, w, y0 + tile)).convert("RGB")
    px = band.getdata()
    if not px:
        return 255.0
    return sum(r + g + b for r, g, b in px) / (len(px) * 3)


def _row_is_black_fringe(canvas: Image.Image, row: int, tile: int) -> bool:
    """True when a tile row is mostly empty/black padding (not map content)."""
    w = canvas.size[0]
    y0 = row * tile
    band = canvas.crop((0, y0, w, y0 + tile)).convert("RGBA")
    px = band.getdata()
    if not px:
        return False
    dark = content = gray = 0
    for r, g, b, a in px:
        if a < 8:
            dark += 1
            continue
        if abs(r - 198) < 8 and abs(g - 198) < 8 and abs(b - 198) < 8:
            gray += 1
            continue
        if r < 20 and g < 20 and b < 20:
            dark += 1
            continue
        content += 1
    n = len(px)
    sparse = content / n < 0.04 and (dark + gray) / n > 0.35
    dim = _row_mean_luminance(canvas, row, tile) < 75
    return sparse or dim


def extract_legend_data(html: str) -> dict:
    m = re.search(r"const\s+LEGEND_DATA\s*=\s*(\{[\s\S]*?\n\s*\});", html)
    if not m:
        raise ValueError("LEGEND_DATA not found")
    raw = m.group(1)
    raw = re.sub(r"(\s)([A-Za-z_][A-Za-z0-9_]*)(\s*:)", r'\1"\2"\3', raw)
    raw = raw.replace("'", '"')
    raw = re.sub(r",\s*}", "}", raw)
    raw = re.sub(r",\s*]", "]", raw)
    return json.loads(raw)


def min_keep_rows_for_legend(html: str, level: int, coord_rows: int, tile: int) -> int:
    """Do not trim below extract/transit points on the active zoom level."""
    try:
        legend = extract_legend_data(html)
    except (ValueError, json.JSONDecodeError):
        return 1
    eh = coord_rows * tile
    max_sy = 0.0
    found = False
    for cat in legend.values():
        if not isinstance(cat, dict):
            continue
        for item in cat.get("items") or []:
            for pos in item.get("positions") or []:
                if int(pos.get("level", -1)) != level:
                    continue
                sy = eh / 2 + float(pos["mapY"])
                max_sy = max(max_sy, sy)
                found = True
    if not found:
        return 1
    # Keep the tile row containing the lowest point (+ one row margin).
    return min(coord_rows, max(1, int(max_sy // tile) + 2))


def trim_stitched_canvas(
    canvas: Image.Image, tile: int, min_keep_rows: int = 1
) -> tuple[Image.Image, int, int]:
    """Drop trailing tile rows that are mostly black/gray padding (e.g. lighthouse floor inset)."""
    w, h = canvas.size
    rows = h // tile
    keep_rows = rows
    floor_rows = max(1, min(rows, min_keep_rows))
    while keep_rows > floor_rows and _row_is_black_fringe(canvas, keep_rows - 1, tile):
        keep_rows -= 1
    if keep_rows < rows:
        canvas = canvas.crop((0, 0, w, keep_rows * tile))
        print(f"  trimmed {rows - keep_rows} black fringe row(s) -> {keep_rows} rows")
    cols = canvas.size[0] // tile
    rows = canvas.size[1] // tile
    return canvas, cols, rows


def composite_stitch(url_slug: str, cfg: dict, html: str = "") -> tuple[bytes, float, float, int, int, int, int, int]:
    if Image is None:
        raise SystemExit("PIL required: pip install Pillow")

    target = len(cfg["total_folders"]) - 1
    tiles, fetched_coords, cols, rows, tile, fetched, padded = download_level_grid(
        url_slug, cfg, target
    )
    total = cols * rows
    print(
        f"  level {target}: {fetched}/{total} fetched, {padded} padded, "
        f"grid {cols}x{rows} @ {tile}px"
    )
    if fetched == 0:
        raise RuntimeError(f"no tiles for {url_slug} at level {target}")

    canvas = Image.new("RGBA", (cols * tile, rows * tile), (0, 0, 0, 0))
    for col in range(cols):
        for row in range(rows):
            canvas.paste(tiles[(col, row)], (col * tile, row * tile))

    min_col, min_row, max_col, max_row = content_bbox(fetched_coords, cols, rows)
    canvas, vis_cols, vis_rows = crop_to_content_bbox(
        canvas, min_col, min_row, max_col, max_row, tile
    )
    off_x = min_col * tile
    off_y = min_row * tile
    if off_x or off_y:
        print(f"  cropped padding -> offset ({off_x},{off_y}) visible {vis_cols}x{vis_rows} tiles")

    canvas, vis_cols, vis_rows = trim_stitched_canvas(
        canvas,
        tile,
        max(1, min_keep_rows_for_legend(html, target, rows, tile) - min_row),
    )
    w, h = canvas.size
    buf = BytesIO()
    canvas.save(buf, format="PNG", optimize=True)
    print(
        f"  stitched -> {w}x{h} grid {vis_cols}x{vis_rows} "
        f"({total} cells, {fetched} from server, {padded} padded)"
    )
    return buf.getvalue(), float(w), float(h), target, cols, rows, off_x, off_y


def write_catalog(out: Path, ok_ids: list[str]) -> None:
    catalog = {"order": ok_ids, "default": "factory" if "factory" in ok_ids else ok_ids[0]}
    (out / "catalog.json").write_text(
        json.dumps(catalog, indent=4, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"wrote catalog ({len(ok_ids)} maps)", flush=True)


def sync_one(map_id: str, url_slug: str, out: Path) -> bool:
    url = f"{BASE}/{url_slug}/"
    html = fetch(url).decode("utf-8", "replace")
    cfg = parse_config(html)
    print(f"sync {map_id} ({url_slug})", flush=True)
    level = len(cfg["total_folders"]) - 1
    coord_cols = cfg["total_folders"][level]
    coord_rows = cfg["images_per_folder"][level]
    png, w, h, _level, coord_cols, coord_rows, off_x, off_y = composite_stitch(url_slug, cfg, html)
    out_dir = out / map_id
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "name": map_id,
        "display_name": map_id.replace("-", " ").title(),
        "description": "",
        "width": w,
        "height": h,
        "coordinates_rotation": 0,
        "eftarkov_level": level,
        "eftarkov_cols": coord_cols,
        "eftarkov_rows": coord_rows,
        "eftarkov_tile_size": cfg["tile_size"],
        "map_offset_x": off_x,
        "map_offset_y": off_y,
        "map_asset_rev": hashlib.sha256(png).hexdigest()[:16],
    }
    (out_dir / "meta.json").write_text(
        json.dumps(meta, indent=4, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (out_dir / "map.png").write_bytes(png)
    print(f"OK {map_id}/map.png ({w:.0f}x{h:.0f}, {len(png)/1024/1024:.1f} MB)", flush=True)
    return True


def main() -> None:
    if Image is None:
        raise SystemExit("PIL required: pip install Pillow")
    Image.MAX_IMAGE_PIXELS = None
    OUT.mkdir(parents=True, exist_ok=True)
    skip_existing = "--force" not in sys.argv
    ok_ids: list[str] = []
    for map_id, slug in CATALOG:
        png_path = OUT / map_id / "map.png"
        if skip_existing and png_path.is_file():
            print(f"skip {map_id} (exists)", flush=True)
            ok_ids.append(map_id)
            write_catalog(OUT, ok_ids)
            continue
        try:
            if sync_one(map_id, slug, OUT):
                ok_ids.append(map_id)
                write_catalog(OUT, ok_ids)
        except Exception as e:
            print(f"FAIL {map_id}: {e}", flush=True)
    write_catalog(OUT, ok_ids)


if __name__ == "__main__":
    main()

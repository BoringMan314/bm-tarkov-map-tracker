#!/usr/bin/env python3
"""Refresh factory DEV A satellite PNG + meta from tarkov.dev tiles (z=4 + z=5 basement).

Ground floor uses z=4 tiles; the underground inset uses z=5 tiles (z=4 basement
tiles are too sparse). Transparent crop + black flatten; map_offset_* for points.

Tunnel composite (satellite only, DEV A):
  1. Bottom: satellite with tunnel (z4 + z5 basement)
  2. Top: satellite without tunnel (z4 only; basement transparent)
  3. Alpha-composite top over bottom → single map.png
"""

from __future__ import annotations

import hashlib
import json
import base64
import os
import subprocess
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
MAPS_DIR_A = ROOT / "internal" / "maps_tarkov.dev" / "factory"
MAPS_DIR_B = ROOT / "internal" / "maps_tarkov.dev_B" / "factory"
SVG_URL = "https://assets.tarkov.dev/maps/svg/Factory.svg"
# DEV A: satellite PNG + Second_Floor schematic overlay.
OVERLAY_LAYERS_A = ["Second_Floor"]
# DEV B: abstract schematic with ground + 2F (tunnel PNG composite still uses basement separately).
SCHEMATIC_LAYERS_B = ["Ground_Floor", "Second_Floor"]
TUNNEL_LAYER = "Basement"
TUNNEL_BASE_OPACITY = 0.5
DEV_B_RENDER_SCALE = 30

import sys

sys.path.insert(0, str(ROOT / "tools"))
from download_tarkov_dev_maps import (  # noqa: E402
    extract_svg_layers,
    fetch as fetch_bytes,
    meta_entry,
    normalize_svg_bytes,
    parse_viewbox,
    probe_tile_meta,
)
MAPS_JSON_URL = "https://raw.githubusercontent.com/the-hideout/tarkov-dev/main/src/data/maps.json"
MAPS_JSON_API = "https://api.github.com/repos/the-hideout/tarkov-dev/contents/src/data/maps.json"
USER_AGENT = "bm-tarkov-map-tracker/1.0"

TILE_URL = "https://assets.tarkov.dev/maps/factory/main/{z}/{x}/{y}.png"
TILE_ZOOM = 4
BASEMENT_ZOOM = 5
BASEMENT_Z4_ROW_MIN = 12
BASEMENT_ROW_MIN = 22
BASEMENT_ROW_MAX = 30
BASEMENT_COL_MAX = 22
TILE_SIZE = 256
MIN_TILE_BYTES = 4000
SCAN = 16
# Transparent canvas so getbbox() trims empty margins; flatten to black before save.
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


def factory_variant(maps_data: list) -> dict:
    for entry in maps_data:
        if entry.get("normalizedName") != "factory":
            continue
        for variant in entry.get("maps") or []:
            if variant.get("key") == "factory" and variant.get("projection") == "interactive":
                return variant
    raise SystemExit("FAIL: factory interactive variant not found in maps.json")


def bounds_to_meta(bounds: list, rotation: int, transform: list | None) -> dict:
    xmax, zmin = bounds[0]
    xmin, zmax = bounds[1]
    meta = {
        "name": "factory",
        "display_name": "Factory",
        "description": "",
        "xmin": round(float(xmin), 4),
        "xmax": round(float(xmax), 4),
        "zmin": round(float(zmin), 4),
        "zmax": round(float(zmax), 4),
        "coordinates_rotation": int(rotation),
    }
    if transform and len(transform) >= 4:
        meta["transform"] = [
            float(transform[0]),
            float(transform[1]),
            float(transform[2]),
            float(transform[3]),
        ]
    return meta


def probe_tiles() -> tuple[list[tuple[int, int]], int, int, int, int]:
    def probe_at(x: int, y: int) -> tuple[int, int] | None:
        url = TILE_URL.format(z=TILE_ZOOM, x=x, y=y)
        try:
            data = fetch(url)
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
        raise SystemExit("FAIL: no factory satellite tiles found")
    min_x = min(x for x, _ in coords)
    max_x = max(x for x, _ in coords)
    min_y = min(y for _, y in coords)
    max_y = max(y for _, y in coords)
    return coords, min_x, max_x, min_y, max_y


def fetch_tile(z: int, x: int, y: int) -> Image.Image | None:
    try:
        data = fetch(TILE_URL.format(z=z, x=x, y=y))
    except OSError:
        return None
    if len(data) < MIN_TILE_BYTES:
        return None
    tile = Image.open(BytesIO(data)).convert("RGBA")
    if not tile.getbbox():
        return None
    return tile


def paste_z5_on_z4(canvas: Image.Image, x5: int, y5: int, tile: Image.Image) -> None:
    """Paste a z=5 tile onto the z=4 stitch canvas (128px cell)."""
    child = tile.resize((128, 128), Image.Resampling.LANCZOS)
    px = (x5 // 2) * TILE_SIZE + (x5 % 2) * 128
    py = (y5 // 2) * TILE_SIZE + (y5 % 2) * 128
    canvas.paste(child, (px, py), child)


def overlay_basement_tiles(canvas: Image.Image) -> int:
    """Fill sparse factory basement using higher-res z=5 tiles."""
    jobs = [
        (x, y)
        for y in range(BASEMENT_ROW_MIN, BASEMENT_ROW_MAX + 1)
        for x in range(BASEMENT_COL_MAX + 1)
    ]
    pasted = 0

    def fetch_one(xy: tuple[int, int]) -> tuple[int, int, Image.Image | None]:
        x, y = xy
        return x, y, fetch_tile(BASEMENT_ZOOM, x, y)

    with ThreadPoolExecutor(max_workers=16) as pool:
        for x, y, tile in pool.map(fetch_one, jobs):
            if tile is None:
                continue
            paste_z5_on_z4(canvas, x, y, tile)
            pasted += 1
    return pasted


def stitch_satellite_canvas(
    min_x: int, max_x: int, min_y: int, max_y: int, *, include_basement: bool
) -> Image.Image:
    if Image is None:
        raise SystemExit("PIL required: pip install Pillow")

    width = (max_x - min_x + 1) * TILE_SIZE
    height = (max_y - min_y + 1) * TILE_SIZE
    canvas = Image.new("RGBA", (width, height), TRANSPARENT_RGBA)
    jobs = [(x, y) for x in range(min_x, max_x + 1) for y in range(min_y, max_y + 1)]

    def fetch_one(xy: tuple[int, int]) -> tuple[int, int, Image.Image | None]:
        x, y = xy
        return x, y, fetch_tile(TILE_ZOOM, x, y)

    pasted = 0
    with ThreadPoolExecutor(max_workers=16) as pool:
        for x, y, tile in pool.map(fetch_one, jobs):
            if tile is None:
                continue
            if y >= BASEMENT_Z4_ROW_MIN:
                continue
            canvas.paste(tile, ((x - min_x) * TILE_SIZE, (y - min_y) * TILE_SIZE), tile)
            pasted += 1

    label = "with basement" if include_basement else "ground only"
    print(f"OK pasted {pasted}/{len(jobs)} z={TILE_ZOOM} tiles ({label})")
    if include_basement:
        basement = overlay_basement_tiles(canvas)
        print(f"OK overlaid {basement} z={BASEMENT_ZOOM} basement tiles")
    return canvas


def crop_satellite_pair(
    canvas_with: Image.Image, canvas_without: Image.Image
) -> tuple[Image.Image, Image.Image, int, int, int, int]:
    crop = canvas_with.getbbox()
    if not crop:
        raise SystemExit("FAIL: stitched factory map is empty")
    off_x, off_y, _, _ = crop
    with_img = canvas_with.crop(crop).convert("RGBA")
    without_img = canvas_without.crop(crop).convert("RGBA")
    return with_img, without_img, off_x, off_y, crop[2] - crop[0], crop[3] - crop[1]


def render_svg_rgba(svg_data: bytes, width: int, height: int) -> Image.Image:
    try:
        import cairosvg

        png = cairosvg.svg2png(bytestring=svg_data, output_width=width, output_height=height)
        return Image.open(BytesIO(png)).convert("RGBA")
    except (ImportError, OSError):
        pass

    node_modules = ROOT / "node_modules" / "@resvg" / "resvg-js"
    render_js = ROOT / "tools" / "render_svg_to_png.js"
    if not node_modules.is_dir() or not render_js.is_file():
        raise SystemExit(
            "FAIL: SVG rasterize requires cairosvg+cairo or node @resvg/resvg-js\n"
            "  pip install cairosvg   OR   npm install (repo root)"
        )

    svg_tmp = tempfile.NamedTemporaryFile(suffix=".svg", delete=False)
    try:
        svg_tmp.write(svg_data)
        svg_tmp.close()
        proc = subprocess.run(
            ["node", str(render_js), str(width), svg_tmp.name],
            cwd=str(ROOT),
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            err = proc.stderr.decode("utf-8", "replace").strip()
            raise SystemExit(f"FAIL: render_svg_to_png.js: {err or proc.returncode}")
        im = Image.open(BytesIO(proc.stdout)).convert("RGBA")
        if im.size != (width, height):
            im = im.resize((width, height), Image.Resampling.LANCZOS)
        return im
    finally:
        os.unlink(svg_tmp.name)


def set_layer_opacity(svg_data: bytes, layer_id: str, opacity: float) -> bytes:
    root = ET.fromstring(svg_data)
    for el in root.iter():
        if el.tag.rsplit("}", 1)[-1] == "g" and el.get("id") == layer_id:
            el.set("opacity", str(opacity))
    return normalize_svg_bytes(ET.tostring(root, encoding="utf-8", xml_declaration=False))


def stack_raster_and_svg(raster: Image.Image, svg_layer: Image.Image) -> Image.Image:
    base = raster.convert("RGBA")
    return Image.alpha_composite(base, svg_layer)


def composite_satellite_tunnel(base_with_tunnel: Image.Image, top_no_tunnel: Image.Image) -> Image.Image:
    """DEV A: satellite with tunnel (bottom), satellite without tunnel (top)."""
    base = base_with_tunnel.convert("RGBA")
    top = top_no_tunnel.convert("RGBA")
    if base.size != top.size:
        raise SystemExit(f"FAIL: tunnel composite size mismatch {base.size} vs {top.size}")
    merged = Image.alpha_composite(base, top)
    return flatten_rgba_on_black(merged)


def composite_tunnel_maps(checked: Image.Image, unchecked: Image.Image) -> Image.Image:
    """DEV B schematic: unchecked over checked, base @ 50% opacity."""
    base = checked.convert("RGBA")
    top = unchecked.convert("RGBA")
    if base.size != top.size:
        raise SystemExit(f"FAIL: tunnel composite size mismatch {base.size} vs {top.size}")
    _, _, _, alpha = base.split()
    alpha = alpha.point(lambda v: int(v * TUNNEL_BASE_OPACITY))
    base = Image.merge("RGBA", (*base.split()[:3], alpha))
    merged = Image.alpha_composite(base, top)
    return flatten_rgba_on_black(merged)


def build_dev_a_satellite_composite(sat_with: Image.Image, sat_without: Image.Image) -> Image.Image:
    return composite_satellite_tunnel(sat_with, sat_without)


def build_dev_b_composite(svg_source: bytes, svg_w: float, svg_h: float) -> Image.Image:
    width = max(1, int(round(svg_w * DEV_B_RENDER_SCALE)))
    height = max(1, int(round(svg_h * DEV_B_RENDER_SCALE)))

    def frame(show_tunnel: bool) -> Image.Image:
        if show_tunnel:
            layers = extract_svg_layers(svg_source, ["Basement", "Ground_Floor"])
            layers = set_layer_opacity(layers, TUNNEL_LAYER, TUNNEL_BASE_OPACITY)
        else:
            layers = extract_svg_layers(svg_source, ["Ground_Floor"])
        return render_svg_rgba(layers, width, height)

    checked = frame(show_tunnel=True)
    unchecked = frame(show_tunnel=False)
    return composite_tunnel_maps(checked, unchecked)


def download_and_stitch(
    min_x: int, max_x: int, min_y: int, max_y: int
) -> tuple[Image.Image, float, float, int, int]:
    canvas_with = stitch_satellite_canvas(min_x, max_x, min_y, max_y, include_basement=True)
    canvas_without = stitch_satellite_canvas(min_x, max_x, min_y, max_y, include_basement=False)
    sat_with, sat_without, off_x, off_y, _, _ = crop_satellite_pair(canvas_with, canvas_without)
    stitch_w = float((max_x - min_x + 1) * TILE_SIZE)
    stitch_h = float((max_y - min_y + 1) * TILE_SIZE)
    composite = build_dev_a_satellite_composite(sat_with, sat_without)
    print(f"OK DEV A satellite tunnel composite {composite.size[0]}x{composite.size[1]}")
    return composite, stitch_w, stitch_h, off_x, off_y


def fetch_overlay_svg(layer_ids: list[str]) -> bytes:
    data = fetch_bytes(SVG_URL)
    data = extract_svg_layers(data, layer_ids)
    return normalize_svg_bytes(data)


def fetch_schematic_svg(layer_ids: list[str]) -> bytes:
    data = fetch_bytes(SVG_URL)
    data = extract_svg_layers(data, layer_ids)
    return normalize_svg_bytes(data)


def write_satellite_variant(
    out_dir: Path,
    meta: dict,
    png: bytes,
    label: str,
    overlay: bytes | None = None,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in ("map.svg", "map-overlay.svg"):
        p = out_dir / name
        if p.is_file():
            p.unlink()
            print(f"removed {label}/{name}")
    (out_dir / "map.png").write_bytes(png)
    if overlay:
        (out_dir / "map-overlay.svg").write_bytes(overlay)
    (out_dir / "meta.json").write_text(
        json.dumps(meta, indent=4, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    extra = f", overlay {len(overlay)} bytes" if overlay else ", no overlay"
    print(f"OK {label}/map.png ({len(png)/1024/1024:.1f} MB{extra})")


def write_schematic_variant(
    out_dir: Path,
    meta: dict,
    svg: bytes,
    label: str,
    png: bytes | None = None,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    if png is None:
        for name in ("map.png", "map-overlay.svg"):
            p = out_dir / name
            if p.is_file():
                p.unlink()
                print(f"removed {label}/{name}")
    else:
        p = out_dir / "map-overlay.svg"
        if p.is_file():
            p.unlink()
            print(f"removed {label}/map-overlay.svg")
    (out_dir / "map.svg").write_bytes(svg)
    if png is not None:
        (out_dir / "map.png").write_bytes(png)
    (out_dir / "meta.json").write_text(
        json.dumps(meta, indent=4, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if png is not None:
        print(f"OK {label}/map.svg + map.png ({len(svg)} + {len(png)/1024/1024:.1f} MB)")
    else:
        print(f"OK {label}/map.svg ({len(svg)} bytes)")


def main() -> None:
    dev_a_only = "--dev-a-only" in sys.argv
    maps_data = fetch_maps_json()
    variant = factory_variant(maps_data)
    coords, min_x, max_x, min_y, max_y = probe_tiles()
    print(
        f"OK factory satellite z={TILE_ZOOM} seeds={len(coords)} "
        f"bbox=({min_x},{min_y})-({max_x},{max_y})"
    )

    image, stitch_w, stitch_h, off_x, off_y = download_and_stitch(
        min_x, max_x, min_y, max_y
    )
    crop_w, crop_h = image.size
    print(f"OK crop offset=({off_x},{off_y}) size={crop_w}x{crop_h} from {stitch_w}x{stitch_h}")

    buf = BytesIO()
    image.save(buf, format="PNG", optimize=True)
    png = buf.getvalue()

    bounds = bounds_to_meta(
        variant["bounds"],
        variant.get("coordinateRotation", 90),
        variant.get("transform"),
    )
    bounds["name"] = "factory"
    bounds["display_name"] = "Factory"
    bounds["description"] = ""

    meta_a = dict(bounds)
    meta_a["width"] = float(crop_w)
    meta_a["height"] = float(crop_h)
    meta_a["stitch_width"] = stitch_w
    meta_a["stitch_height"] = stitch_h
    meta_a["map_offset_x"] = off_x
    meta_a["map_offset_y"] = off_y
    meta_a["tile_zoom"] = TILE_ZOOM
    meta_a["tile_min_x"] = min_x
    meta_a["tile_min_y"] = min_y
    meta_a["tile_max_x"] = max_x
    meta_a["tile_max_y"] = max_y
    meta_a["tile_size"] = TILE_SIZE
    meta_a["map_asset_rev"] = hashlib.sha256(png).hexdigest()[:16]

    overlay_a = fetch_overlay_svg(OVERLAY_LAYERS_A)
    write_satellite_variant(MAPS_DIR_A, meta_a, png, "DEV A factory", overlay=None)
    if dev_a_only:
        print("skip DEV B factory (--dev-a-only)")
    else:
        schematic_b = fetch_schematic_svg(SCHEMATIC_LAYERS_B)
        svg_w, svg_h, _ = parse_viewbox(schematic_b)
        tile_cfg = probe_tile_meta(maps_data, "factory")
        meta_b = meta_entry("factory", bounds, svg_w, svg_h, tile_cfg=tile_cfg)
        write_schematic_variant(MAPS_DIR_B, meta_b, schematic_b, "DEV B factory", png=None)
        print(f"OK factory A png {crop_w}x{crop_h}, B svg {svg_w}x{svg_h}")
        return
    print(f"OK factory A png {crop_w}x{crop_h}")


if __name__ == "__main__":
    main()

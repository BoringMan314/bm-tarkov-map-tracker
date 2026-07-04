#!/usr/bin/env python3
"""Refresh interchange: DEV A satellite only; DEV B abstract + 2F schematic."""

from __future__ import annotations

import hashlib
import json
import base64
import math
import os
import re
import subprocess
import sys
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
MAPS_DIR_A = ROOT / "internal" / "maps_tarkov.dev" / "interchange"
MAPS_DIR_B = ROOT / "internal" / "maps_tarkov.dev_B" / "interchange"
MAPS_JSON_URL = "https://raw.githubusercontent.com/the-hideout/tarkov-dev/main/src/data/maps.json"
MAPS_JSON_API = "https://api.github.com/repos/the-hideout/tarkov-dev/contents/src/data/maps.json"
SVG_URL = "https://assets.tarkov.dev/maps/svg/Interchange.svg"
# tarkov.dev maps.json: "2nd Floor" -> First_Floor; "3rd Floor" -> Second_Floor
OVERLAY_LAYERS_A = ["First_Floor"]
SCHEMATIC_LAYERS_B = ["Ground_Level", "First_Floor"]
SATELLITE_OVERLAY_OPACITY = 1.0
# Solid building shell reads as abstract schematic on satellite; keep floor paths only.
SATELLITE_OVERLAY_HIDE_GROUPS = ("Structure-1", "Pavament-1")
USER_AGENT = "bm-tarkov-map-tracker/1.0"

sys.path.insert(0, str(ROOT / "tools"))
from download_tarkov_dev_maps import (  # noqa: E402
    discover_tiles,
    extract_svg_layers,
    fetch as fetch_bytes,
    meta_entry,
    normalize_svg_bytes,
    parse_viewbox,
    probe_tile_meta,
)

TILE_URL = "https://assets.tarkov.dev/maps/interchange/main/{z}/{x}/{y}.png"
TILE_ZOOM = 4
FILL_ZOOM = 5
FILL_ZOOM_COARSE = 3
TILE_SIZE = 256
TILE_MIN_BYTES = 100
PROBE_MIN_BYTES = 4000
SPARSE_OPAQUE = 45_000
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
        if entry.get("normalizedName") != "interchange":
            continue
        for variant in entry.get("maps") or []:
            if variant.get("key") == "interchange" and variant.get("projection") == "interactive":
                return variant
    raise SystemExit("FAIL: interchange variant not found")


def bounds_to_meta(bounds: list, rotation: int, transform: list | None) -> dict:
    xmax, zmin = bounds[0]
    xmin, zmax = bounds[1]
    meta = {
        "name": "interchange",
        "display_name": "Interchange",
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


def probe_tiles() -> tuple[int, int, int, int]:
    coords = discover_tiles(TILE_URL, TILE_ZOOM, PROBE_MIN_BYTES, seed_scan=16)
    if not coords:
        raise SystemExit(f"FAIL: no interchange tiles at z={TILE_ZOOM}")
    return (
        min(x for x, _ in coords),
        max(x for x, _ in coords),
        min(y for _, y in coords),
        max(y for _, y in coords),
    )


def tile_opaque_count(tile: Image.Image) -> int:
    px = tile.convert("RGBA").load()
    return sum(1 for y in range(tile.height) for x in range(tile.width) if px[x, y][3] > 0)


def fetch_tile(z: int, x: int, y: int) -> Image.Image | None:
    try:
        data = fetch(TILE_URL.format(z=z, x=x, y=y))
    except OSError:
        return None
    if len(data) < TILE_MIN_BYTES:
        return None
    tile = Image.open(BytesIO(data)).convert("RGBA")
    return tile if tile.getbbox() else None


def composite_z4_from_z5(x4: int, y4: int) -> Image.Image:
    out = Image.new("RGBA", (TILE_SIZE, TILE_SIZE), TRANSPARENT_RGBA)
    for dx in (0, 1):
        for dy in (0, 1):
            child_tile = fetch_tile(FILL_ZOOM, x4 * 2 + dx, y4 * 2 + dy)
            if child_tile is None:
                continue
            child = child_tile.resize((128, 128), Image.Resampling.LANCZOS)
            out.paste(child, (dx * 128, dy * 128), child)
    return out


def z3_quadrant_for_z4(x4: int, y4: int) -> Image.Image | None:
    px, py = x4 // 2, y4 // 2
    qx, qy = x4 % 2, y4 % 2
    parent = fetch_tile(FILL_ZOOM_COARSE, px, py)
    if parent is None:
        return None
    parent = parent.resize((512, 512), Image.Resampling.LANCZOS)
    return parent.crop((qx * 256, qy * 256, (qx + 1) * 256, (qy + 1) * 256))


def merge_transparent(base: Image.Image, fill: Image.Image) -> Image.Image:
    out = base.copy()
    bp = out.load()
    fp = fill.load()
    w = min(out.width, fill.width)
    h = min(out.height, fill.height)
    for y in range(h):
        for x in range(w):
            if bp[x, y][3] == 0 and fp[x, y][3] > 0:
                bp[x, y] = fp[x, y]
    return out


def enhance_z4_tile(x4: int, y4: int, tile: Image.Image | None) -> Image.Image | None:
    """Fill z=4 holes from higher-zoom CDN tiles (same source as tarkov.dev)."""
    if tile is None or not tile.getbbox():
        rebuilt = composite_z4_from_z5(x4, y4)
        return rebuilt if rebuilt.getbbox() else None
    if tile_opaque_count(tile) >= SPARSE_OPAQUE:
        return tile
    merged = merge_transparent(tile, composite_z4_from_z5(x4, y4))
    z3 = z3_quadrant_for_z4(x4, y4)
    if z3 is not None:
        merged = merge_transparent(merged, z3)
    return merged if merged.getbbox() else tile


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

    def fetch_one(xy: tuple[int, int]) -> tuple[int, int, Image.Image | None]:
        x, y = xy
        try:
            data = fetch(TILE_URL.format(z=TILE_ZOOM, x=x, y=y))
        except OSError:
            return x, y, enhance_z4_tile(x, y, None)
        if len(data) < TILE_MIN_BYTES:
            return x, y, enhance_z4_tile(x, y, None)
        base = Image.open(BytesIO(data)).convert("RGBA")
        return x, y, enhance_z4_tile(x, y, base if base.getbbox() else None)

    filled = 0
    with ThreadPoolExecutor(max_workers=16) as pool:
        for x, y, tile in pool.map(fetch_one, jobs):
            if tile is None:
                continue
            canvas.paste(tile, ((x - min_x) * TILE_SIZE, (y - min_y) * TILE_SIZE), tile)
            pasted += 1
            if tile_opaque_count(tile) > SPARSE_OPAQUE:
                continue
            filled += 1

    print(f"OK pasted {pasted}/{len(jobs)} tiles ({filled} sparse cells filled from z={FILL_ZOOM}/z={FILL_ZOOM_COARSE})")
    crop = canvas.getbbox()
    if not crop:
        raise SystemExit("FAIL: stitched interchange map is empty")
    off_x, off_y, _, _ = crop
    cropped = flatten_rgba_on_black(canvas.crop(crop))
    return cropped, float(width), float(height), int(off_x), int(off_y)


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


def mall_game_bounds(variant: dict) -> tuple[float, float, float, float]:
    for layer in variant.get("layers") or []:
        if layer.get("svgLayer") != "First_Floor":
            continue
        for extent in layer.get("extents") or []:
            for entry in extent.get("bounds") or []:
                if len(entry) >= 3 and entry[2] == "mall":
                    x1, z1 = entry[0]
                    x2, z2 = entry[1]
                    return min(x1, x2), max(x1, x2), min(z1, z2), max(z1, z2)
    raise SystemExit("FAIL: interchange mall bounds not found in maps.json")


def game_to_svg_px(
    gx: float, gz: float, bounds: dict, svg_w: float, svg_h: float
) -> tuple[float, float]:
    xmin, xmax = bounds["xmin"], bounds["xmax"]
    zmin, zmax = bounds["zmin"], bounds["zmax"]
    span_x = xmax - xmin
    span_z = zmax - zmin
    if not span_x or not span_z:
        raise SystemExit("FAIL: invalid interchange bounds span")
    u = (gx - xmin) / span_x
    v = (zmax - gz) / span_z
    return u * svg_w, v * svg_h


def mall_svg_viewbox(
    bounds: dict,
    mall_xmin: float,
    mall_xmax: float,
    mall_zmin: float,
    mall_zmax: float,
    svg_w: float,
    svg_h: float,
) -> tuple[float, float, float, float]:
    corners = [
        (mall_xmin, mall_zmin),
        (mall_xmax, mall_zmin),
        (mall_xmin, mall_zmax),
        (mall_xmax, mall_zmax),
    ]
    pts = [game_to_svg_px(gx, gz, bounds, svg_w, svg_h) for gx, gz in corners]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0 = min(xs)
    y0 = min(ys)
    w = max(xs) - x0
    h = max(ys) - y0
    return x0, y0, max(w, 1.0), max(h, 1.0)


def svg_paint_bbox(svg_data: bytes) -> tuple[float, float, float, float]:
    """Tight axis-aligned bbox of painted SVG geometry (paths, polylines, …)."""
    root = ET.fromstring(svg_data)
    paint_tags = frozenset({"path", "polyline", "polygon", "rect", "circle", "ellipse", "line"})
    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")
    number = re.compile(r"-?(?:\d+\.\d*|\.\d+|\d+)(?:e[-+]?\d+)?", re.I)

    def consume_pairs(nums: list[float]) -> None:
        nonlocal min_x, min_y, max_x, max_y
        for i in range(0, len(nums) - 1, 2):
            x, y = nums[i], nums[i + 1]
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)

    for elem in root.iter():
        tag = elem.tag.rsplit("}", 1)[-1]
        if tag not in paint_tags:
            continue
        if tag == "rect":
            x = float(elem.get("x") or 0)
            y = float(elem.get("y") or 0)
            w = float(elem.get("width") or 0)
            h = float(elem.get("height") or 0)
            consume_pairs([x, y, x + w, y + h])
            continue
        if tag == "circle":
            cx = float(elem.get("cx") or 0)
            cy = float(elem.get("cy") or 0)
            r = float(elem.get("r") or 0)
            consume_pairs([cx - r, cy - r, cx + r, cy + r])
            continue
        if tag == "ellipse":
            cx = float(elem.get("cx") or 0)
            cy = float(elem.get("cy") or 0)
            rx = float(elem.get("rx") or 0)
            ry = float(elem.get("ry") or 0)
            consume_pairs([cx - rx, cy - ry, cx + rx, cy + ry])
            continue
        if tag == "line":
            consume_pairs(
                [
                    float(elem.get("x1") or 0),
                    float(elem.get("y1") or 0),
                    float(elem.get("x2") or 0),
                    float(elem.get("y2") or 0),
                ]
            )
            continue
        points = elem.get("d") if tag == "path" else elem.get("points")
        if not points:
            continue
        consume_pairs([float(v) for v in number.findall(points)])

    if not math.isfinite(min_x):
        raise SystemExit("FAIL: empty interchange overlay geometry")
    return min_x, min_y, max(max_x - min_x, 1.0), max(max_y - min_y, 1.0)


def crop_svg_viewbox(svg_data: bytes, x: float, y: float, w: float, h: float) -> bytes:
    root = ET.fromstring(svg_data)
    root.set("viewBox", f"{x} {y} {w} {h}")
    root.attrib.pop("width", None)
    root.attrib.pop("height", None)
    return normalize_svg_bytes(ET.tostring(root, encoding="utf-8", xml_declaration=False))


def game_to_satellite_px(gx: float, gz: float, meta: dict) -> tuple[float, float]:
    t = meta["transform"]
    rot = int(meta["coordinates_rotation"])
    z = int(meta["tile_zoom"])
    ts = int(meta["tile_size"])
    rad = math.radians(rot)
    cos_r, sin_r = math.cos(rad), math.sin(rad)
    lat = gx * sin_r + gz * cos_r
    lng = gx * cos_r - gz * sin_r
    cx = t[0] * lng + t[1]
    cy = (-t[2]) * (-lat) + t[3]
    factor = 2**z
    lx, ly = cx * factor, cy * factor
    bmin_x = meta["tile_min_x"] * ts
    bmin_y = meta["tile_min_y"] * ts
    bmax_x = (meta["tile_max_x"] + 1) * ts
    bmax_y = (meta["tile_max_y"] + 1) * ts
    stitch_w = float(meta["stitch_width"])
    stitch_h = float(meta["stitch_height"])
    off_x = float(meta.get("map_offset_x") or 0)
    off_y = float(meta.get("map_offset_y") or 0)
    x = (lx - bmin_x) / (bmax_x - bmin_x) * stitch_w - off_x
    y = (ly - bmin_y) / (bmax_y - bmin_y) * stitch_h - off_y
    return x, y


def game_to_satellite_px_display(gx: float, gz: float, meta: dict) -> tuple[float, float]:
    """Display pixels with horizontal flip — matches interchange DEV A marker coords."""
    x, y = game_to_satellite_px(gx, gz, meta)
    return float(meta["width"]) - x, y


def schematic_to_satellite_affine(
    meta: dict, bounds: dict, svg_w: float, svg_h: float
) -> tuple[float, float, float, float, float, float, float, float]:
    """Full schematic -> display pixel affine (positive scale; aligns 2F on satellite mall)."""
    nw_g = (bounds["xmin"], bounds["zmax"])
    ne_g = (bounds["xmax"], bounds["zmax"])
    sw_g = (bounds["xmin"], bounds["zmin"])
    nw_s = game_to_svg_px(*nw_g, bounds, svg_w, svg_h)
    ne_s = game_to_svg_px(*ne_g, bounds, svg_w, svg_h)
    sw_s = game_to_svg_px(*sw_g, bounds, svg_w, svg_h)
    nw_p = game_to_satellite_px_display(*nw_g, meta)
    ne_p = game_to_satellite_px_display(*ne_g, meta)
    sw_p = game_to_satellite_px_display(*sw_g, meta)
    span_x = ne_s[0] - nw_s[0]
    span_y = sw_s[1] - nw_s[1]
    if not span_x or not span_y:
        raise SystemExit("FAIL: invalid schematic span for overlay affine")
    a = (ne_p[0] - nw_p[0]) / span_x
    b = (ne_p[1] - nw_p[1]) / span_x
    c = (sw_p[0] - nw_p[0]) / span_y
    d = (sw_p[1] - nw_p[1]) / span_y
    return a, b, c, d, nw_p[0], nw_p[1], nw_s[0], nw_s[1]


def embed_mall_overlay_on_map(
    floor_svg: bytes,
    map_w: float,
    map_h: float,
    origin_x: float,
    origin_y: float,
    matrix: tuple[float, float, float, float, float, float],
) -> bytes:
    inner = ET.fromstring(floor_svg)
    a, b, c, d, e, f = matrix
    out = ET.Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "version": "1.1",
            "viewBox": f"0 0 {map_w} {map_h}",
        },
    )
    for el in inner:
        tag = el.tag.rsplit("}", 1)[-1]
        if tag == "style":
            out.append(el)
    g = ET.SubElement(
        out,
        "g",
        {"transform": f"matrix({a} {b} {c} {d} {e} {f})"},
    )
    shift = ET.SubElement(g, "g", {"transform": f"translate({-origin_x} {-origin_y})"})
    for el in inner:
        tag = el.tag.rsplit("}", 1)[-1]
        if tag != "style":
            shift.append(el)
    return normalize_svg_bytes(ET.tostring(out, encoding="utf-8", xml_declaration=False))


def keep_floor_paths_only(svg_data: bytes) -> bytes:
    """Drop ramp geometry outside the mall shell — it skews alignment and adds ghosts."""
    root = ET.fromstring(svg_data)
    for parent in root.iter():
        if parent.tag.rsplit("}", 1)[-1] != "g":
            continue
        if parent.get("id") != "First_Floor":
            continue
        for child in list(parent):
            if child.get("id") != "Floor-1":
                parent.remove(child)
    return normalize_svg_bytes(ET.tostring(root, encoding="utf-8", xml_declaration=False))


def mall_pixel_rect(meta: dict, variant: dict) -> tuple[int, int, int, int]:
    xmin, xmax, zmin, zmax = mall_game_bounds(variant)
    corners = [(xmin, zmin), (xmax, zmin), (xmin, zmax), (xmax, zmax)]
    pts = [game_to_satellite_px_display(x, z, meta) for x, z in corners]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    left = min(xs)
    top = min(ys)
    width = max(xs) - left
    height = max(ys) - top
    return int(round(left)), int(round(top)), max(1, int(round(width))), max(1, int(round(height)))


def strip_svg_groups(svg_data: bytes, group_ids: tuple[str, ...]) -> bytes:
    root = ET.fromstring(svg_data)
    hide = set(group_ids)

    def prune(parent) -> None:
        for child in list(parent):
            tag = child.tag.rsplit("}", 1)[-1]
            if tag == "g":
                gid = child.get("id") or ""
                if gid in hide or any(token in gid for token in ("Structure", "Pavament", "Pavement")):
                    parent.remove(child)
                    continue
            prune(child)

    prune(root)
    return normalize_svg_bytes(ET.tostring(root, encoding="utf-8", xml_declaration=False))


def apply_rgba_opacity(image: Image.Image, opacity: float) -> Image.Image:
    out = image.convert("RGBA")
    if opacity >= 1:
        return out
    alpha = out.split()[3].point(lambda a: int(a * opacity))
    out.putalpha(alpha)
    return out


def strip_dark_fill_pixels(image: Image.Image, threshold: int = 48) -> Image.Image:
    """Remove near-black SVG fills that read as solid blocks on satellite."""
    rgba = image.convert("RGBA")
    px = rgba.load()
    w, h = rgba.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a > 0 and r <= threshold and g <= threshold and b <= threshold:
                px[x, y] = TRANSPARENT_RGBA
    return rgba


def strip_solid_fills(svg_data: bytes) -> bytes:
    """Keep floor strokes only; solid fills become black blocks on satellite."""
    root = ET.fromstring(svg_data)
    paint_tags = ("path", "polygon", "rect", "polyline", "circle", "ellipse")
    for elem in root.iter():
        tag = elem.tag.rsplit("}", 1)[-1]
        if tag not in paint_tags:
            continue
        fill = (elem.get("fill") or "").strip().lower()
        if fill in ("", "none", "transparent"):
            continue
        elem.set("fill", "none")
    return normalize_svg_bytes(ET.tostring(root, encoding="utf-8", xml_declaration=False))


def composite_mall_floor(
    base: Image.Image,
    floor_rgba: Image.Image,
    left: int,
    top: int,
    opacity: float,
) -> Image.Image:
    canvas = base.convert("RGBA")
    layer = apply_rgba_opacity(floor_rgba, opacity)
    overlay = Image.new("RGBA", canvas.size, TRANSPARENT_RGBA)
    overlay.paste(layer, (left, top), layer)
    merged = Image.alpha_composite(canvas, overlay)
    return merged.convert("RGB")


def bake_satellite_floor_overlay(
    base: Image.Image, overlay_svg: bytes, meta: dict, variant: dict
) -> Image.Image:
    left, top, width, height = mall_pixel_rect(meta, variant)
    trimmed = strip_svg_groups(overlay_svg, SATELLITE_OVERLAY_HIDE_GROUPS)
    trimmed = strip_solid_fills(trimmed)
    floor = render_svg_rgba(trimmed, width, height)
    floor = strip_dark_fill_pixels(floor)
    print(
        f"OK bake 2F on mall px=({left},{top}) size={width}x{height} "
        f"opacity={SATELLITE_OVERLAY_OPACITY}"
    )
    return composite_mall_floor(base, floor, left, top, SATELLITE_OVERLAY_OPACITY)


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
    for name in ("map.svg",):
        p = out_dir / name
        if p.is_file():
            p.unlink()
            print(f"removed {label}/map.svg")
    overlay_path = out_dir / "map-overlay.svg"
    if overlay:
        overlay_path.write_bytes(overlay)
    elif overlay_path.is_file():
        overlay_path.unlink()
        print(f"removed {label}/map-overlay.svg")
    (out_dir / "map.png").write_bytes(png)
    (out_dir / "meta.json").write_text(
        json.dumps(meta, indent=4, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if overlay:
        print(
            f"OK {label}/map.png + map-overlay.svg ({len(png)/1024/1024:.1f} MB, "
            f"overlay {len(overlay)} bytes)"
        )
    else:
        print(f"OK {label}/map.png ({len(png)/1024/1024:.1f} MB, satellite only)")


def write_schematic_variant(
    out_dir: Path,
    meta: dict,
    svg: bytes,
    label: str,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in ("map.png", "map-overlay.svg"):
        p = out_dir / name
        if p.is_file():
            p.unlink()
            print(f"removed {label}/{name}")
    (out_dir / "map.svg").write_bytes(svg)
    (out_dir / "meta.json").write_text(
        json.dumps(meta, indent=4, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"OK {label}/map.svg ({len(svg)} bytes)")


def main() -> None:
    maps_data = fetch_maps_json()
    variant = map_variant(maps_data)
    min_x, max_x, min_y, max_y = probe_tiles()
    print(f"OK interchange z={TILE_ZOOM} bbox=({min_x},{min_y})-({max_x},{max_y})")

    image, stitch_w, stitch_h, off_x, off_y = download_and_stitch(
        min_x, max_x, min_y, max_y
    )
    schematic_b = fetch_schematic_svg(SCHEMATIC_LAYERS_B)
    svg_w, svg_h, _ = parse_viewbox(schematic_b)

    bounds = bounds_to_meta(
        variant["bounds"],
        variant.get("coordinateRotation", 180),
        variant.get("transform"),
    )
    bounds["name"] = "interchange"
    bounds["display_name"] = "Interchange"
    bounds["description"] = ""

    meta_a = dict(bounds)
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

    crop_w, crop_h = image.size
    meta_a["width"] = float(crop_w)
    meta_a["height"] = float(crop_h)

    buf = BytesIO()
    image.save(buf, format="PNG", optimize=True)
    png = buf.getvalue()
    meta_a["map_asset_rev"] = hashlib.sha256(png).hexdigest()[:16]

    tile_cfg = probe_tile_meta(maps_data, "interchange")
    meta_b = meta_entry("interchange", bounds, svg_w, svg_h, tile_cfg=tile_cfg)

    write_satellite_variant(MAPS_DIR_A, meta_a, png, "DEV A interchange")
    write_schematic_variant(MAPS_DIR_B, meta_b, schematic_b, "DEV B interchange")
    print(f"OK interchange A png {crop_w}x{crop_h}, B svg {svg_w}x{svg_h}")


if __name__ == "__main__":
    main()

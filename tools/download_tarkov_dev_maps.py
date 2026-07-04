"""
Manual map asset fetcher (run only when updating embedded graphics).

Updates internal/maps_tarkov.dev/<id>/{meta.json,map.svg|map.png} and catalog.json.

Not invoked by build_win10.bat.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import base64
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore

REPO = Path(__file__).resolve().parent.parent
VARIANT_ROOTS = {
    "A": REPO / "internal" / "maps_tarkov.dev",
    "B": REPO / "internal" / "maps_tarkov.dev_B",
}
MAPS_ROOT = VARIANT_ROOTS["A"]
CATALOG_OUT = MAPS_ROOT / "catalog.json"
TILES_TMP = REPO / "tools" / "_tmp_tiles"

MAPS_JSON_URL = "https://raw.githubusercontent.com/the-hideout/tarkov-dev/main/src/data/maps.json"
CDN_SVG = "https://assets.tarkov.dev/maps/svg/{file}"

SVG_MAPS_REPO = "https://raw.githubusercontent.com/the-hideout/tarkov-dev-svg-maps/main/{file}"

ID_ALIASES = {
    "streets-of-tarkov": "streets",
    "ground-zero": "groundzero",
    "the-lab": "labs",
    "the-labyrinth": "labyrinth",
}

EXTRA_SVG = {
    "labs": "Labs.svg",
}

LABS_TILES = {
    "layer": "1st",
    "tile_size": 256,
    "min_bytes": 8000,
    "min_zoom": 4,
    "max_zoom": 6,
    "scan": 32,
    "min_zoom_ratio": 0.9,
    "remote_url": "https://assets.tarkov.dev/maps/labs_v4/1st/{z}/{x}/{y}.png",
}

LABYRINTH_TILES = {
    "zoom": 4,
    "tile_size": 256,
    "min_bytes": 5000,
    "min_zoom_ratio": 0.9,
    "remote_url": "https://assets.tarkov.dev/maps/labyrinth/main/{z}/{x}/{y}.png",
    "scan": 16,
}

CATALOG_ORDER = [
    "factory",
    "groundzero",
    "interchange",
    "lighthouse",
    "labs",
    "customs",
    "shoreline",
    "labyrinth",
    "reserve",
    "woods",
    "streets",
]

SKIPPED_MAPS = {
    "icebreaker": "tarkov.dev has only re3mr icebreaker-2d.jpg (no official map assets)",
}

DISPLAY_NAMES = {
    "woods": "Woods",
    "customs": "Customs",
    "factory": "Factory",
    "groundzero": "Ground Zero",
    "interchange": "Interchange",
    "lighthouse": "Lighthouse",
    "labs": "Labs",
    "reserve": "Reserve",
    "shoreline": "Shoreline",
    "streets": "Streets of Tarkov",
    "labyrinth": "Labyrinth",
}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "bm-tarkov-map-tracker"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read()


def fetch_maps_json() -> list:
    try:
        return json.loads(fetch(MAPS_JSON_URL).decode("utf-8"))
    except OSError:
        api = "https://api.github.com/repos/the-hideout/tarkov-dev/contents/src/data/maps.json"
        payload = json.loads(fetch(api).decode("utf-8"))
        return json.loads(base64.b64decode(payload["content"]))


def tile_url(template: str, zoom: int, x: int, y: int, **fmt: str) -> str:
    out = template.replace("{z}", str(zoom)).replace("{x}", str(x)).replace("{y}", str(y))
    for key, val in fmt.items():
        out = out.replace("{" + key + "}", val)
    return out


def probe_tile_coords(
    template: str,
    zoom: int,
    scan: int,
    min_bytes: int,
    **fmt: str,
) -> tuple[list[tuple[int, int]], int]:
    def probe_at(x: int, y: int) -> tuple[int, int, int] | None:
        url = tile_url(template, zoom, x, y, **fmt)
        try:
            data = fetch(url)
            if len(data) >= min_bytes:
                return x, y, len(data)
        except OSError:
            pass
        return None

    coords: list[tuple[int, int]] = []
    total = 0
    jobs = [(x, y) for x in range(scan) for y in range(scan)]
    with ThreadPoolExecutor(max_workers=16) as pool:
        for hit in pool.map(lambda xy: probe_at(*xy), jobs):
            if hit:
                coords.append((hit[0], hit[1]))
                total += hit[2]
    coords.sort()
    return coords, total


def try_fetch_tile(
    template: str,
    zoom: int,
    x: int,
    y: int,
    min_bytes: int,
    **fmt: str,
) -> bool:
    try:
        data = fetch(tile_url(template, zoom, x, y, **fmt))
        return len(data) >= min_bytes
    except OSError:
        return False


def probe_coords_list(
    template: str,
    zoom: int,
    coords_list: list[tuple[int, int]],
    min_bytes: int,
    **fmt: str,
) -> list[tuple[int, int]]:
    if not coords_list:
        return []

    def probe_at(xy: tuple[int, int]) -> tuple[int, int] | None:
        x, y = xy
        if try_fetch_tile(template, zoom, x, y, min_bytes, **fmt):
            return x, y
        return None

    hits: list[tuple[int, int]] = []
    with ThreadPoolExecutor(max_workers=24) as pool:
        for hit in pool.map(probe_at, coords_list):
            if hit:
                hits.append(hit)
    hits.sort()
    return hits


def discover_tiles(
    template: str,
    zoom: int,
    min_bytes: int,
    seed_scan: int = 32,
    **fmt: str,
) -> list[tuple[int, int]]:
    """Expand from seed grid so maps wider than seed_scan still stitch completely."""
    seeds, _ = probe_tile_coords(template, zoom, seed_scan, min_bytes, **fmt)
    found: set[tuple[int, int]] = set(seeds)
    if not found:
        return []
    while True:
        min_x = min(x for x, _ in found)
        max_x = max(x for x, _ in found)
        min_y = min(y for _, y in found)
        max_y = max(y for _, y in found)
        ring: list[tuple[int, int]] = []
        for x in range(min_x - 1, max_x + 2):
            for y in range(min_y - 1, max_y + 2):
                if min_x <= x <= max_x and min_y <= y <= max_y:
                    continue
                if x < 0 or y < 0:
                    continue
                if (x, y) not in found:
                    ring.append((x, y))
        if not ring:
            break
        added = probe_coords_list(template, zoom, ring, min_bytes, **fmt)
        if not added:
            break
        found.update(added)
    missing = [
        (x, y)
        for x in range(min_x, max_x + 1)
        for y in range(min_y, max_y + 1)
        if (x, y) not in found
    ]
    if missing:
        found.update(probe_coords_list(template, zoom, missing, min_bytes, **fmt))
    return sorted(found)


def tile_payload(
    map_id: str,
    cfg: dict,
    zoom: int,
    coords: list[tuple[int, int]],
    min_x: int,
    max_x: int,
    min_y: int,
    max_y: int,
) -> dict:
    tile_size = cfg["tile_size"]
    width = (max_x - min_x + 1) * tile_size
    height = (max_y - min_y + 1) * tile_size
    return {
        map_id: {
            "zoom": zoom,
            "tileSize": tile_size,
            "minX": min_x,
            "minY": min_y,
            "maxX": max_x,
            "maxY": max_y,
            "width": width,
            "height": height,
            "coords": [{"x": x, "y": y} for x, y in coords],
        }
    }


def download_tile_assets(
    map_id: str,
    remote_url: str,
    zoom: int,
    coords: list[tuple[int, int]],
) -> int:
    map_root = TILES_TMP / map_id
    if map_root.is_dir():
        shutil.rmtree(map_root)
    total = 0

    def fetch_one(xy: tuple[int, int]) -> int:
        x, y = xy
        data = fetch(tile_url(remote_url, zoom, x, y))
        out = map_root / str(zoom) / str(x) / f"{y}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        return len(data)

    with ThreadPoolExecutor(max_workers=24) as pool:
        done = 0
        for size in pool.map(fetch_one, coords):
            total += size
            done += 1
            if done % 100 == 0 or done == len(coords):
                print(
                    f"... {map_id} tiles {done}/{len(coords)}",
                    flush=True,
                )
    print(f"OK {map_id} temp tiles z={zoom} count={len(coords)} bytes={total}")
    return total


FACTORY_LAND_RGBA = (31, 80, 84, 255)
# Factory satellite tiles are sparse in the grid; opaque land fill breaks getbbox() crop.
STITCH_UNDERLAY: dict[str, tuple[int, int, int, int]] = {
    "factory": (0, 0, 0, 0),
    "interchange": (0, 0, 0, 0),
    "shoreline": (0, 0, 0, 0),
    "reserve": (0, 0, 0, 0),
    "woods": (0, 0, 0, 0),
    "groundzero": (0, 0, 0, 0),
    "customs": (0, 0, 0, 0),
}
STITCH_FLATTEN_BLACK = {
    "factory",
    "interchange",
    "shoreline",
    "reserve",
    "woods",
    "groundzero",
    "customs",
}
SATELLITE_ZOOM_LOCK = {
    "factory": 4,
    "interchange": 4,
    "shoreline": 4,
    "reserve": 4,
    "woods": 4,
    "customs": 5,
    "groundzero": 4,
}

# DEV A streets uses the same tarkov.dev SVG as variant B (no eftarkov raster).
EFTARKOV_RASTER_FALLBACK: dict[str, str] = {}


def flatten_rgba_on_black(image: Image.Image) -> Image.Image:
    if image.mode != "RGBA":
        return image.convert("RGB")
    bg = Image.new("RGB", image.size, (0, 0, 0))
    bg.paste(image, mask=image.split()[3])
    return bg


def stitch_tiles(map_id: str, tile_cfg: dict) -> tuple[bytes, float, float, dict]:
    if Image is None:
        raise SystemExit("PIL required for PNG maps: pip install Pillow")
    Image.MAX_IMAGE_PIXELS = max(getattr(Image, "MAX_IMAGE_PIXELS", 0) or 0, 500_000_000)
    z = str(tile_cfg["zoom"])
    ts = tile_cfg["tileSize"]
    w, h = int(tile_cfg["width"]), int(tile_cfg["height"])
    underlay = STITCH_UNDERLAY.get(map_id)
    if underlay is None:
        underlay = FACTORY_LAND_RGBA if map_id in SATELLITE_ZOOM_LOCK else (0, 0, 0, 0)
    canvas = Image.new("RGBA", (w, h), underlay)
    root = TILES_TMP / map_id / z
    paths = sorted(root.rglob("*.png"))
    if not paths:
        raise SystemExit(f"FAIL stitch {map_id}: no tiles under {root}")
    for path in paths:
        x = int(path.parent.name)
        y = int(path.stem)
        tile = Image.open(path).convert("RGBA")
        canvas.paste(tile, ((x - tile_cfg["minX"]) * ts, (y - tile_cfg["minY"]) * ts), tile)
    crop_extra: dict = {
        "stitch_width": float(w),
        "stitch_height": float(h),
        "map_offset_x": 0,
        "map_offset_y": 0,
    }
    if map_id in SATELLITE_ZOOM_LOCK:
        bbox = canvas.getbbox()
        if bbox:
            crop_extra["map_offset_x"] = bbox[0]
            crop_extra["map_offset_y"] = bbox[1]
            canvas = canvas.crop(bbox)
            crop_extra["width"] = float(canvas.size[0])
            crop_extra["height"] = float(canvas.size[1])
    if map_id in STITCH_FLATTEN_BLACK:
        canvas = flatten_rgba_on_black(canvas)
    buf = BytesIO()
    canvas.save(buf, format="PNG", optimize=True)
    if buf.tell() < 50_000 and len(paths) > 20:
        raise SystemExit(
            f"FAIL stitch {map_id}: {len(paths)} tiles but PNG only {buf.tell()} bytes"
        )
    return buf.getvalue(), float(canvas.size[0]), float(canvas.size[1]), crop_extra


def write_map_folder(map_id: str, meta: dict, image: bytes, ext: str) -> None:
    out_dir = MAPS_ROOT / map_id
    out_dir.mkdir(parents=True, exist_ok=True)
    opposite = ".svg" if ext == ".png" else ".png"
    opp_path = out_dir / f"map{opposite}"
    if opp_path.is_file():
        opp_path.unlink()
        print(f"removed {map_id}/map{opposite}")
    (out_dir / "meta.json").write_text(
        json.dumps(meta, indent=4, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out_dir / f"map{ext}").write_bytes(image)
    print(f"OK {map_id}/meta.json + map{ext} ({len(image)} bytes)")


def meta_entry(
    map_id: str, bounds: dict, width: float, height: float, tile_cfg: dict | None = None
) -> dict:
    entry = {
        "name": map_id,
        "display_name": DISPLAY_NAMES.get(map_id, map_id.title()),
        "description": "",
        "xmin": bounds.get("xmin", 0),
        "xmax": bounds.get("xmax", 0),
        "zmin": bounds.get("zmin", 0),
        "zmax": bounds.get("zmax", 0),
        "coordinates_rotation": bounds.get("coordinates_rotation", 180),
        "width": width,
        "height": height,
    }
    if bounds.get("transform"):
        entry["transform"] = bounds["transform"]
    for key in ("svg_xmin", "svg_xmax", "svg_zmin", "svg_zmax"):
        if bounds.get(key) is not None:
            entry[key] = bounds[key]
    if bounds.get("display_rotation") is not None:
        entry["display_rotation"] = bounds["display_rotation"]
    if tile_cfg:
        entry["tile_zoom"] = tile_cfg["zoom"]
        entry["tile_min_x"] = tile_cfg["minX"]
        entry["tile_min_y"] = tile_cfg["minY"]
        entry["tile_max_x"] = tile_cfg["maxX"]
        entry["tile_max_y"] = tile_cfg["maxY"]
        entry["tile_size"] = tile_cfg["tileSize"]
    return entry


def probe_tile_meta(maps_data: list, map_id: str) -> dict | None:
    """Tile grid metadata shared by DEV A satellite and DEV B SVG (same CRS, different image)."""
    variant = collect_interactive_variants(maps_data).get(map_id)
    if not variant or not variant.get("tilePath"):
        return None
    tile_path = variant["tilePath"]
    zoom, coords, min_x, max_x, min_y, max_y = pick_satellite_zoom(tile_path, map_id)
    cfg = {"tile_size": int(variant.get("tileSize") or 256)}
    return tile_payload(map_id, cfg, zoom, coords, min_x, max_x, min_y, max_y)[map_id]


def pick_labs_zoom() -> tuple[int, list[tuple[int, int]], int, int, int, int]:
    cfg = LABS_TILES
    best: tuple[int, list[tuple[int, int]], int, int, int, int, float] | None = None
    for zoom in range(cfg["max_zoom"], cfg["min_zoom"] - 1, -1):
        coords = discover_tiles(
            cfg["remote_url"],
            zoom,
            cfg["min_bytes"],
            seed_scan=cfg["scan"],
        )
        if not coords:
            continue
        min_x = min(x for x, _ in coords)
        max_x = max(x for x, _ in coords)
        min_y = min(y for _, y in coords)
        max_y = max(y for _, y in coords)
        avg = 1.0
        area = (max_x - min_x + 1) * (max_y - min_y + 1)
        score = len(coords) * min(avg, 120_000) / max(area, 1)
        row = (zoom, coords, min_x, max_x, min_y, max_y, score)
        if best is None or row[6] >= best[6]:
            best = row
    if best is None:
        raise SystemExit("FAIL labs: no interactive tiles found")
    zoom, coords, min_x, max_x, min_y, max_y, _ = best
    print(
        f"OK labs tiles z={zoom} count={len(coords)} "
        f"bbox=({min_x},{min_y})-({max_x},{max_y})"
    )
    return zoom, coords, min_x, max_x, min_y, max_y


def probe_labs_tiles() -> tuple[dict, bytes, float, float]:
    cfg = LABS_TILES
    zoom, coords, min_x, max_x, min_y, max_y = pick_labs_zoom()
    download_tile_assets("labs", cfg["remote_url"], zoom, coords)
    payload = tile_payload("labs", cfg, zoom, coords, min_x, max_x, min_y, max_y)["labs"]
    png, aw, ah, _ = stitch_tiles("labs", payload)
    shutil.rmtree(TILES_TMP / "labs", ignore_errors=True)
    print(f"OK labs tile map size={payload['width']}x{payload['height']} z={zoom}")
    return payload, png, aw, ah


def catalog_id(normalized: str) -> str:
    if normalized in ID_ALIASES:
        return ID_ALIASES[normalized]
    return normalized.replace("-", "")


# Reserve SVG is drawn on a diagonal; interactive view uses a small CCW correction.
DISPLAY_ROTATION: dict[str, int] = {
    "reserve": -15,
}


def bounds_to_meta(
    bounds: list,
    rotation: int,
    map_id: str = "",
    transform: list | None = None,
) -> dict[str, int | float | list[float]]:
    xmax, zmin = bounds[0]
    xmin, zmax = bounds[1]
    meta = {
        "xmin": round(float(xmin), 4),
        "xmax": round(float(xmax), 4),
        "zmin": round(float(zmin), 4),
        "zmax": round(float(zmax), 4),
        "coordinates_rotation": int(rotation),
    }
    if transform and len(transform) >= 4:
        meta["transform"] = [float(transform[0]), float(transform[1]), float(transform[2]), float(transform[3])]
    if map_id in DISPLAY_ROTATION:
        meta["display_rotation"] = DISPLAY_ROTATION[map_id]
    return meta


def parse_viewbox(data: bytes) -> tuple[float, float, str]:
    head = data[:8000].decode("utf-8", "replace")
    m = re.search(r'viewBox="([^"]+)"', head)
    if not m:
        return 0, 0, ""
    parts = re.split(r"[\s,]+", m.group(1).strip())
    if len(parts) != 4:
        return 0, 0, m.group(1)
    return float(parts[2]), float(parts[3]), m.group(1)


def _svg_local_name(name: str) -> str:
    if "}" in name:
        name = name.rsplit("}", 1)[-1]
    return name


def _clone_svg_plain(el: ET.Element) -> ET.Element:
    tag = _svg_local_name(el.tag)
    attribs = {
        _svg_local_name(k): v
        for k, v in el.attrib.items()
        if not _svg_local_name(k).startswith("xmlns")
    }
    plain = ET.Element(tag, attribs)
    if el.text:
        plain.text = el.text
    if el.tail:
        plain.tail = el.tail
    for child in el:
        plain.append(_clone_svg_plain(child))
    return plain


def normalize_svg_bytes(data: bytes) -> bytes:
    """Strip XML namespace prefixes so embedded <style> rules apply in WebView."""
    head = data[:4096].decode("utf-8", "replace")
    if "<style" in head and "ns0:" not in head and "{http" not in head:
        return data
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        text = re.sub(r"<(/?)(ns\d+):", r"<\1", data.decode("utf-8", "replace"))
        text = re.sub(r'\s+xmlns:ns\d+="[^"]*"', "", text)
        return text.encode("utf-8")

    viewbox = root.get("viewBox") or root.get("viewbox") or "0 0 100 100"
    out = ET.Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "xmlns:xlink": "http://www.w3.org/1999/xlink",
            "version": root.get("version") or "1.1",
            "viewBox": viewbox,
        },
    )
    skip_root = {"viewBox", "viewbox", "xmlns", "version"}
    for key, value in root.attrib.items():
        local = _svg_local_name(key)
        if local in skip_root or ":" in local:
            continue
        out.set(local, value)
    for child in root:
        out.append(_clone_svg_plain(child))
    return ET.tostring(out, encoding="utf-8", xml_declaration=False)


def extract_svg_layer(svg_data: bytes, layer_id: str) -> bytes:
    """Keep one interactive layer (matches tarkov.dev svgLayer default)."""
    try:
        root = ET.fromstring(svg_data)
    except ET.ParseError:
        return svg_data
    layer = None
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag == "g" and el.get("id") == layer_id:
            layer = el
            break
    if layer is None:
        return svg_data
    viewbox = root.get("viewBox") or "0 0 100 100"
    out_root = ET.Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "version": "1.1",
            "viewBox": viewbox,
        },
    )
    for el in root:
        tag = el.tag.rsplit("}", 1)[-1]
        if tag == "style":
            out_root.append(el)
    out_root.append(layer)
    return normalize_svg_bytes(ET.tostring(out_root, encoding="utf-8", xml_declaration=False))


def extract_svg_layers(svg_data: bytes, layer_ids: list[str]) -> bytes:
    """Keep multiple floor groups in document order (bottom → top)."""
    try:
        root = ET.fromstring(svg_data)
    except ET.ParseError:
        return svg_data
    viewbox = root.get("viewBox") or "0 0 100 100"
    out_root = ET.Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "version": "1.1",
            "viewBox": viewbox,
        },
    )
    for el in root:
        tag = el.tag.rsplit("}", 1)[-1]
        if tag == "style":
            out_root.append(el)
    for layer_id in layer_ids:
        layer = None
        for el in root.iter():
            tag = el.tag.rsplit("}", 1)[-1]
            if tag == "g" and el.get("id") == layer_id:
                layer = el
                break
        if layer is not None:
            out_root.append(layer)
    if len(out_root) <= 1:
        return svg_data
    return normalize_svg_bytes(ET.tostring(out_root, encoding="utf-8", xml_declaration=False))


def probe_labyrinth_tiles() -> tuple[dict, bytes, float, float]:
    cfg = LABYRINTH_TILES
    zoom = cfg["zoom"]
    tile_size = cfg["tile_size"]
    coords = discover_tiles(
        cfg["remote_url"],
        zoom,
        cfg["min_bytes"],
        seed_scan=cfg["scan"],
    )
    if not coords:
        raise SystemExit("FAIL labyrinth: no tiles found")

    coords.sort()
    min_x = min(x for x, _ in coords)
    max_x = max(x for x, _ in coords)
    min_y = min(y for _, y in coords)
    max_y = max(y for _, y in coords)
    download_tile_assets("labyrinth", cfg["remote_url"], zoom, coords)
    width = (max_x - min_x + 1) * tile_size
    height = (max_y - min_y + 1) * tile_size
    payload = tile_payload(
        "labyrinth",
        cfg,
        zoom,
        coords,
        min_x,
        max_x,
        min_y,
        max_y,
    )["labyrinth"]
    png, aw, ah, _ = stitch_tiles("labyrinth", payload)
    shutil.rmtree(TILES_TMP / "labyrinth", ignore_errors=True)
    print(
        f"OK labyrinth tiles z={zoom} count={len(coords)} "
        f"bbox=({min_x},{min_y})-({max_x},{max_y}) size={width}x{height}"
    )
    return payload, png, aw, ah


def collect_meta(maps_data: list) -> dict[str, dict]:
    meta_by_id: dict[str, dict] = {}
    for entry in maps_data:
        normalized = entry.get("normalizedName", "")
        map_id = catalog_id(normalized)
        for variant in entry.get("maps") or []:
            bounds = variant.get("bounds")
            if not bounds or len(bounds) != 2:
                continue
            key = variant.get("key", "")
            if map_id == "labs" and key != "the-lab":
                continue
            if map_id == "labyrinth" and key != "the-labyrinth":
                continue
            meta_by_id[map_id] = bounds_to_meta(
                bounds,
                variant.get("coordinateRotation", 180),
                map_id,
                variant.get("transform"),
            )
    return meta_by_id


def collect_interactive_variants(maps_data: list) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for entry in maps_data:
        normalized = entry.get("normalizedName", "")
        map_id = catalog_id(normalized)
        for variant in entry.get("maps") or []:
            if variant.get("projection") != "interactive":
                continue
            key = variant.get("key", "")
            if map_id == "labs" and key != "the-lab":
                continue
            if map_id == "labyrinth" and key != "the-labyrinth":
                continue
            out[map_id] = variant
    return out


def pick_satellite_zoom(
    tile_path: str, map_id: str, scan: int = 32, min_bytes: int = 4000
) -> tuple[int, list[tuple[int, int]], int, int, int, int]:
    locked = SATELLITE_ZOOM_LOCK.get(map_id)
    if locked is not None:
        zoom = locked
        seed = 16 if zoom <= 4 else 32
        coords = discover_tiles(tile_path, zoom, min_bytes, seed_scan=seed)
        if not coords:
            raise SystemExit(f"FAIL {map_id}: no satellite tiles at z={zoom}")
        if map_id == "shoreline":
            if locked >= 6:
                coords = [(x, y) for x, y in coords if x <= 31 and y <= 31]
            elif locked == 4:
                coords = [(x, y) for x, y in coords if x <= 15 and y <= 13]
        elif map_id == "reserve":
            if locked >= 6:
                coords = [(x, y) for x, y in coords if x <= 39 and y <= 39]
            elif locked == 5:
                coords = [(x, y) for x, y in coords if x <= 31 and y <= 29]
            elif locked == 4:
                coords = [(x, y) for x, y in coords if x <= 15 and y <= 14]
        elif map_id == "woods":
            if locked >= 6:
                coords = [(x, y) for x, y in coords if x <= 47 and y <= 47]
            elif locked == 5:
                coords = [(x, y) for x, y in coords if x <= 31 and y <= 31]
            elif locked == 4:
                coords = [(x, y) for x, y in coords if x <= 15 and y <= 15]
        elif map_id == "customs":
            if locked >= 6:
                coords = [(x, y) for x, y in coords if x <= 31 and y <= 39]
            elif locked == 5:
                coords = [(x, y) for x, y in coords if x <= 31 and y <= 24]
            elif locked == 4:
                coords = [(x, y) for x, y in coords if x <= 15 and y <= 12]
        elif map_id == "groundzero":
            if locked >= 6:
                coords = [(x, y) for x, y in coords if x <= 54 and y <= 63]
            elif locked == 5:
                coords = [(x, y) for x, y in coords if x <= 27 and y <= 31]
            elif locked == 4:
                coords = [(x, y) for x, y in coords if x <= 13 and y <= 15]
        min_x = min(x for x, _ in coords)
        max_x = max(x for x, _ in coords)
        min_y = min(y for _, y in coords)
        max_y = max(y for _, y in coords)
        print(
            f"OK {map_id} satellite z={zoom} (locked) count={len(coords)} "
            f"bbox=({min_x},{min_y})-({max_x},{max_y})"
        )
        return zoom, coords, min_x, max_x, min_y, max_y

    max_tiles_edge = 72
    for zoom in range(6, 2, -1):
        coords = discover_tiles(tile_path, zoom, min_bytes, seed_scan=scan)
        if not coords:
            continue
        min_x = min(x for x, _ in coords)
        max_x = max(x for x, _ in coords)
        min_y = min(y for _, y in coords)
        max_y = max(y for _, y in coords)
        w_tiles = max_x - min_x + 1
        h_tiles = max_y - min_y + 1
        if max(w_tiles, h_tiles) > max_tiles_edge:
            print(
                f"SKIP {map_id} z={zoom}: {w_tiles}x{h_tiles} tiles exceeds {max_tiles_edge}"
            )
            continue
        fill = len(coords) / max(w_tiles * h_tiles, 1)
        print(
            f"OK {map_id} satellite z={zoom} count={len(coords)} "
            f"bbox=({min_x},{min_y})-({max_x},{max_y}) fill={fill:.1%}"
        )
        return zoom, coords, min_x, max_x, min_y, max_y
    raise SystemExit(f"FAIL {map_id}: no satellite tiles at {tile_path}")


def build_satellite_png_maps(maps_data: list) -> dict[str, tuple[dict, bytes, float, float]]:
    variants = collect_interactive_variants(maps_data)
    png_maps: dict[str, tuple[dict, bytes, float, float]] = {}

    labyrinth_cfg, labyrinth_png, labyrinth_w, labyrinth_h = probe_labyrinth_tiles()
    png_maps["labyrinth"] = (labyrinth_cfg, labyrinth_png, labyrinth_w, labyrinth_h)

    labs_cfg, labs_png, labs_w, labs_h = probe_labs_tiles()
    png_maps["labs"] = (labs_cfg, labs_png, labs_w, labs_h)

    for map_id, variant in variants.items():
        if map_id in {"labs", "labyrinth"}:
            continue
        tile_path = variant.get("tilePath")
        if not tile_path:
            continue
        zoom, coords, min_x, max_x, min_y, max_y = pick_satellite_zoom(tile_path, map_id)
        download_tile_assets(map_id, tile_path, zoom, coords)
        cfg = {"tile_size": int(variant.get("tileSize") or 256)}
        payload = tile_payload(map_id, cfg, zoom, coords, min_x, max_x, min_y, max_y)[map_id]
        png, aw, ah, crop = stitch_tiles(map_id, payload)
        shutil.rmtree(TILES_TMP / map_id, ignore_errors=True)
        png_maps[map_id] = (payload, png, aw, ah, crop)
    return png_maps


def sync_bundled(_downloads: dict[str, tuple[str, bytes, str]]) -> None:
    pass


def apply_eftarkov_raster_fallback(meta_by_id: dict[str, dict]) -> None:
    """DEV A: maps without tarkov.dev satellite tiles get eftarkov.com PNG."""
    if Image is None:
        raise SystemExit("PIL required for eftarkov raster fallback: pip install Pillow")
    Image.MAX_IMAGE_PIXELS = None

    from sync_maps_from_eftarkov import composite_stitch, fetch, parse_config

    for map_id, url_slug in EFTARKOV_RASTER_FALLBACK.items():
        if (MAPS_ROOT / map_id / "map.png").is_file():
            continue
        bounds = meta_by_id.get(map_id)
        if not bounds:
            print(f"SKIP {map_id}: no bounds meta")
            continue
        try:
            html = fetch(f"https://api.eftarkov.com/map/{url_slug}/").decode("utf-8", "replace")
            cfg = parse_config(html)
            png, w, h, _level, _cols, _rows = composite_stitch(url_slug, cfg)
            write_map_folder(
                map_id,
                meta_entry(map_id, bounds, w, h, tile_cfg=None),
                png,
                ".png",
            )
            print(f"OK {map_id} eftarkov raster fallback ({w:.0f}x{h:.0f})")
        except Exception as exc:
            print(f"FAIL {map_id} eftarkov fallback: {exc}")


def parse_variant() -> str:
    variant = "A"
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg in ("--variant", "-v") and i + 1 < len(args):
            variant = args[i + 1].strip().upper()
        elif arg.startswith("--variant="):
            variant = arg.split("=", 1)[1].strip().upper()
    if variant not in VARIANT_ROOTS:
        raise SystemExit(f"unknown variant {variant!r}; use A or B")
    return variant


def set_maps_root(variant: str) -> None:
    global MAPS_ROOT, CATALOG_OUT
    MAPS_ROOT = VARIANT_ROOTS[variant]
    CATALOG_OUT = MAPS_ROOT / "catalog.json"


def remove_png_assets(map_id: str) -> None:
    png = MAPS_ROOT / map_id / "map.png"
    if png.is_file():
        png.unlink()
        print(f"removed {map_id}/map.png (abstract SVG)")


def has_satellite_tiles(maps_data: list, map_id: str) -> bool:
    return bool(collect_interactive_variants(maps_data).get(map_id, {}).get("tilePath"))


def main() -> None:
    variant = parse_variant()
    set_maps_root(variant)
    abstract = variant == "B"
    print(f"sync DEV variant={variant} -> {MAPS_ROOT}", flush=True)

    maps_data = fetch_maps_json()
    meta_by_id = collect_meta(maps_data)
    interactive = collect_interactive_variants(maps_data)

    downloads: dict[str, tuple[str, bytes, str]] = {}

    for entry in maps_data:
        normalized = entry.get("normalizedName", "")
        for map_variant in entry.get("maps") or []:
            svg_path = map_variant.get("svgPath")
            if not svg_path or map_variant.get("projection") != "interactive":
                continue
            map_id = catalog_id(normalized)
            if not abstract and map_variant.get("tilePath"):
                continue
            url = svg_path
            data = fetch(url)
            svg_layer = map_variant.get("svgLayer")
            if svg_layer:
                data = extract_svg_layer(data, svg_layer)
            downloads[map_id] = (url, data, ".svg")
            layer_note = f" layer={svg_layer}" if svg_layer else ""
            print(f"OK {map_id}.svg <- {url} ({len(data)} bytes){layer_note}")

    for map_id, remote_file in EXTRA_SVG.items():
        if map_id in downloads or (not abstract and map_id in interactive and interactive[map_id].get("tilePath")):
            continue
        url = CDN_SVG.format(file=remote_file)
        data = fetch(url)
        downloads[map_id] = (url, data, ".svg")
        print(f"OK {map_id}.svg <- {url} ({len(data)} bytes)")

    png_maps: dict[str, tuple[dict, float, float]] = {}
    if not abstract:
        png_maps = build_satellite_png_maps(maps_data)

    allowed_dirs = set(CATALOG_ORDER)
    for map_id in CATALOG_ORDER:
        bounds = meta_by_id.get(map_id, {})
        if map_id in png_maps:
            cfg, png, aw, ah, crop = png_maps[map_id]
            meta = meta_entry(map_id, bounds, aw, ah, tile_cfg=cfg)
            for key in ("stitch_width", "stitch_height", "map_offset_x", "map_offset_y"):
                if key in crop:
                    meta[key] = crop[key]
            write_map_folder(
                map_id,
                meta,
                png,
                ".png",
            )
            continue
        if map_id not in downloads:
            print(f"SKIP {map_id}: no download")
            continue
        url, data, ext = downloads[map_id]
        if ext != ".svg":
            raise SystemExit(f"FAIL {map_id}: unsupported asset type {ext}")
        data = normalize_svg_bytes(data)
        w, h, _vb = parse_viewbox(data)
        if w <= 0 or h <= 0:
            raise SystemExit(f"FAIL {map_id}: no viewBox in SVG from {url}")
        tile_cfg = probe_tile_meta(maps_data, map_id) if abstract else None
        write_map_folder(
            map_id,
            meta_entry(map_id, bounds, w, h, tile_cfg=tile_cfg),
            data,
            ".svg",
        )
        if abstract:
            remove_png_assets(map_id)

    if not abstract:
        apply_eftarkov_raster_fallback(meta_by_id)

    if abstract:
        for map_id in ("labyrinth",):
            if map_id not in meta_by_id:
                continue
            cfg = LABYRINTH_TILES
            zoom = cfg["zoom"]
            coords = discover_tiles(
                cfg["remote_url"], zoom, cfg["min_bytes"], seed_scan=cfg["scan"]
            )
            if not coords:
                print(f"SKIP {map_id}: no tiles for abstract fallback")
                continue
            min_x = min(x for x, _ in coords)
            max_x = max(x for x, _ in coords)
            min_y = min(y for _, y in coords)
            max_y = max(y for _, y in coords)
            download_tile_assets(map_id, cfg["remote_url"], zoom, coords)
            payload = tile_payload(
                map_id, cfg, zoom, coords, min_x, max_x, min_y, max_y
            )[map_id]
            png, aw, ah, _ = stitch_tiles(map_id, payload)
            write_map_folder(
                map_id,
                meta_entry(map_id, meta_by_id[map_id], aw, ah, tile_cfg=payload),
                png,
                ".png",
            )
            print(f"OK {map_id} raster fallback (no SVG on tarkov.dev)")

    catalog = {"order": CATALOG_ORDER, "default": "woods"}
    CATALOG_OUT.write_text(json.dumps(catalog, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")

    if TILES_TMP.is_dir():
        shutil.rmtree(TILES_TMP)

    for child in MAPS_ROOT.iterdir():
        if child.is_dir() and child.name not in allowed_dirs:
            shutil.rmtree(child)

    svg_n = sum(1 for mid in CATALOG_ORDER if (MAPS_ROOT / mid / "map.svg").is_file())
    png_n = sum(1 for mid in CATALOG_ORDER if (MAPS_ROOT / mid / "map.png").is_file())
    print(f"wrote {svg_n} SVG + {png_n} PNG map folders, catalog.json")


if __name__ == "__main__":
    main()

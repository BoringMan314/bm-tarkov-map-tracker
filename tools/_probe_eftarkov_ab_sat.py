#!/usr/bin/env python3
"""Find eftarkov satellite vs abstract tile roots."""
from __future__ import annotations

import re
import urllib.error
import urllib.request
from io import BytesIO

try:
    from PIL import Image
except ImportError:
    Image = None

UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://api.eftarkov.com/"}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read()


def parse_config(html: str) -> dict:
    folders = [int(x.strip()) for x in re.search(r"totalFolders:\s*\[([^\]]+)\]", html).group(1).split(",")]
    rows = [int(x.strip()) for x in re.search(r"imagesPerFolder:\s*\[([^\]]+)\]", html).group(1).split(",")]
    paths = re.findall(r"'([^']+)'", re.search(r"basePaths:\s*\[([\s\S]*?)\],", html).group(1))
    tile = int(re.search(r"tileSize:\s*(\d+)", html).group(1))
    return {"total_folders": folders, "images_per_folder": rows, "base_paths": paths, "tile_size": tile}


def tile_url(slug: str, base: str, col: int, row: int) -> str:
    base = base.rstrip("/")
    if base.startswith("http"):
        rel = base
    else:
        rel = f"https://api.eftarkov.com/map/{slug}/{base}"
    return f"{rel}/{col}/{row}.webp"


def sample_tile_stats(url: str) -> str:
    try:
        data = fetch(url)
        if len(data) < 80:
            return f"short({len(data)})"
        if Image is None:
            return f"ok({len(data)})"
        img = Image.open(BytesIO(data)).convert("RGBA")
        px = img.getdata()
        colors = len(set(px))
        avg = sum(sum(p[:3]) for p in px) / (len(px) * 3)
        return f"ok {len(data)}b colors={colors} avg={avg:.0f}"
    except urllib.error.HTTPError as e:
        return f"HTTP{e.code}"
    except OSError as e:
        return f"err:{e}"


def main() -> None:
    slug = "factory"
    html = fetch(f"https://api.eftarkov.com/map/{slug}/").decode("utf-8", "replace")
    cfg = parse_config(html)
    level = len(cfg["base_paths"]) - 1
    base = cfg["base_paths"][level]
    print("default max level", level, base)

    # sample center tile
    col = cfg["total_folders"][level] // 2
    row = cfg["images_per_folder"][level] // 2
    print("center", tile_url(slug, base, col, row), sample_tile_stats(tile_url(slug, base, col, row)))

    prefixes = [
        "images4/",
        "images3/",
        "images/",
        "wximages4/",
        "wximages/",
        "satimages4/",
        "satimages/",
        "abstract4/",
        "abstract/",
        "absimages4/",
        "absimages/",
        "vector4/",
        "vector/",
        "images4_sat/",
        "images4_abs/",
        "images4a/",
        "images4b/",
        "images_sat/",
        "images_abs/",
    ]
    print("\nprobe prefixes at center tile:")
    for p in prefixes:
        url = tile_url(slug, p, col, row)
        stat = sample_tile_stats(url)
        if stat.startswith("ok"):
            print(f"  {p:16} {stat}")

    # search html for extra path literals
    extras = sorted(set(re.findall(r"'([a-zA-Z0-9_./:-]*images[a-zA-Z0-9_./-]*/)'", html)))
    print("\nhtml path literals:", extras)


if __name__ == "__main__":
    main()

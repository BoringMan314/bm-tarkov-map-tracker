#!/usr/bin/env python3
"""Find missing factory tiles and try alternate URL patterns."""
from __future__ import annotations

import re
import urllib.error
import urllib.request
from io import BytesIO

try:
    from PIL import Image
except ImportError:
    raise SystemExit("need pillow")

BASE = "https://api.eftarkov.com/map/factory"
UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://api.eftarkov.com/"}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def try_urls(urls: list[str]) -> tuple[str | None, str]:
    last = ""
    for url in urls:
        try:
            data = fetch(url)
            if len(data) < 16:
                last = f"short {len(data)}"
                continue
            Image.open(BytesIO(data))
            return url, "ok"
        except Exception as e:
            last = str(e)[:80]
    return None, last


def main() -> None:
    html = fetch(BASE + "/").decode("utf-8", "replace")
    folders = [int(x.strip()) for x in re.search(r"totalFolders:\s*\[([^\]]+)\]", html).group(1).split(",")]
    rows = [int(x.strip()) for x in re.search(r"imagesPerFolder:\s*\[([^\]]+)\]", html).group(1).split(",")]
    paths = re.findall(r"'([^']+)'", re.search(r"basePaths:\s*\[([\s\S]*?)\],", html).group(1))
    level = len(folders) - 1
    cols, rws, path = folders[level], rows[level], paths[level]
    rel = f"{BASE}/{path.rstrip('/')}"
    print(f"level {level} grid {cols}x{rws} path={path}")

    missing: list[tuple[int, int, str]] = []
    for c in range(cols):
        for r in range(rws):
            urls = [f"{rel}/{c}/{r}.webp", f"{rel}/{c}/{r}.png"]
            hit, err = try_urls(urls)
            if not hit:
                missing.append((c, r, err))

    print(f"missing: {len(missing)}")
    for c, r, err in missing:
        print(f"  col={c} row={r} err={err}")
        alts = [
            f"{rel}/{c+1}/{r}.webp",
            f"{rel}/{c}/{r+1}.webp",
            f"{rel}/{r}/{c}.webp",
            f"{BASE}/images4/{c}/{r}.webp",
        ]
        for alt in alts:
            hit, msg = try_urls([alt])
            if hit:
                print(f"    ALT OK: {hit}")


if __name__ == "__main__":
    main()

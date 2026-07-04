#!/usr/bin/env python3
"""Probe eftarkov.com map pages for satellite vs abstract tile roots."""
from __future__ import annotations

import re
import urllib.error
import urllib.request

UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://api.eftarkov.com/"}
SLUGS = [
    ("factory", "factory"),
    ("customs", "customs"),
    ("reserve", "reserve"),
]


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "replace")


def probe_tile(url: str) -> tuple[bool, int]:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        return True, len(data)
    except urllib.error.HTTPError as e:
        return False, e.code
    except OSError:
        return False, 0


def main() -> None:
    for map_id, slug in SLUGS:
        html = fetch(f"https://api.eftarkov.com/map/{slug}/")
        print(f"\n=== {map_id} ===")
        bp = re.search(r"basePaths:\s*\[([\s\S]*?)\],", html)
        if bp:
            paths = re.findall(r"'([^']+)'", bp.group(1))
            print("basePaths", paths)
        for pat in [
            r"mapStyle[s]?\s*[:=]\s*['\"]?(\w+)",
            r"currentStyle\s*[:=]\s*['\"]?(\w+)",
            r"styleType\s*[:=]\s*['\"]?(\w+)",
            r"satellite",
            r"abstract",
            r"wximages",
            r"vector",
        ]:
            hits = re.findall(pat, html, re.I)
            if hits:
                print(f"  {pat}: {sorted(set(hits))[:8]}")
        # try alternate path prefixes at level 4/3
        level = len(paths) - 1 if bp else 4
        base = paths[level] if bp else "images4/"
        rel = f"https://api.eftarkov.com/map/{slug}/{base.rstrip('/')}"
        alts = [
            base,
            base.replace("images", "wximages"),
            base.replace("images", "satimages"),
            base.replace("images4", "images4_sat"),
            "satellite/",
            "abstract/",
            "wx/",
            "vector/",
            "images_sat/",
            "images_abs/",
            "images4_sat/",
            "images4_abs/",
            "images4a/",
            "images4b/",
        ]
        for alt in sorted(set(alts)):
            ok, n = probe_tile(f"{rel.replace(base.rstrip('/'), alt.rstrip('/'))}/0/0.webp")
            if ok and n > 100:
                print(f"  TILE OK {alt}0/0.webp ({n} bytes)")


if __name__ == "__main__":
    main()

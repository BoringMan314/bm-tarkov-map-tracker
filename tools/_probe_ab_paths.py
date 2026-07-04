#!/usr/bin/env python3
"""Probe eftarkov tile roots for satellite vs abstract variants."""
import urllib.error
import urllib.request

UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://api.eftarkov.com/"}
MAPS = [("factory", 27, 15), ("woods", 40, 40), ("streets", 30, 30)]
PREFIXES = [
    "images4/",
    "abstractimages4/",
    "abstract4/",
    "absimages4/",
    "satelliteimages4/",
    "satimages4/",
    "wximages4/",
    "realimages4/",
    "photoimages4/",
    "images4_satellite/",
    "images4_abstract/",
    "images4abstract/",
    "images4satellite/",
]


from typing import Optional


def ok(url: str) -> Optional[int]:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            if len(data) > 100:
                return len(data)
    except (urllib.error.HTTPError, OSError):
        pass
    return None


def main() -> None:
    for slug, col, row in MAPS:
        print(f"\n=== {slug} ===")
        for prefix in PREFIXES:
            for base in [
                f"https://api.eftarkov.com/map/{slug}/{prefix}",
                f"https://img.eftarkov.com/map/{slug}/{prefix}",
            ]:
                url = f"{base}{col}/{row}.webp"
                n = ok(url)
                if n:
                    print(f"  OK {n:5} {url}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Download exfil marker icons from tarkov.dev (same assets as the interactive map)."""

from __future__ import annotations

import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "internal" / "points" / "icons"
BASE_URL = "https://tarkov.dev/maps/interactive"
USER_AGENT = "bm-tarkov-map-tracker/1.0"

# tarkov.dev faction name -> local embed filename
ICONS = {
    "extract_pmc": "exfil-pmc.png",
    "extract_scav": "exfil-scav.png",
    "extract_shared": "exfil-coop.png",
    "extract_transit": "exfil-transit.png",
}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    if len(data) < 200 or not data.startswith(b"\x89PNG"):
        raise RuntimeError(f"unexpected PNG from {url} ({len(data)} bytes)")
    return data


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for remote, local in ICONS.items():
        url = f"{BASE_URL}/{remote}.png"
        data = fetch(url)
        path = OUT / local
        path.write_bytes(data)
        print(f"wrote {path.relative_to(ROOT)} ({len(data)} bytes) <- {url}")
    print("source: https://tarkov.dev/maps/interactive/")


if __name__ == "__main__":
    main()

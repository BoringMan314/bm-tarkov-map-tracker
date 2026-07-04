from __future__ import annotations

import re
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MAPS = REPO / "maps"
DEV_BASE = "https://raw.githubusercontent.com/the-hideout/tarkov-dev-svg-maps/main"

VIEWBOX_TO_ID = {
    "0 0 2181 1554": "woods",
    "0 0 1062.4827 535.17401": "customs",
    "0 0 130.81831 141.23242": "factory",
    "0 0 605.32395 831.57753": "groundzero",
    "0 0 1127.6852 947.02582": "interchange",
    "0 0 1059.3752 1722.9499": "labs",
    "0 0 1559.5717 1032.4935": "lighthouse",
    "0 0 827.28742 761.16437": "reserve",
    "0 0 1472.7926 1420.5995": "shoreline",
    "0 0 348.92543 488.44792": "streets",
}

DEV_FILES = [
    "Customs.svg",
    "Factory.svg",
    "GroundZero.svg",
    "Interchange.svg",
    "Labs.svg",
    "Lighthouse.svg",
    "Reserve.svg",
    "Shoreline.svg",
    "StreetsOfTarkov.svg",
    "Terminal.svg",
    "Woods.svg",
]


def fingerprint(data: bytes) -> tuple[str, bool]:
    head = data[:8000].decode("utf-8", "replace")
    m = re.search(r'viewBox="([^"]+)"', head)
    vb = m.group(1) if m else "?"
    png = "data:image/png" in head
    content = VIEWBOX_TO_ID.get(vb, "?")
    if png and vb == "0 0 2181 1554":
        content = "woods"
    return content, png


def fetch_dev(name: str) -> bytes:
    url = f"{DEV_BASE}/{name}"
    req = urllib.request.Request(url, headers={"User-Agent": "bm-tarkov-map-tracker"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def main() -> None:
    print("=== repo maps/ (filename vs content) ===")
    for path in sorted(MAPS.glob("*.svg")):
        data = path.read_bytes()
        content, png = fingerprint(data)
        ok = path.stem == content or (path.stem == "terminal" and content == "customs")
        if path.stem == "woods" and content == "woods" and png:
            ok = True
        status = "OK" if ok else f"WRONG (content={content})"
        print(f"  {path.name:14} {len(data):8} bytes  content={content:12}  {status}")

    print("\n=== tarkov-dev-svg-maps upstream (remote filename vs content) ===")
    for name in DEV_FILES:
        data = fetch_dev(name)
        content, png = fingerprint(data)
        print(f"  {name:22} {len(data):8} bytes  content={content:12}  png={png}")


if __name__ == "__main__":
    main()

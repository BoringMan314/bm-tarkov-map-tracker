#!/usr/bin/env python3
"""Extract exfil POI icons (fS/pS/mS) from reference frontend bundle."""

from __future__ import annotations

import base64
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS = ROOT / "參考" / "rebuild" / "map-sources" / "frontend_dist" / "assets" / "index-CYNNpvnS.js"
OUT = ROOT / "internal" / "points" / "icons"

MAP = {
    "fS": "exfil-pmc.png",
    "pS": "exfil-scav.png",
    "mS": "exfil-coop.png",
}


def main() -> None:
    text = JS.read_text(encoding="utf-8", errors="replace")
    OUT.mkdir(parents=True, exist_ok=True)

    for var, out_name in MAP.items():
        m = re.search(rf'{var}="(data:image/png;base64,[^"]+)"', text)
        if not m:
            print(f"skip {var}: not found")
            continue
        b64 = m.group(1).split(",", 1)[1]
        data = base64.b64decode(b64)
        path = OUT / out_name
        path.write_bytes(data)
        print(f"wrote {path.relative_to(ROOT)} ({len(data)} bytes)")


if __name__ == "__main__":
    main()

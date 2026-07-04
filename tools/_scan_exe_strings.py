#!/usr/bin/env python3
import re
from pathlib import Path

data = Path("參考/TarkovMapTracker.exe").read_bytes()
keys = (
    "screenshot",
    "extract data",
    "player-change",
    "watcher",
    "global.json",
    "Quaternion",
    "Location",
    "Position",
    "tEXt",
    "iTXt",
    "png",
)
seen = set()
for m in re.finditer(rb"[\x20-\x7e]{8,220}", data):
    s = m.group().decode("ascii", "replace")
    low = s.lower()
    if any(k.lower() in low for k in keys):
        if "github" in s or "frontend/dist" in s:
            continue
        if s in seen:
            continue
        seen.add(s)
        print(s)

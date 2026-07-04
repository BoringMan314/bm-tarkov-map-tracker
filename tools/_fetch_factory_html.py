#!/usr/bin/env python3
import re
import urllib.request
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://api.eftarkov.com/"}
out = Path(__file__).resolve().parent / "_factory_page.html"
for attempt in range(5):
    try:
        data = urllib.request.urlopen(
            urllib.request.Request("https://api.eftarkov.com/map/factory/", headers=UA),
            timeout=60,
        ).read()
        out.write_bytes(data)
        print("saved", len(data))
        break
    except Exception as e:
        print("attempt", attempt, e)
html = out.read_text("utf-8", errors="replace")
for m in re.finditer(r"(images\d*|loadTile|tileSize|totalFolders|\.webp|folderIndex|imageIndex)[^\n]{0,120}", html):
    print(m.group(0)[:140])

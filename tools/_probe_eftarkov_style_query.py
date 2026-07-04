#!/usr/bin/env python3
import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://api.eftarkov.com/"}


def cfg(url: str) -> None:
    html = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode(
        "utf-8", "replace"
    )
    bp = re.search(r"basePaths:\s*\[([\s\S]*?)\],", html)
    tf = re.search(r"totalFolders:\s*\[([^\]]+)\]", html)
    ip = re.search(r"imagesPerFolder:\s*\[([^\]]+)\]", html)
    paths = re.findall(r"'([^']+)'", bp.group(1)) if bp else []
    print(url)
    print("  basePaths", paths)
    print("  totalFolders", tf.group(1) if tf else None)
    print("  imagesPerFolder", ip.group(1) if ip else None)


for q in ["", "?style=abstract", "?style=satellite", "?style=sat", "?map=satellite", "?type=abstract"]:
    cfg(f"https://api.eftarkov.com/map/factory/{q}")

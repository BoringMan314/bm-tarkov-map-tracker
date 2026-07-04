#!/usr/bin/env python3
import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://api.eftarkov.com/"}
html = urllib.request.urlopen(
    urllib.request.Request("https://api.eftarkov.com/map/lighthouse/", headers=UA),
    timeout=60,
).read().decode("utf-8", "replace")
folders = re.search(r"totalFolders:\s*\[([^\]]+)\]", html)
per = re.search(r"imagesPerFolder:\s*\[([^\]]+)\]", html)
paths = re.search(r"basePaths:\s*\[([\s\S]*?)\],", html)
print("folders", folders.group(1) if folders else None)
print("per", per.group(1) if per else None)
bps = re.findall(r"'([^']+)'", paths.group(1)) if paths else []
print("paths", bps)
if bps:
    lv = len(bps) - 1
    url = f"https://api.eftarkov.com/map/lighthouse/{bps[lv]}/0/0.webp"
    r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30)
    print("tile ok", url, r.headers.get("Content-Length"))

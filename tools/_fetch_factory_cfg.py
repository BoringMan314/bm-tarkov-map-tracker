#!/usr/bin/env python3
import re
import urllib.request

url = "https://api.eftarkov.com/map/factory/"
html = urllib.request.urlopen(
    urllib.request.Request(url, headers={"User-Agent": "bm/1"}), timeout=60
).read().decode("utf-8", "replace")

folders = re.search(r"totalFolders:\s*\[([^\]]+)\]", html)
per = re.search(r"imagesPerFolder:\s*\[([^\]]+)\]", html)
paths = re.search(r"basePaths:\s*\[([\s\S]*?)\],", html)
tile = re.search(r"tileSize:\s*(\d+)", html)

print("totalFolders", [int(x.strip()) for x in folders.group(1).split(",")])
print("imagesPerFolder", [int(x.strip()) for x in per.group(1).split(",")])
print("basePaths", re.findall(r"'([^']+)'", paths.group(1)))
print("tileSize", tile.group(1) if tile else None)

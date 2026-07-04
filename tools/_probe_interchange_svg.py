#!/usr/bin/env python3
import re
import urllib.request

UA = {"User-Agent": "bm-tarkov-map-tracker/1.0"}
data = urllib.request.urlopen(
    urllib.request.Request("https://assets.tarkov.dev/maps/svg/Interchange.svg", headers=UA)
).read().decode("utf-8", "replace")
print("viewBox", re.search(r'viewBox="([^"]+)"', data).group(1))
for m in re.finditer(r'id="([^"]+)"', data):
    s = m.group(1)
    if "loor" in s or "Level" in s or "Structure" in s:
        print(s)

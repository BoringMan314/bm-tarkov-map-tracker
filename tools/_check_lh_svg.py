#!/usr/bin/env python3
import re
import urllib.request

UA = {"User-Agent": "bm"}
data = urllib.request.urlopen(
    urllib.request.Request("https://assets.tarkov.dev/maps/svg/Lighthouse.svg", headers=UA),
    timeout=60,
).read().decode("utf-8", "replace")
print("len", len(data))
for pat in ["image", "jpeg", "png", "base64", "href"]:
    print(pat, data.lower().count(pat))
hrefs = re.findall(r'(?:xlink:)?href="([^"]+)"', data)
print("hrefs", len(hrefs), hrefs[:10])

#!/usr/bin/env python3
import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://api.eftarkov.com/"}
html = urllib.request.urlopen(
    urllib.request.Request("https://api.eftarkov.com/map/customs/", headers=UA), timeout=30
).read().decode("utf-8", "replace")
open("tools/_customs_live.html", "w", encoding="utf-8").write(html)
print("len", len(html))
for kw in ["卫星", "抽象", "satellite", "abstract", "wx", "vector", "mapStyle", "styleType", "layerMode", "imageType", "basePaths2", "configs"]:
    if kw in html or kw.lower() in html.lower():
        print("has", kw)
# all string literals containing 'image'
refs = sorted(set(re.findall(r"'([^']*image[^']*)'", html, re.I)))
print("image strings", refs[:30])
refs2 = sorted(set(re.findall(r'"([^"]*image[^"]*)"', html, re.I)))
print("image strings2", refs2[:30])
# button labels
for m in re.finditer(r"<button[^>]*>([^<]+)</button>", html):
    t = m.group(1).strip()
    if t:
        print("btn", t[:40])

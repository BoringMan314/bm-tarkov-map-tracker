#!/usr/bin/env python3
import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://api.eftarkov.com/"}
url = "https://api.eftarkov.com/map/factory/"
html = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode("utf-8", "replace")
print("html bytes", len(html))
folders = re.search(r"totalFolders:\s*\[([^\]]+)\]", html)
per = re.search(r"imagesPerFolder:\s*\[([^\]]+)\]", html)
if folders and per:
    tf = [int(x.strip()) for x in folders.group(1).split(",")]
    ip = [int(x.strip()) for x in per.group(1).split(",")]
    total = sum(a * b for a, b in zip(tf, ip))
    print("levels", len(tf), "grid", list(zip(tf, ip)), "slot count", total)
imgs = re.findall(r"https?://[^\"'\s>]+\.(?:png|webp|jpg)", html)
print("direct image urls in html", len(set(imgs)))
for u in sorted(set(imgs))[:15]:
    print(" ", u[:120])

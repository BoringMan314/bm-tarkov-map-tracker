#!/usr/bin/env python3
import re
import urllib.request
from io import BytesIO

try:
    from PIL import Image
except ImportError:
    raise SystemExit("need pillow")

BASE = "https://api.eftarkov.com/map/factory"
html = urllib.request.urlopen(
    urllib.request.Request(f"{BASE}/", headers={"User-Agent": "bm/1"}), timeout=60
).read().decode("utf-8", "replace")

folders = [int(x.strip()) for x in re.search(r"totalFolders:\s*\[([^\]]+)\]", html).group(1).split(",")]
rows = [int(x.strip()) for x in re.search(r"imagesPerFolder:\s*\[([^\]]+)\]", html).group(1).split(",")]
paths = re.findall(r"'([^']+)'", re.search(r"basePaths:\s*\[([\s\S]*?)\],", html).group(1))

for level in range(len(folders)):
    cols, rws, path = folders[level], rows[level], paths[level]
    rel = f"{BASE}/{path.rstrip('/')}"
    ok = 0
    for c in range(cols):
        for r in range(rws):
            for ext in (".webp", ".png"):
                url = f"{rel}/{c}/{r}{ext}"
                try:
                    data = urllib.request.urlopen(
                        urllib.request.Request(url, headers={"User-Agent": "bm/1"}), timeout=20
                    ).read()
                    if len(data) >= 80:
                        img = Image.open(BytesIO(data)).convert("RGBA")
                        if len(set(img.getdata())) >= 5:
                            ok += 1
                            break
                except OSError:
                    pass
    print(f"level {level}: {ok}/{cols*rws} tiles, grid {cols}x{rws}, path {path}")

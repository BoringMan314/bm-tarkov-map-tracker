#!/usr/bin/env python3
import urllib.error
import urllib.request
from io import BytesIO

from PIL import Image

UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://api.eftarkov.com/"}
COL, ROW = 38, 0
BASE = "https://api.eftarkov.com/map/factory"

candidates = [
    f"{BASE}/images4/{COL}/{ROW}.webp",
    f"{BASE}/images4/{COL}/{ROW}.png",
    f"images4/{COL}/{ROW}.webp",
    f"{BASE}/images4/{COL+1}/{ROW}.webp",
    f"{BASE}/images4/{COL}/{ROW+1}.webp",
    f"{BASE}/images4/{ROW}/{COL}.webp",
    f"{BASE}/images4/{COL:02d}/{ROW}.webp",
    f"{BASE}/images4/{COL}/{ROW:02d}.webp",
]

for url in candidates:
    try:
        if not url.startswith("http"):
            url = f"{BASE}/{url}"
        data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20).read()
        img = Image.open(BytesIO(data))
        print(f"OK {len(data)} bytes {img.size} {url}")
    except Exception as e:
        print(f"FAIL {url[:90]} -> {e}")

# neighbors for comparison
for nc, nr in [(37, 0), (39, 0), (38, 1)]:
    url = f"{BASE}/images4/{nc}/{nr}.webp"
    try:
        data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20).read()
        print(f"neighbor OK ({nc},{nr}) {len(data)} bytes")
    except Exception as e:
        print(f"neighbor FAIL ({nc},{nr}) {e}")

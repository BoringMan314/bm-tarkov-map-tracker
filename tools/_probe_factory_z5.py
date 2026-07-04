#!/usr/bin/env python3
import urllib.request
from io import BytesIO
from PIL import Image

UA = {"User-Agent": "bm-tarkov-map-tracker/1.0"}
URL = "https://assets.tarkov.dev/maps/factory/main/5/{x}/{y}.png"


def ok(x, y):
    try:
        d = urllib.request.urlopen(urllib.request.Request(URL.format(x=x, y=y), headers=UA), timeout=20).read()
        if len(d) < 4000:
            return False
        return Image.open(BytesIO(d)).convert("RGBA").getbbox() is not None
    except OSError:
        return False


for row in range(22, 31):
    cols = [x for x in range(32) if ok(x, row)]
    print(f"row {row}: {len(cols)} cols {cols[:20]}{'...' if len(cols)>20 else ''}")

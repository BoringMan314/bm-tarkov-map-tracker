#!/usr/bin/env python3
import json
import urllib.request

url = "https://raw.githubusercontent.com/the-hideout/tarkov-dev/main/src/data/maps.json"
data = json.loads(urllib.request.urlopen(url, timeout=30).read())
for entry in data:
    if entry.get("normalizedName") != "interchange":
        continue
    for v in entry.get("maps") or []:
        if v.get("key") == "interchange":
            keys = [
                "projection",
                "svgPath",
                "svgLayer",
                "svgBounds",
                "bounds",
                "tilePath",
                "layers",
                "transform",
                "coordinateRotation",
            ]
            print(json.dumps({k: v.get(k) for k in keys if k in v}, indent=2))

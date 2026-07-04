#!/usr/bin/env python3
"""Diagnose interchange DEV A satellite."""
import json
import math
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
meta = json.loads((ROOT / "internal/maps_tarkov.dev/interchange/meta.json").read_text())
pmc = json.loads((ROOT / "internal/points/exfil/pmc.json").read_text()).get("interchange", [])
png = ROOT / "internal/maps_tarkov.dev/interchange/map.png"
UA = "bm-tarkov-map-tracker/1.0"
TILE = "https://assets.tarkov.dev/maps/interchange/main/{z}/{x}/{y}.png"


def fetch_maps():
    for url in (
        "https://raw.githubusercontent.com/the-hideout/tarkov-dev/main/src/data/maps.json",
        "https://api.github.com/repos/the-hideout/tarkov-dev/contents/src/data/maps.json",
    ):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            raw = urllib.request.urlopen(req, timeout=60).read()
            if b"content" in raw[:80]:
                import base64

                raw = base64.b64decode(json.loads(raw)["content"])
            return json.loads(raw)
        except Exception:
            continue
    raise SystemExit("no maps.json")


def variant(maps):
    for e in maps:
        if e.get("normalizedName") != "interchange":
            continue
        for v in e.get("maps") or []:
            if v.get("key") == "interchange":
                return v
    raise SystemExit("no variant")


def rot_ll(gz, gx, r):
    if not r:
        return gz, gx
    rad = math.radians(r)
    c, s = math.cos(rad), math.sin(rad)
    return gx * s + gz * c, gx * c - gz * s


def crs_xy(gx, gz, t, rot, y_neg=False):
    lat, lng = rot_ll(gz, gx, rot)
    cx = t[0] * lng + t[1]
    cy = (-t[2] if y_neg else t[2]) * lat + t[3] if not y_neg else (-t[2]) * lat + t[3]
    if y_neg:
        cy = (-t[2]) * lat + t[3]
    else:
        cy = t[2] * (-lat) + t[3]  # app.js: scaleY*-lat
    return cx, cy


def layer_pt(gx, gz, t, rot, z, ymode):
    if ymode == "app":
        lat, lng = rot_ll(gz, gx, rot)
        cx = t[0] * lng + t[1]
        cy = (-t[2]) * (-lat) + t[3]
    elif ymode == "neg":
        lat, lng = rot_ll(gz, gx, rot)
        cx = t[0] * lng + t[1]
        cy = (-t[2]) * lat + t[3]
    else:
        cx, cy = crs_xy(gx, gz, t, rot)
    f = 2**z
    return cx * f, cy * f


def probe_zoom(z, scan=40):
    def one(xy):
        x, y = xy
        url = TILE.format(z=z, x=x, y=y)
        try:
            d = urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": UA}), timeout=15
            ).read()
            return (x, y) if len(d) >= 4000 else None
        except Exception:
            return None

    jobs = [(x, y) for x in range(scan) for y in range(scan)]
    hits = []
    with ThreadPoolExecutor(max_workers=24) as pool:
        for h in pool.map(one, jobs):
            if h:
                hits.append(h)
    if not hits:
        return
    xs, ys = zip(*hits)
    print(
        f"z={z} tiles={len(hits)} bbox=({min(xs)},{min(ys)})-({max(xs)},{max(ys)}) "
        f"grid={(max(xs)-min(xs)+1)}x{(max(ys)-min(ys)+1)}"
    )


print("meta zoom", meta["tile_zoom"], "size", meta["width"], meta["height"])
print("bounds", meta["xmin"], meta["xmax"], meta["zmin"], meta["zmax"])
v = variant(fetch_maps())
print("maps.json bounds", v.get("bounds"), "rotation", v.get("coordinateRotation"))

if png.is_file():
    im = Image.open(png).convert("RGBA")
    print("PNG", im.size, "content bbox", im.getbbox())
    # sample tile grid 8x8 center
    w, h = im.size
    tw, th = w // 256, h // 256
    holes = 0
    for ty in range(min(th, 20)):
        for tx in range(min(tw, 20)):
            p = im.getpixel((tx * 256 + 128, ty * 256 + 128))
            if p[3] < 128 or sum(p[:3]) < 30:
                holes += 1
    print(f"sample 20x20 center-ish holes {holes}/400")

    t = meta["transform"]
    rot = meta["coordinates_rotation"]
    z = int(meta["tile_zoom"])
    ts = meta["tile_size"]
    b = dict(
        minX=meta["tile_min_x"] * ts,
        minY=meta["tile_min_y"] * ts,
        maxX=(meta["tile_max_x"] + 1) * ts,
        maxY=(meta["tile_max_y"] + 1) * ts,
    )

    for ymode in ("app", "neg"):
        hits = 0
        print(f"\nmarkers y={ymode}:")
        for p in pmc[:8]:
            gx, gz = p["coordinates"]
            lx, ly = layer_pt(gx, gz, t, rot, z, ymode)
            x = (lx - b["minX"]) / (b["maxX"] - b["minX"]) * w
            y = (ly - b["minY"]) / (b["maxY"] - b["minY"]) * h
            ok = False
            if 0 <= x < w and 0 <= y < h:
                r, g, b0, a = im.getpixel((int(x), int(y)))
                ok = a > 128 and (r + g + b0) > 40
                hits += ok
            print(f"  {p.get('name','?'):22} ({int(x)},{int(y)}) ok={ok}")
        print("  hits", hits, "/", min(8, len(pmc)))

print("\nProbe zooms:")
for z in (6, 5, 4, 3):
    probe_zoom(z, scan=24 if z >= 5 else 16)

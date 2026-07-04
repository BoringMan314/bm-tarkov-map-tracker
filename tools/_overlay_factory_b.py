#!/usr/bin/env python3
"""Overlay exfil points on DEV B factory SVG."""
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
meta = json.loads((ROOT / "internal/maps_tarkov.dev_B/factory/meta.json").read_text())
pmc = json.loads((ROOT / "internal/points/exfil/pmc.json").read_text())["factory"]
svg_path = ROOT / "internal/maps_tarkov.dev_B/factory/map.svg"
t = meta["transform"]
rot = int(meta["coordinates_rotation"])


def apply_rot(gz, gx, r):
    rad = math.radians(r)
    c, s = math.cos(rad), math.sin(rad)
    return gx * s + gz * c, gx * c - gz * s


def game_to_crs(gx, gz):
    lat, lng = apply_rot(gz, gx, rot)
    return t[0] * lng + t[1], -t[2] * (-lat) + t[3]


def svg_px(gx, gz, m):
    xmin, xmax, zmin, zmax = m["xmin"], m["xmax"], m["zmin"], m["zmax"]
    sw = game_to_crs(xmin, zmin)
    ne = game_to_crs(xmax, zmax)
    pt = game_to_crs(gx, gz)
    iw, ih = m["width"], m["height"]
    return (
        (pt[0] - sw[0]) / (ne[0] - sw[0]) * iw,
        (pt[1] - ne[1]) / (sw[1] - ne[1]) * ih,
    )


float_meta = dict(meta)
float_meta.update(xmin=-65.5, xmax=77.0, zmin=-64.5, zmax=67.4)

text = svg_path.read_text(encoding="utf-8")
markers = []
for p in pmc:
    gx, gz = p["coordinates"]
    ix, iy = svg_px(gx, gz, meta)
    fx, fy = svg_px(gx, gz, float_meta)
    markers.append((p["name"], ix, iy, fx, fy))
    print(f"{p['name']:18} int=({ix:5.1f},{iy:5.1f}) float=({fx:5.1f},{fy:5.1f})")

circles = []
for name, ix, iy, _, _ in markers:
    circles.append(
        f'<circle cx="{ix:.2f}" cy="{iy:.2f}" r="1.5" fill="#ffcc00" stroke="#000" stroke-width="0.2">'
        f'<title>{name}</title></circle>'
    )

if "</svg>" in text:
    out = text.replace("</svg>", "\n  <g id=\"debug-markers\">\n    " + "\n    ".join(circles) + "\n  </g>\n</svg>")
    out_path = ROOT / "tools" / "_factory_b_overlay.svg"
    out_path.write_text(out, encoding="utf-8")
    print("saved", out_path)

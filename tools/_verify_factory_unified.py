import json, math
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
meta_a = json.loads((ROOT/"internal/maps_tarkov.dev/factory/meta.json").read_text())
meta_b = json.loads((ROOT/"internal/maps_tarkov.dev_B/factory/meta.json").read_text())
pmc = json.loads((ROOT/"internal/points/exfil/pmc.json").read_text())["factory"]
t = meta_a["transform"]; rot = 90; F = 2**4

def rot_ll(gz, gx, r):
    rad = math.radians(r); c, s = math.cos(rad), math.sin(rad)
    return gx*s+gz*c, gx*c-gz*s

def layer_pt(gx, gz, meta):
    lat, lng = rot_ll(gz, gx, rot)
    cx, cy = t[0]*lng+t[1], (-t[2])*lat+t[3]
    return cx*F, cy*F

def norm_pt(gx, gz, meta, iw, ih):
    ts = meta["tile_size"]
    b = dict(minX=meta["tile_min_x"]*ts, minY=meta["tile_min_y"]*ts,
             maxX=(meta["tile_max_x"]+1)*ts, maxY=(meta["tile_max_y"]+1)*ts)
    lx, ly = layer_pt(gx, gz, meta)
    nx = (lx-b["minX"])/(b["maxX"]-b["minX"])
    ny = (ly-b["minY"])/(b["maxY"]-b["minY"])
    return nx*iw, ny*ih, nx, ny

print("A vs B: same nx,ny => same relative position")
for p in pmc:
    gx, gz = p["coordinates"]
    ax, ay, nx, ny = norm_pt(gx, gz, meta_a, meta_a["width"], meta_a["height"])
    bx, by, nx2, ny2 = norm_pt(gx, gz, meta_b, meta_b["width"], meta_b["height"])
    same = abs(nx-nx2)<1e-9 and abs(ny-ny2)<1e-9
    print(f"{p['name']:18} A=({nx:.3f},{ny:.3f}) B=({nx2:.3f},{ny2:.3f}) match={same}")

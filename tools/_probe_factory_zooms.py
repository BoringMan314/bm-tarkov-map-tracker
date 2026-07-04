#!/usr/bin/env python3
import json, math, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
meta = json.loads((ROOT/"internal/maps_tarkov.dev/factory/meta.json").read_text())
pmc = json.loads((ROOT/"internal/points/exfil/pmc.json").read_text())["factory"]
t = meta["transform"]; rot = int(meta["coordinates_rotation"])
TILE = "https://assets.tarkov.dev/maps/factory/main/{z}/{x}/{y}.png"

def apply_rot(gz,gx,r):
    rad=math.radians(r); c,s=math.cos(rad),math.sin(rad)
    return gx*s+gz*c, gx*c-gz*s

def layer_pt(gx,gz,z):
    lat,lng=apply_rot(gz,gx,rot)
    cx,cy=t[0]*lng+t[1], -t[2]*(-lat)+t[3]
    f=2**z; return cx*f,cy*f

def fetch_head(z,x,y):
    url=TILE.format(z=z,x=x,y=y)
    req=urllib.request.Request(url,method='HEAD',headers={'User-Agent':'bm'})
    try:
        with urllib.request.urlopen(req,timeout=10) as r:
            return r.status,int(r.headers.get('Content-Length',0))
    except Exception as e:
        return getattr(e,'code','err'),0

for Z in (4,5,6):
    xs,ys=[],[]
    for gx,gz in [(-65,67),(77,-64),(-65,-64),(77,67)]:
        lx,ly=layer_pt(gx,gz,Z); xs.append(lx); ys.append(ly)
    tx0,tx1=int(min(xs)//256),int(max(xs)//256)
    ty0,ty1=int(min(ys)//256),int(max(ys)//256)
    print(f"z={Z} need tiles x={tx0}..{tx1} y={ty0}..{ty1} ({tx1-tx0+1}x{ty1-ty0+1})")
    for p in pmc:
        lx,ly=layer_pt(*p['coordinates'],Z)
        print(f"  {p['name']:18} tile=({int(lx//256)},{int(ly//256)}) layer=({lx:.0f},{ly:.0f})")

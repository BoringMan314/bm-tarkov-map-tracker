#!/usr/bin/env python3
import json, math
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parent.parent
meta = json.loads((ROOT/"internal/maps_tarkov.dev/factory/meta.json").read_text())
pmc = json.loads((ROOT/"internal/points/exfil/pmc.json").read_text())["factory"]
im = Image.open(ROOT/"internal/maps_tarkov.dev/factory/map.png").convert("RGBA")
t=meta["transform"]; rot=90; F=2**4; iw=ih=4096

def rot_ll(gz,gx,r):
 rad=math.radians(r); c,s=math.cos(rad),math.sin(rad)
 return gx*s+gz*c,gx*c-gz*s

def px(gx,gz):
 lat,lng=rot_ll(gz,gx,rot)
 cx=t[0]*lng+t[1]; cy=(-t[2])*lat+t[3]
 lx,ly=cx*F,cy*F
 return lx/4096*iw, ly/4096*ih

for p in pmc:
 x,y=px(*p["coordinates"])
 ok=0<=x<4096 and 0<=y<4096
 a=im.getpixel((int(x),int(y))) if ok else None
 hit=a and a[3]>128 and sum(a[:3])>40
 print(f"{p['name']:18} ({x:6.0f},{y:6.0f}) hit={hit} rgb={a[:3] if a else 'OOB'}")

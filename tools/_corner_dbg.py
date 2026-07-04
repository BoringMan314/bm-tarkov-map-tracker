import json, math
from pathlib import Path
meta = json.loads(Path("internal/maps_tarkov.dev/factory/meta.json").read_text())
t = meta["transform"]; ROT = meta["coordinates_rotation"]; Z=4; f=2**4
xmin,xmax,zmin,zmax = meta["xmin"], meta["xmax"], meta["zmin"], meta["zmax"]

def apply_rot(gz,gx,r):
    if not r: return gz,gx
    rad=math.radians(r); c,s=math.cos(rad),math.sin(rad)
    return gz*s+gx*c, gz*c-gx*s

def layer(gx,gz):
    lat,lng=apply_rot(gz,gx,ROT)
    sx,mx,sy,mz=t[0],t[1],t[2]*-1,t[3]
    return (sx*lng+mx)*f, (sy*lat+mz)*f

corners=[(xmin,zmax),(xmax,zmin),(xmin,zmin),(xmax,zmax)]
for c in corners:
    print(c, layer(*c))
pts=[layer(*c) for c in corners]
print('minmax', min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))

import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
pmc = json.loads((ROOT / "internal/points/exfil/pmc.json").read_text())["factory"]
meta = dict(
    xmin=-65.5, xmax=77.0, zmin=-64.5, zmax=67.4,
    coordinates_rotation=90, width=130.81831, height=141.23242,
)
span_x = meta["xmax"] - meta["xmin"]
span_z = meta["zmax"] - meta["zmin"]
print("=== normalizedGameCoords rot=90 (original app style) ===")
for p in pmc:
    gx, gz = p["coordinates"]
    u = (meta["zmax"] - gz) / span_z
    v = (gx - meta["xmin"]) / span_x
    x, y = u * meta["width"], v * meta["height"]
    print(f"{p['name']:18} ({x:5.1f},{y:5.1f})")

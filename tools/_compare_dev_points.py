#!/usr/bin/env python3
"""Compare our exfil/transit data vs tarkov.dev GraphQL."""

from __future__ import annotations

import json
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXFIL = ROOT / "internal" / "points" / "exfil"
GRAPHQL = "https://api.tarkov.dev/graphql"
UA = {"User-Agent": "bm-tarkov-map-tracker/1.0", "Content-Type": "application/json"}

MAP_ALIASES = {
    "streets-of-tarkov": "streets",
    "ground-zero": "groundzero",
    "the-lab": "labs",
    "the-labyrinth": "labyrinth",
}

CATALOG = [
    "factory", "groundzero", "interchange", "lighthouse", "labs", "terminal",
    "customs", "shoreline", "labyrinth", "reserve", "woods", "streets",
]

QUERY = """
query {
  maps {
    normalizedName
    extracts { id name faction position { x z } }
    transits { id description position { x z } }
  }
}
"""


def mid(normalized: str) -> str | None:
    key = (normalized or "").strip().lower().replace("-", "")
    for a, b in MAP_ALIASES.items():
        if key == a.replace("-", ""):
            key = b
    if key in CATALOG:
        return key
    return None


def load_ours() -> dict[str, dict[str, list]]:
    out = {"pmc": {}, "scav": {}, "coop": {}, "transit": {}}
    out["pmc"] = json.loads((EXFIL / "pmc.json").read_text(encoding="utf-8"))
    out["scav"] = json.loads((EXFIL / "scav.json").read_text(encoding="utf-8"))
    out["coop"] = json.loads((EXFIL / "coop.json").read_text(encoding="utf-8"))
    out["transit"] = json.loads((EXFIL / "transit.json").read_text(encoding="utf-8"))
    return out


def fetch_dev() -> dict[str, dict[str, list]]:
    body = json.dumps({"query": QUERY}).encode()
    req = urllib.request.Request(GRAPHQL, data=body, headers=UA)
    data = json.loads(urllib.request.urlopen(req, timeout=60).read())
    out: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for m in data["data"]["maps"]:
        map_id = mid(m["normalizedName"])
        if not map_id:
            continue
        for ex in m.get("extracts") or []:
            f = (ex.get("faction") or "shared").lower()
            if f == "shared":
                bucket = "coop"
            elif f in ("pmc", "scav"):
                bucket = f
            else:
                bucket = f"unknown:{f}"
            pos = ex.get("position") or {}
            out[map_id][bucket].append({
                "id": ex["id"],
                "name": ex["name"],
                "coordinates": [pos.get("x"), pos.get("z")],
            })
        for tr in m.get("transits") or []:
            pos = tr.get("position") or {}
            out[map_id]["transit"].append({
                "id": tr["id"],
                "name": tr.get("description", ""),
                "coordinates": [pos.get("x"), pos.get("z")],
            })
    return out


def key(row: dict) -> tuple:
    return (row.get("id", ""), row.get("name", ""))


def compare_lists(dev_rows: list, our_rows: list) -> dict:
    dev_by_id = {r["id"]: r for r in dev_rows}
    our_by_id = {r["id"]: r for r in our_rows}
    return {
        "dev_only": [dev_by_id[i] for i in dev_by_id if i not in our_by_id],
        "our_only": [our_by_id[i] for i in our_by_id if i not in dev_by_id],
        "coord_diff": [
            {"id": i, "name": dev_by_id[i]["name"], "dev": dev_by_id[i]["coordinates"], "ours": our_by_id[i]["coordinates"]}
            for i in dev_by_id
            if i in our_by_id and dev_by_id[i]["coordinates"] != our_by_id[i]["coordinates"]
        ],
    }


def main() -> None:
    ours = load_ours()
    dev = fetch_dev()

    for map_id in CATALOG:
        issues = []
        for kind, dev_key in [("pmc", "pmc"), ("scav", "scav"), ("coop", "coop"), ("transit", "transit")]:
            dev_rows = dev.get(map_id, {}).get(dev_key, [])
            our_rows = ours[kind].get(map_id, [])
            if len(dev_rows) != len(our_rows):
                issues.append(f"{kind}: count dev={len(dev_rows)} ours={len(our_rows)}")
            cmp = compare_lists(dev_rows, our_rows)
            if cmp["dev_only"]:
                issues.append(f"{kind} dev_only: {[r['name'] for r in cmp['dev_only']]}")
            if cmp["our_only"]:
                issues.append(f"{kind} our_only: {[r['name'] for r in cmp['our_only']]}")
            if cmp["coord_diff"]:
                issues.append(f"{kind} coord_diff: {len(cmp['coord_diff'])}")
        if issues:
            print(f"\n=== {map_id} ===")
            for line in issues:
                print(f"  {line}")

    print("\n=== factory detail ===")
    for kind in ("pmc", "scav", "transit", "coop"):
        print(f"\n-- {kind} dev --")
        for r in dev.get("factory", {}).get(kind, []):
            print(f"  {r['name']}: {r['coordinates']}")
        print(f"-- {kind} ours --")
        for r in ours[kind].get("factory", []):
            print(f"  {r['name']}: {r['coordinates']}")


if __name__ == "__main__":
    main()

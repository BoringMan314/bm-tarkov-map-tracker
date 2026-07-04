#!/usr/bin/env python3
"""Sync exfil markers and map bounds from tarkov.dev into internal/."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "internal" / "points" / "exfil"
MAPS_DIR = ROOT / "internal" / "maps_tarkov.dev"

GRAPHQL_URL = "https://api.tarkov.dev/graphql"
MAPS_JSON_URL = "https://raw.githubusercontent.com/the-hideout/tarkov-dev/main/src/data/maps.json"
USER_AGENT = "bm-tarkov-map-tracker/1.0"

DISPLAY_NAMES = {
    "woods": "Woods",
    "customs": "Customs",
    "factory": "Factory",
    "groundzero": "Ground Zero",
    "interchange": "Interchange",
    "lighthouse": "Lighthouse",
    "labs": "Labs",
    "reserve": "Reserve",
    "shoreline": "Shoreline",
    "streets": "Streets of Tarkov",
    "labyrinth": "Labyrinth",
}

DISPLAY_ROTATION: dict[str, int] = {
    "reserve": -15,
}

CATALOG_ORDER = [
    "factory",
    "groundzero",
    "interchange",
    "lighthouse",
    "labs",
    "customs",
    "shoreline",
    "labyrinth",
    "reserve",
    "woods",
    "streets",
]

MAP_ALIASES = {
    "streets-of-tarkov": "streets",
    "ground-zero": "groundzero",
    "the-lab": "labs",
    "the-labyrinth": "labyrinth",
}

FACTION_FILES = {
    "pmc": "pmc.json",
    "scav": "scav.json",
    "shared": "coop.json",
}

# Woods shared extracts: tarkov.dev lists UN Roadblock / Outskirts under pmc+scav, not shared.
WOODS_COOP_EXTRACT_NAMES = frozenset({"UN Roadblock", "Outskirts"})
WOODS_COOP_PREFERRED_ID = {
    "UN Roadblock": "e6fd5a732d1fd0662221d75f31f0e2e8021ef4ca",
    "Outskirts": "e70d314d202e673b96671e810e54cef5657c16ca",
}

# tarkov.dev LanguageCode values used for localized extract names
NAME_LANGS = ["en", "zh", "ja"]

QUERY = """
query ($lang: LanguageCode) {
  maps(lang: $lang) {
    normalizedName
    extracts {
      id
      name
      faction
      position { x z }
    }
    transits {
      id
      description
      position { x z }
    }
  }
}
"""


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def bounds_to_meta(
    bounds: list,
    rotation: int,
    map_id: str = "",
    transform: list | None = None,
    svg_bounds: list | None = None,
) -> dict:
    xmax, zmin = bounds[0]
    xmin, zmax = bounds[1]
    def bound_val(v: float) -> float | int:
        fv = float(v)
        return int(fv) if fv.is_integer() else round(fv, 4)

    meta: dict = {
        "xmin": bound_val(xmin),
        "xmax": bound_val(xmax),
        "zmin": bound_val(zmin),
        "zmax": bound_val(zmax),
        "coordinates_rotation": int(rotation),
    }
    if transform and len(transform) >= 4:
        meta["transform"] = [float(transform[0]), float(transform[1]), float(transform[2]), float(transform[3])]
    if svg_bounds and len(svg_bounds) == 2:
        sxmax, szmin = svg_bounds[0]
        sxmin, szmax = svg_bounds[1]
        meta["svg_xmin"] = int(sxmin)
        meta["svg_xmax"] = int(sxmax)
        meta["svg_zmin"] = int(szmin)
        meta["svg_zmax"] = int(szmax)
    if map_id in DISPLAY_ROTATION:
        meta["display_rotation"] = DISPLAY_ROTATION[map_id]
    return meta


def collect_bounds(maps_data: list) -> dict[str, dict]:
    meta_by_id: dict[str, dict] = {}
    for entry in maps_data:
        normalized = entry.get("normalizedName", "")
        mid = map_id(normalized)
        if not mid:
            continue
        for variant in entry.get("maps") or []:
            if variant.get("projection") != "interactive":
                continue
            bounds = variant.get("bounds")
            if not bounds or len(bounds) != 2:
                continue
            key = variant.get("key", "")
            if mid == "labs" and key != "the-lab":
                continue
            if mid == "labyrinth" and key != "the-labyrinth":
                continue
            meta_by_id[mid] = bounds_to_meta(
                bounds,
                variant.get("coordinateRotation", 180),
                mid,
                transform=variant.get("transform"),
                svg_bounds=variant.get("svgBounds"),
            )
    return meta_by_id


def sync_bounds() -> None:
    maps_data = json.loads(fetch(MAPS_JSON_URL).decode("utf-8"))
    meta_by_id = collect_bounds(maps_data)
    print(f"fetched interactive bounds for {len(meta_by_id)} maps")

    updated = 0
    for mid in CATALOG_ORDER:
        meta_path = MAPS_DIR / mid / "meta.json"
        existing: dict = {}
        if meta_path.is_file():
            existing = json.loads(meta_path.read_text(encoding="utf-8"))

        bounds = meta_by_id.get(mid)
        if bounds:
            entry = {
                "name": mid,
                "display_name": DISPLAY_NAMES.get(mid, mid.title()),
                "description": existing.get("description", ""),
                "xmin": bounds["xmin"],
                "xmax": bounds["xmax"],
                "zmin": bounds["zmin"],
                "zmax": bounds["zmax"],
                "coordinates_rotation": bounds["coordinates_rotation"],
            }
            if bounds.get("transform"):
                entry["transform"] = bounds["transform"]
            for key in ("svg_xmin", "svg_xmax", "svg_zmin", "svg_zmax"):
                if bounds.get(key) is not None:
                    entry[key] = bounds[key]
            if bounds.get("display_rotation") is not None:
                entry["display_rotation"] = bounds["display_rotation"]
            for key in ("width", "height"):
                if existing.get(key) is not None:
                    entry[key] = existing[key]
        elif existing:
            entry = existing
            print(f"kept existing meta: {mid}")
        else:
            print(f"skip meta: {mid} (no interactive variant)")
            continue

        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps(entry, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
        updated += 1

    print(f"updated {updated} map meta.json under {MAPS_DIR.relative_to(ROOT)}")


def gql(lang: str) -> list[dict]:
    body = json.dumps({"query": QUERY, "variables": {"lang": lang}}).encode("utf-8")
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if payload.get("errors"):
        raise RuntimeError(payload["errors"][0].get("message", payload["errors"]))
    return payload["data"]["maps"]


def map_id(normalized: str) -> str | None:
    key = (normalized or "").strip().lower()
    if not key:
        return None
    if key in MAP_ALIASES:
        key = MAP_ALIASES[key]
    key = key.replace("-", "")
    if key not in CATALOG_ORDER:
        return None
    return key


def apply_woods_coop_overrides(buckets: dict[str, dict[str, list]]) -> None:
    pmc_rows = list((buckets.get("pmc.json") or {}).get("woods") or [])
    scav_rows = list((buckets.get("scav.json") or {}).get("woods") or [])
    coop_rows = list((buckets.get("coop.json") or {}).get("woods") or [])
    coop_names = {(row.get("name") or "").strip() for row in coop_rows}

    chosen: dict[str, dict] = {}
    for rows in (pmc_rows, scav_rows):
        for row in rows:
            name = (row.get("name") or "").strip()
            if name not in WOODS_COOP_EXTRACT_NAMES:
                continue
            pref = WOODS_COOP_PREFERRED_ID.get(name)
            if name not in chosen or row.get("id") == pref:
                chosen[name] = row

    pmc_rows = [r for r in pmc_rows if (r.get("name") or "").strip() not in WOODS_COOP_EXTRACT_NAMES]
    scav_rows = [r for r in scav_rows if (r.get("name") or "").strip() not in WOODS_COOP_EXTRACT_NAMES]

    for name in sorted(WOODS_COOP_EXTRACT_NAMES):
        if name in chosen and name not in coop_names:
            row = dict(chosen[name])
            if name in WOODS_COOP_PREFERRED_ID:
                row["id"] = WOODS_COOP_PREFERRED_ID[name]
            coop_rows.append(row)

    buckets.setdefault("pmc.json", {})["woods"] = pmc_rows
    buckets.setdefault("scav.json", {})["woods"] = scav_rows
    buckets.setdefault("coop.json", {})["woods"] = coop_rows


def clean_transit_label(name: str) -> str:
    """tarkov.dev appends '?' to some transit labels; display without it."""
    text = (name or "").strip()
    while text.endswith("?") or text.endswith("？"):
        text = text[:-1].rstrip()
    return text


def localize_chinese_names(names: dict[str, dict[str, str]]) -> None:
    """Split API zh (Simplified) into zh_CN and zh_TW (OpenCC s2t)."""
    try:
        import opencc

        converter = opencc.OpenCC("s2t")
    except ImportError:
        print("warning: opencc not installed; run: pip install opencc-python-reimplemented")
        converter = None
    for langs in names.values():
        zh = langs.pop("zh", None)
        if not zh:
            continue
        langs["zh_CN"] = zh
        if converter:
            langs["zh_TW"] = converter.convert(zh)


def main() -> None:
    by_lang: dict[str, list[dict]] = {}
    for lang in NAME_LANGS:
        by_lang[lang] = gql(lang)
        print(f"fetched maps(lang: {lang})")

    base_maps = by_lang["en"]
    buckets: dict[str, dict[str, list]] = {name: {} for name in FACTION_FILES.values()}
    transit_buckets: dict[str, list] = {}
    names: dict[str, dict[str, str]] = {}

    for entry in base_maps:
        mid = map_id(entry.get("normalizedName", ""))
        if not mid:
            continue
        for ex in entry.get("extracts") or []:
            faction = (ex.get("faction") or "").strip().lower()
            fname = FACTION_FILES.get(faction)
            if not fname:
                continue
            pos = ex.get("position") or {}
            x, z = pos.get("x"), pos.get("z")
            if x is None or z is None:
                continue
            ex_id = (ex.get("id") or "").strip()
            name = (ex.get("name") or "").strip()
            if not ex_id or not name:
                continue
            buckets[fname].setdefault(mid, []).append(
                {
                    "id": ex_id,
                    "name": name,
                    "coordinates": [float(x), float(z)],
                }
            )
            if ex_id not in names:
                names[ex_id] = {}
        for tr in entry.get("transits") or []:
            pos = tr.get("position") or {}
            x, z = pos.get("x"), pos.get("z")
            tr_id = (tr.get("id") or "").strip()
            desc = clean_transit_label((tr.get("description") or "").strip())
            if x is None or z is None or not tr_id or not desc:
                continue
            transit_buckets.setdefault(mid, []).append(
                {
                    "id": tr_id,
                    "name": desc,
                    "coordinates": [float(x), float(z)],
                }
            )
            if tr_id not in names:
                names[tr_id] = {}

    for lang in NAME_LANGS:
        for entry in by_lang[lang]:
            mid = map_id(entry.get("normalizedName", ""))
            if not mid:
                continue
            for ex in entry.get("extracts") or []:
                ex_id = (ex.get("id") or "").strip()
                name = (ex.get("name") or "").strip()
                if ex_id and name:
                    names.setdefault(ex_id, {})[lang] = name
            for tr in entry.get("transits") or []:
                tr_id = (tr.get("id") or "").strip()
                desc = clean_transit_label((tr.get("description") or "").strip())
                if tr_id and desc:
                    names.setdefault(tr_id, {})[lang] = desc

    localize_chinese_names(names)
    apply_woods_coop_overrides(buckets)

    OUT.mkdir(parents=True, exist_ok=True)
    for fname, by_map in buckets.items():
        ordered = {}
        for mid in CATALOG_ORDER:
            ordered[mid] = by_map.get(mid, [])
        path = OUT / fname
        path.write_text(json.dumps(ordered, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
        total = sum(len(v) for v in ordered.values())
        print(f"wrote {path.relative_to(ROOT)} ({total} markers)")

    transit_ordered = {}
    for mid in CATALOG_ORDER:
        transit_ordered[mid] = transit_buckets.get(mid, [])
    transit_path = OUT / "transit.json"
    transit_path.write_text(json.dumps(transit_ordered, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
    transit_total = sum(len(v) for v in transit_ordered.values())
    print(f"wrote {transit_path.relative_to(ROOT)} ({transit_total} markers)")

    names_path = OUT / "names.json"
    names_path.write_text(json.dumps(names, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {names_path.relative_to(ROOT)} ({len(names)} entries)")

    sync_bounds()
    print("sources: https://api.tarkov.dev/graphql + tarkov.dev maps.json (interactive)")


if __name__ == "__main__":
    main()

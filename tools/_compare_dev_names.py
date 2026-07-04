#!/usr/bin/env python3
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
names = json.loads((ROOT / "internal/points/exfil/names.json").read_text(encoding="utf-8"))
UA = {"User-Agent": "x", "Content-Type": "application/json"}
QUERY = """
query ($lang: LanguageCode) {
  maps(lang: $lang) {
    normalizedName
    extracts { id name faction }
    transits { id description }
  }
}
"""

for lang in ["en", "zh"]:
    body = json.dumps({"query": QUERY, "variables": {"lang": lang}}).encode()
    d = json.loads(
        urllib.request.urlopen(
            urllib.request.Request("https://api.tarkov.dev/graphql", data=body, headers=UA),
            timeout=60,
        ).read()
    )
    m = next(x for x in d["data"]["maps"] if x["normalizedName"] == "factory")
    print(f"\n=== factory lang={lang} ===")
    for ex in m["extracts"]:
        nid = ex["id"]
        ours = names.get(nid, {})
        print(f"  [{ex['faction']}] dev={ex['name']!r} ours_en={ours.get('en','')!r} ours_zh={ours.get('zh_CN','')!r} ours_tw={ours.get('zh_TW','')!r}")
    for tr in m["transits"]:
        nid = tr["id"]
        ours = names.get(nid, {})
        print(f"  [transit] dev={tr['description']!r} ours_en={ours.get('en','')!r} ours_zh={ours.get('zh_CN','')!r} ours_tw={ours.get('zh_TW','')!r}")

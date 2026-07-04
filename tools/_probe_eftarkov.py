#!/usr/bin/env python3
import json
import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def main() -> None:
    base = "https://api.eftarkov.com"
    html = fetch(f"{base}/map/factory/").decode("utf-8", "replace")
    print("html_len", len(html))
    for m in re.finditer(r'src="([^"]+)"', html):
        print("script", m.group(1))
    for m in re.finditer(r"href=\"([^\"]+\.json[^\"]*)\"", html):
        print("json_href", m.group(1))
    for pat in re.findall(r"/[a-zA-Z0-9_./-]+\.json", html):
        print("json_path", pat)
    for pat in sorted(set(re.findall(r"https?://[^\s\"'<>]+", html))):
        if "eftarkov" in pat or ".json" in pat:
            print("url", pat)

    candidates = [
        f"{base}/map/factory/config.json",
        f"{base}/map/factory/data.json",
        f"{base}/map/factory/points.json",
        f"{base}/map/factory/markers.json",
        f"{base}/map/factory/exfil.json",
        f"{base}/map/factory/legend.json",
        f"{base}/data/factory.json",
        f"{base}/maps/factory.json",
        f"{base}/static/map/factory.json",
    ]
    for u in candidates:
        try:
            data = fetch(u)
            print("OK", u, len(data), data[:80])
        except Exception as e:
            print("fail", u, e)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import urllib.request
from concurrent.futures import ThreadPoolExecutor

T = "https://assets.tarkov.dev/maps/shoreline/main_summer/6/{x}/{y}.png"
UA = {"User-Agent": "bm"}
z = 6
jobs = [(x, y) for x in range(40) for y in range(40)]


def hit(xy):
    x, y = xy
    try:
        d = urllib.request.urlopen(
            urllib.request.Request(T.format(x=x, y=y), headers=UA), timeout=8
        ).read()
        if len(d) >= 4000:
            return x, y
    except OSError:
        pass
    return None


hits = []
with ThreadPoolExecutor(24) as p:
    for h in p.map(hit, jobs):
        if h:
            hits.append(h)

cluster = [h for h in hits if h[0] <= 31 and h[1] <= 31]
print(
    "all",
    len(hits),
    "x",
    min(x for x, _ in hits),
    max(x for x, _ in hits),
    "y",
    min(y for _, y in hits),
    max(y for _, y in hits),
)
print(
    "cluster",
    len(cluster),
    "x",
    min(x for x, _ in cluster),
    max(x for x, _ in cluster),
    "y",
    min(y for _, y in cluster),
    max(y for _, y in cluster),
)
outliers = [h for h in hits if h not in cluster]
print("outliers", len(outliers), outliers[:15])

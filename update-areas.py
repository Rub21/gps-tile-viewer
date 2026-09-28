#!/usr/bin/env python3
"""Build areas.json from the tile server's shape data.

Lists the zoom-8 tiles that contain GPS data, groups them by zoom-5 tile,
keeps the densest groups, names each one with Nominatim and writes areas.json.

Usage:
    ./update-areas.py root@<host> [max_areas]
"""

import json
import math
import subprocess
import sys
import time
import urllib.parse
import urllib.request

HOST = sys.argv[1] if len(sys.argv) > 1 else "root@2.28.108.188"
MAX_AREAS = int(sys.argv[2]) if len(sys.argv) > 2 else 20
GROUP_ZOOM = 5
LIST_ZOOM = 8
SHAPES = "/srv/gps-tile.openstreetmap.org"


def tile_center(z, x, y):
    n = 2 ** z
    lon = (x + 0.5) / n * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 0.5) / n))))
    return lat, lon


def list_tiles():
    cmd = f"cd {SHAPES} && ./datamaps/enumerate -Z{LIST_ZOOM} -z{LIST_ZOOM} shapes/current 2>/dev/null"
    out = subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, cmd], capture_output=True, text=True, check=True).stdout
    # lines look like: "shapes/current 8 40 87 165 49.16,-123.15" (file z x y points lat,lon)
    tiles = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5:
            tiles[(int(parts[1]), int(parts[2]), int(parts[3]))] = int(parts[4])
    return tiles


def place_name(lat, lon):
    url = "https://nominatim.openstreetmap.org/reverse?" + urllib.parse.urlencode(
        {"lat": lat, "lon": lon, "format": "json", "zoom": 8, "accept-language": "en"}
    )
    req = urllib.request.Request(url, headers={"User-Agent": "gps-tile-viewer/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)
        a = data.get("address", {})
        parts = [a.get(k) for k in ("city", "town", "county", "state", "country") if a.get(k)]
        seen = []
        for p in parts:
            if p not in seen:
                seen.append(p)
        return ", ".join(seen[:2]) if seen else f"{lat:.2f}, {lon:.2f}"
    except Exception:
        return f"{lat:.2f}, {lon:.2f}"


def main():
    tiles = list_tiles()
    groups = {}
    shift = LIST_ZOOM - GROUP_ZOOM
    for (z, x, y), points in tiles.items():
        key = (x >> shift, y >> shift)
        groups.setdefault(key, []).append((x, y, points))

    ranked = sorted(groups.items(), key=lambda kv: sum(m[2] for m in kv[1]), reverse=True)[:MAX_AREAS]

    areas = []
    for (gx, gy), members in ranked:
        xs = [m[0] for m in members]
        ys = [m[1] for m in members]
        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)
        lat, lon = tile_center(LIST_ZOOM, cx, cy)
        name = place_name(lat, lon)
        points = sum(m[2] for m in members)
        areas.append({"name": name, "lat": round(lat, 4), "lon": round(lon, 4), "zoom": 9, "points": points})
        print(f"{points:8d} points  {name}", file=sys.stderr)
        time.sleep(1.1)  # Nominatim usage policy: max 1 request/s

    areas.sort(key=lambda a: a["name"])
    with open("areas.json", "w") as f:
        json.dump({"updated": time.strftime("%Y-%m-%d"), "areas": areas}, f, indent=2)
    print(f"wrote areas.json with {len(areas)} areas", file=sys.stderr)


if __name__ == "__main__":
    main()

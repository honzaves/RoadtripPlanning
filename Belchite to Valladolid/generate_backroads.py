#!/usr/bin/env python3
"""Strictly motorway-free variant of the Belchite -> Valladolid routes.

Routes the original waypoint sequences through FOSSGIS Valhalla with
use_highways=0 / use_tolls=0, which holds the line on the old N-/regional
roads (N-II, N-122, N-234, CL-116, SO-920, BU-910, A-222...) and avoids every
autovia. Valhalla caps at 20 locations per request, so the sequence is routed
in overlapping chunks and stitched. Output: *_backroads.gpx (dense <trk>,
waypoints preserved).
"""
import json
import time
import urllib.request
import urllib.error
import generate_valladolid as gv   # reuse parse(), build_gpx(), haversine_km()

VALHALLA = "https://valhalla1.openstreetmap.de/route"
UA = {"User-Agent": "belchite-valladolid-backroads/1.0", "Content-Type": "application/json"}
MAX_LOC = 20


def _decode_polyline6(s):
    coords, idx, lat, lon = [], 0, 0, 0
    while idx < len(s):
        for is_lon in (False, True):
            shift, result = 0, 0
            while True:
                b = ord(s[idx]) - 63
                idx += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            d = ~(result >> 1) if (result & 1) else (result >> 1)
            if is_lon:
                lon += d
            else:
                lat += d
        coords.append((lat / 1e6, lon / 1e6))
    return coords


def _route_chunk(points, use_highways):
    payload = {
        "locations": [{"lat": la, "lon": lo} for la, lo in points],
        "costing": "auto",
        "costing_options": {"auto": {"use_highways": use_highways, "use_tolls": 0.0}},
        "directions_options": {"units": "kilometers"},
    }
    data = json.dumps(payload).encode()
    for attempt in range(4):
        try:
            req = urllib.request.Request(VALHALLA, data=data, headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r:
                resp = json.load(r)
            break
        except (urllib.error.URLError, TimeoutError):
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))
    if "trip" not in resp:
        raise RuntimeError(f"Valhalla error: {str(resp)[:200]}")
    out = []
    for leg in resp["trip"]["legs"]:
        seg = _decode_polyline6(leg["shape"])
        if out and seg and out[-1] == seg[0]:
            seg = seg[1:]
        out.extend(seg)
    return out


def valhalla_geometry(points, use_highways=0.0):
    """Route through all points, chunking at <=20 locations with 1 overlap."""
    full = []
    start = 0
    n = len(points)
    while start < n - 1:
        end = min(start + MAX_LOC, n)
        seg = _route_chunk(points[start:end], use_highways)
        if full and seg and full[-1] == seg[0]:
            seg = seg[1:]
        full.extend(seg)
        start = end - 1   # overlap last point into next chunk
    return full


def main():
    jobs = [
        ("originals_backup/route_basic.gpx", "route_basic_backroads.gpx",
         "Belchite to Valladolid - Backroads (motorway-free)",
         "The 9 core waypoints on a strictly motorway-free line (old N-/regional roads, no autovia)."),
        ("originals_backup/route_enhanced.gpx", "route_enhanced_backroads.gpx",
         "Belchite to Valladolid - Backroads Enhanced (motorway-free)",
         "Waypoints plus all detours on a strictly motorway-free line (old N-/regional roads, no autovia)."),
    ]
    for src, dst, name, desc in jobs:
        _, _, wpts, rte = gv.parse(src)
        track = valhalla_geometry(rte, use_highways=0.0)
        gpx = gv.build_gpx(name, desc, wpts, track)
        with open(dst, "w", encoding="utf-8") as fh:
            fh.write(gpx)
        print(f"{dst:34s} {len(wpts):2d} wpts  {len(track):5d} trkpts  ~{gv.haversine_km(track):6.1f} km")


if __name__ == "__main__":
    main()

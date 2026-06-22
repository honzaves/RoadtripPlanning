#!/usr/bin/env python3
"""Render a map thumbnail for each Belchite -> Valladolid route over an OSM
basemap. Core waypoints = blue, detours = orange; start = green, end = red.

Resolution scale is read from THUMB_SCALE (default 4 -> 3600x2240). A larger
canvas makes staticmap fetch a higher zoom level, i.e. genuinely more map
detail, not an upscaled blur.
"""
import os
import xml.etree.ElementTree as ET
from staticmap import StaticMap, Line, CircleMarker

NS = {"g": "http://www.topografix.com/GPX/1/1"}
UA = "belchite-valladolid-thumbnails/1.0 (personal route planning)"
OUT = "images"
S = float(os.environ.get("THUMB_SCALE", "4"))
FILES = ["route_basic.gpx", "route_enhanced.gpx",
         "route_basic_backroads.gpx", "route_enhanced_backroads.gpx"]


def read(path):
    r = ET.parse(path).getroot()
    track = [(float(p.get("lon")), float(p.get("lat")))
             for p in r.findall(".//g:trkpt", NS)]
    wpts = []
    for w in r.findall("g:wpt", NS):
        wpts.append({
            "lonlat": (float(w.get("lon")), float(w.get("lat"))),
            "sym": w.findtext("g:sym", default="", namespaces=NS),
        })
    return track, wpts


def downsample(pts, target):
    if len(pts) <= target:
        return pts
    step = len(pts) / target
    out = [pts[int(i * step)] for i in range(target)]
    out[-1] = pts[-1]
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    w_px, h_px = int(900 * S), int(560 * S)
    pad = int(45 * S)
    for f in FILES:
        track, wpts = read(f)
        line = downsample(track, int(900 * S))
        m = StaticMap(w_px, h_px, padding_x=pad, padding_y=pad,
                      headers={"User-Agent": UA}, tile_request_timeout=30,
                      delay_between_retries=1)
        m.add_line(Line(line, "white", int(7 * S)))
        m.add_line(Line(line, "#c0392b", int(4 * S)))
        for w in wpts[1:-1]:
            color = "#e67e22" if "Green" in w["sym"] else "#2c6fbb"  # detour vs core
            m.add_marker(CircleMarker(w["lonlat"], "white", int(11 * S)))
            m.add_marker(CircleMarker(w["lonlat"], color, int(7 * S)))
        m.add_marker(CircleMarker(wpts[0]["lonlat"], "white", int(16 * S)))
        m.add_marker(CircleMarker(wpts[0]["lonlat"], "#2e8b3d", int(11 * S)))
        m.add_marker(CircleMarker(wpts[-1]["lonlat"], "white", int(16 * S)))
        m.add_marker(CircleMarker(wpts[-1]["lonlat"], "#c0392b", int(11 * S)))
        img = m.render()
        out = os.path.join(OUT, f.replace(".gpx", "").lower() + ".png")
        img.save(out)
        print(f"{out}  ({img.width}x{img.height}, {len(wpts)} wpts, {len(track)} pts)")


if __name__ == "__main__":
    main()

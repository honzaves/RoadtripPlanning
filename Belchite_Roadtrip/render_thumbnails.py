#!/usr/bin/env python3
"""Render a map thumbnail per day from the redesigned-route GPX tracks.

Route line over an OpenStreetMap basemap, with start (green), end (red) and
the named waypoint stops (white-edged dots). Output: images/new_dayN.png

Resolution scale is read from THUMB_SCALE (default 4 -> 3600x2240). A larger
canvas makes staticmap fetch a higher zoom level, i.e. genuinely more map
detail, not an upscaled blur.
"""
import os
import xml.etree.ElementTree as ET
from staticmap import StaticMap, Line, CircleMarker

NS = {"g": "http://www.topografix.com/GPX/1/1"}
UA = "belchite-roadtrip-thumbnails/1.0 (personal route planning)"
OUT = "images"
S = float(os.environ.get("THUMB_SCALE", "4"))

DAYS = [
    "New_Day1_Uitgeest_to_Toul.gpx",
    "New_Day2_Toul_to_Langeac.gpx",
    "New_Day3_Langeac_to_Galamus.gpx",
    "New_Day4_Galamus_to_Belchite.gpx",
]


def read_gpx(path):
    r = ET.parse(path).getroot()
    track = [(float(p.get("lon")), float(p.get("lat")))
             for p in r.findall(".//g:trkpt", NS)]
    wpts = [(float(p.get("lon")), float(p.get("lat")))
            for p in r.findall("g:wpt", NS)]
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
    for f in DAYS:
        track, wpts = read_gpx(f)
        line = downsample(track, int(900 * S))
        m = StaticMap(w_px, h_px, padding_x=pad, padding_y=pad,
                      headers={"User-Agent": UA}, tile_request_timeout=30,
                      delay_between_retries=1)
        m.add_line(Line(line, "white", int(7 * S)))
        m.add_line(Line(line, "#c0392b", int(4 * S)))
        for w in wpts[1:-1]:
            m.add_marker(CircleMarker(w, "white", int(11 * S)))
            m.add_marker(CircleMarker(w, "#2c6fbb", int(7 * S)))
        m.add_marker(CircleMarker(wpts[0], "white", int(16 * S)))
        m.add_marker(CircleMarker(wpts[0], "#2e8b3d", int(11 * S)))
        m.add_marker(CircleMarker(wpts[-1], "white", int(16 * S)))
        m.add_marker(CircleMarker(wpts[-1], "#c0392b", int(11 * S)))
        img = m.render()
        out = os.path.join(OUT, f.replace(".gpx", "").lower() + ".png")
        img.save(out)
        print(f"{out}  ({img.width}x{img.height}, {len(track)} pts -> {len(line)} drawn)")


if __name__ == "__main__":
    main()

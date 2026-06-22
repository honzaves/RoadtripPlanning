#!/usr/bin/env python3
"""Rebuild the Belchite -> Valladolid GPX files with real OSM road geometry.

The originals are straight-line <rte> routes (stops connected as the crow
flies). This snaps each route onto actual roads via the FOSSGIS OSRM service
(OpenStreetMap data) and writes a dense <trk>, keeping the <wpt> stops and
their descriptions intact.
"""
import json
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
import xml.sax.saxutils as su

OSRM = "https://routing.openstreetmap.de/routed-car/route/v1/driving/"
NS = {"g": "http://www.topografix.com/GPX/1/1"}
UA = {"User-Agent": "belchite-valladolid-gpx/1.0"}


def _get(url):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))


def osrm_geometry(points):
    """points: list of (lat, lon). Returns dense list of (lat, lon) on roads."""
    coords = ";".join(f"{lon},{lat}" for lat, lon in points)
    url = f"{OSRM}{coords}?overview=full&geometries=geojson&steps=false"
    data = _get(url)
    if data.get("code") != "Ok":
        raise RuntimeError(f"OSRM: {data.get('code')} {data.get('message','')}")
    return [(lat, lon) for lon, lat in data["routes"][0]["geometry"]["coordinates"]]


def haversine_km(track):
    from math import radians, sin, cos, asin, sqrt
    tot = 0.0
    for (la1, lo1), (la2, lo2) in zip(track, track[1:]):
        dla, dlo = radians(la2 - la1), radians(lo2 - lo1)
        a = sin(dla / 2) ** 2 + cos(radians(la1)) * cos(radians(la2)) * sin(dlo / 2) ** 2
        tot += 2 * 6371.0 * asin(sqrt(a))
    return tot


def parse(path):
    """Return (gpx_name, gpx_desc, wpts, route_points)."""
    r = ET.parse(path).getroot()
    meta = r.find("g:metadata", NS)
    name = meta.findtext("g:name", default="", namespaces=NS)
    desc = meta.findtext("g:desc", default="", namespaces=NS)
    wpts = []
    for w in r.findall("g:wpt", NS):
        wpts.append({
            "lat": float(w.get("lat")), "lon": float(w.get("lon")),
            "name": w.findtext("g:name", default="", namespaces=NS),
            "desc": w.findtext("g:desc", default="", namespaces=NS),
            "type": w.findtext("g:type", default="", namespaces=NS),
            "sym": w.findtext("g:sym", default="", namespaces=NS),
        })
    rte = [(float(p.get("lat")), float(p.get("lon")))
           for p in r.findall(".//g:rtept", NS)]
    return name, desc, wpts, rte


def build_gpx(name, desc, wpts, track):
    e = su.escape
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gpx version="1.1" creator="generate_valladolid.py -- OSM routing.openstreetmap.de" '
        'xmlns="http://www.topografix.com/GPX/1/1" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">',
        "  <metadata>",
        f"    <name>{e(name)}</name>",
        f"    <desc>{e(desc)}</desc>",
        "  </metadata>",
    ]
    for w in wpts:
        out.append(f'  <wpt lat="{w["lat"]:.6f}" lon="{w["lon"]:.6f}">')
        out.append(f"    <name>{e(w['name'])}</name>")
        if w["desc"]:
            out.append(f"    <desc>{e(w['desc'])}</desc>")
        if w["type"]:
            out.append(f"    <type>{e(w['type'])}</type>")
        if w["sym"]:
            out.append(f"    <sym>{e(w['sym'])}</sym>")
        out.append("  </wpt>")
    out.append("  <trk>")
    out.append(f"    <name>{e(name)}</name>")
    out.append(f"    <desc>{e(desc)}</desc>")
    out.append("    <trkseg>")
    for la, lo in track:
        out.append(f'      <trkpt lat="{la:.6f}" lon="{lo:.6f}"></trkpt>')
    out.append("    </trkseg>")
    out.append("  </trk>")
    out.append("</gpx>")
    return "\n".join(out) + "\n"


def main():
    for f in ["route_basic.gpx", "route_enhanced.gpx"]:
        name, desc, wpts, rte = parse(f)
        track = osrm_geometry(rte)
        gpx = build_gpx(name, desc, wpts, track)
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(gpx)
        print(f"{f:22s} {len(wpts):2d} wpts  {len(track):5d} trkpts  ~{haversine_km(track):6.1f} km")


if __name__ == "__main__":
    main()

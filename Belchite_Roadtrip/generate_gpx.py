#!/usr/bin/env python3
"""Rebuild the Belchite road-trip GPX files with real OSM road geometry.

Geometry comes from the FOSSGIS routing services (OpenStreetMap data):
  - OSRM  : https://routing.openstreetmap.de/routed-car  (fastest car route)
  - Valhalla: https://valhalla1.openstreetmap.de/route    (auto, use_highways=0)

Each output file keeps the original named <wpt> stops and adds a dense <trk>
that follows the actual roads, so the line is correct regardless of how the
navigation device is configured.
"""
import json
import time
import urllib.request
import urllib.error
import xml.sax.saxutils as su

OSRM = "https://routing.openstreetmap.de/routed-car/route/v1/driving/"
VALHALLA = "https://valhalla1.openstreetmap.de/route"
UA = {"User-Agent": "belchite-roadtrip-gpx/1.0"}


def _get(url):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))


def _post(url, payload):
    data = json.dumps(payload).encode()
    headers = {**UA, "Content-Type": "application/json"}
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))


def osrm_geometry(points):
    """points: list of (lat, lon). Returns list of (lat, lon) along roads."""
    coords = ";".join(f"{lon},{lat}" for lat, lon in points)
    url = f"{OSRM}{coords}?overview=full&geometries=geojson&steps=false"
    data = _get(url)
    if data.get("code") != "Ok":
        raise RuntimeError(f"OSRM: {data.get('code')} {data.get('message','')}")
    line = data["routes"][0]["geometry"]["coordinates"]  # [lon, lat]
    return [(lat, lon) for lon, lat in line]


def _decode_polyline6(s):
    """Decode a Valhalla polyline (precision 6) into (lat, lon) pairs."""
    coords, index, lat, lon = [], 0, 0, 0
    while index < len(s):
        for is_lon in (False, True):
            shift, result = 0, 0
            while True:
                b = ord(s[index]) - 63
                index += 1
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


def valhalla_geometry(points, use_highways=0.0):
    """No-motorway auto route. points: (lat, lon). Returns (lat, lon) list."""
    payload = {
        "locations": [{"lat": la, "lon": lo} for la, lo in points],
        "costing": "auto",
        "costing_options": {"auto": {"use_highways": use_highways, "use_tolls": 0.0}},
        "directions_options": {"units": "kilometers"},
    }
    data = _post(VALHALLA, payload)
    if "trip" not in data:
        raise RuntimeError(f"Valhalla error: {str(data)[:200]}")
    out = []
    for leg in data["trip"]["legs"]:
        seg = _decode_polyline6(leg["shape"])
        if out and seg and out[-1] == seg[0]:
            seg = seg[1:]
        out.extend(seg)
    return out


def haversine_km(track):
    from math import radians, sin, cos, asin, sqrt
    tot = 0.0
    for (la1, lo1), (la2, lo2) in zip(track, track[1:]):
        dla, dlo = radians(la2 - la1), radians(lo2 - lo1)
        a = sin(dla / 2) ** 2 + cos(radians(la1)) * cos(radians(la2)) * sin(dlo / 2) ** 2
        tot += 2 * 6371.0 * asin(sqrt(a))
    return tot


def build_gpx(name, desc, waypoints, track):
    """waypoints: list of dict(lat, lon, name, sym). track: (lat, lon) list."""
    esc = su.escape
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gpx xmlns="http://www.topografix.com/GPX/1/1" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xsi:schemaLocation="http://www.topografix.com/GPX/1/1 '
        'http://www.topografix.com/GPX/1/1/gpx.xsd" version="1.1" '
        'creator="generate_gpx.py -- OSM routing.openstreetmap.de">',
        "  <metadata>",
        f"    <name>{esc(name)}</name>",
        f"    <desc>{esc(desc)}</desc>",
        "  </metadata>",
    ]
    for w in waypoints:
        lines.append(f'  <wpt lat="{w["lat"]:.5f}" lon="{w["lon"]:.5f}">')
        lines.append(f"    <name>{esc(w['name'])}</name>")
        lines.append(f"    <sym>{esc(w['sym'])}</sym>")
        lines.append("  </wpt>")
    lines.append("  <trk>")
    lines.append(f"    <name>{esc(name)}</name>")
    lines.append(f"    <desc>{esc(desc)}</desc>")
    lines.append("    <trkseg>")
    for la, lo in track:
        lines.append(f'      <trkpt lat="{la:.6f}" lon="{lo:.6f}"></trkpt>')
    lines.append("    </trkseg>")
    lines.append("  </trk>")
    lines.append("</gpx>")
    return "\n".join(lines) + "\n"


# --- Day definitions -------------------------------------------------------

DAYS = []

# Day 1 — pure motorway transit, OSRM fastest.
day1_wpts = [
    {"lat": 52.5333, "lon": 4.7167, "name": "Uitgeest START", "sym": "Flag, Green"},
    {"lat": 50.6326, "lon": 5.5797, "name": "Liege (E25)", "sym": "Waypoint"},
    {"lat": 50.0030, "lon": 5.7186, "name": "Bastogne", "sym": "Waypoint"},
    {"lat": 49.1547, "lon": 5.3697, "name": "Camping Les Breuils, Verdun CAMP", "sym": "Campground"},
]
DAYS.append(dict(
    file="Day1_Uitgeest_to_Verdun.gpx",
    name="Day1_Uitgeest_to_Verdun",
    desc="Wed 12:00. Motorway transit A2/E25 to Verdun. Track snapped to OSM roads (OSRM fastest).",
    wpts=day1_wpts,
    build=lambda w: osrm_geometry([(x["lat"], x["lon"]) for x in w]),
))

# Day 2 — OSRM fastest to Decize (motorway start + Morvan), then Valhalla
# no-highway down the Allier valley to Langeac.
day2_wpts = [
    {"lat": 49.1597, "lon": 5.3828, "name": "Verdun START", "sym": "Flag, Green"},
    {"lat": 48.6753, "lon": 5.8910, "name": "A31 Toul", "sym": "Waypoint"},
    {"lat": 47.2810, "lon": 4.2300, "name": "Saulieu EXIT A6", "sym": "Waypoint"},
    {"lat": 47.2436, "lon": 4.0625, "name": "Saut de Gouloux", "sym": "Waypoint"},
    {"lat": 47.1900, "lon": 4.0500, "name": "Lac des Settons", "sym": "Waypoint"},
    {"lat": 46.9870, "lon": 3.8200, "name": "Moulins-Engilbert", "sym": "Waypoint"},
    {"lat": 46.8290, "lon": 3.4600, "name": "Decize (Loire)", "sym": "Waypoint"},
    {"lat": 45.1555, "lon": 3.4359, "name": "Chilhac", "sym": "Waypoint"},
    {"lat": 45.1026, "lon": 3.4998, "name": "Camping des Gorges de l'Allier, Langeac CAMP", "sym": "Campground"},
]


def build_day2(w):
    north = [(x["lat"], x["lon"]) for x in w[:7]]          # Verdun .. Decize
    south = [(x["lat"], x["lon"]) for x in w[6:]]          # Decize .. Langeac
    g1 = osrm_geometry(north)
    g2 = valhalla_geometry(south, use_highways=0.0)
    if g1 and g2 and g1[-1] == g2[0]:
        g2 = g2[1:]
    return g1 + g2


DAYS.append(dict(
    file="Day2_Verdun_to_Langeac.gpx",
    name="Day2_Verdun_to_Langeac",
    desc=("Thu. A31->A6 to Saulieu (OSRM), then OSM D-roads through the Morvan "
          "and the Allier valley to Langeac (Valhalla no-motorway). Track on real roads."),
    wpts=day2_wpts,
    build=build_day2,
))

# Day 3 — zero motorway, inland. OSRM with inland shaping vias on the long
# Florac -> Galamus leg so it stays off the A75/A9 and out to the coast.
day3_wpts = [
    {"lat": 45.1026, "lon": 3.4998, "name": "Langeac START", "sym": "Flag, Green"},
    {"lat": 44.9732, "lon": 3.6390, "name": "Cave Chapel Sainte-Madeleine, Monistrol", "sym": "Waypoint"},
    {"lat": 44.8662, "lon": 3.9237, "name": "Arlempdes", "sym": "Waypoint"},
    {"lat": 44.7699, "lon": 3.8820, "name": "Pradelles", "sym": "Waypoint"},
    {"lat": 44.3793, "lon": 3.6746, "name": "Cascade de Runes", "sym": "Waypoint"},
    {"lat": 44.3247, "lon": 3.5933, "name": "Florac", "sym": "Waypoint"},
    {"lat": 42.8121, "lon": 2.5036, "name": "Camping Agly, Saint-Paul / Galamus CAMP", "sym": "Campground"},
]
# Inland shaping vias (not shown as stops) between Florac and Galamus.
day3_vias = [
    (44.1796, 3.4307),   # Meyrueis (D996, Gorges de la Jonte)
    (43.9570, 2.8880),   # Saint-Affrique (D999)
    (43.7095, 2.6925),   # Lacaune (D607/D622)
    (43.4940, 2.3760),   # Mazamet (D612)
    (43.0550, 2.2160),   # Limoux (D118)
    (42.8740, 2.1830),   # Quillan (D117 -> Saint-Paul)
]


def build_day3(w):
    pts = [(x["lat"], x["lon"]) for x in w[:6]]            # Langeac .. Florac
    pts += day3_vias                                       # inland shaping
    pts.append((w[6]["lat"], w[6]["lon"]))                 # Galamus
    return osrm_geometry(pts)


DAYS.append(dict(
    file="Day3_Langeac_to_Galamus.gpx",
    name="Day3_Langeac_to_Galamus",
    desc=("Fri. Allier gorges, upper Loire, Margeride, Haut-Languedoc to Galamus. "
          "Zero motorway, inland line on OSM D-roads (OSRM with inland shaping vias)."),
    wpts=day3_wpts,
    build=build_day3,
))

# Day 4 — OSRM fastest. Galamus gorge (D7) is held by the Ermitage stop;
# Spanish motorway across Aragon is intended.
day4_wpts = [
    {"lat": 42.8121, "lon": 2.5036, "name": "Saint-Paul START", "sym": "Flag, Green"},
    {"lat": 42.8390, "lon": 2.4960, "name": "Gorges de Galamus / Ermitage", "sym": "Waypoint"},
    {"lat": 42.8368, "lon": 2.6215, "name": "Chateau de Queribus", "sym": "Waypoint"},
    {"lat": 42.7600, "lon": 2.6900, "name": "Maury / D117", "sym": "Waypoint"},
    {"lat": 42.4625, "lon": 2.8639, "name": "Le Perthus BORDER", "sym": "Waypoint"},
    {"lat": 42.2662, "lon": 2.9610, "name": "Figueres", "sym": "Waypoint"},
    {"lat": 41.6176, "lon": 0.6200, "name": "Lleida", "sym": "Waypoint"},
    {"lat": 41.3061, "lon": -0.7547, "name": "Belchite END", "sym": "Flag, Red"},
]
DAYS.append(dict(
    file="Day4_Galamus_to_Belchite.gpx",
    name="Day4_Galamus_to_Belchite",
    desc=("Sat. Galamus balcony road (D7), Queribus, cross at Le Perthus, then "
          "AP-7/A-2 across Aragon to Belchite. Track on real OSM roads (OSRM)."),
    wpts=day4_wpts,
    build=lambda w: osrm_geometry([(x["lat"], x["lon"]) for x in w]),
))


def main():
    for d in DAYS:
        track = d["build"](d["wpts"])
        gpx = build_gpx(d["name"], d["desc"], d["wpts"], track)
        with open(d["file"], "w", encoding="utf-8") as f:
            f.write(gpx)
        print(f"{d['file']:34s} {len(track):5d} pts  ~{haversine_km(track):6.1f} km road geometry")


if __name__ == "__main__":
    main()
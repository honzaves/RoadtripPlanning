#!/usr/bin/env python3
"""Build the redesigned 4-day route (Toul night 1, Gorges du Tarn, scenic
Cerdagne Pyrenean crossing). Dense OSM road tracks via routing.openstreetmap.de.

Reuses the geometry/GPX helpers from generate_gpx.py.
"""
import generate_gpx as g

# --- Day 1: Uitgeest -> Toul (transit, OSRM fastest) -----------------------
d1_wpts = [
    {"lat": 52.5333, "lon": 4.7167, "name": "Uitgeest START", "sym": "Flag, Green"},
    {"lat": 50.6326, "lon": 5.5797, "name": "Liege (E25)", "sym": "Waypoint"},
    {"lat": 48.6753, "lon": 5.8910, "name": "Toul CAMP", "sym": "Campground"},
]


def build_d1(w):
    return g.osrm_geometry([(x["lat"], x["lon"]) for x in w])


# --- Day 2: Toul -> Morvan -> Allier valley -> Langeac ---------------------
# OSRM fastest Toul..Decize (A31/A6 start + Morvan stops force D-roads),
# then Valhalla no-motorway down the Allier to Langeac.
d2_wpts = [
    {"lat": 48.6753, "lon": 5.8910, "name": "Toul START", "sym": "Flag, Green"},
    {"lat": 47.2810, "lon": 4.2300, "name": "Saulieu EXIT A6", "sym": "Waypoint"},
    {"lat": 47.2436, "lon": 4.0625, "name": "Saut de Gouloux", "sym": "Waypoint"},
    {"lat": 47.1900, "lon": 4.0500, "name": "Lac des Settons", "sym": "Waypoint"},
    {"lat": 46.9870, "lon": 3.8200, "name": "Moulins-Engilbert", "sym": "Waypoint"},
    {"lat": 46.8290, "lon": 3.4600, "name": "Decize (Loire)", "sym": "Waypoint"},
    {"lat": 45.1555, "lon": 3.4359, "name": "Chilhac", "sym": "Waypoint"},
    {"lat": 45.1026, "lon": 3.4998, "name": "Camping des Gorges de l'Allier, Langeac CAMP", "sym": "Campground"},
]


def build_d2(w):
    north = [(x["lat"], x["lon"]) for x in w[:6]]   # Toul .. Decize
    south = [(x["lat"], x["lon"]) for x in w[5:]]    # Decize .. Langeac
    g1 = g.osrm_geometry(north)
    g2 = g.valhalla_geometry(south, use_highways=0.0)
    if g1 and g2 and g1[-1] == g2[0]:
        g2 = g2[1:]
    return g1 + g2


# --- Day 3: Langeac -> Cevennes -> Gorges du Tarn -> Galamus ---------------
# OSRM with inland shaping vias; fully motorway-free.
d3_wpts = [
    {"lat": 45.1026, "lon": 3.4998, "name": "Langeac START", "sym": "Flag, Green"},
    {"lat": 44.9732, "lon": 3.6390, "name": "Cave Chapel Sainte-Madeleine, Monistrol", "sym": "Waypoint"},
    {"lat": 44.3793, "lon": 3.6746, "name": "Cascade de Runes (Mont Lozere)", "sym": "Waypoint"},
    {"lat": 44.3247, "lon": 3.5933, "name": "Florac", "sym": "Waypoint"},
    {"lat": 44.3620, "lon": 3.4120, "name": "Gorges du Tarn / Sainte-Enimie", "sym": "Waypoint"},
    {"lat": 44.1930, "lon": 3.2050, "name": "Le Rozier (Tarn gorge exit)", "sym": "Waypoint"},
    {"lat": 42.8121, "lon": 2.5036, "name": "Camping Agly, Saint-Paul / Galamus CAMP", "sym": "Campground"},
]
d3_vias = [  # inland, motorway-free corridor Le Rozier -> Galamus
    (43.7095, 2.6925),   # Lacaune
    (43.4940, 2.3760),   # Mazamet
    (43.0550, 2.2160),   # Limoux
    (42.8740, 2.1830),   # Quillan (D117 -> Saint-Paul)
]


def build_d3(w):
    pts = [(x["lat"], x["lon"]) for x in w[:6]]   # Langeac .. Le Rozier
    pts += d3_vias
    pts.append((w[6]["lat"], w[6]["lon"]))        # Galamus
    return g.osrm_geometry(pts)


# --- Day 4: Galamus dawn -> Cerdagne crossing -> Belchite ------------------
# OSRM fastest. French side is naturally motorway-free (D117/D118/N20);
# only the final Lleida->Belchite uses Spanish motorway (AP-2).
d4_wpts = [
    {"lat": 42.8121, "lon": 2.5036, "name": "Saint-Paul / Galamus START", "sym": "Flag, Green"},
    {"lat": 42.8390, "lon": 2.4960, "name": "Gorges de Galamus / Ermitage", "sym": "Waypoint"},
    {"lat": 42.8740, "lon": 2.1830, "name": "Quillan / Gorges de l'Aude", "sym": "Waypoint"},
    {"lat": 42.7190, "lon": 1.8380, "name": "Ax-les-Thermes", "sym": "Waypoint"},
    {"lat": 42.4310, "lon": 1.9280, "name": "Puigcerda / Cerdagne BORDER", "sym": "Waypoint"},
    {"lat": 42.3580, "lon": 1.4590, "name": "La Seu d'Urgell", "sym": "Waypoint"},
    {"lat": 41.6170, "lon": 0.6200, "name": "Lleida", "sym": "Waypoint"},
    {"lat": 41.3061, "lon": -0.7547, "name": "Belchite END", "sym": "Flag, Red"},
]


def build_d4(w):
    return g.osrm_geometry([(x["lat"], x["lon"]) for x in w])


DAYS = [
    dict(file="New_Day1_Uitgeest_to_Toul.gpx", name="New_Day1_Uitgeest_to_Toul",
         desc="Day 1 transit: Uitgeest -> Liege -> Luxembourg -> Toul. Motorway, comfortable. OSM road track (OSRM).",
         wpts=d1_wpts, build=build_d1),
    dict(file="New_Day2_Toul_to_Langeac.gpx", name="New_Day2_Toul_to_Langeac",
         desc="Day 2: Toul, A31/A6 to Saulieu, Morvan forests, then no-motorway Allier valley to Langeac. OSM track (OSRM + Valhalla no-motorway).",
         wpts=d2_wpts, build=build_d2),
    dict(file="New_Day3_Langeac_to_Galamus.gpx", name="New_Day3_Langeac_to_Galamus",
         desc="Day 3 (wild day): Allier gorges, Mont Lozere, Florac, Gorges du Tarn, Haut-Languedoc to Galamus. Zero motorway, inland (OSRM + shaping vias).",
         wpts=d3_wpts, build=build_d3),
    dict(file="New_Day4_Galamus_to_Belchite.gpx", name="New_Day4_Galamus_to_Belchite",
         desc="Day 4: dawn Galamus gorge, Gorges de l'Aude, Ax-les-Thermes, scenic Cerdagne crossing at Puigcerda, La Seu d'Urgell, then to Belchite. OSM track (OSRM).",
         wpts=d4_wpts, build=build_d4),
]


def main():
    for d in DAYS:
        track = d["build"](d["wpts"])
        gpx = g.build_gpx(d["name"], d["desc"], d["wpts"], track)
        with open(d["file"], "w", encoding="utf-8") as f:
            f.write(gpx)
        print(f"{d['file']:34s} {len(track):5d} pts  ~{g.haversine_km(track):6.1f} km")


if __name__ == "__main__":
    main()

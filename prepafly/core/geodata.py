"""Détection des routes et voies ferrées autour de la zone de vol.

Interroge OpenStreetMap via l'API Overpass : renvoie, dans une fenêtre autour de
la zone, les routes (highway) et voies ferrées (railway) avec leur nom et leur
tracé. Utilisé pour documenter automatiquement les contraintes « Routes » et
« Voies ferrées » du dossier de vol (comme un dossier officiel).

Appel côté serveur (pas de CORS). Échoue proprement hors ligne : l'appelant
affiche l'erreur et le dossier reste générable sans ces cartes.
"""
from __future__ import annotations

import math

import httpx

# Miroirs Overpass (on essaie le suivant si le premier échoue/est saturé).
OVERPASS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
_UA = {"User-Agent": "PrepaFlyPy/1.0"}

# Ordre d'importance des routes (pour trier et limiter le nombre de cartes).
_ROAD_RANK = {
    "motorway": 0, "trunk": 1, "primary": 2, "secondary": 3, "tertiary": 4,
    "unclassified": 5, "residential": 6, "living_street": 7, "service": 8, "road": 9,
}
_MAX_ROADS = 8
_MAX_RAILS = 4


def _road_type_label(ref: str, highway: str) -> str:
    """Déduit un type lisible (Autoroute, Départementale…) du ref/de la classe."""
    r = (ref or "").strip().upper()
    if r.startswith("A"):
        return "Autoroute"
    if r.startswith("N"):
        return "Route nationale"
    if r.startswith("D"):
        return "Route départementale"
    if r.startswith("M"):
        return "Route métropolitaine"
    return {"motorway": "Autoroute", "trunk": "Voie rapide", "primary": "Route principale",
            "secondary": "Route secondaire", "tertiary": "Route", "residential": "Rue",
            "living_street": "Voie", "service": "Voie de service"}.get(highway, "Route")


def query_roads_rails(zone: list, buffer_m: float = 120.0, timeout: float = 25.0) -> dict:
    """Renvoie les routes et voies ferrées autour de la zone.

    zone : liste de sommets [lat, lon]. Retour : {"ok", "roads":[{name,type,geoms}],
    "rails":[{name,type,geoms}], "error"}. geoms = liste de tracés [[lat,lon],…].
    """
    pts = [(float(p[0]), float(p[1])) for p in (zone or []) if p]
    if not pts:
        return {"ok": False, "roads": [], "rails": [], "error": "Aucune zone dessinée"}
    lats = [p[0] for p in pts]
    lons = [p[1] for p in pts]
    clat = sum(lats) / len(lats)
    dlat = buffer_m / 111000.0
    dlon = buffer_m / (111000.0 * max(0.1, math.cos(math.radians(clat))))
    s, w = min(lats) - dlat, min(lons) - dlon
    n, e = max(lats) + dlat, max(lons) + dlon
    bbox = f"{s},{w},{n},{e}"
    query = (
        "[out:json][timeout:25];("
        f'way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street|service|road)$"]({bbox});'
        f'way["railway"~"^(rail|light_rail|tram|subway|narrow_gauge)$"]({bbox});'
        ");out geom;"
    )
    print(f"[geodata] bbox={bbox}", flush=True)
    data, err = None, ""
    for url in OVERPASS:
        try:
            print(f"[geodata] interrogation {url} …", flush=True)
            r = httpx.post(url, data={"data": query}, headers=_UA, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            print(f"[geodata] {url} → {len(data.get('elements', []))} éléments", flush=True)
            break
        except Exception as ex:  # noqa: BLE001 - miroir suivant
            err = str(ex)
            print(f"[geodata] échec {url} : {ex}", flush=True)
            continue
    if data is None:
        return {"ok": False, "roads": [], "rails": [], "error": err or "Service indisponible"}
    # Overpass peut répondre 200 avec seulement une « remark » d'erreur.
    if not data.get("elements") and data.get("remark"):
        return {"ok": False, "roads": [], "rails": [], "error": "Overpass : " + str(data.get("remark"))}

    roads: dict = {}
    rails: dict = {}
    for el in data.get("elements", []):
        if el.get("type") != "way":
            continue
        tags = el.get("tags", {}) or {}
        geom = [[g["lat"], g["lon"]] for g in el.get("geometry", []) if "lat" in g and "lon" in g]
        if len(geom) < 2:
            continue
        if "highway" in tags:
            ref = tags.get("ref", "")
            name = ref or tags.get("name", "") or _road_type_label(ref, tags.get("highway", ""))
            typ = _road_type_label(ref, tags.get("highway", ""))
            rank = _ROAD_RANK.get(tags.get("highway", ""), 9)
            entry = roads.setdefault(name, {"name": name, "type": typ, "rank": rank, "geoms": []})
            entry["geoms"].append(geom)
            entry["rank"] = min(entry["rank"], rank)
        elif "railway" in tags:
            name = tags.get("name", "") or "Voie ferrée"
            entry = rails.setdefault(name, {"name": name, "type": "Voie ferrée", "rank": 0, "geoms": []})
            entry["geoms"].append(geom)

    road_list = sorted(roads.values(), key=lambda x: (x["rank"], x["name"]))[:_MAX_ROADS]
    rail_list = sorted(rails.values(), key=lambda x: x["name"])[:_MAX_RAILS]
    for x in road_list + rail_list:
        x.pop("rank", None)
    return {"ok": True, "roads": road_list, "rails": rail_list, "error": ""}

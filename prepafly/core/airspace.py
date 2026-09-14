"""Interrogation des contraintes drone à un point (couche IGN/Géoportail).

La carte affiche la couche raster « restrictions drone » (TRANSPORTS.DRONES.
RESTRICTIONS), qui n'est qu'une image. Pour obtenir la LISTE des contraintes à un
point précis, on interroge le service WMS interrogeable d'IGN (GetFeatureInfo),
qui renvoie les entités (zones) présentes sous le point avec leurs attributs.

L'appel est fait côté serveur (pas de contrainte CORS) et échoue proprement hors
ligne. Les attributs exacts renvoyés par IGN peuvent varier : on renvoie donc à
la fois un libellé lisible (best-effort) et les propriétés brutes, pour rester
robuste et affichable quoi qu'il arrive.
"""
from __future__ import annotations

import math

import httpx

# Service WMS raster interrogeable d'IGN (sans clé).
WMS = "https://data.geopf.fr/wms-r/wms"
LAYER = "TRANSPORTS.DRONES.RESTRICTIONS"
_UA = {"User-Agent": "PrepaFlyPy/1.0"}

# Clés d'attributs susceptibles de porter un nom / un plafond de hauteur, testées
# dans l'ordre. IGN peut nommer ces champs différemment selon les millésimes.
_NAME_KEYS = ("nom", "name", "libelle", "libellé", "intitule", "zone", "designation", "title")
_LIMIT_KEYS = ("limite", "hauteur", "height", "plafond", "altitude", "niveau", "gridcode", "value", "valeur")


def _to_mercator(lon: float, lat: float) -> tuple[float, float]:
    """Convertit lon/lat (WGS84) en coordonnées Web Mercator (EPSG:3857)."""
    x = lon * 20037508.34 / 180.0
    y = math.log(math.tan((90.0 + lat) * math.pi / 360.0)) / (math.pi / 180.0)
    y = y * 20037508.34 / 180.0
    return x, y


def _feature_label(props: dict) -> str:
    """Construit un libellé lisible à partir des propriétés d'une entité."""
    name = ""
    for k in props:
        if k.lower() in _NAME_KEYS and props[k] not in (None, ""):
            name = str(props[k]).strip()
            break
    limit = ""
    for k in props:
        if k.lower() in _LIMIT_KEYS and props[k] not in (None, ""):
            limit = str(props[k]).strip()
            break
    if name and limit:
        return f"{name} — {limit}"
    if name:
        return name
    if limit:
        return f"Restriction (plafond {limit})"
    # Dernier recours : premières propriétés non vides.
    parts = [f"{k}: {v}" for k, v in props.items() if v not in (None, "")][:3]
    return " / ".join(parts) if parts else "Zone de restriction (détails non fournis)"


def query_restrictions(lat: float, lon: float, timeout: float = 8.0) -> dict:
    """Renvoie les contraintes drone au point donné.

    Retour : {"ok": bool, "count": int, "features": [{"label": str,
    "properties": dict}], "error": str}. En cas d'absence de réseau ou d'erreur,
    ok=False et error est renseigné (l'appelant l'affiche tel quel)."""
    try:
        latf, lonf = float(lat), float(lon)
    except (TypeError, ValueError):
        return {"ok": False, "count": 0, "features": [], "error": "Coordonnées invalides"}

    x, y = _to_mercator(lonf, latf)
    half = 120.0  # demi-fenêtre (m) autour du point interrogé
    bbox = f"{x - half},{y - half},{x + half},{y + half}"
    params = {
        "SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetFeatureInfo",
        "LAYERS": LAYER, "QUERY_LAYERS": LAYER,
        "CRS": "EPSG:3857", "WIDTH": "101", "HEIGHT": "101", "I": "50", "J": "50",
        "INFO_FORMAT": "application/json", "FEATURE_COUNT": "20", "BBOX": bbox,
    }
    try:
        r = httpx.get(WMS, params=params, headers=_UA, timeout=timeout)
        r.raise_for_status()
        data = r.json()
    except Exception as e:  # noqa: BLE001 - hors ligne / service indisponible
        return {"ok": False, "count": 0, "features": [], "error": str(e)}

    feats = data.get("features", []) if isinstance(data, dict) else []
    out = []
    for f in feats:
        props = f.get("properties", {}) if isinstance(f, dict) else {}
        out.append({"label": _feature_label(props), "properties": props})
    return {"ok": True, "count": len(out), "features": out, "error": ""}

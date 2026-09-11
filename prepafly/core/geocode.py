"""Géocodage adresse -> coordonnées via OpenStreetMap Nominatim.

Sert à pré-remplir latitude/longitude à partir d'une adresse. Usage raisonnable
(un appel ponctuel à la validation d'un site) conforme à la politique Nominatim.
"""
from __future__ import annotations

import httpx

_URL = "https://nominatim.openstreetmap.org/search"
_UA = {"User-Agent": "PrepaFlyPy/1.0 (preparation vol drone)"}


def geocode(query: str, timeout: float = 8.0) -> dict | None:
    """Renvoie {lat, lon, label} pour la meilleure correspondance, ou None."""
    query = (query or "").strip()
    if not query:
        return None
    params = {"q": query, "format": "json", "limit": 1, "addressdetails": 0}
    r = httpx.get(_URL, params=params, headers=_UA, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if not data:
        return None
    top = data[0]
    return {"lat": float(top["lat"]), "lon": float(top["lon"]),
            "label": top.get("display_name", query)}


def geoportail_url(lat: float, lon: float) -> str:
    """Lien Géoportail centré sur le point (carte des restrictions)."""
    return f"https://www.geoportail.gouv.fr/carte?c={lon},{lat}&z=15&l0=GEOGRAPHICALGRIDSYSTEMS.MAPS"

"""Interrogation des contraintes drone à un point (couche IGN/Géoplateforme).

La carte affiche la couche raster « restrictions drone » (WMTS), qui n'est qu'une
image et n'est pas interrogeable. Pour obtenir la LISTE des zones à un point, on
interroge le service WFS (données vectorielles) de la Géoplateforme, qui renvoie
les polygones de restriction avec leurs attributs.

Couche : TRANSPORTS.DRONES.RESTRICTIONS:carte_restriction_drones_lf
(« Restrictions UAS catégorie Ouverte et Aéromodélisme », IGN/DGAC).
Attributs par zone : « limite » (plafond de hauteur en m ; 0 = interdiction) et
« remarque » (motif / précision).

L'appel est fait côté serveur (pas de contrainte CORS) et échoue proprement hors
ligne (l'appelant affiche l'erreur).
"""
from __future__ import annotations

import httpx

WFS = "https://data.geopf.fr/wfs/ows"
TYPENAME = "TRANSPORTS.DRONES.RESTRICTIONS:carte_restriction_drones_lf"
_UA = {"User-Agent": "PrepaFlyPy/1.0"}


def _feature_label(props: dict) -> str:
    """Libellé lisible d'une zone à partir de « limite » et « remarque »."""
    # IGN suffixe parfois d'un « * » renvoyant à une note : on l'enlève.
    lim = str(props.get("limite") or "").strip().rstrip(" *").strip()
    rem = str(props.get("remarque") or "").strip().rstrip(" *").strip()
    # « limite » est une hauteur en mètres (0 = vol interdit) ou parfois un texte.
    lim_txt = ""
    if lim:
        num = lim.replace(",", ".").replace(" ", "")
        if num.replace(".", "", 1).isdigit():
            val = float(num)
            lim_txt = "Vol interdit (0 m)" if val == 0 else f"Hauteur max {lim} m"
        else:
            lim_txt = lim
    if lim_txt and rem:
        return f"{lim_txt} — {rem}"
    if lim_txt:
        return lim_txt
    if rem:
        return rem
    parts = [f"{k}: {v}" for k, v in props.items()
             if v not in (None, "") and k not in ("geom", "geometry")][:3]
    return " / ".join(parts) if parts else "Zone de restriction (détails non fournis)"


def query_restrictions(lat: float, lon: float, timeout: float = 20.0) -> dict:
    """Renvoie les contraintes drone au point donné.

    Retour : {"ok": bool, "count": int, "features": [{"label": str,
    "properties": dict}], "error": str}. En cas d'absence de réseau ou d'erreur,
    ok=False et error est renseigné (l'appelant l'affiche tel quel)."""
    try:
        latf, lonf = float(lat), float(lon)
    except (TypeError, ValueError):
        return {"ok": False, "count": 0, "features": [], "error": "Coordonnées invalides"}

    # Petite fenêtre autour du point (~170 m). En CRS urn EPSG::4326, l'ordre des
    # axes est lat, lon : la BBOX suit donc lat_min, lon_min, lat_max, lon_max.
    d = 0.0016
    bbox = f"{latf - d},{lonf - d},{latf + d},{lonf + d},urn:ogc:def:crs:EPSG::4326"
    params = {
        "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
        "TYPENAMES": TYPENAME, "SRSNAME": "urn:ogc:def:crs:EPSG::4326",
        # On ne récupère que les attributs (pas la géométrie, lourde) : bien plus rapide.
        "PROPERTYNAME": "limite,remarque",
        "BBOX": bbox, "COUNT": "30", "outputFormat": "application/json",
    }
    try:
        r = httpx.get(WFS, params=params, headers=_UA, timeout=timeout)
        r.raise_for_status()
        data = r.json()
    except Exception as e:  # noqa: BLE001 - hors ligne / service indisponible
        return {"ok": False, "count": 0, "features": [], "error": str(e)}

    feats = data.get("features", []) if isinstance(data, dict) else []
    seen, out = set(), []
    for f in feats:
        props = (f.get("properties", {}) if isinstance(f, dict) else {}) or {}
        key = (props.get("limite"), props.get("remarque"))
        if key in seen:  # une même zone peut être renvoyée en plusieurs morceaux
            continue
        seen.add(key)
        out.append({"label": _feature_label(props), "properties": props})
    return {"ok": True, "count": len(out), "features": out, "error": ""}

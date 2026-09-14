"""Élévation du sol sur la zone de vol (API altimétrie IGN / Géoplateforme).

Interroge le service d'altimétrie (RGE ALTI, sans clé) sur les sommets de la zone
et renvoie l'altitude min/max. Sert à documenter la contrainte « Élévation du sol »
du dossier (tenir la hauteur réglementaire au-dessus de la surface).

Appel côté serveur (pas de CORS) ; échoue proprement hors ligne.
"""
from __future__ import annotations

import httpx

ALTI = "https://data.geopf.fr/altimetrie/1.0/calcul/alti/rest/elevation.json"
_UA = {"User-Agent": "PrepaFlyPy/1.0"}


def query_elevation(points: list, timeout: float = 12.0) -> dict:
    """Altitude min/max (m) sur les points fournis ([[lat, lon], …]).

    Retour : {"ok", "min", "max", "error"}.
    """
    pts = []
    for p in (points or []):
        try:
            pts.append((float(p[0]), float(p[1])))
        except (TypeError, ValueError, IndexError):
            pass
    pts = pts[:40]  # le service limite le nombre de points par requête
    if not pts:
        return {"ok": False, "min": None, "max": None, "error": "Aucune zone dessinée"}
    lats = "|".join(f"{la:.6f}" for la, _ in pts)
    lons = "|".join(f"{lo:.6f}" for _, lo in pts)
    params = {"lat": lats, "lon": lons, "resource": "ign_rge_alti_wld",
              "delimiter": "|", "zonly": "true"}
    try:
        r = httpx.get(ALTI, params=params, headers=_UA, timeout=timeout)
        r.raise_for_status()
        j = r.json()
    except Exception as e:  # noqa: BLE001 - hors ligne / service indisponible
        return {"ok": False, "min": None, "max": None, "error": str(e)}
    raw = j.get("elevations", [])
    zs = []
    for el in raw:
        z = el.get("z") if isinstance(el, dict) else el
        try:
            zf = float(z)
        except (TypeError, ValueError):
            continue
        if zf > -1000:  # -99999 = donnée absente
            zs.append(zf)
    if not zs:
        return {"ok": False, "min": None, "max": None, "error": "Pas de données d'altitude"}
    return {"ok": True, "min": round(min(zs), 1), "max": round(max(zs), 1), "error": ""}

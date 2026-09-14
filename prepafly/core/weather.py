"""Météo aéronautique : METAR/TAF depuis aviationweather.gov.

Comme dans l'application Tauri, l'accès réseau météo est restreint à ce seul
domaine. Les appels sont faits côté serveur (pas de contrainte CORS) et échouent
proprement hors ligne (l'appelant gère l'absence de réseau).
"""
from __future__ import annotations

import httpx

BASE = "https://aviationweather.gov/api/data"
_UA = {"User-Agent": "PrepaFlyPy/1.0"}


def metar(icao: str, timeout: float = 8.0) -> str:
    """Renvoie le METAR brut le plus récent pour un code OACI (ex. 'LFRS')."""
    icao = (icao or "").strip().upper()
    if not icao:
        raise ValueError("Code OACI manquant")
    url = f"{BASE}/metar?ids={icao}&format=raw"
    r = httpx.get(url, headers=_UA, timeout=timeout)
    r.raise_for_status()
    return r.text.strip()


def taf(icao: str, timeout: float = 8.0) -> str:
    """Renvoie le TAF brut pour un code OACI."""
    icao = (icao or "").strip().upper()
    if not icao:
        raise ValueError("Code OACI manquant")
    url = f"{BASE}/taf?ids={icao}&format=raw"
    r = httpx.get(url, headers=_UA, timeout=timeout)
    r.raise_for_status()
    return r.text.strip()


def brief(icao: str) -> dict:
    """METAR + TAF regroupés (chacun peut être vide si indisponible)."""
    out = {"icao": (icao or "").strip().upper(), "metar": "", "taf": "", "error": ""}
    try:
        out["metar"] = metar(icao)
    except Exception as e:  # noqa: BLE001 - on remonte l'erreur en texte
        out["error"] = str(e)
    try:
        out["taf"] = taf(icao)
    except Exception:  # noqa: BLE001
        pass
    return out


# --- Prévision horaire (Open-Meteo, gratuit, sans clé) ------------------------
OPEN_METEO = "https://api.open-meteo.com/v1/forecast"


def forecast_hourly(lat, lon, date: str = "", timeout: float = 10.0) -> dict:
    """Prévision heure par heure pour un point (et une date si fournie).

    Retour : {"ok", "date", "rows":[{heure,nuages,temp,pluie,vent,rafales,cap}], "error"}.
    Ne garde que les heures de jour (6 h–21 h). vent/rafales en km/h, cap = direction
    du vent en degrés. Open-Meteo ne fournit la prévision que ~16 jours à l'avance :
    hors de cette fenêtre, on renvoie ok=False proprement.
    """
    try:
        latf, lonf = float(lat), float(lon)
    except (TypeError, ValueError):
        return {"ok": False, "date": date, "rows": [], "error": "Coordonnées manquantes"}
    params = {
        "latitude": latf, "longitude": lonf,
        "hourly": "temperature_2m,precipitation,cloud_cover,wind_speed_10m,wind_gusts_10m,wind_direction_10m",
        "wind_speed_unit": "kmh", "timezone": "Europe/Paris",
    }
    if date:
        params["start_date"] = date
        params["end_date"] = date
    else:
        params["forecast_days"] = 1
    try:
        r = httpx.get(OPEN_METEO, params=params, headers=_UA, timeout=timeout)
        r.raise_for_status()
        j = r.json()
    except Exception as e:  # noqa: BLE001 - hors ligne / hors fenêtre de prévision
        return {"ok": False, "date": date, "rows": [], "error": str(e)}
    h = j.get("hourly", {}) or {}
    times = h.get("time", []) or []

    def col(name):
        return h.get(name, []) or []
    temp, prec, cloud = col("temperature_2m"), col("precipitation"), col("cloud_cover")
    wind, gust, wdir = col("wind_speed_10m"), col("wind_gusts_10m"), col("wind_direction_10m")
    rows = []
    for i, ts in enumerate(times):
        try:
            hour = int(ts[11:13])
        except (ValueError, IndexError):
            continue
        if hour < 6 or hour > 21:
            continue

        def g(arr):
            return arr[i] if i < len(arr) and arr[i] is not None else None
        rows.append({
            "heure": ts[11:16],
            "nuages": g(cloud), "temp": g(temp), "pluie": g(prec),
            "vent": round(g(wind)) if g(wind) is not None else None,
            "rafales": round(g(gust)) if g(gust) is not None else None,
            "cap": g(wdir),
        })
    return {"ok": True, "date": date or (times[0][:10] if times else ""), "rows": rows, "error": ""}

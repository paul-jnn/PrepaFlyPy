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

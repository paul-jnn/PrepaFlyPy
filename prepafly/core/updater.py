"""Vérification de mise à jour : compare la version installée à la dernière release
publiée sur GitHub. N'installe rien (contrairement à l'updater Tauri) : renvoie
l'info pour proposer le téléchargement. Silencieux et non bloquant hors ligne.
"""
from __future__ import annotations

import httpx

from .version import LATEST_API, RELEASES_URL, __version__


def _parse(v: str) -> tuple:
    v = (v or "").lstrip("vV").split("+")[0].split("-")[0]
    parts = []
    for x in v.split("."):
        try:
            parts.append(int(x))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def check(timeout: float = 6.0) -> dict:
    """Renvoie {current, latest, update_available, url}. Erreurs -> pas de maj."""
    out = {"current": __version__, "latest": None, "update_available": False, "url": RELEASES_URL}
    try:
        r = httpx.get(LATEST_API, headers={"Accept": "application/vnd.github+json",
                                           "User-Agent": "PrepaFlyPy"}, timeout=timeout)
        r.raise_for_status()
        tag = r.json().get("tag_name", "")
        out["latest"] = tag
        out["update_available"] = _parse(tag) > _parse(__version__)
    except Exception:  # noqa: BLE001
        pass
    return out

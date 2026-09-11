"""Internationalisation FR/EN (amorce). L'interface demande le dictionnaire de la
langue courante ; les clés absentes retombent sur le français."""
from __future__ import annotations

STRINGS = {
    "fr": {
        "app_title": "PrepaFlyPy — Préparation de vol drone",
        "nav_exploitant": "Exploitant",
        "nav_pilotes": "Télépilotes",
        "nav_dossiers": "Dossiers de vol",
        "nav_checklist": "Check-list pré-vol",
        "nav_docs": "Documents / MANEX",
        "nav_links": "Liens & contacts",
        "regime": "Régime d'exploitation",
        "generate_dossier": "Générer le dossier de vol",
        "generate_report": "Rapport de mission client",
        "generate_manex": "Générer la trame MANEX",
        "save": "Enregistrer",
        "saved": "Enregistré",
    },
    "en": {
        "app_title": "PrepaFlyPy — Drone flight preparation",
        "nav_exploitant": "Operator",
        "nav_pilotes": "Remote pilots",
        "nav_dossiers": "Flight files",
        "nav_checklist": "Pre-flight checklist",
        "nav_docs": "Documents / OpsManual",
        "nav_links": "Links & contacts",
        "regime": "Operating category",
        "generate_dossier": "Generate flight file",
        "generate_report": "Client mission report",
        "generate_manex": "Generate OpsManual draft",
        "save": "Save",
        "saved": "Saved",
    },
}

LANGUAGES = [("fr", "FR"), ("en", "EN")]


def strings(lang: str = "fr") -> dict:
    base = dict(STRINGS["fr"])
    base.update(STRINGS.get(lang, {}))
    return base

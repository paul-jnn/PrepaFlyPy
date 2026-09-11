"""Internationalisation FR/EN. L'interface demande le dictionnaire de la langue
courante (/api/i18n/<lang>) ; les clés absentes retombent sur le français.

La couverture s'étend progressivement : navigation, titres d'écran et libellés
communs d'abord ; les champs détaillés suivront."""
from __future__ import annotations

STRINGS = {
    "fr": {
        "app_title": "PrepaFlyPy — Préparation de vol drone",
        "section_consultation": "Consultation",
        "nav_exploitant": "Exploitant",
        "nav_pilotes": "Télépilotes",
        "nav_dossiers": "Dossiers de vol",
        "nav_carte": "Carte & restrictions",
        "nav_checklist": "Check-list pré-vol",
        "nav_docs": "Documents / MANEX",
        "nav_links": "Liens & contacts",
        "carte_sub": "Couches aéronautiques (restrictions drone), IGN et satellite, avec noms de communes. Nécessite Internet.",
        "carte_search": "Rechercher une adresse ou une commune…",
        "carte_go": "Aller",
        "carte_click": "Cliquez sur la carte pour lire les coordonnées.",
        "layer_osm": "OpenStreetMap (communes)",
        "layer_plan": "Plan IGN",
        "layer_ortho": "Satellite IGN",
        "layer_resto": "Restrictions drone (aéro)",
        "update_available": "Mise à jour {v} disponible.",
        "update_install": "Installer & redémarrer",
        "update_download": "Télécharger",
        "setup_title": "Bienvenue dans PrepaFlyPy",
        "setup_msg": "Ajouter un raccourci sur le Bureau et dans le menu Démarrer pour lancer l'application plus facilement ?",
        "setup_yes": "Oui, ajouter les raccourcis",
        "setup_no": "Non merci",
        "setup_done": "Raccourcis créés : {where}.",
        "save": "Enregistrer",
        "saved": "Enregistré",
    },
    "en": {
        "app_title": "PrepaFlyPy — Drone flight preparation",
        "section_consultation": "Reference",
        "nav_exploitant": "Operator",
        "nav_pilotes": "Remote pilots",
        "nav_dossiers": "Flight files",
        "nav_carte": "Map & restrictions",
        "nav_checklist": "Pre-flight checklist",
        "nav_docs": "Documents / OpsManual",
        "nav_links": "Links & contacts",
        "carte_sub": "Aeronautical layers (drone restrictions), IGN and satellite, with town names. Requires Internet.",
        "carte_search": "Search an address or town…",
        "carte_go": "Go",
        "carte_click": "Click the map to read coordinates.",
        "layer_osm": "OpenStreetMap (towns)",
        "layer_plan": "IGN map",
        "layer_ortho": "IGN satellite",
        "layer_resto": "Drone restrictions (aero)",
        "update_available": "Update {v} available.",
        "update_install": "Install & restart",
        "update_download": "Download",
        "setup_title": "Welcome to PrepaFlyPy",
        "setup_msg": "Add a shortcut on the Desktop and in the Start menu to launch the app more easily?",
        "setup_yes": "Yes, add shortcuts",
        "setup_no": "No thanks",
        "setup_done": "Shortcuts created: {where}.",
        "save": "Save",
        "saved": "Saved",
    },
}

LANGUAGES = [("fr", "FR"), ("en", "EN")]


def strings(lang: str = "fr") -> dict:
    base = dict(STRINGS["fr"])
    base.update(STRINGS.get(lang, {}))
    return base

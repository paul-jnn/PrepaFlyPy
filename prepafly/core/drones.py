"""Base de référence des drones DJI.

Chaque entrée décrit un modèle avec les valeurs utiles à l'analyse SORA et à la
détermination du régime :

  key    : identifiant unique et stable (ne jamais renommer : les dossiers
           enregistrés retrouvent leur appareil par cette clé).
  cat    : catégorie d'affichage (regroupe les modèles dans le sélecteur).
  modele : nom commercial.
  dim    : dimension caractéristique max, hélices dépliées (m).
  vit    : vitesse horizontale max (m/s), mode Sport/Manuel selon le modèle.
  masse  : masse au décollage (g). Pour les gros porteurs (Matrice lourds, cargo,
           Agras), config chargée/représentative : la masse réelle dépend du
           payload et des batteries, à vérifier au cas par cas.
  c      : classe C (marquage CE) usuelle ; "" = hors classe / legacy. À CONFIRMER
           sur le marquage réel de l'exemplaire ; certains modèles portent
           plusieurs classes selon firmware/kit (ex. Mini 4 Pro C0 ou C1 ;
           Matrice 400 C3, et C6 avec le Dock 3).

Ajouter un modèle = ajouter un dict à DRONES avec une nouvelle `key`.
Sources : fiches constructeur DJI et listes de certification EASA (2024-2026).
"""
from __future__ import annotations

from typing import Optional

DRONES: list[dict] = [
    # --- Mini < 250 g ---
    {"key": "neo",       "cat": "Mini < 250 g", "modele": "Neo",              "dim": 0.16, "vit": 8,  "masse": 135,   "c": "C0"},
    {"key": "neo2",      "cat": "Mini < 250 g", "modele": "Neo 2",            "dim": 0.16, "vit": 12, "masse": 151,   "c": "C0"},
    {"key": "flip",      "cat": "Mini < 250 g", "modele": "Flip",             "dim": 0.28, "vit": 12, "masse": 249,   "c": "C0"},
    {"key": "mini2se",   "cat": "Mini < 250 g", "modele": "Mini 2 SE",        "dim": 0.29, "vit": 16, "masse": 246,   "c": "C0"},
    {"key": "mini2",     "cat": "Mini < 250 g", "modele": "Mini 2",           "dim": 0.29, "vit": 16, "masse": 249,   "c": ""},
    {"key": "mini3",     "cat": "Mini < 250 g", "modele": "Mini 3",           "dim": 0.25, "vit": 16, "masse": 248,   "c": "C0"},
    {"key": "mini3pro",  "cat": "Mini < 250 g", "modele": "Mini 3 Pro",       "dim": 0.25, "vit": 16, "masse": 249,   "c": "C0"},
    {"key": "mini4k",    "cat": "Mini < 250 g", "modele": "Mini 4K",          "dim": 0.29, "vit": 16, "masse": 246,   "c": ""},
    {"key": "mini4pro",  "cat": "Mini < 250 g", "modele": "Mini 4 Pro",       "dim": 0.30, "vit": 16, "masse": 249,   "c": "C0"},
    {"key": "mini5pro",  "cat": "Mini < 250 g", "modele": "Mini 5 Pro",       "dim": 0.30, "vit": 18, "masse": 250,   "c": "C0"},
    # --- Grand public 250 g et + ---
    {"key": "air2",      "cat": "Grand public", "modele": "Air 2",            "dim": 0.32, "vit": 19, "masse": 570,   "c": ""},
    {"key": "air2s",     "cat": "Grand public", "modele": "Air 2S",           "dim": 0.32, "vit": 19, "masse": 595,   "c": "C1"},
    {"key": "air3",      "cat": "Grand public", "modele": "Air 3",            "dim": 0.33, "vit": 19, "masse": 720,   "c": "C1"},
    {"key": "air3s",     "cat": "Grand public", "modele": "Air 3S",           "dim": 0.33, "vit": 19, "masse": 724,   "c": "C1"},
    # --- Mavic (prosommateur) ---
    {"key": "mavic3classic", "cat": "Mavic",    "modele": "Mavic 3 Classic",  "dim": 0.38, "vit": 19, "masse": 895,   "c": "C1"},
    {"key": "mavic3",    "cat": "Mavic",        "modele": "Mavic 3",          "dim": 0.38, "vit": 19, "masse": 895,   "c": "C1"},
    {"key": "mavic3cine","cat": "Mavic",        "modele": "Mavic 3 Cine",     "dim": 0.38, "vit": 19, "masse": 899,   "c": "C1"},
    {"key": "mavic3pro", "cat": "Mavic",        "modele": "Mavic 3 Pro",      "dim": 0.38, "vit": 21, "masse": 958,   "c": "C2"},
    {"key": "mavic4pro", "cat": "Mavic",        "modele": "Mavic 4 Pro",      "dim": 0.39, "vit": 25, "masse": 1063,  "c": "C2"},
    {"key": "mavic2pro", "cat": "Mavic",        "modele": "Mavic 2 Pro",      "dim": 0.35, "vit": 20, "masse": 907,   "c": ""},
    {"key": "mavic2zoom","cat": "Mavic",        "modele": "Mavic 2 Zoom",     "dim": 0.35, "vit": 20, "masse": 905,   "c": ""},
    # --- FPV / immersif ---
    {"key": "avata2",    "cat": "FPV",          "modele": "Avata 2",          "dim": 0.19, "vit": 27, "masse": 377,   "c": "C1"},
    {"key": "avata",     "cat": "FPV",          "modele": "Avata",            "dim": 0.18, "vit": 27, "masse": 410,   "c": ""},
    {"key": "fpv",       "cat": "FPV",          "modele": "DJI FPV",          "dim": 0.31, "vit": 39, "masse": 795,   "c": ""},
    # --- Phantom / legacy ---
    {"key": "phantom4prov2", "cat": "Phantom",  "modele": "Phantom 4 Pro V2.0","dim": 0.35,"vit": 20, "masse": 1388,  "c": ""},
    {"key": "phantom4rtk","cat": "Phantom",     "modele": "Phantom 4 RTK",    "dim": 0.35, "vit": 20, "masse": 1391,  "c": ""},
    # --- Entreprise ---
    {"key": "mavic3e",   "cat": "Entreprise",   "modele": "Mavic 3E (Enterprise)", "dim": 0.38, "vit": 21, "masse": 915, "c": "C2"},
    {"key": "mavic3t",   "cat": "Entreprise",   "modele": "Mavic 3T (Thermal)",    "dim": 0.38, "vit": 21, "masse": 920, "c": "C2"},
    {"key": "mavic3m",   "cat": "Entreprise",   "modele": "Mavic 3M (Multispec.)", "dim": 0.38, "vit": 21, "masse": 980, "c": "C2"},
    {"key": "m4e",       "cat": "Entreprise",   "modele": "Matrice 4E",       "dim": 0.44, "vit": 21, "masse": 1219,  "c": "C2"},
    {"key": "m4t",       "cat": "Entreprise",   "modele": "Matrice 4T",       "dim": 0.44, "vit": 21, "masse": 1219,  "c": "C2"},
    {"key": "m4d",       "cat": "Entreprise",   "modele": "Matrice 4D",       "dim": 0.44, "vit": 21, "masse": 1233,  "c": "C2"},
    {"key": "m30",       "cat": "Entreprise",   "modele": "Matrice 30",       "dim": 0.67, "vit": 23, "masse": 3770,  "c": "C2"},
    {"key": "m30t",      "cat": "Entreprise",   "modele": "Matrice 30T",      "dim": 0.67, "vit": 23, "masse": 3770,  "c": "C2"},
    {"key": "m300",      "cat": "Entreprise",   "modele": "Matrice 300 RTK",  "dim": 0.90, "vit": 23, "masse": 6300,  "c": ""},
    {"key": "m350",      "cat": "Entreprise",   "modele": "Matrice 350 RTK",  "dim": 0.90, "vit": 23, "masse": 6470,  "c": ""},
    {"key": "m400",      "cat": "Entreprise",   "modele": "Matrice 400",      "dim": 1.07, "vit": 25, "masse": 9740,  "c": "C3"},
    # --- Inspire (cinéma pro) ---
    {"key": "inspire3",  "cat": "Inspire",      "modele": "Inspire 3",        "dim": 0.66, "vit": 24, "masse": 3995,  "c": "C3"},
    {"key": "inspire2",  "cat": "Inspire",      "modele": "Inspire 2",        "dim": 0.60, "vit": 26, "masse": 3440,  "c": ""},
    # --- Lourd / cargo ---
    {"key": "flycart30", "cat": "Lourd / cargo","modele": "FlyCart 30",       "dim": 3.09, "vit": 12, "masse": 42500, "c": ""},
    {"key": "flycart100","cat": "Lourd / cargo","modele": "FlyCart 100",      "dim": 3.22, "vit": 20, "masse": 55200, "c": ""},
    # --- Agricole (pulvérisation/épandage) — masse à pleine charge ---
    {"key": "agrast25",  "cat": "Agricole",     "modele": "Agras T25",        "dim": 2.80, "vit": 10, "masse": 52000, "c": ""},
    {"key": "agrast40",  "cat": "Agricole",     "modele": "Agras T40",        "dim": 3.00, "vit": 10, "masse": 50000, "c": ""},
    {"key": "agrast50",  "cat": "Agricole",     "modele": "Agras T50",        "dim": 3.09, "vit": 10, "masse": 52000, "c": ""},
    {"key": "agrast70p", "cat": "Agricole",     "modele": "Agras T70P",       "dim": 3.52, "vit": 14, "masse": 88000, "c": ""},
]

_BY_KEY = {d["key"]: d for d in DRONES}


def find(key: str) -> Optional[dict]:
    """Renvoie le modèle correspondant à `key`, ou None."""
    return _BY_KEY.get(key)


def by_category() -> dict[str, list[dict]]:
    """Regroupe les modèles par catégorie, dans l'ordre de DRONES."""
    out: dict[str, list[dict]] = {}
    for d in DRONES:
        out.setdefault(d["cat"], []).append(d)
    return out


def count() -> int:
    return len(DRONES)

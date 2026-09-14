"""Structures de données de l'application (le « store ») et leur normalisation.

Le store est un dict sérialisable en JSON — même forme que l'application Tauri,
pour que les sauvegardes soient interchangeables entre les deux outils. Les
fonctions empty_*() décrivent la forme vierge de chaque objet ; normalize()
garantit qu'un store lu depuis le disque a toujours la forme attendue (champs
complétés, anciens formats migrés).
"""
from __future__ import annotations

import time
import uuid

MENTIONS = ["A1", "A2", "A3", "STS-01", "STS-02", "CATS"]

STORE_VERSION = 1


def _uid(prefix: str) -> str:
    return prefix + uuid.uuid4().hex[:8]


def empty_exploitant() -> dict:
    return {"raison": "", "forme": "", "siret": "", "numUAS": "", "responsable": "",
            "adresse": "", "cp": "", "ville": "", "tel": "", "mail": "",
            "assureur": "", "police": "", "notes": ""}


def empty_pilote() -> dict:
    return {"id": _uid("p"), "prenom": "", "nom": "", "tel": "", "mail": "",
            "numTele": "", "brevets": "", "mentions": [], "habilitations": [], "notes": ""}


def empty_dossier() -> dict:
    return {
        "id": _uid("d"),
        "titre": "", "date": "", "lieu": "", "notes": "", "client": "",
        "dateDebut": "", "dateFin": "", "hauteurMax": "", "classeC": "", "typeVol": "",
        "environnement": "", "distanceTiers": "",
        "siteAdresse": "", "siteCp": "", "siteVille": "",
        "lat": "", "lon": "", "icao": "", "meteo": {},
        "regime": "", "sousCategorie": "", "pdra": "",
        "appareil": {"key": "", "marque": "", "modele": "", "masse": "", "serie": "",
                     "equipements": [], "numId": "", "numEnr": "", "geoloc": ""},
        # Points de contexte : décollage/atterrissage et observateurs (type, intitulé, lat, lon).
        "points": [],
        # Contraintes / points de vigilance notés par l'exploitant.
        "contraintesNotes": "",
        "grc": {"dim": "", "vit": "", "densite": "", "mini": False,
                "m1a": "none", "m1b": "none", "m1c": "none", "m2": "none"},
        "arc": {"atypical": "", "fl600": "", "airport": "", "airportClass": "",
                "above500": "", "adsb": "", "eac": "", "urban": "", "residual": "",
                "reduceJust": "", "tacJust": ""},
        "prevol": {}, "journal": [],
        "forms": {"regime": "", "expType": "morale", "derogType": "",
                  "aotGestionnaire": "", "aotObjet": ""},
    }


def empty_store() -> dict:
    return {"version": STORE_VERSION, "exploitant": empty_exploitant(), "pilotes": [],
            "referent": "", "dossiers": [], "currentId": "", "logo": ""}


def _merge(base: dict, over) -> dict:
    out = dict(base)
    if isinstance(over, dict):
        out.update(over)
    return out


def norm_dossier(d) -> dict:
    nd = empty_dossier()
    if isinstance(d, dict):
        nd.update(d)
        nd["appareil"] = _merge(empty_dossier()["appareil"], d.get("appareil"))
        nd["grc"] = _merge(empty_dossier()["grc"], d.get("grc"))
        nd["arc"] = _merge(empty_dossier()["arc"], d.get("arc"))
        nd["forms"] = _merge(empty_dossier()["forms"], d.get("forms"))
        nd["prevol"] = dict(d.get("prevol") or {})
        nd["meteo"] = dict(d.get("meteo") or {})
    if not isinstance(nd.get("journal"), list):
        nd["journal"] = []
    if not isinstance(nd.get("points"), list):
        nd["points"] = []
    if not isinstance(nd["appareil"].get("equipements"), list):
        nd["appareil"]["equipements"] = []
    return nd


def norm_pilote(p) -> dict:
    np = empty_pilote()
    if isinstance(p, dict):
        np.update(p)
    # mentions : ancien texte -> liste de codes
    mentions = np.get("mentions")
    if isinstance(mentions, str):
        np["mentions"] = [c for c in MENTIONS if c in mentions] if mentions else []
    elif not isinstance(mentions, list):
        np["mentions"] = []
    # habilitations : ancien texte -> une ligne {t, d}
    hab = np.get("habilitations")
    if isinstance(hab, str):
        np["habilitations"] = [{"t": hab.strip(), "d": ""}] if hab.strip() else []
    elif not isinstance(hab, list):
        np["habilitations"] = []
    np["habilitations"] = [_merge({"t": "", "d": ""}, h) for h in np["habilitations"]]
    return np


def normalize(raw) -> dict:
    """Ramène n'importe quel store (ancien/incomplet/vide) à la forme attendue."""
    s = empty_store()
    if isinstance(raw, dict):
        s.update(raw)
    s["version"] = STORE_VERSION
    s["exploitant"] = _merge(empty_exploitant(), (raw or {}).get("exploitant") if isinstance(raw, dict) else None)
    pilotes = s.get("pilotes")
    s["pilotes"] = [norm_pilote(p) for p in pilotes] if isinstance(pilotes, list) else []
    if s.get("referent") and not any(p["id"] == s["referent"] for p in s["pilotes"]):
        s["referent"] = s["pilotes"][0]["id"] if s["pilotes"] else ""
    dossiers = s.get("dossiers")
    if not isinstance(dossiers, list):
        dossiers = []
    # migration : ancien SORA unique -> premier dossier
    if not dossiers and isinstance(raw, dict) and raw.get("sora"):
        d = empty_dossier()
        d["titre"] = "Dossier importé"
        d["grc"] = _merge(d["grc"], raw["sora"].get("grc"))
        d["arc"] = _merge(d["arc"], raw["sora"].get("arc"))
        dossiers = [d]
    s["dossiers"] = [norm_dossier(d) for d in dossiers]
    if s.get("currentId") and not any(d["id"] == s["currentId"] for d in s["dossiers"]):
        s["currentId"] = ""
    if not isinstance(s.get("logo"), str):
        s["logo"] = ""
    return s


def new_dossier(titre: str = "") -> dict:
    d = empty_dossier()
    d["titre"] = titre
    d["date"] = time.strftime("%Y-%m-%d")
    return d


def hab_status(date_str: str):
    """Statut d'une date de validité d'habilitation : périmé / à renouveler / valide."""
    if not date_str:
        return None
    try:
        import datetime
        dt = datetime.date.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None
    days = (dt - __import__("datetime").date.today()).days
    if days < 0:
        return {"cls": "red", "txt": "Périmé"}
    if days <= 60:
        return {"cls": "orange", "txt": f"À renouveler ({days} j)"}
    return {"cls": "green", "txt": "Valide"}

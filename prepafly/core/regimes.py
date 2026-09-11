"""Régimes d'exploitation français/européens : recommandation et conformité.

À partir des infos de base d'un dossier (classe C, type de vol, environnement,
distance aux tiers, hauteur, masse), on propose le cadre réglementaire le plus
adapté et on vérifie la cohérence de la catégorie ouverte.

Rappels 2026 : les scénarios nationaux S-1/S-2/S-3 sont caducs depuis le
01/01/2026. Catégorie ouverte A1/A2/A3 (drones C0-C4), spécifique via STS
(déclaration), PDRA (autorisation allégée) ou SORA (autorisation complète).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

REGIME_LABEL = {
    "open": "Catégorie ouverte",
    "sts": "Catégorie spécifique — STS",
    "pdra": "Catégorie spécifique — PDRA",
    "sora": "Catégorie spécifique — SORA",
}
REGIME_SHORT = {"open": "OPEN", "sts": "STS", "pdra": "PDRA", "sora": "SORA"}

OPEN_CLASSES = ["C0", "C1", "C2", "C3", "C4"]


def _to_float(x) -> float:
    try:
        return float(str(x).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


@dataclass
class Recommendation:
    regime: str
    sub: Optional[str] = None
    why: str = ""
    missing: str = ""

    def as_dict(self) -> dict:
        return {"regime": self.regime, "sub": self.sub, "why": self.why,
                "missing": self.missing, "label": REGIME_LABEL.get(self.regime, ""),
                "short": REGIME_SHORT.get(self.regime, "")}


def recommend(d: dict) -> Recommendation:
    """Propose le régime le plus adapté. `d` = dict du dossier (champs de base)."""
    c = d.get("classeC", "")
    bvlos = d.get("typeVol") == "BVLOS"
    h = _to_float(d.get("hauteurMax")) or 0.0
    env = d.get("environnement", "")
    dist = d.get("distanceTiers", "")
    m = _to_float((d.get("appareil") or {}).get("masse")) or 0.0

    open_class = c in OPEN_CLASSES
    height_ok = (h == 0) or (h <= 120)

    missing = ""
    if not c:
        missing = "Renseignez la classe C du drone pour fiabiliser la recommandation."
    elif not d.get("typeVol"):
        missing = "Renseignez le type de vol (VLOS / BVLOS)."
    elif not env:
        missing = "Renseignez l'environnement survolé."

    # Catégorie ouverte : vol en vue, drone classé, <= 120 m, hors rassemblement, < 25 kg.
    if (not bvlos) and height_ok and open_class and env != "rassemblement" and m < 25000:
        if c in ("C0", "C1"):
            sub = "A1"
            why = (f"Drone {c}, vol en vue et ≤ 120 m : sous-catégorie A1 "
                   "(pas de survol intentionnel de tiers, jamais de rassemblement).")
        elif c == "C2" and dist in ("30m", "5m"):
            sub = "A2"
            why = ("Drone C2 avec distance de sécurité aux tiers (30 m, ou 5 m en "
                   "basse vitesse) : sous-catégorie A2 (examen A2 requis).")
        else:
            sub = "A3"
            why = (f"Drone {c} tenu à distance des zones habitées (≥ 150 m) et sans "
                   "tiers : sous-catégorie A3.")
        return Recommendation("open", sub, why, missing)

    # Scénarios standard européens (déclaration).
    if (not bvlos) and c == "C5" and height_ok:
        return Recommendation("sts", "STS-01",
                              "Vol en vue au-dessus d'une zone au sol contrôlée (même "
                              "peuplée), drone C5, ≤ 120 m : STS-01 (déclaration).", missing)
    if bvlos and c == "C6":
        return Recommendation("sts", "STS-02",
                              "Vol hors vue avec observateurs en zone peu peuplée, "
                              "drone C6 : STS-02 (déclaration).", missing)

    # Hors vue sans drone C6 : PDRA si couvert, sinon SORA.
    if bvlos:
        return Recommendation("pdra", None,
                              "Vol hors vue sans drone C6 : vérifiez si un PDRA (hors vue "
                              "en zone peu peuplée, inspection à faible hauteur…) couvre le "
                              "concept ; sinon SORA.", missing)

    return Recommendation("sora", None,
                          "Opération hors scénario standard et hors PDRA courant : analyse "
                          "SORA requise (autorisation d'exploitation).", missing)


def open_conformity(d: dict) -> dict:
    """Vérifie la cohérence de la catégorie ouverte pour un dossier.

    Renvoie {ok: bool, items: [{ok, text}]} : chaque item est un point de contrôle.
    """
    c = d.get("classeC", "")
    sub = d.get("sousCategorie", "")
    h = _to_float(d.get("hauteurMax")) or 0.0
    env = d.get("environnement", "")
    m = _to_float((d.get("appareil") or {}).get("masse")) or 0.0
    items: list[dict] = []

    def chk(ok: bool, text: str):
        items.append({"ok": bool(ok), "text": text})

    chk(c in OPEN_CLASSES, f"Classe C du drone compatible ouverte (C0-C4) : {c or '—'}")
    chk(h == 0 or h <= 120, f"Hauteur ≤ 120 m : {h or '—'} m")
    chk(env != "rassemblement", "Pas de survol de rassemblement de personnes")
    chk(m < 25000, f"Masse au décollage < 25 kg : {int(m) or '—'} g")

    if sub == "A1":
        chk(c in ("C0", "C1"), "A1 exige un drone C0 ou C1")
    elif sub == "A2":
        chk(c == "C2", "A2 exige un drone C2")
        chk(d.get("distanceTiers") in ("30m", "5m"), "A2 : distance de sécurité aux tiers (30 m / 5 m)")
    elif sub == "A3":
        chk(c in ("C2", "C3", "C4", "C0", "C1"), "A3 : drone classé, tenu à ≥ 150 m des zones habitées")

    return {"ok": all(i["ok"] for i in items), "items": items}

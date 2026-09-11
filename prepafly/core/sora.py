"""Moteur SORA 2.5 (méthode d'analyse de risque, guide DGAC/EASA).

Enchaînement : risque au sol (iGRC -> GRC) + risque en l'air (ARC) => SAIL (I..VI)
=> niveau de robustesse exigé pour chaque objectif de sécurité opérationnelle (OSO).

Les tables ci-dessous sont les données officielles ; les fonctions ne font que les
parcourir. Ce module est identique, dans sa logique, au moteur de l'application
Tauri « Assistant Vol Drone », vérifié sur plusieurs cas connus (voir tests/).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# --- Table iGRC : colonnes (appareil) x lignes (densité de population) ---------
# Colonnes : bornes supérieures de dimension (m) et de vitesse (m/s).
IGRC_COLS = [
    {"dim": 1, "spd": 25},
    {"dim": 3, "spd": 35},
    {"dim": 8, "spd": 75},
    {"dim": 20, "spd": 120},
    {"dim": 40, "spd": 200},
]
# Énergie critique indicative par colonne (kJ) — pour information.
IGRC_CRIT = [6.5, 65, 650, 6500, 65000]

# Lignes de densité. `vals` = iGRC pour chaque colonne (None = interdit / hors table).
IGRC_ROWS = [
    {"key": "ctrl",   "label": "Zone contrôlée au sol (tiers exclus)",          "vals": [1, 1, 2, 3, 3]},
    {"key": "d5",     "label": "< 5 hab/km² — isolé / rural",                   "vals": [2, 3, 4, 5, 6]},
    {"key": "d50",    "label": "< 50 hab/km² — faible peuplement",              "vals": [3, 4, 5, 6, 7]},
    {"key": "d500",   "label": "< 500 hab/km² — résidentiel peu dense",         "vals": [4, 5, 6, 7, 8]},
    {"key": "d5000",  "label": "< 5 000 hab/km² — péri-urbain",                 "vals": [5, 6, 7, 8, 9]},
    {"key": "d50000", "label": "< 50 000 hab/km² — urbain dense",               "vals": [6, 7, 8, 9, 10]},
    {"key": "dsup",   "label": "> 50 000 hab/km² — rassemblement de personnes", "vals": [7, 8, None, None, None]},
]

# Atténuations du risque au sol. Chaque option : (code, libellé, points retranchés).
MIT = {
    "m1a": {"label": "M1(A) — Stratégique · Facteur de refuge (sheltering)",
            "opts": [("none", "Absent / Faible", 0), ("low", "Faible", -1), ("med", "Moyenne", -2)]},
    "m1b": {"label": "M1(B) — Stratégique · Restrictions opérationnelles",
            "opts": [("none", "Absent", 0), ("med", "Moyenne", -1), ("high", "Haute", -2)]},
    "m1c": {"label": "M1(C) — Tactique · Observation au sol (VLOS)",
            "opts": [("none", "Absent", 0), ("low", "Faible", -1)]},
    "m2":  {"label": "M2 — Réduction des effets de l'impact au sol",
            "opts": [("none", "Absent / Faible", 0), ("med", "Moyenne", -1), ("high", "Haute", -2)]},
}

# Table SAIL : SAILT[GRC][index ARC], ARC a=0, b=1, c=2, d=3.
SAILT = {
    2: ["I", "II", "IV", "VI"],
    3: ["II", "II", "IV", "VI"],
    4: ["III", "III", "IV", "VI"],
    5: ["IV", "IV", "IV", "VI"],
    6: ["V", "V", "V", "VI"],
    7: ["VI", "VI", "VI", "VI"],
}

# Atténuation tactique requise selon l'ARC final.
TAC = {
    "a": {"nom": "Aucun minimum", "robustesse": "Aucune"},
    "b": {"nom": "Faible", "robustesse": "Faible"},
    "c": {"nom": "Moyen", "robustesse": "Moyenne"},
    "d": {"nom": "Haut", "robustesse": "Haute"},
}

# Objectifs de sécurité opérationnelle. `r` = robustesse exigée pour SAIL I..VI
# ('-' non requis, 'L' faible, 'M' moyen, 'H' haut).
OSO = [
    {"id": "01", "cat": "Technique",  "t": "Opérateur UAS compétent et/ou approuvé",            "r": ["-", "L", "M", "H", "H", "H"]},
    {"id": "02", "cat": "Technique",  "t": "Constructeur UAS compétent et/ou approuvé",         "r": ["-", "-", "L", "M", "H", "H"]},
    {"id": "03", "cat": "Technique",  "t": "Maintenance de l'UAS",                              "r": ["L", "L", "M", "M", "H", "H"]},
    {"id": "04", "cat": "Technique",  "t": "Composants essentiels selon standards de navigabilité", "r": ["-", "-", "-", "M", "H", "H"]},
    {"id": "05", "cat": "Technique",  "t": "UAS conçu selon standards fiabilité/sécurité",      "r": ["-", "-", "L", "M", "H", "H"]},
    {"id": "06", "cat": "Technique",  "t": "Performances du lien C3 appropriées",               "r": ["-", "L", "L", "M", "H", "H"]},
    {"id": "07", "cat": "Technique",  "t": "Vérification de conformité de la configuration UAS", "r": ["L", "L", "M", "M", "H", "H"]},
    {"id": "08", "cat": "Procédures", "t": "Procédures opérationnelles définies et validées",    "r": ["L", "M", "H", "H", "H", "H"]},
    {"id": "09", "cat": "Équipage",   "t": "Équipage formé et entraîné régulièrement",           "r": ["L", "L", "M", "M", "H", "H"]},
    {"id": "13", "cat": "Procédures", "t": "Systèmes externes de soutien adéquats",              "r": ["L", "L", "M", "H", "H", "H"]},
    {"id": "16", "cat": "Équipage",   "t": "Coordination intra-équipage",                        "r": ["L", "L", "M", "M", "H", "H"]},
    {"id": "17", "cat": "Équipage",   "t": "Équipage en capacité d'exploiter l'UAS",             "r": ["L", "L", "M", "M", "H", "H"]},
    {"id": "18", "cat": "Technique",  "t": "Protection auto. de l'enveloppe de vol",             "r": ["-", "-", "L", "M", "H", "H"]},
    {"id": "19", "cat": "Procédures", "t": "Retour à la normale après une erreur humaine",       "r": ["-", "-", "L", "M", "M", "H"]},
    {"id": "20", "cat": "Équipage",   "t": "Facteurs humains évalués, IHM adaptée",              "r": ["-", "L", "L", "M", "M", "H"]},
    {"id": "23", "cat": "Procédures", "t": "Conditions environnementales définies et surveillées", "r": ["L", "L", "M", "M", "H", "H"]},
    {"id": "24", "cat": "Technique",  "t": "UAS conçu/adapté aux conditions défavorables",       "r": ["-", "-", "M", "H", "H", "H"]},
]

REQ_TXT = {"L": "Faible (L)", "M": "Moyen (M)", "H": "Haut (H)", "-": "Non requis"}
_SAIL_ORDER = ["I", "II", "III", "IV", "V", "VI"]


def col_index(dim: float, vit: float) -> int:
    """Colonne iGRC de l'appareil : la plus pénalisante entre dimension et vitesse."""
    ci = cv = 0
    for i, col in enumerate(IGRC_COLS):
        if dim <= col["dim"]:
            ci = i
            break
        ci = i
    for i, col in enumerate(IGRC_COLS):
        if vit <= col["spd"]:
            cv = i
            break
        cv = i
    return max(ci, cv)


def _mit_val(kind: str, key: str) -> int:
    for code, _label, val in MIT[kind]["opts"]:
        if code == key:
            return val
    return 0


def compute_arc(arc: dict) -> str:
    """ARC initial (a..d) selon l'espace aérien, par arbre de décision."""
    def yes(k: str) -> bool:
        return arc.get(k) == "yes"
    if yes("atypical"):
        return "a"
    if yes("fl600"):
        return "b"
    if yes("airport"):
        return "d" if yes("airportClass") else "c"
    if yes("above500"):
        return "d" if (yes("adsb") or yes("eac")) else "c"
    if yes("adsb") or yes("eac") or yes("urban"):
        return "c"
    return "b"


@dataclass
class SoraResult:
    valid: bool = False
    col_index: Optional[int] = None
    igrc: Optional[int] = None
    crit: Optional[float] = None
    reduction: int = 0
    floor: Optional[int] = None
    grc: Optional[int] = None
    cumul_conflict: bool = False
    arc_initial: Optional[str] = None
    arc_residual: Optional[str] = None
    sail: Optional[str] = None
    sail_index: Optional[int] = None
    oso_req: list[dict] = field(default_factory=list)
    tac: Optional[dict] = None

    def as_dict(self) -> dict:
        return {
            "valid": self.valid, "colIndex": self.col_index, "igrc": self.igrc,
            "crit": self.crit, "reduction": self.reduction, "floor": self.floor,
            "grc": self.grc, "cumulConflict": self.cumul_conflict,
            "arcInitial": self.arc_initial, "arcResidual": self.arc_residual,
            "sail": self.sail, "sailIndex": self.sail_index, "osoReq": self.oso_req,
            "tac": self.tac,
        }


def _to_float(x) -> Optional[float]:
    try:
        return float(str(x).replace(",", "."))
    except (TypeError, ValueError):
        return None


def compute_sora(grc_in: dict, arc_in: dict) -> SoraResult:
    """Calcul SORA complet à partir des saisies GRC et ARC d'un dossier."""
    out = SoraResult()
    dim = _to_float(grc_in.get("dim"))
    vit = _to_float(grc_in.get("vit"))
    densite = grc_in.get("densite")

    if dim is not None and vit is not None and densite:
        ci = col_index(dim, vit)
        row = next((r for r in IGRC_ROWS if r["key"] == densite), None)
        if row is not None:
            igrc = row["vals"][ci]
            # Note 1 : < 250 g et <= 25 m/s => iGRC 1 (hors rassemblement).
            mini = bool(grc_in.get("mini")) and densite != "dsup"
            if mini:
                igrc = 1
            out.col_index = ci
            out.igrc = igrc
            out.crit = IGRC_CRIT[ci]
            red = (_mit_val("m1a", grc_in.get("m1a", "none"))
                   + _mit_val("m1b", grc_in.get("m1b", "none"))
                   + _mit_val("m1c", grc_in.get("m1c", "none"))
                   + _mit_val("m2", grc_in.get("m2", "none")))
            floor = IGRC_ROWS[0]["vals"][ci]  # plancher : le GRC ne descend jamais dessous
            out.reduction = red
            out.floor = floor
            out.grc = max(igrc + red, floor) if igrc is not None else None
            out.cumul_conflict = (grc_in.get("m1a") == "med" and grc_in.get("m1b", "none") != "none")
            out.valid = igrc is not None

    out.arc_initial = compute_arc(arc_in)
    out.arc_residual = arc_in.get("residual") or out.arc_initial
    out.tac = TAC.get(out.arc_residual)

    if out.grc is not None and out.arc_residual:
        if out.grc > 7:
            out.sail = "CERT"  # catégorie certifiée
        else:
            gc = max(2, min(7, out.grc))
            ai = {"a": 0, "b": 1, "c": 2, "d": 3}[out.arc_residual]
            out.sail = SAILT[gc][ai]

    if out.sail and out.sail != "CERT":
        si = _SAIL_ORDER.index(out.sail)
        out.sail_index = si
        out.oso_req = [{"id": o["id"], "cat": o["cat"], "t": o["t"], "lvl": o["r"][si]} for o in OSO]

    return out

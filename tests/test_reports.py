"""Tests de génération des PDF (dossier, rapport, MANEX, formulaires)."""
from prepafly.core import forms, models, reports


def _store():
    s = models.empty_store()
    s["exploitant"].update({"raison": "M.G.I.", "numUAS": "UAS-FR-368093",
                            "adresse": "12 Le Pinier", "cp": "85250", "ville": "Vendrennes",
                            "assureur": "AssurDrone"})
    p = models.empty_pilote()
    p.update({"prenom": "Paul", "nom": "Jeannin-Girardon", "numTele": "FR-XXXX",
              "mentions": ["A1", "A2", "STS-01"]})
    s["pilotes"] = [p]
    s["referent"] = p["id"]
    d = models.new_dossier("Inspection toiture")
    d.update({"client": "Client Test", "siteVille": "La Roche-sur-Yon",
              "classeC": "C2", "typeVol": "VLOS", "hauteurMax": "45",
              "regime": "sora", "appareil": {"key": "m30", "modele": "Matrice 30",
                                             "masse": "3770", "serie": "SN123"},
              "grc": {"dim": "0.67", "vit": "23", "densite": "d500"},
              "arc": {"residual": "b"},
              "prevol": {"NOTAM consultés": True, "Météo vérifiée": True, "Périmètre": False},
              "journal": [{"date": "2026-09-10", "debut": "09:00", "fin": "10:30",
                           "nb": 3, "incidents": "RAS"}]})
    s["dossiers"] = [d]
    s["currentId"] = d["id"]
    return s, d


def test_dossier_pdf():
    s, d = _store()
    pdf = reports.dossier_pdf(s, d)
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 2000


def test_rapport_pdf():
    s, d = _store()
    pdf = reports.rapport_pdf(s, d)
    assert pdf[:4] == b"%PDF"


def test_manex_pdf():
    s, _ = _store()
    pdf = reports.manex_pdf(s)
    assert pdf[:4] == b"%PDF"


def test_forms_generate():
    s, d = _store()
    for kind in ("cerfa", "derog", "aot"):
        pdf = forms.generate(kind, s, d)
        assert pdf[:4] == b"%PDF", f"{kind} n'a pas produit de PDF"

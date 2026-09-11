"""Tests du moteur SORA 2.5 sur des cas calculables à la main."""
from prepafly.core import sora


def test_igrc_lookup_and_note1():
    # d500, colonne 0 (petit drone lent) => iGRC 4 sans Note 1.
    r = sora.compute_sora({"dim": 0.30, "vit": 16, "densite": "d500"}, {})
    assert r.col_index == 0
    assert r.igrc == 4
    # Note 1 (< 250 g et <= 25 m/s) ramène l'iGRC à 1.
    r2 = sora.compute_sora({"dim": 0.30, "vit": 16, "densite": "d500", "mini": True}, {})
    assert r2.igrc == 1
    assert r2.grc == 1


def test_column_selected_by_speed():
    # DJI FPV : dim 0.31 m (col 0) mais 39 m/s => colonne vitesse index 2.
    r = sora.compute_sora({"dim": 0.31, "vit": 39, "densite": "d5"}, {})
    assert r.col_index == 2
    assert r.igrc == 4  # ligne d5 [2,3,4,5,6], colonne 2


def test_mitigations_and_floor():
    # d5000 col0 => iGRC 5 ; M1(A) med (-2) + M2 high (-2) = -4 ; plancher = 1.
    grc = {"dim": 0.3, "vit": 15, "densite": "d5000", "m1a": "med", "m2": "high"}
    r = sora.compute_sora(grc, {})
    assert r.igrc == 5
    assert r.reduction == -4
    assert r.floor == 1
    assert r.grc == 1  # max(5-4, 1)


def test_sail_from_grc_and_arc():
    r = sora.compute_sora({"dim": 0.3, "vit": 15, "densite": "d5000"},
                          {"residual": "c"})
    assert r.grc == 5
    assert r.arc_residual == "c"
    assert r.sail == "IV"          # SAILT[5][c=2]
    assert r.sail_index == 3
    # OSO 08 (procédures) exige robustesse Haute (H) à SAIL IV.
    oso08 = next(o for o in r.oso_req if o["id"] == "08")
    assert oso08["lvl"] == "H"


def test_grc_over_7_is_cert():
    # dim 25 m => colonne 4 ; d50000 col4 => 10 (> 7) => catégorie certifiée.
    r = sora.compute_sora({"dim": 25, "vit": 10, "densite": "d50000"}, {"residual": "b"})
    assert r.grc == 10
    assert r.sail == "CERT"
    assert r.oso_req == []


def test_arc_decision_tree():
    assert sora.compute_arc({"atypical": "yes"}) == "a"
    assert sora.compute_arc({"fl600": "yes"}) == "b"
    assert sora.compute_arc({"airport": "yes", "airportClass": "yes"}) == "d"
    assert sora.compute_arc({"airport": "yes"}) == "c"
    assert sora.compute_arc({"above500": "yes", "adsb": "yes"}) == "d"
    assert sora.compute_arc({"above500": "yes"}) == "c"
    assert sora.compute_arc({"urban": "yes"}) == "c"
    assert sora.compute_arc({}) == "b"


def test_dsup_restricted_columns():
    # Rassemblement, colonne 2 = interdit (None) => pas de résultat valide.
    r = sora.compute_sora({"dim": 5, "vit": 15, "densite": "dsup"}, {})
    assert r.igrc is None
    assert r.valid is False
    assert r.grc is None


def test_invalid_inputs_are_safe():
    r = sora.compute_sora({"dim": "", "vit": "", "densite": ""}, {})
    assert r.valid is False
    assert r.grc is None
    # ARC est toujours calculé (défaut 'b').
    assert r.arc_initial == "b"

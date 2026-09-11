"""Tests de la base de référence des drones DJI."""
from prepafly.core import drones


def test_count_and_unique_keys():
    assert drones.count() >= 45
    keys = [d["key"] for d in drones.DRONES]
    assert len(keys) == len(set(keys)), "clés de drone dupliquées"


def test_find_known_models():
    assert drones.find("m4t")["masse"] == 1219
    assert drones.find("mavic4pro")["c"] == "C2"
    assert drones.find("neo")["masse"] == 135
    assert drones.find("inconnu") is None


def test_all_fields_present_and_valid():
    valid_c = {"", "C0", "C1", "C2", "C3", "C4", "C5", "C6"}
    for d in drones.DRONES:
        assert set(d) >= {"key", "cat", "modele", "dim", "vit", "masse", "c"}
        assert d["c"] in valid_c
        assert d["dim"] > 0 and d["vit"] > 0 and d["masse"] > 0


def test_matrice_4_series_present():
    models = {d["modele"] for d in drones.DRONES}
    assert "Matrice 4E" in models
    assert "Matrice 4T" in models
    assert "Matrice 400" in models


def test_by_category_groups():
    cats = drones.by_category()
    assert "Entreprise" in cats and "Mini < 250 g" in cats
    total = sum(len(v) for v in cats.values())
    assert total == drones.count()

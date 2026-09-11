"""Tests de la recommandation de régime et de la conformité ouverte."""
from prepafly.core import regimes


def _d(**kw):
    base = {"classeC": "", "typeVol": "", "environnement": "hors", "distanceTiers": "",
            "hauteurMax": "80", "appareil": {"masse": "500"}, "sousCategorie": ""}
    base.update(kw)
    return base


def test_open_a1():
    r = regimes.recommend(_d(classeC="C0", typeVol="VLOS"))
    assert r.regime == "open" and r.sub == "A1"


def test_open_a2_requires_distance():
    r = regimes.recommend(_d(classeC="C2", typeVol="VLOS", distanceTiers="30m"))
    assert r.regime == "open" and r.sub == "A2"
    # Sans distance de sécurité, C2 bascule en A3.
    r2 = regimes.recommend(_d(classeC="C2", typeVol="VLOS"))
    assert r2.regime == "open" and r2.sub == "A3"


def test_sts_01_and_02():
    r1 = regimes.recommend(_d(classeC="C5", typeVol="VLOS"))
    assert r1.regime == "sts" and r1.sub == "STS-01"
    r2 = regimes.recommend(_d(classeC="C6", typeVol="BVLOS"))
    assert r2.regime == "sts" and r2.sub == "STS-02"


def test_pdra_when_bvlos_without_c6():
    r = regimes.recommend(_d(classeC="C2", typeVol="BVLOS"))
    assert r.regime == "pdra"


def test_sora_when_rassemblement():
    r = regimes.recommend(_d(classeC="C1", typeVol="VLOS", environnement="rassemblement"))
    assert r.regime == "sora"


def test_missing_info_flagged():
    r = regimes.recommend(_d(classeC="", typeVol="VLOS"))
    assert r.missing  # message non vide


def test_open_conformity():
    d = _d(classeC="C0", typeVol="VLOS", sousCategorie="A1", hauteurMax="100",
           appareil={"masse": "249"})
    conf = regimes.open_conformity(d)
    assert conf["ok"] is True
    # Hauteur > 120 => non conforme.
    d2 = _d(classeC="C0", typeVol="VLOS", sousCategorie="A1", hauteurMax="150",
            appareil={"masse": "249"})
    assert regimes.open_conformity(d2)["ok"] is False

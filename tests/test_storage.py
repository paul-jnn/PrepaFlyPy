"""Tests du stockage : round-trip JSON, PIN, normalisation/migration."""
import os

import pytest

from prepafly.core import models, storage


@pytest.fixture(autouse=True)
def tmp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("PREPAFLY_DATA_DIR", str(tmp_path))
    yield


def test_empty_store_on_first_use():
    s = storage.load_store()
    assert s["exploitant"]["raison"] == ""
    assert s["dossiers"] == []


def test_save_and_load_roundtrip():
    s = models.empty_store()
    s["exploitant"]["raison"] = "M.G.I."
    d = models.new_dossier("Test")
    s["dossiers"] = [d]
    storage.save_store(s)
    s2 = storage.load_store()
    assert s2["exploitant"]["raison"] == "M.G.I."
    assert s2["dossiers"][0]["titre"] == "Test"


def test_pin():
    assert storage.pin_status() is False
    storage.set_pin("1234")
    assert storage.pin_status() is True
    assert storage.verify_pin("1234") is True
    assert storage.verify_pin("0000") is False
    with pytest.raises(ValueError):
        storage.set_pin("12")
    storage.reset_pin()
    assert storage.pin_status() is False


def test_normalize_migrates_legacy_mentions():
    raw = {"pilotes": [{"prenom": "P", "mentions": "A1 A2", "habilitations": "NF C 18-510"}]}
    s = models.normalize(raw)
    assert s["pilotes"][0]["mentions"] == ["A1", "A2"]
    assert s["pilotes"][0]["habilitations"][0]["t"] == "NF C 18-510"


def test_normalize_migrates_single_sora():
    raw = {"sora": {"grc": {"dim": "0.3"}, "arc": {"residual": "b"}}}
    s = models.normalize(raw)
    assert len(s["dossiers"]) == 1
    assert s["dossiers"][0]["grc"]["dim"] == "0.3"


def test_documents(tmp_path):
    name = storage.import_doc("assurance.pdf", b"%PDF-1.4 test")
    assert name == "assurance.pdf"
    assert any(x["name"] == "assurance.pdf" for x in storage.list_docs())
    assert storage.read_doc("assurance.pdf") == b"%PDF-1.4 test"
    storage.delete_doc("assurance.pdf")
    assert storage.list_docs() == []

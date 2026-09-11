"""Tests d'intégration de l'API FastAPI (via TestClient, sans réseau)."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PREPAFLY_DATA_DIR", str(tmp_path))
    from prepafly.server import app
    return TestClient(app)


def test_meta_and_drones(client):
    m = client.get("/api/meta").json()
    assert m["dronesCount"] >= 45
    dr = client.get("/api/drones").json()
    assert len(dr["all"]) >= 45
    assert "Entreprise" in dr["byCategory"]


def test_store_roundtrip(client):
    s = client.get("/api/store").json()
    s["exploitant"]["raison"] = "M.G.I."
    assert client.put("/api/store", json=s).json()["ok"] is True
    assert client.get("/api/store").json()["exploitant"]["raison"] == "M.G.I."


def test_sora_endpoint(client):
    r = client.post("/api/sora", json={"grc": {"dim": 0.3, "vit": 15, "densite": "d5000"},
                                       "arc": {"residual": "c"}}).json()
    assert r["grc"] == 5 and r["sail"] == "IV"


def test_regime_endpoint(client):
    r = client.post("/api/regime", json={"classeC": "C0", "typeVol": "VLOS",
                                         "environnement": "hors", "appareil": {"masse": "249"}}).json()
    assert r["regime"] == "open" and r["sub"] == "A1"


def test_pin_flow(client):
    assert client.get("/api/pin/status").json()["set"] is False
    assert client.post("/api/pin/set", json={"pin": "4321"}).json()["ok"] is True
    assert client.post("/api/pin/verify", json={"pin": "4321"}).json()["ok"] is True
    assert client.post("/api/pin/verify", json={"pin": "0000"}).json()["ok"] is False


def test_pdf_generation_endpoints(client):
    s = client.get("/api/store").json()
    s["exploitant"]["raison"] = "M.G.I."
    d = {"id": "dtest", "titre": "Mission", "regime": "sora",
         "appareil": {"key": "m30", "modele": "Matrice 30", "masse": "3770"},
         "grc": {"dim": "0.67", "vit": "23", "densite": "d500"}, "arc": {"residual": "b"},
         "prevol": {"Météo": True}, "journal": []}
    s["dossiers"] = [d]
    client.put("/api/store", json=s)
    for path in ("/api/report/dossier", "/api/report/rapport"):
        r = client.post(path, json={"dossierId": "dtest"})
        assert r.status_code == 200 and r.content[:4] == b"%PDF"
    assert client.post("/api/report/manex").content[:4] == b"%PDF"
    for kind in ("cerfa", "derog", "aot"):
        r = client.post(f"/api/form/{kind}", json={"dossierId": "dtest"})
        assert r.status_code == 200 and r.content[:4] == b"%PDF"


def test_backup_download(client):
    r = client.get("/api/backup")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")


def test_index_served(client):
    r = client.get("/")
    assert r.status_code == 200 and "PrepaFlyPy" in r.text

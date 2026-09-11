"""API FastAPI de PrepaFlyPy.

Ce module est l'équivalent de la « coque » : il expose le cœur métier sous forme
d'endpoints que l'interface web appelle par fetch. Toute la logique reste dans
prepafly.core ; ici on ne fait que router les requêtes et sérialiser les réponses.

Lancement direct :  uvicorn prepafly.server:app
ou via l'app :      python -m prepafly --web
"""
from __future__ import annotations

import base64
import io
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .core import (drones, forms, geocode, i18n, models, regimes, reports,
                   sora, storage, updater, weather)
from .core.version import RELEASES_URL, REPO_URL, __version__

WEB_DIR = Path(__file__).resolve().parent / "web"

app = FastAPI(title="PrepaFlyPy", version=__version__)


# --- Méta / références --------------------------------------------------------
@app.get("/api/meta")
def meta():
    return {"version": __version__, "dronesCount": drones.count(),
            "languages": i18n.LANGUAGES, "repo": REPO_URL, "releases": RELEASES_URL}


@app.get("/api/i18n/{lang}")
def i18n_strings(lang: str):
    return i18n.strings(lang)


@app.get("/api/drones")
def list_drones():
    return {"all": drones.DRONES, "byCategory": drones.by_category()}


@app.get("/api/update")
def check_update():
    return updater.check()


# --- Store (données) ----------------------------------------------------------
@app.get("/api/store")
def get_store():
    return storage.load_store()


@app.put("/api/store")
async def put_store(request: Request):
    body = await request.json()
    storage.save_store(body)
    return {"ok": True}


# --- Moteur SORA / régimes ----------------------------------------------------
@app.post("/api/sora")
async def api_sora(request: Request):
    body = await request.json()
    res = sora.compute_sora(body.get("grc", {}), body.get("arc", {}))
    return res.as_dict()


@app.post("/api/regime")
async def api_regime(request: Request):
    body = await request.json()
    return regimes.recommend(body).as_dict()


@app.post("/api/regime/open")
async def api_open_conformity(request: Request):
    body = await request.json()
    return regimes.open_conformity(body)


# --- PIN ----------------------------------------------------------------------
@app.get("/api/pin/status")
def pin_status():
    return {"set": storage.pin_status()}


@app.post("/api/pin/set")
async def pin_set(request: Request):
    pin = (await request.json()).get("pin", "")
    try:
        storage.set_pin(pin)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@app.post("/api/pin/verify")
async def pin_verify(request: Request):
    pin = (await request.json()).get("pin", "")
    return {"ok": storage.verify_pin(pin)}


# --- Météo / géocodage --------------------------------------------------------
@app.get("/api/weather")
def api_weather(icao: str):
    return weather.brief(icao)


@app.get("/api/geocode")
def api_geocode(q: str):
    try:
        res = geocode.geocode(q)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Géocodage indisponible : {e}")
    if not res:
        raise HTTPException(404, "Adresse introuvable")
    return res


# --- Documents (justificatifs) ------------------------------------------------
@app.get("/api/docs")
def docs_list():
    return storage.list_docs()


@app.post("/api/docs")
async def docs_upload(file: UploadFile):
    data = await file.read()
    name = storage.import_doc(file.filename or "document", data)
    return {"name": name}


@app.get("/api/docs/{name}")
def docs_read(name: str):
    try:
        data = storage.read_doc(name)
    except FileNotFoundError:
        raise HTTPException(404, "introuvable")
    media = "application/pdf" if name.lower().endswith(".pdf") else "application/octet-stream"
    return Response(content=data, media_type=media,
                    headers={"Content-Disposition": f'inline; filename="{name}"'})


@app.delete("/api/docs/{name}")
def docs_delete(name: str):
    storage.delete_doc(name)
    return {"ok": True}


# --- Génération de documents (PDF) --------------------------------------------
def _current(store, dossier_id):
    for d in store.get("dossiers", []):
        if d["id"] == dossier_id:
            return d
    raise HTTPException(404, "Dossier introuvable")


def _pdf(data: bytes, filename: str) -> Response:
    return Response(content=data, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.post("/api/report/dossier")
async def report_dossier(request: Request):
    body = await request.json()
    store = storage.load_store()
    d = _current(store, body.get("dossierId"))
    return _pdf(reports.dossier_pdf(store, d), "dossier_de_vol.pdf")


@app.post("/api/report/rapport")
async def report_rapport(request: Request):
    body = await request.json()
    store = storage.load_store()
    d = _current(store, body.get("dossierId"))
    return _pdf(reports.rapport_pdf(store, d), "rapport_mission.pdf")


@app.post("/api/report/manex")
def report_manex():
    store = storage.load_store()
    return _pdf(reports.manex_pdf(store), "manex_trame.pdf")


@app.post("/api/form/{kind}")
async def gen_form(kind: str, request: Request):
    body = await request.json()
    store = storage.load_store()
    d = _current(store, body.get("dossierId"))
    try:
        data = forms.generate(kind, store, d)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _pdf(data, f"{kind}.pdf")


# --- Sauvegarde / restauration ------------------------------------------------
@app.get("/api/backup")
def backup_download():
    import json
    store = storage.load_store()
    data = json.dumps(store, ensure_ascii=False, indent=2).encode("utf-8")
    return Response(content=data, media_type="application/json",
                    headers={"Content-Disposition": 'attachment; filename="sauvegarde_prepaflypy.json"'})


@app.post("/api/backup")
async def backup_restore(request: Request):
    body = await request.json()
    storage.save_store(models.normalize(body))
    return {"ok": True}


# --- Interface web ------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def index():
    idx = WEB_DIR / "index.html"
    if idx.exists():
        return HTMLResponse(idx.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>PrepaFlyPy</h1><p>Interface non trouvée.</p>")


if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

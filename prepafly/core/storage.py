"""Stockage local : dossier de configuration, données JSON, PIN, documents.

Tout vit HORS du programme, dans le dossier de données utilisateur propre à chaque
poste (via platformdirs). Les données survivent donc aux mises à jour. Écriture
atomique (fichier temporaire puis renommage) pour ne jamais corrompre le JSON.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from platformdirs import user_data_dir

from . import models, security

APP_NAME = "PrepaFlyPy"
APP_AUTHOR = "MGI"


def data_root() -> Path:
    p = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    p.mkdir(parents=True, exist_ok=True)
    return p


def _override_root() -> Path | None:
    # Permet de rediriger le stockage (tests, poste portable) via une variable
    # d'environnement, sans toucher aux données réelles de l'utilisateur.
    env = os.environ.get("PREPAFLY_DATA_DIR")
    if env:
        p = Path(env)
        p.mkdir(parents=True, exist_ok=True)
        return p
    return None


def root() -> Path:
    return _override_root() or data_root()


def data_file() -> Path:
    return root() / "donnees.json"


def pin_file() -> Path:
    return root() / "pin.hash"


def docs_dir() -> Path:
    d = root() / "documents"
    d.mkdir(parents=True, exist_ok=True)
    return d


# --- Premier lancement (proposition de raccourcis) ---------------------------

def _setup_marker() -> Path:
    return root() / ".setup_done"


def first_run() -> bool:
    """Vrai tant que la proposition d'installation n'a pas été traitée."""
    return not _setup_marker().exists()


def mark_setup_done() -> None:
    try:
        _setup_marker().write_text("1", encoding="utf-8")
    except OSError:
        pass


# --- Données -----------------------------------------------------------------

def load_store() -> dict:
    """Lit et normalise le store. Une première utilisation démarre vierge."""
    f = data_file()
    if not f.exists():
        return models.empty_store()
    try:
        raw = json.loads(f.read_text(encoding="utf-8") or "{}")
    except (json.JSONDecodeError, OSError):
        raw = {}
    return models.normalize(raw)


def save_store(store: dict) -> None:
    """Écriture atomique du store normalisé."""
    store = models.normalize(store)
    f = data_file()
    tmp = f.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, f)


def export_backup(dest: str | Path) -> Path:
    """Copie le fichier de données vers `dest` (sauvegarde JSON)."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(load_store(), ensure_ascii=False, indent=2), encoding="utf-8")
    return dest


def import_backup(src: str | Path) -> dict:
    """Restaure un store depuis un fichier JSON (remplace les données)."""
    raw = json.loads(Path(src).read_text(encoding="utf-8"))
    store = models.normalize(raw)
    save_store(store)
    return store


# --- PIN ----------------------------------------------------------------------

def pin_status() -> bool:
    return pin_file().exists()


def set_pin(pin: str) -> None:
    if len(pin) < 4:
        raise ValueError("Le code PIN doit comporter au moins 4 chiffres.")
    pin_file().write_text(security.hash_pin(pin), encoding="utf-8")


def verify_pin(pin: str) -> bool:
    try:
        return pin_file().read_text(encoding="utf-8").strip() == security.hash_pin(pin)
    except OSError:
        return False


def reset_pin() -> None:
    """Supprime le PIN (secours si oublié). Les données restent intactes."""
    try:
        pin_file().unlink()
    except FileNotFoundError:
        pass


# --- Documents (justificatifs : MANEX, assurance, attestations…) --------------

def _sanitize(name: str) -> str:
    bad = '\\/:*?"<>|'
    out = "".join("_" if ch in bad else ch for ch in name).strip().strip(".")
    return out or "Sans_titre"


def import_doc(filename: str, data: bytes) -> str:
    name = _sanitize(filename)
    (docs_dir() / name).write_bytes(data)
    return name


def list_docs() -> list[dict]:
    out = []
    for p in sorted(docs_dir().iterdir()):
        if p.is_file():
            out.append({"name": p.name, "size": p.stat().st_size})
    return out


def read_doc(filename: str) -> bytes:
    return (docs_dir() / _sanitize(filename)).read_bytes()


def doc_path(filename: str) -> str:
    p = docs_dir() / _sanitize(filename)
    if not p.exists():
        raise FileNotFoundError("introuvable")
    return str(p)


def delete_doc(filename: str) -> None:
    (docs_dir() / _sanitize(filename)).unlink(missing_ok=True)


def export_doc(filename: str, dest_dir: str | Path) -> Path:
    name = _sanitize(filename)
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dst = dest_dir / name
    shutil.copy(docs_dir() / name, dst)
    return dst

"""Mise à jour automatique.

Deux niveaux :
  - check() : compare la version installée à la dernière release GitHub (silencieux
    et non bloquant hors ligne).
  - apply_update() : quand l'application tourne en exécutable packagé (PyInstaller),
    télécharge le nouvel .exe depuis la release, puis lance un petit script qui
    attend la fermeture de l'app, remplace l'exe et relance — l'équivalent du
    « Installer & redémarrer » de la version Rust/Tauri. En mode développement
    (non figé), apply_update refuse et on retombe sur le lien de téléchargement.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

import httpx

from .version import LATEST_API, RELEASES_URL, __version__


def _parse(v: str) -> tuple:
    v = (v or "").lstrip("vV").split("+")[0].split("-")[0]
    parts = []
    for x in v.split("."):
        try:
            parts.append(int(x))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def is_frozen() -> bool:
    """Vrai quand on tourne dans l'exécutable packagé (et non en dev Python)."""
    return bool(getattr(sys, "frozen", False))


def _latest_release(timeout: float = 8.0) -> dict:
    r = httpx.get(LATEST_API, headers={"Accept": "application/vnd.github+json",
                                       "User-Agent": "PrepaFlyPy"}, timeout=timeout)
    r.raise_for_status()
    return r.json()


def check(timeout: float = 6.0) -> dict:
    """Renvoie {current, latest, update_available, url, can_auto}. Erreurs -> pas de maj."""
    out = {"current": __version__, "latest": None, "update_available": False,
           "url": RELEASES_URL, "can_auto": is_frozen()}
    try:
        rel = _latest_release(timeout)
        tag = rel.get("tag_name", "")
        out["latest"] = tag
        out["update_available"] = _parse(tag) > _parse(__version__)
    except Exception:  # noqa: BLE001
        pass
    return out


def _asset_name() -> str:
    return "PrepaFlyPy-windows.exe" if os.name == "nt" else "PrepaFlyPy-linux"


def _asset_url(release: dict) -> str | None:
    want = _asset_name()
    for a in release.get("assets", []):
        if a.get("name") == want:
            return a.get("browser_download_url")
    return None


def _download(url: str, dest: str) -> None:
    with httpx.stream("GET", url, follow_redirects=True, timeout=None) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=1 << 16):
                f.write(chunk)


# Script Windows : attend que l'exe se libère, le remplace, relance, se nettoie.
_WIN_SWAP = """@echo off
setlocal enableextensions
set "EXE={exe}"
set "NEW={new}"
set /a n=0
:wait
set /a n+=1
move /Y "%EXE%" "%EXE%.old" >nul 2>&1
if exist "%EXE%" (
  if %n% GEQ 60 goto relaunch_old
  ping -n 2 127.0.0.1 >nul
  goto wait
)
move /Y "%NEW%" "%EXE%" >nul 2>&1
start "" "%EXE%"
del "%EXE%.old" >nul 2>&1
del "%~f0" >nul 2>&1
exit
:relaunch_old
move /Y "%EXE%.old" "%EXE%" >nul 2>&1
start "" "%EXE%"
del "%~f0" >nul 2>&1
"""

# Script Unix (Linux) équivalent.
_NIX_SWAP = """#!/bin/sh
EXE="{exe}"
NEW="{new}"
n=0
while [ -e "$EXE" ] && ! mv "$EXE" "$EXE.old" 2>/dev/null; do
  n=$((n+1)); [ $n -ge 60 ] && break; sleep 1
done
mv "$NEW" "$EXE" 2>/dev/null && chmod +x "$EXE"
rm -f "$EXE.old" 2>/dev/null
"$EXE" &
rm -f "$0"
"""


def _dir_writable(d: str) -> bool:
    """Teste réellement l'écriture dans le dossier (fiable sous Windows)."""
    try:
        p = os.path.join(d, ".prepafly_wtest")
        with open(p, "w", encoding="utf-8") as f:
            f.write("1")
        os.remove(p)
        return True
    except Exception:  # noqa: BLE001
        return False


def apply_update() -> bool:
    """Télécharge la dernière version et programme le remplacement + relance.

    Après l'appel, l'application doit se fermer (le serveur le fait) pour libérer
    l'exe : le script de bascule prend alors le relais. Lève une exception si la
    mise à jour auto n'est pas possible (mode dev, dossier protégé, pas d'exe…) —
    l'interface propose alors le téléchargement manuel.
    """
    if not is_frozen():
        raise RuntimeError("Mise à jour automatique disponible uniquement dans l'exécutable "
                           "(en développement, relancez depuis les sources).")
    exe = os.path.abspath(sys.executable)   # l'exe en cours d'exécution
    exe_dir = os.path.dirname(exe)
    if not _dir_writable(exe_dir):
        raise RuntimeError("Application installée dans un dossier protégé (Program Files) : "
                           "téléchargez et réinstallez la dernière version depuis la page des versions.")
    rel = _latest_release()
    url = _asset_url(rel)
    if not url:
        raise RuntimeError("Aucun exécutable trouvé dans la dernière version publiée.")

    # On télécharge dans un dossier temporaire (toujours accessible en écriture),
    # puis le script de bascule déplace le fichier par-dessus l'exe.
    new = os.path.join(tempfile.gettempdir(), "PrepaFlyPy_update" + (".exe" if os.name == "nt" else ""))
    _download(url, new)

    if os.name == "nt":
        script = _WIN_SWAP.format(exe=exe, new=new)
        path = os.path.join(tempfile.gettempdir(), "prepafly_maj.bat")
        with open(path, "w", encoding="utf-8") as f:
            f.write(script)
        DETACHED = 0x00000008 | 0x00000200 | 0x08000000  # DETACHED|NEW_GROUP|NO_WINDOW
        subprocess.Popen(["cmd", "/c", path], creationflags=DETACHED, close_fds=True)
    else:
        script = _NIX_SWAP.format(exe=exe, new=new)
        path = os.path.join(tempfile.gettempdir(), "prepafly_maj.sh")
        with open(path, "w", encoding="utf-8") as f:
            f.write(script)
        os.chmod(path, 0o755)
        subprocess.Popen(["/bin/sh", path], start_new_session=True, close_fds=True)
    return True

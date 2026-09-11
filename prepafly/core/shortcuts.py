"""Création de raccourcis Windows (Bureau + menu Démarrer).

L'application est un exécutable portable ; au premier lancement elle propose de
créer des raccourcis pointant vers l'exe courant (avec son icône). Les raccourcis
sont créés via PowerShell (WScript.Shell), sans dépendance supplémentaire. Sous
un autre système, ou en développement, la création est simplement indisponible.
"""
from __future__ import annotations

import os
import subprocess
import sys


def can_create() -> bool:
    """Vrai uniquement dans l'exécutable packagé sous Windows."""
    return os.name == "nt" and bool(getattr(sys, "frozen", False))


def _exe() -> str:
    return os.path.abspath(sys.executable)


def create_windows_shortcuts(desktop: bool = True, start_menu: bool = True) -> dict:
    """Crée les raccourcis demandés. Renvoie {created: [emplacements]}."""
    if os.name != "nt":
        raise RuntimeError("Les raccourcis ne sont disponibles que sous Windows.")
    exe = _exe().replace("'", "''")          # échappe les apostrophes pour PowerShell
    workdir = os.path.dirname(_exe()).replace("'", "''")
    name = "PrepaFlyPy"
    lines = ["$W = New-Object -ComObject WScript.Shell;"]
    created: list[str] = []
    if desktop:
        lines.append("$d = [Environment]::GetFolderPath('Desktop');")
        lines.append(f"$s = $W.CreateShortcut((Join-Path $d '{name}.lnk'));"
                     f"$s.TargetPath='{exe}';$s.IconLocation='{exe},0';"
                     f"$s.WorkingDirectory='{workdir}';$s.Description='PrepaFlyPy';$s.Save();")
        created.append("Bureau")
    if start_menu:
        lines.append("$p = Join-Path ([Environment]::GetFolderPath('StartMenu')) 'Programs';")
        lines.append(f"$s2 = $W.CreateShortcut((Join-Path $p '{name}.lnk'));"
                     f"$s2.TargetPath='{exe}';$s2.IconLocation='{exe},0';"
                     f"$s2.WorkingDirectory='{workdir}';$s2.Description='PrepaFlyPy';$s2.Save();")
        created.append("Menu Démarrer")
    script = " ".join(lines)
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                   check=True, creationflags=0x08000000)  # CREATE_NO_WINDOW
    return {"created": created}

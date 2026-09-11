"""Lancement en application de bureau.

Démarre le serveur FastAPI local (uvicorn) dans un thread, puis ouvre une fenêtre
native (pywebview) pointant dessus — l'équivalent de la fenêtre Tauri. Si pywebview
n'est pas disponible, on se rabat sur le navigateur par défaut. Tout est local :
aucune donnée ne sort du poste, hors appels explicites météo/carte.
"""
from __future__ import annotations

import socket
import threading
import time

from .core.version import __version__


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _serve(port: int):
    import uvicorn
    from .server import app
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


def run(width: int = 1180, height: int = 820):
    port = _free_port()
    url = f"http://127.0.0.1:{port}/"
    t = threading.Thread(target=_serve, args=(port,), daemon=True)
    t.start()
    # Laisse le serveur démarrer.
    for _ in range(50):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                break
        except OSError:
            time.sleep(0.1)

    try:
        import webview  # pywebview
        webview.create_window(f"PrepaFlyPy {__version__}", url, width=width, height=height,
                              min_size=(900, 600))
        webview.start()
    except Exception:  # noqa: BLE001 - pas de moteur de fenêtre : repli navigateur
        import webbrowser
        print(f"PrepaFlyPy — interface disponible sur {url}")
        print("(Fenêtre native indisponible : ouverture dans le navigateur. Ctrl+C pour quitter.)")
        webbrowser.open(url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

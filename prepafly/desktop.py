"""Lancement en application de bureau.

Démarre le serveur FastAPI local (uvicorn) dans un thread, attend qu'il réponde
vraiment (HTTP 200), puis ouvre une fenêtre native (pywebview) pointant dessus —
l'équivalent de la fenêtre Tauri. Si pywebview n'est pas disponible, repli sur le
navigateur par défaut.

Points de robustesse (importants une fois l'app packagée en .exe par PyInstaller) :
  - uvicorn est forcé en boucle « asyncio » et protocole « h11 » (100 % Python),
    pour éviter la détection auto (uvloop/httptools) qui échoue dans un exe figé ;
  - les signaux ne sont pas installés (thread secondaire) ;
  - on attend une vraie réponse HTTP avant d'afficher la fenêtre (pas juste un port
    ouvert), avec un délai large pour le premier démarrage à froid de l'exe ;
  - toute erreur de démarrage du serveur est écrite dans un journal
    (<dossier de données>/desktop.log) consultable en cas de souci.
"""
from __future__ import annotations

import socket
import threading
import time
import traceback
import urllib.request
from pathlib import Path

from .core.version import __version__

LOADING_HTML = """<!doctype html><html><head><meta charset="utf-8">
<style>html,body{height:100%;margin:0;background:#12294d;color:#cdddf2;
font-family:system-ui,sans-serif;display:flex;align-items:center;justify-content:center}
.b{text-align:center}.s{width:38px;height:38px;border:4px solid #2f6fb0;border-top-color:transparent;
border-radius:50%;margin:0 auto 16px;animation:sp 1s linear infinite}
@keyframes sp{to{transform:rotate(360deg)}}</style></head>
<body><div class="b"><div class="s"></div><div>PrepaFlyPy démarre…</div></div></body></html>"""


def _log_path() -> Path:
    try:
        from .core import storage
        return storage.root() / "desktop.log"
    except Exception:
        import tempfile
        return Path(tempfile.gettempdir()) / "prepaflypy-desktop.log"


def _log(msg: str) -> None:
    try:
        with open(_log_path(), "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
    except Exception:
        pass


def _free_port() -> int:
    import os
    env = os.environ.get("PREPAFLY_PORT")
    if env and env.isdigit():
        return int(env)
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _serve(port: int):
    try:
        import uvicorn
        from .server import app
        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning",
                                loop="asyncio", http="h11")
        server = uvicorn.Server(config)
        # Les gestionnaires de signaux ne fonctionnent que dans le thread principal.
        server.install_signal_handlers = lambda: None
        server.run()
    except Exception as e:  # noqa: BLE001
        _log("SERVEUR - echec du demarrage : " + repr(e) + "\n" + traceback.format_exc())


def _wait_http(url: str, timeout: float = 120.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        try:
            with urllib.request.urlopen(url, timeout=1.5) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.25)
    return False


def run(width: int = 1180, height: int = 820):
    _log(f"Demarrage PrepaFlyPy {__version__}")
    port = _free_port()
    url = f"http://127.0.0.1:{port}/"
    threading.Thread(target=_serve, args=(port,), daemon=True).start()

    try:
        import webview  # pywebview
    except Exception:
        webview = None

    if webview is not None:
        # On ouvre tout de suite une page « chargement… » puis on bascule sur l'app
        # dès que le serveur répond — jamais d'écran « connexion refusée ».
        window = webview.create_window(f"PrepaFlyPy {__version__}", html=LOADING_HTML,
                                       width=width, height=height, min_size=(900, 600))

        def _switch():
            if _wait_http(url):
                _log("Serveur pret, chargement de l'interface.")
                try:
                    window.load_url(url)
                except Exception as e:  # noqa: BLE001
                    _log("load_url a echoue : " + repr(e))
            else:
                _log("Le serveur n'a pas repond a temps. Voir les erreurs ci-dessus.")
                try:
                    window.load_html("<body style='font-family:sans-serif;padding:40px;color:#c0392b'>"
                                     "<h2>PrepaFlyPy n'a pas pu démarrer son moteur interne.</h2>"
                                     "<p>Consultez le journal :<br><code>" + str(_log_path()) +
                                     "</code></p></body>")
                except Exception:
                    pass

        webview.start(_switch)
    else:
        import webbrowser
        ready = _wait_http(url)
        _log(f"Mode navigateur, serveur pret={ready}")
        print(f"PrepaFlyPy — interface disponible sur {url}")
        print("(Fenêtre native indisponible : ouverture dans le navigateur. Ctrl+C pour quitter.)")
        if ready:
            webbrowser.open(url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

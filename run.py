"""Point d'entrée pour l'exécutable packagé (PyInstaller).

Lance l'application en fenêtre bureau. En développement, préférez `prepafly gui`
ou `python -m prepafly`.
"""
from prepafly import desktop

if __name__ == "__main__":
    desktop.run()

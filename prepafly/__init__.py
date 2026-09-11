"""PrepaFlyPy — assistant de préparation de vol drone (équivalent Python de
Assistant Vol Drone). Éditeur : M.G.I. — Maintenance Générale Industrielle.

Le paquet est découpé ainsi :
  - prepafly.core   : toute la logique métier, en Python pur et testable
                      (moteur SORA, régimes, base drones, stockage, PDF…).
  - prepafly.server : l'API FastAPI qui expose le cœur (les « commandes »).
  - prepafly.web    : l'interface HTML/JS servie par l'API.
  - prepafly.desktop: lance l'app en fenêtre bureau (pywebview) sur le serveur local.
  - prepafly.cli    : interface en ligne de commande sur le même cœur.

Rien dans core ne dépend de l'interface : on peut tout piloter en Python ou en CLI.
"""
from .core.version import __version__

__all__ = ["__version__"]

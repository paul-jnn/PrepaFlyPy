"""Point d'entrée `python -m prepafly` : délègue à la CLI.

Sans argument -> fenêtre bureau. `--web` -> serveur web. Voir prepafly.cli.
"""
import sys

from .cli import main

if __name__ == "__main__":
    # Compat : `python -m prepafly --web` == `prepafly web`.
    argv = sys.argv[1:]
    if argv and argv[0] == "--web":
        argv = ["web"] + argv[1:]
    sys.exit(main(argv))

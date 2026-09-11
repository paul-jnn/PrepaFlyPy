# PrepaFlyPy

Assistant de préparation de vol drone, en Python. Équivalent — et extension — de
l'application *Assistant Vol Drone*, réécrit avec un cœur métier Python testé, une
API, une interface web, une fenêtre bureau et une ligne de commande.

**Éditeur :** M.G.I. — Maintenance Générale Industrielle.
Aide à la préparation ; ne se substitue pas à la réglementation ni au jugement du télépilote.

## Ce qu'il fait

Gère l'exploitant et les télépilotes (mentions, habilitations datées avec alerte de
péremption), un dossier par mission, et pour chaque mission : choix assisté du
**régime** (catégorie ouverte A1/A2/A3, STS, PDRA ou SORA), **moteur SORA 2.5**
complet (iGRC → GRC → ARC → SAIL → OSO), contrôle de conformité, base de **45
modèles DJI** avec auto-remplissage, repérage du site (adresse, carte, météo
METAR/TAF), check-list pré-vol, journal de vol, et génération PDF du **dossier de
vol**, du **rapport de mission client** (à votre logo) et d'une **trame de MANEX**.
Formulaires Cerfa/dérogation/AOT pré-remplis. Verrou par code PIN, données locales,
sauvegarde/restauration, vérification de mise à jour.

## Installation

```bash
python -m pip install -e ".[desktop]"
# ou, sans installer le paquet :
pip install -r requirements.txt
```

Python 3.10+ requis.

## Lancer

```bash
prepafly gui            # fenêtre bureau (pywebview ; sinon ouvre le navigateur)
prepafly web            # serveur web local sur http://127.0.0.1:8000
python -m prepafly      # équivaut à « gui »
```

En ligne de commande (même cœur métier, sans interface) :

```bash
prepafly drones                                   # les 45 modèles DJI
prepafly sora --dim 0.67 --vit 23 --densite d500 --arc b
prepafly dossiers                                 # dossiers enregistrés
prepafly report dossier <id> -o dossier.pdf       # génère un PDF
```

## Architecture

Deux couches nettes, comme dans l'app Tauri d'origine, mais tout en Python :

- **`prepafly/core/`** — la logique métier, pure et testée : `sora` (moteur),
  `regimes` (recommandation + conformité), `drones` (base DJI), `models` +
  `storage` (données JSON locales, PIN, documents), `reports` (PDF reportlab),
  `forms` (Cerfa/dérogation/AOT), `weather`, `geocode`, `updater`, `i18n`.
- **`prepafly/server.py`** — API FastAPI qui expose le cœur (les « commandes »).
- **`prepafly/web/`** — interface HTML/JS servie par l'API (fetch).
- **`prepafly/desktop.py`** — fenêtre bureau (uvicorn + pywebview).
- **`prepafly/cli.py`** — ligne de commande.

Rien dans `core` ne dépend de l'interface : on peut tout piloter en Python.

## Tests

```bash
pytest -q
```

38 tests couvrent le moteur SORA (cas calculés à la main), la recommandation de
régime, la base DJI, la génération des PDF et l'API.

## Construire l'exécutable

```bash
pip install -e ".[dev,desktop]"
pyinstaller prepafly.spec        # -> dist/PrepaFlyPy(.exe)
```

La CI GitHub construit automatiquement les exécutables Windows et Linux à chaque
tag `vX.Y.Z` (voir `.github/workflows/release.yml`).

## Données

Stockées **hors du programme**, dans le dossier de données utilisateur du poste
(via `platformdirs`) : `donnees.json`, `pin.hash`, `documents/`. Elles survivent
aux mises à jour. Redirigeables via la variable `PREPAFLY_DATA_DIR` (postes
portables, tests).

## Licence

MIT — voir `LICENSE`. Documentation complète : `docs/DOSSIER_TECHNIQUE.md`.

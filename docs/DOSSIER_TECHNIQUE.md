# PrepaFlyPy — Dossier technique

**Éditeur :** M.G.I. — Maintenance Générale Industrielle
**Version du document :** 1.0 (application 0.3.0)
**Application :** PrepaFlyPy — préparation de vol drone (référentiel, régimes, SORA 2.5, formulaires, MANEX, rapports)
**Public visé :** l'utilisateur-mainteneur (vous), pour comprendre, exploiter, faire évoluer et dépanner l'outil, même avec seulement des bases de Python.
**Code source :** public, https://github.com/paul-jnn/PrepaFlyPy

---

## 1. À quoi sert l'application

PrepaFlyPy accompagne la préparation d'un vol drone professionnel, du choix du
régime jusqu'au dossier présentable en contrôle et au rapport remis au client.
C'est l'équivalent en Python de l'application *Assistant Vol Drone* (Tauri), avec le
même périmètre métier et quelques ajouts : un cœur testé, une API, une ligne de
commande, et une amorce de bascule de langue FR/EN.

Elle conserve l'exploitant et les télépilotes, gère un dossier par mission, propose
le régime adapté (ouverte A1/A2/A3, ou spécifique via STS, PDRA ou SORA), déroule
l'analyse, produit check-list et journal, et génère le dossier de vol PDF, le
rapport de mission client et une trame de MANEX. Elle embarque une base de 45
drones DJI, pré-remplit les formulaires, localise le site (adresse, carte, météo),
et stocke les justificatifs. Données locales, accès par PIN.

Elle ne remplace ni la réglementation ni le jugement du télépilote.

---

## 2. Sur quoi l'application est construite

Tout est en **Python**, découpé en deux couches nettes (le même esprit que la coque
Rust + interface web de l'app Tauri, mais sans Rust) :

- **Le cœur métier** (`prepafly/core/`) : la logique pure, sans aucune dépendance à
  l'interface. C'est là que vivent le moteur SORA, les régimes, la base drones, le
  stockage, la génération PDF. On peut l'utiliser directement en Python ou en CLI.
- **Les interfaces** : une API **FastAPI** (`server.py`) qui expose le cœur ; une
  **interface web** (`web/`) servie par l'API ; une **fenêtre bureau**
  (`desktop.py`) qui lance le serveur local et l'affiche dans une fenêtre native
  (pywebview) ; une **CLI** (`cli.py`).

Le pont interface → cœur est l'appel HTTP `fetch('/api/...')` (analogue de l'appel
`invoke` de Tauri). L'interface ne calcule rien elle-même : elle affiche ce que le
cœur renvoie.

Bibliothèques : FastAPI + uvicorn (API/serveur), reportlab (PDF), pypdf (remplissage
de formulaires), httpx (météo, géocodage, vérification de mise à jour), platformdirs
(dossier de données), pywebview (fenêtre bureau, optionnelle).

---

## 3. Arborescence du projet

```
PrepaFlyPy/
├─ prepafly/
│  ├─ core/                 CŒUR MÉTIER (logique pure, testée)
│  │  ├─ sora.py            moteur SORA 2.5 (tables + calcul)
│  │  ├─ regimes.py         recommandation de régime + conformité ouverte
│  │  ├─ drones.py          base de 45 modèles DJI
│  │  ├─ models.py          structures de données (store, dossier) + normalisation
│  │  ├─ storage.py         stockage JSON local, PIN, documents
│  │  ├─ security.py        empreinte du PIN (SHA-256)
│  │  ├─ reports.py         PDF : dossier de vol, rapport client, MANEX
│  │  ├─ forms.py           Cerfa / dérogation / AOT
│  │  ├─ weather.py         METAR/TAF (aviationweather.gov)
│  │  ├─ geocode.py         adresse → coordonnées (Nominatim)
│  │  ├─ updater.py         vérification de version (GitHub)
│  │  ├─ i18n.py            libellés FR/EN
│  │  └─ version.py         version unique
│  ├─ server.py             API FastAPI (les « commandes »)
│  ├─ desktop.py            fenêtre bureau (uvicorn + pywebview)
│  ├─ cli.py                ligne de commande
│  ├─ __main__.py           python -m prepafly
│  └─ web/                  interface (index.html + app.js)
├─ tests/                   suite pytest (38 tests)
├─ forms/                   gabarits officiels (à déposer) + README
├─ run.py                   point d'entrée de l'exécutable packagé
├─ prepafly.spec            recette PyInstaller
├─ pyproject.toml           métadonnées + dépendances + entry point `prepafly`
├─ requirements.txt
├─ .github/workflows/       ci.yml (tests) + release.yml (build exe)
└─ docs/DOSSIER_TECHNIQUE.md  ce document
```

Le fichier central pour faire évoluer le métier est `prepafly/core/` ; pour l'écran,
`prepafly/web/`. Trois emplacements gardent les données **hors du programme**, dans
le dossier de données du poste (via platformdirs) : `donnees.json`, `pin.hash`, et
`documents/`. Ils survivent aux mises à jour. La variable `PREPAFLY_DATA_DIR` permet
de les rediriger (poste portable, tests).

---

## 4. Le cœur métier (`prepafly/core/`)

### 4.1 Moteur SORA (`sora.py`)

Contient les tables officielles (iGRC, atténuations M1/M2, SAIL, OSO) et le calcul
`compute_sora(grc, arc)` : croisement iGRC (colonne appareil × ligne densité),
application des atténuations jusqu'à un plancher pour le GRC, arbre de décision de
l'ARC, puis SAIL = table GRC × ARC, et liste des OSO exigés selon le SAIL. Un GRC
> 7 bascule en catégorie certifiée. Vérifié sur des cas calculés à la main (voir
`tests/test_sora.py`).

### 4.2 Régimes (`regimes.py`)

`recommend(dossier)` propose le cadre le plus adapté (ouverte/STS/PDRA/SORA) et sa
justification ; `open_conformity(dossier)` vérifie la cohérence de la catégorie
ouverte. La recommandation est une aide : les conditions officielles priment. Les
scénarios nationaux S-1/S-2/S-3 sont caducs depuis le 01/01/2026.

### 4.3 Base drones (`drones.py`)

45 modèles DJI (Mini/Neo/Flip, Air, Mavic, FPV, Phantom, Entreprise dont Matrice 4
et 400, Inspire, cargo FlyCart, Agras) avec dimension, vitesse, masse et classe C.
`find(key)` et `by_category()`. Ajouter un modèle = ajouter une entrée à `DRONES`
avec une clé unique (ne jamais renommer une clé existante).

### 4.4 Données et stockage (`models.py`, `storage.py`, `security.py`)

`models` décrit la forme du store (dict sérialisable JSON, même format que l'app
Tauri : sauvegardes interchangeables) et `normalize()` migre/complète tout store
ancien. `storage` lit/écrit `donnees.json` (écriture atomique), gère le PIN
(empreinte SHA-256, jamais en clair) et les documents importés. Une installation
neuve démarre **vierge**.

### 4.5 Documents (`reports.py`, `forms.py`)

`reports` produit trois PDF avec reportlab : dossier de vol complet, rapport de
mission client (en-tête à votre logo) et trame de MANEX (plan A-E pré-rempli).
`forms` remplit les Cerfa/dérogation avec pypdf si les gabarits sont présents dans
`forms/`, sinon génère un brouillon lisible ; l'AOT est toujours une lettre générée.

### 4.6 Réseau (`weather.py`, `geocode.py`, `updater.py`)

Météo restreinte à aviationweather.gov (METAR/TAF), géocodage via Nominatim,
vérification de version via l'API GitHub. Tous échouent proprement hors ligne.

---

## 5. L'API (`prepafly/server.py`)

FastAPI expose le cœur sous forme d'endpoints, appelés par l'interface :

| Domaine | Endpoints |
|---|---|
| Méta / références | `GET /api/meta`, `/api/drones`, `/api/i18n/{lang}`, `/api/update` |
| Données | `GET/PUT /api/store`, `GET/POST /api/backup` |
| Analyse | `POST /api/sora`, `/api/regime`, `/api/regime/open` |
| PIN | `GET /api/pin/status`, `POST /api/pin/set`, `/api/pin/verify` |
| Site | `GET /api/weather?icao=`, `/api/geocode?q=` |
| Documents | `GET/POST /api/docs`, `GET/DELETE /api/docs/{name}` |
| PDF | `POST /api/report/dossier|rapport|manex`, `/api/form/{cerfa|derog|aot}` |

L'interface web (`web/index.html` + `web/app.js`) est servie à la racine `/`.

---

## 6. Interfaces : bureau, web, CLI

- **Bureau** (`prepafly gui`) : démarre uvicorn sur un port libre local et ouvre une
  fenêtre native (pywebview). Sans moteur de fenêtre, repli sur le navigateur.
- **Web** (`prepafly web`) : serveur local, à ouvrir dans un navigateur.
- **CLI** (`prepafly …`) : `drones`, `dossiers`, `sora`, `regime`, `report` — utile
  pour l'automatisation et vérifiable sans écran.

---

## 7. Sécurité et données

Accès par **code PIN** (empreinte SHA-256, jamais en clair). Données **sur le
poste** uniquement ; le seul réseau sortant est explicite (météo, géocodage,
vérification de mise à jour). Installation neuve vierge. `donnees.json` est en clair :
le PIN protège l'ouverture, pas le fichier — pour un poste partagé, compter sur la
session et le chiffrement disque. La sauvegarde JSON (section Données) est le filet
de sécurité recommandé.

---

## 8. Mise à jour

`updater.check()` compare la version installée à la dernière release publiée sur
GitHub et signale une mise à jour (bannière dans l'interface). Contrairement à
l'updater Tauri, il n'installe pas automatiquement : il pointe vers la page des
releases. Publier une version : bump de `version` dans `pyproject.toml` et
`prepafly/core/version.py`, `git push`, puis `git tag vX.Y.Z && git push origin
vX.Y.Z` — la CI construit les exécutables Windows/Linux et crée la release.

---

## 9. Tests et intégration continue

`pytest -q` lance 38 tests : moteur SORA (cas connus), régimes, base DJI,
génération PDF, et API (via TestClient, sans réseau). La CI (`ci.yml`) les exécute à
chaque push. `release.yml` construit les exécutables à chaque tag `v*`.

---

## 10. Construire l'exécutable

`pip install -e ".[dev,desktop]"` puis `pyinstaller prepafly.spec` produit
`dist/PrepaFlyPy(.exe)`, autonome, incluant l'interface web. La CI le fait pour
Windows et Linux à chaque tag.

---

## 11. Dépannage

**La fenêtre ne s'ouvre pas.** pywebview ou son moteur (WebKit/WebView2) est absent :
l'app se rabat sur le navigateur ; installez `pywebview` pour la fenêtre native.

**Carte / météo / localisation muettes.** Elles nécessitent Internet ; hors ligne,
saisissez les coordonnées à la main.

**Formulaire Cerfa peu rempli.** Déposez le gabarit officiel dans `forms/` et
complétez `FIELD_MAPS` (voir `forms/README.md`).

**PIN oublié.** Supprimez `pin.hash` dans le dossier de données (les données
restent) ; l'app en redemandera un.

**Perte de données.** Elles vivent hors du programme et survivent aux mises à jour ;
faites en plus un export JSON régulier.

---

## 12. Évolutions envisagées

Interface FR/EN complète (l'amorce est en place). Remplissage Cerfa avec gabarits
officiels et mappage complet. Carte des restrictions drone préchargée. Signature des
exécutables. Suivi des appels d'offres avec échéances.

---

*Document généré pour M.G.I. — Maintenance Générale Industrielle. Aide à la
préparation de vol ; ne se substitue pas à la réglementation applicable.*

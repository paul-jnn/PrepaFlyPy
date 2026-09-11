# -*- mode: python ; coding: utf-8 -*-
# Spec PyInstaller pour PrepaFlyPy.
# Construit un exécutable autonome (fenêtre bureau) incluant l'interface web et
# les gabarits de formulaires. Build : pyinstaller prepafly.spec
from PyInstaller.utils.hooks import collect_submodules

# Fichiers de données embarqués (chemins relatifs a ce .spec = racine du projet).
# On copie explicitement le dossier web (interface) et forms (gabarits) : plus
# fiable que collect_data_files, qui manquait le dossier web.
datas = [
    ("prepafly/web", "prepafly/web"),
    ("forms", "forms"),
]

# uvicorn est force en boucle asyncio + protocole h11 (voir desktop.py), mais on
# embarque quand meme ses sous-modules par securite.
hiddenimports = []
hiddenimports += collect_submodules("uvicorn")
hiddenimports += [
    "uvicorn.loops.asyncio",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.lifespan.on",
    "h11",
    "reportlab.graphics.barcode",
]

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="PrepaFlyPy",
    icon="assets/icon.ico",   # même icône que l'app Rust (Assistant Vol Drone)
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,   # application fenêtrée
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

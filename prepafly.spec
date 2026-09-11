# -*- mode: python ; coding: utf-8 -*-
# Spec PyInstaller pour PrepaFlyPy.
# Construit un exécutable autonome (fenêtre bureau) incluant l'interface web et
# les gabarits de formulaires. Build : pyinstaller prepafly.spec
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

datas = []
datas += collect_data_files("prepafly", includes=["web/*"])
# Gabarits de formulaires s'ils sont présents (sinon ignorés).
try:
    datas += [("forms", "forms")]
except Exception:
    pass

hiddenimports = []
hiddenimports += collect_submodules("uvicorn")
hiddenimports += ["reportlab.graphics.barcode"]

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

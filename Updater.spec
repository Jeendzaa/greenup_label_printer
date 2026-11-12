# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

ROOT_DIR = Path(SPECPATH).resolve()
updater_icon = ROOT_DIR / "assets" / "updater_icon.ico"
if not updater_icon.is_file():
    raise FileNotFoundError(f"Nie znaleziono ikony aktualizatora: {updater_icon}")

analysis = Analysis(
    [str(ROOT_DIR / "updater.py")],
    pathex=[str(ROOT_DIR)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(analysis.pure)

EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="Updater",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(updater_icon),
)

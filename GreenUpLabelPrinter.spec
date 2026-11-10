
# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import collect_all


ROOT_DIR = Path(SPECPATH)

# --------------------------------------------------
# LIBRARIES
# --------------------------------------------------

customtkinter_datas, customtkinter_binaries, customtkinter_hiddenimports = (
    collect_all("customtkinter")
)

zplkit_datas, zplkit_binaries, zplkit_hiddenimports = (
    collect_all("zplkit")
)

# --------------------------------------------------
# APPLICATION RESOURCES
# --------------------------------------------------

app_datas = []

for folder_name in ("assets", "templates"):
    folder = ROOT_DIR / folder_name

    if folder.exists():
        for file_path in folder.rglob("*"):
            if file_path.is_file():
                destination = str(
                    file_path.relative_to(ROOT_DIR).parent
                )

                app_datas.append((str(file_path), destination))


# --------------------------------------------------
# ANALYSIS
# --------------------------------------------------

a = Analysis(
    [str(ROOT_DIR / "main.py")],
    pathex=[str(ROOT_DIR)],
    binaries=(
        customtkinter_binaries
        + zplkit_binaries
    ),
    datas=(
        customtkinter_datas
        + zplkit_datas
        + app_datas
    ),
    hiddenimports=(
        customtkinter_hiddenimports
        + zplkit_hiddenimports
    ),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)


# --------------------------------------------------
# EXECUTABLE
# --------------------------------------------------

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="GreenUpLabelPrinter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon=str(ROOT_DIR / "assets" / "greenup_label_printer_icon.ico"),
)


# --------------------------------------------------
# COLLECTION - ONEDIR
# --------------------------------------------------

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="GreenUpLabelPrinter",
)

# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import collect_all

ROOT_DIR = Path(SPECPATH).resolve()

# Third-party packages used by the GUI, image handling and ZPL preview.
customtkinter_datas, customtkinter_binaries, customtkinter_hiddenimports = collect_all("customtkinter")
zplkit_datas, zplkit_binaries, zplkit_hiddenimports = collect_all("zplkit")

# Bundle application assets and built-in templates. User templates/configuration
# continue to live in Documents/GreenUpLabelPrinter.
app_datas = []
for folder_name in ("assets", "templates"):
    source_dir = ROOT_DIR / folder_name
    if source_dir.is_dir():
        for source_file in source_dir.rglob("*"):
            if source_file.is_file():
                destination = str(source_file.relative_to(ROOT_DIR).parent)
                app_datas.append((str(source_file), destination))

main_icon = ROOT_DIR / "assets" / "greenup_label_printer_icon.ico"
if not main_icon.is_file():
    raise FileNotFoundError(f"Nie znaleziono ikony aplikacji: {main_icon}")

analysis = Analysis(
    [str(ROOT_DIR / "main.py")],
    pathex=[str(ROOT_DIR)],
    binaries=customtkinter_binaries + zplkit_binaries,
    datas=customtkinter_datas + zplkit_datas + app_datas,
    hiddenimports=customtkinter_hiddenimports + zplkit_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(analysis.pure)

app_exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="GreenUpLabelPrinter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(main_icon),
)

COLLECT(
    app_exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="GreenUpLabelPrinter",
)

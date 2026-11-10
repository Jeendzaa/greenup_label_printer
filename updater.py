
import argparse
import ctypes
import os
import json
import base64
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile

from datetime import datetime
from pathlib import Path, PurePosixPath


APP_EXE = "GreenUpLabelPrinter.exe"
UPDATER_EXE = "Updater.exe"

CONFIRMATION_TIMEOUT = 60
CONFIRMATION_INTERVAL = 0.5


# --------------------------------------------------
# PROCESS MANAGEMENT
# --------------------------------------------------

def wait_for_process(pid):
    """Czeka na zakończenie głównej aplikacji."""

    if os.name != "nt":
        raise RuntimeError("Updater obsługuje tylko Windows.")

    if pid <= 0:
        raise ValueError("Nieprawidłowy PID procesu.")

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    kernel32.OpenProcess.argtypes = [
        ctypes.c_ulong,
        ctypes.c_int,
        ctypes.c_ulong
    ]
    kernel32.OpenProcess.restype = ctypes.c_void_p

    kernel32.WaitForSingleObject.argtypes = [
        ctypes.c_void_p,
        ctypes.c_ulong
    ]
    kernel32.WaitForSingleObject.restype = ctypes.c_ulong

    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int

    handle = kernel32.OpenProcess(
        0x00100000,
        False,
        pid
    )

    if not handle:
        error = ctypes.get_last_error()

        if error == 87:
            return

        raise ctypes.WinError(error)

    try:
        result = kernel32.WaitForSingleObject(
            handle,
            0xFFFFFFFF
        )

        if result != 0:
            raise RuntimeError(
                "Nie udało się poczekać na zamknięcie aplikacji."
            )

    finally:
        kernel32.CloseHandle(handle)


def terminate_process(process):
    """Kończy proces nowej aplikacji, jeśli nadal działa."""

    if process is None or process.poll() is not None:
        return

    process.terminate()

    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


# --------------------------------------------------
# UPDATER SELF-COPY
# --------------------------------------------------

def launch_worker(arguments):
    """
    Kopiuje Updater.exe do katalogu tymczasowego
    i uruchamia jego niezależną kopię.
    """

    if not getattr(sys, "frozen", False):
        return False

    source = Path(sys.executable).resolve()

    temp_dir = (
        Path(tempfile.gettempdir())
        / "GreenUpLabelPrinter"
        / "updater"
    )

    temp_dir.mkdir(parents=True, exist_ok=True)

    destination = temp_dir / f"Updater_{os.getpid()}.exe"

    shutil.copy2(source, destination)

    command = [
        str(destination),
        "--worker",
        "--pid", str(arguments.pid),
        "--archive", str(arguments.archive),
        "--app-exe", str(arguments.app_exe),
        "--target-version", arguments.target_version,
    ]

    subprocess.Popen(
        command,
        cwd=temp_dir,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
    )

    return True


# --------------------------------------------------
# ARCHIVE VALIDATION
# --------------------------------------------------

def safe_extract(archive_path, destination):
    """Bezpiecznie sprawdza i rozpakowuje archiwum ZIP."""

    destination = destination.resolve()

    with zipfile.ZipFile(archive_path, "r") as archive:

        for info in archive.infolist():
            name = info.filename

            if "\\" in name or "\x00" in name:
                raise RuntimeError(
                    f"Nieprawidłowa ścieżka w ZIP: {name}"
                )

            member = PurePosixPath(name)

            if member.is_absolute() or ".." in member.parts:
                raise RuntimeError(
                    f"Niebezpieczna ścieżka w ZIP: {name}"
                )

            if member.parts and ":" in member.parts[0]:
                raise RuntimeError(
                    f"Nieprawidłowa ścieżka w ZIP: {name}"
                )

            unix_mode = info.external_attr >> 16

            if (unix_mode & 0o170000) == 0o120000:
                raise RuntimeError(
                    f"Dowiązania symboliczne nie są obsługiwane: {name}"
                )

            target = (
                destination / Path(*member.parts)
            ).resolve()

            if (
                target != destination
                and destination not in target.parents
            ):
                raise RuntimeError(
                    f"Plik wychodzi poza katalog docelowy: {name}"
                )

        corrupted_file = archive.testzip()

        if corrupted_file:
            raise RuntimeError(
                f"Uszkodzony plik w archiwum: {corrupted_file}"
            )

        archive.extractall(destination)


def find_application_root(staging_dir):
    """Znajduje katalog zawierający główny plik EXE."""

    candidates = [
        path.parent
        for path in staging_dir.rglob(APP_EXE)
        if path.is_file()
    ]

    if len(candidates) != 1:
        raise RuntimeError(
            "Nie znaleziono jednoznacznego katalogu aplikacji."
        )

    app_dir = candidates[0]

    if not (app_dir / "_internal").is_dir():
        raise RuntimeError(
            "Archiwum nie zawiera katalogu _internal."
        )

    if not (app_dir / UPDATER_EXE).is_file():
        raise RuntimeError(
            "Archiwum nie zawiera Updater.exe."
        )

    return app_dir


# --------------------------------------------------
# START CONFIRMATION
# --------------------------------------------------

def wait_for_confirmation(
    confirmation_file,
    expected_token,
    process,
    timeout=CONFIRMATION_TIMEOUT
):
    """
    Czeka na potwierdzenie poprawnego uruchomienia aplikacji.

    Aplikacja musi zapisać oczekiwany token
    do wskazanego pliku.
    """

    start_time = time.monotonic()

    print(
        f"Oczekiwanie na potwierdzenie uruchomienia "
        f"(maksymalnie {timeout} sekund)..."
    )

    while time.monotonic() - start_time < timeout:

        if confirmation_file.is_file():
            try:
                received_token = confirmation_file.read_text(
                    encoding="utf-8"
                ).strip()

                if received_token == expected_token:
                    print("Otrzymano potwierdzenie uruchomienia.")
                    return True

            except OSError:
                # Plik może być właśnie zapisywany.
                pass

        if process.poll() is not None:
            raise RuntimeError(
                "Nowa aplikacja zakończyła działanie "
                "przed potwierdzeniem poprawnego uruchomienia."
            )

        time.sleep(CONFIRMATION_INTERVAL)

    raise TimeoutError(
        "Nie otrzymano potwierdzenia uruchomienia "
        f"w ciągu {timeout} sekund."
    )


# --------------------------------------------------
# WINDOWS SHORTCUT MANAGEMENT
# --------------------------------------------------

def _run_powershell(script, payload=None):
    # Uruchamia PowerShell bez dodatkowych bibliotek COM.
    encoded_payload = base64.b64encode(
        json.dumps(payload or [], ensure_ascii=False).encode("utf-8")
    ).decode("ascii")
    wrapper = "$ErrorActionPreference = 'Stop'\n$payload = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('" + encoded_payload + "')) | ConvertFrom-Json\n" + script
    encoded_script = base64.b64encode(wrapper.encode("utf-16le")).decode("ascii")
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded_script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Nie udało się obsłużyć skrótów Windows. "
            + (result.stderr.strip() or result.stdout.strip() or "Nieznany błąd PowerShell.")
        )
    return result.stdout.strip()


def find_application_shortcuts(old_app_exe):
    # Zbiera skróty aplikacji.
    script = r'''
$oldTarget = [IO.Path]::GetFullPath([string]$payload[0]).TrimEnd('\')
$folders = @(
    [Environment]::GetFolderPath('DesktopDirectory'),
    [Environment]::GetFolderPath('CommonDesktopDirectory'),
    [Environment]::GetFolderPath('Programs'),
    [Environment]::GetFolderPath('CommonPrograms'),
    (Join-Path $env:APPDATA 'Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar')
) | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Container) } | Select-Object -Unique
$ws = New-Object -ComObject WScript.Shell
$results = @()
foreach ($folder in $folders) {
    Get-ChildItem -LiteralPath $folder -Filter '*.lnk' -File -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            $shortcut = $ws.CreateShortcut($_.FullName)
            if ($shortcut.TargetPath -and [IO.Path]::GetFullPath($shortcut.TargetPath).Equals($oldTarget, [StringComparison]::OrdinalIgnoreCase)) {
                $results += [PSCustomObject]@{
                    Path = $_.FullName
                    TargetPath = $shortcut.TargetPath
                    WorkingDirectory = $shortcut.WorkingDirectory
                    Arguments = $shortcut.Arguments
                    IconLocation = $shortcut.IconLocation
                }
            }
        } catch { }
    }
}
ConvertTo-Json -InputObject @($results) -Compress -Depth 4
'''
    output = _run_powershell(script, [str(Path(old_app_exe).resolve())])
    if not output:
        return []
    parsed = json.loads(output)
    if isinstance(parsed, dict):
        return [parsed]
    return parsed


def update_application_shortcuts(shortcuts, old_install_dir, new_install_dir):
    # Przekierowuje skróty.
    if not shortcuts:
        return
    script = r'''
$ws = New-Object -ComObject WScript.Shell
foreach ($item in $payload) {
    $shortcut = $ws.CreateShortcut([string]$item.Path)
    $shortcut.TargetPath = [string]$item.NewTargetPath
    $shortcut.WorkingDirectory = [string]$item.NewWorkingDirectory
    if ($item.NewIconLocation) { $shortcut.IconLocation = [string]$item.NewIconLocation }
    $shortcut.Arguments = [string]$item.Arguments
    $shortcut.Save()
}
'''
    old_prefix = str(Path(old_install_dir).resolve())
    new_prefix = str(Path(new_install_dir).resolve())
    payload = []
    for item in shortcuts:
        icon_location = item.get("IconLocation") or ""
        new_icon = icon_location
        if icon_location.lower().startswith(old_prefix.lower()):
            new_icon = new_prefix + icon_location[len(old_prefix):]
        payload.append({
            "Path": item["Path"],
            "NewTargetPath": str(Path(new_install_dir) / APP_EXE),
            "NewWorkingDirectory": new_prefix,
            "NewIconLocation": new_icon,
            "Arguments": item.get("Arguments") or "",
        })
    _run_powershell(script, payload)


def restore_application_shortcuts(shortcuts):
    # Przywraca oryginalne właściwości skrótów.
    if not shortcuts:
        return
    script = r'''
$ws = New-Object -ComObject WScript.Shell
foreach ($item in $payload) {
    if (-not (Test-Path -LiteralPath ([string]$item.Path))) { continue }
    $shortcut = $ws.CreateShortcut([string]$item.Path)
    $shortcut.TargetPath = [string]$item.TargetPath
    $shortcut.WorkingDirectory = [string]$item.WorkingDirectory
    $shortcut.Arguments = [string]$item.Arguments
    $shortcut.IconLocation = [string]$item.IconLocation
    $shortcut.Save()
}
'''
    _run_powershell(script, shortcuts)


# --------------------------------------------------
# INSTALLATION
# --------------------------------------------------

def install_update(
    archive_path,
    app_exe,
    pid,
    target_version,
    launch_app=True,
    confirmation_timeout=CONFIRMATION_TIMEOUT
):
    """Instaluje aktualizację w katalogu nazwanym zgodnie z nową wersją."""
    archive_path = Path(archive_path).resolve()
    app_exe = Path(app_exe).resolve()

    if not archive_path.is_file():
        raise RuntimeError("Nie znaleziono archiwum aktualizacji.")
    if app_exe.name.lower() != APP_EXE.lower():
        raise RuntimeError(f"Oczekiwano pliku {APP_EXE}.")
    if not target_version or not re.fullmatch(r"v?\d+\.\d+(?:\.\d+)?", target_version, re.IGNORECASE):
        raise ValueError(f"Nieprawidłowy numer docelowej wersji: {target_version}")

    target_version = target_version.lstrip("vV")
    install_dir = app_exe.parent
    if not install_dir.is_dir():
        raise RuntimeError("Nie znaleziono katalogu instalacyjnego.")
    if not (install_dir / UPDATER_EXE).is_file():
        raise RuntimeError("W katalogu aplikacji nie znaleziono Updater.exe.")

    parent_dir = install_dir.parent
    new_install_dir = parent_dir / f"GreenUpLabelPrinter-{target_version}"
    if new_install_dir.resolve() == install_dir.resolve():
        raise RuntimeError("Aplikacja jest już zainstalowana w katalogu docelowej wersji.")
    if new_install_dir.exists():
        raise RuntimeError(
            "Katalog docelowej wersji już istnieje. Aktualizator nie nadpisze go automatycznie:\n"
            f"{new_install_dir}"
        )

    if pid > 0:
        print("Oczekiwanie na zamknięcie aplikacji...")
        wait_for_process(pid)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    staging_dir = parent_dir / f".greenup_staging_{timestamp}"
    backup_dir = parent_dir / f".greenup_backup_{timestamp}"
    failed_dir = parent_dir / f".greenup_failed_{timestamp}"
    staging_dir.mkdir(parents=True, exist_ok=False)

    old_install_moved = False
    new_install_moved = False
    new_process = None
    confirmation_file = None
    shortcut_snapshot = []
    shortcuts_changed = False

    try:
        print("Rozpakowywanie i weryfikacja aktualizacji...")
        safe_extract(archive_path, staging_dir)
        new_app_dir = find_application_root(staging_dir)

        # Najpierw zapisujemy stan skrótów, zanim zmienimy jakiekolwiek ścieżki.
        print("Wyszukiwanie skrótów aplikacji...")
        shortcut_snapshot = find_application_shortcuts(app_exe)
        print(f"Znaleziono skrótów: {len(shortcut_snapshot)}")

        print("Przenoszenie poprzedniej wersji do kopii zapasowej...")
        os.replace(install_dir, backup_dir)
        old_install_moved = True

        print(f"Instalowanie wersji {target_version}...")
        os.replace(new_app_dir, new_install_dir)
        new_install_moved = True

        for required in (APP_EXE, UPDATER_EXE):
            if not (new_install_dir / required).is_file():
                raise RuntimeError(f"Po aktualizacji brakuje pliku {required}.")
        if not (new_install_dir / "_internal").is_dir():
            raise RuntimeError("Po aktualizacji brakuje katalogu _internal.")

        # Zmiana skrótów następuje dopiero po prawidłowym umieszczeniu nowej wersji.
        print("Aktualizowanie skrótów Windows...")
        update_application_shortcuts(shortcut_snapshot, install_dir, new_install_dir)
        shortcuts_changed = bool(shortcut_snapshot)

        if launch_app:
            token = uuid.uuid4().hex
            confirmation_dir = Path(tempfile.gettempdir()) / "GreenUpLabelPrinter" / "confirmations"
            confirmation_dir.mkdir(parents=True, exist_ok=True)
            confirmation_file = confirmation_dir / f"{token}.txt"
            command = [
                str(new_install_dir / APP_EXE),
                "--update-confirmation-file", str(confirmation_file),
                "--update-confirmation-token", token,
            ]
            print("Uruchamianie nowej wersji...")
            new_process = subprocess.Popen(command, cwd=new_install_dir)
            wait_for_confirmation(
                confirmation_file=confirmation_file,
                expected_token=token,
                process=new_process,
                timeout=confirmation_timeout,
            )

        print("Aktualizacja zakończona pomyślnie.")
        print(f"Nowy katalog: {new_install_dir}")
        print(f"Kopia zapasowa: {backup_dir}")

    except Exception:
        print("\nWystąpił błąd aktualizacji. Przywracanie poprzedniej wersji...")
        if new_process is not None:
            terminate_process(new_process)

        # Najpierw cofamy skróty, gdyż w razie błędu nadal istnieje stara lokalizacja.
        if shortcuts_changed or shortcut_snapshot:
            try:
                restore_application_shortcuts(shortcut_snapshot)
                print("Przywrócono poprzednie ścieżki skrótów.")
            except Exception as shortcut_error:
                print(f"UWAGA: nie udało się w pełni przywrócić skrótów: {shortcut_error}")

        if new_install_moved and new_install_dir.exists():
            os.replace(new_install_dir, failed_dir)
        if old_install_moved and backup_dir.exists():
            os.replace(backup_dir, install_dir)
            print(f"Przywrócono poprzednią wersję: {install_dir}")
        if failed_dir.exists():
            shutil.rmtree(failed_dir, ignore_errors=True)
        raise

    finally:
        if confirmation_file and confirmation_file.exists():
            confirmation_file.unlink()
        if staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)


# --------------------------------------------------
# ARGUMENTS
# --------------------------------------------------

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="GreenUp Label Printer Updater"
    )

    parser.add_argument(
        "--pid",
        type=int,
        default=0
    )

    parser.add_argument(
        "--archive",
        type=Path,
        required=True
    )

    parser.add_argument(
        "--app-exe",
        type=Path,
        required=True
    )

    parser.add_argument(
        "--target-version",
        type=str,
        required=True,
        help="Docelowa wersja aplikacji, np. 1.1.1",
    )

    parser.add_argument(
        "--worker",
        action="store_true"
    )

    return parser.parse_args()


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    if os.name != "nt":
        raise RuntimeError(
            "Updater obsługuje obecnie tylko Windows."
        )

    arguments = parse_arguments()

    if not arguments.worker:
        if launch_worker(arguments):
            return

    install_update(
        archive_path=arguments.archive,
        app_exe=arguments.app_exe,
        pid=arguments.pid,
        target_version=arguments.target_version,
    )


if __name__ == "__main__":
    try:
        main()

    except Exception as error:
        print(f"\nBŁĄD AKTUALIZACJI: {error}")

        if os.name == "nt":
            input("\nNaciśnij Enter, aby zamknąć...")

        sys.exit(1)

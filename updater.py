
import argparse
import ctypes
import os
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
        "--app-exe", str(arguments.app_exe)
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
# INSTALLATION
# --------------------------------------------------

def install_update(
    archive_path,
    app_exe,
    pid,
    launch_app=True,
    confirmation_timeout=CONFIRMATION_TIMEOUT
):
    """
    Instaluje nową wersję aplikacji.

    Po instalacji uruchamia ją i oczekuje na
    potwierdzenie poprawnego startu.
    """

    archive_path = Path(archive_path).resolve()
    app_exe = Path(app_exe).resolve()

    if not archive_path.is_file():
        raise RuntimeError(
            "Nie znaleziono archiwum aktualizacji."
        )

    if app_exe.name.lower() != APP_EXE.lower():
        raise RuntimeError(
            f"Oczekiwano pliku {APP_EXE}."
        )

    install_dir = app_exe.parent

    if not install_dir.is_dir():
        raise RuntimeError(
            "Nie znaleziono katalogu instalacyjnego."
        )

    if not (install_dir / UPDATER_EXE).is_file():
        raise RuntimeError(
            "W katalogu aplikacji nie znaleziono Updater.exe."
        )

    if pid > 0:
        print("Oczekiwanie na zamknięcie aplikacji...")
        wait_for_process(pid)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    parent_dir = install_dir.parent

    staging_dir = (
        parent_dir / f".greenup_staging_{timestamp}"
    )

    backup_dir = (
        parent_dir / f".greenup_backup_{timestamp}_{datetime.now().strftime('%f')}"
    )

    staging_dir.mkdir(parents=True, exist_ok=False)

    old_install_moved = False
    new_process = None

    confirmation_file = None

    try:
        # 1. Rozpakowanie i weryfikacja archiwum.
        print("Rozpakowywanie aktualizacji...")

        safe_extract(
            archive_path,
            staging_dir
        )

        new_app_dir = find_application_root(staging_dir)

        # 2. Przygotowanie kopii zapasowej.
        print("Przygotowywanie kopii zapasowej...")

        os.replace(
            install_dir,
            backup_dir
        )

        old_install_moved = True

        # 3. Instalacja nowej wersji.
        print("Podmienianie plików aplikacji...")

        os.replace(
            new_app_dir,
            install_dir
        )

        if not (install_dir / APP_EXE).is_file():
            raise RuntimeError(
                "Po aktualizacji brakuje głównego pliku EXE."
            )

        if not (install_dir / "_internal").is_dir():
            raise RuntimeError(
                "Po aktualizacji brakuje katalogu _internal."
            )

        if not (install_dir / UPDATER_EXE).is_file():
            raise RuntimeError(
                "Po aktualizacji brakuje Updater.exe."
            )

        print("Nowa wersja została zainstalowana.")

        # 4. Uruchomienie i potwierdzenie.
        if launch_app:
            token = uuid.uuid4().hex

            confirmation_dir = (
                Path(tempfile.gettempdir())
                / "GreenUpLabelPrinter"
                / "confirmations"
            )

            confirmation_dir.mkdir(
                parents=True,
                exist_ok=True
            )

            confirmation_file = (
                confirmation_dir / f"{token}.txt"
            )

            command = [
                str(install_dir / APP_EXE),
                "--update-confirmation-file",
                str(confirmation_file),
                "--update-confirmation-token",
                token
            ]

            print("Uruchamianie nowej wersji...")

            new_process = subprocess.Popen(
                command,
                cwd=install_dir
            )

            wait_for_confirmation(
                confirmation_file=confirmation_file,
                expected_token=token,
                process=new_process,
                timeout=confirmation_timeout
            )

            print("Aktualizacja zakończona pomyślnie.")
            print(f"Kopia zapasowa: {backup_dir}")

        else:
            print(
                "Tryb testowy: pominięto uruchamianie aplikacji."
            )

    except Exception:
        print(
            "\nWystąpił błąd aktualizacji. "
            "Przywracanie poprzedniej wersji..."
        )

        if new_process is not None:
            terminate_process(new_process)

        if old_install_moved:
            failed_dir = (
                parent_dir / f".greenup_failed_{timestamp}"
            )

            if install_dir.exists():
                os.replace(
                    install_dir,
                    failed_dir
                )

            os.replace(
                backup_dir,
                install_dir
            )

            if failed_dir.exists():
                shutil.rmtree(
                    failed_dir,
                    ignore_errors=True
                )

            print("Poprzednia wersja została przywrócona.")

        raise

    finally:
        if confirmation_file and confirmation_file.exists():
            confirmation_file.unlink()

        if staging_dir.exists():
            shutil.rmtree(
                staging_dir,
                ignore_errors=True
            )


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
        pid=arguments.pid
    )


if __name__ == "__main__":
    try:
        main()

    except Exception as error:
        print(f"\nBŁĄD AKTUALIZACJI: {error}")

        if os.name == "nt":
            input("\nNaciśnij Enter, aby zamknąć...")

        sys.exit(1)

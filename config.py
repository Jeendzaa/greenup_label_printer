from pathlib import Path
import sys


APP_NAME = "GreenUpLabelPrinter"


def get_documents_dir():
    """
    Zwraca katalog Dokumenty użytkownika.
    """

    return Path.home() / "Documents"


def get_app_data_dir():
    """
    Główny katalog danych aplikacji.
    """

    return get_documents_dir() / APP_NAME


def get_templates_dir():
    """
    Katalog szablonów edytowalnych przez użytkownika.
    """

    return get_app_data_dir() / "templates"


def get_config_file():
    return get_app_data_dir() / "config.json"


def get_resource_dir():
    """
    Katalog zasobów aplikacji.

    Obsługuje zwykłe uruchomienie oraz przyszłe
    pakowanie aplikacji przez PyInstaller.
    """

    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)

    return Path(__file__).resolve().parent


def get_bundled_templates_dir():
    return get_resource_dir() / "templates"
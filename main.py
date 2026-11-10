
import argparse
import os

from pathlib import Path

from services.template_service import TemplateService
from services.zpl_service import ZPLService
from services.printer_service import PrinterService
from views.main_window import MainWindow


def parse_arguments():
    """Odczytuje argumenty przekazane do aplikacji."""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--update-confirmation-file",
        type=Path
    )

    parser.add_argument(
        "--update-confirmation-token",
        type=str
    )

    return parser.parse_args()


def confirm_update_start(arguments):
    """
    Zapisuje potwierdzenie poprawnego uruchomienia aplikacji.

    Plik jest zapisywany atomowo, aby aktualizator
    nie odczytał częściowo zapisanego tokenu.
    """

    confirmation_file = arguments.update_confirmation_file
    confirmation_token = arguments.update_confirmation_token

    if confirmation_file is None and confirmation_token is None:
        return

    if confirmation_file is None or not confirmation_token:
        raise ValueError(
            "Niekompletne dane potwierdzenia aktualizacji."
        )

    confirmation_file = confirmation_file.resolve()

    confirmation_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    temporary_file = confirmation_file.with_name(
        confirmation_file.name + ".tmp"
    )

    try:
        temporary_file.write_text(
            confirmation_token,
            encoding="utf-8"
        )

        os.replace(
            temporary_file,
            confirmation_file
        )

    finally:
        if temporary_file.exists():
            temporary_file.unlink()


def main():
    arguments = parse_arguments()

    # Inicjalizacja serwisów.
    template_service = TemplateService()
    zpl_service = ZPLService()
    printer_service = PrinterService()

    # Inicjalizacja głównego okna.
    app = MainWindow(
        template_service=template_service,
        zpl_service=zpl_service,
        printer_service=printer_service,
    )

    # Potwierdzenie poprawnego uruchomienia.
    confirm_update_start(arguments)

    # Uruchomienie pętli aplikacji.
    app.mainloop()


if __name__ == "__main__":
    main()

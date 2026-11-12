import os
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from config import APP_VERSION
from services.download_service import DownloadService
from services.update_service import UpdateService
from views.print_view import PrintView
from views.template_editor import TemplateEditorView
from views.zpl_view import ZPLView


class MainWindow(ctk.CTk):
    def __init__(
        self,
        template_service,
        zpl_service,
        printer_service,
    ):
        super().__init__()

        icon_path = (
            Path(__file__).resolve().parent.parent
            / "assets"
            / "greenup_label_printer_icon.ico"
        )

        if icon_path.is_file():
            self.iconbitmap(str(icon_path))

        self.template_service = template_service
        self.zpl_service = zpl_service
        self.printer_service = printer_service

        # Usługi aktualizacji.
        self.update_service = UpdateService()
        self.download_service = DownloadService()
        self.update_in_progress = False

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("GreenUp! Label Printer")
        self.minsize(900, 600)
        self.after(0, self.state, "zoomed")

        self.sidebar_color = "#18212B"
        self.main_color = "#222D38"
        self.accent_color = "#27845B"
        self.text_color = "#F3F6F8"
        self.muted_color = "#AAB7C4"

        self.configure(fg_color=self.main_color)

        # Główny układ okna: treść + pasek statusu.
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        self._create_workspace()
        self._create_status_bar()
        self._create_views()

        self.show_view("druk")

        # Ciche sprawdzenie aktualizacji po uruchomieniu GUI.
        self.after(1500, self._automatic_update_check)

    def _create_workspace(self):
        """Tworzy obszar roboczy z menu i panelem treści."""

        self.workspace = ctk.CTkFrame(
            self,
            fg_color=self.main_color,
            corner_radius=0,
        )
        self.workspace.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        self.workspace.grid_columnconfigure(0, weight=0)
        self.workspace.grid_columnconfigure(1, weight=1)
        self.workspace.grid_rowconfigure(0, weight=1)

        self._create_sidebar()
        self._create_main_area()

    def _create_sidebar(self):
        """Tworzy menu boczne."""

        self.sidebar = ctk.CTkFrame(
            self.workspace,
            width=230,
            corner_radius=0,
            fg_color=self.sidebar_color,
        )
        self.sidebar.grid(
            row=0,
            column=0,
            sticky="nsew",
        )
        self.sidebar.grid_propagate(False)

        logo = ctk.CTkLabel(
            self.sidebar,
            text="GREENUP!\nLABEL PRINTER",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=self.text_color,
            justify="left",
        )
        logo.pack(
            anchor="w",
            padx=22,
            pady=(28, 35),
        )

        self.menu_buttons = {}

        menu_items = [
            ("druk", "Drukuj etykietę"),
            ("tworz", "Edytor szablonów"),
            ("zplcode", "Kod ZPL"),
        ]

        for view_id, label in menu_items:
            button = ctk.CTkButton(
                self.sidebar,
                text=label,
                height=42,
                anchor="w",
                corner_radius=8,
                fg_color="transparent",
                hover_color="#2B3947",
                text_color=self.text_color,
                font=ctk.CTkFont(size=14),
                command=lambda v=view_id: self.show_view(v),
            )
            button.pack(
                fill="x",
                padx=12,
                pady=4,
            )

            self.menu_buttons[view_id] = button

        # Elementy dolnej części sidebara.
        exit_button = ctk.CTkButton(
            self.sidebar,
            text="Zamknij program",
            height=40,
            corner_radius=8,
            fg_color="#873D42",
            hover_color="#A44A50",
            command=self.destroy,
        )
        exit_button.pack(
            side="bottom",
            fill="x",
            padx=12,
            pady=(8, 18),
        )

        self.update_button = ctk.CTkButton(
            self.sidebar,
            text="Sprawdź aktualizacje",
            height=40,
            corner_radius=8,
            fg_color="#27845B",
            hover_color="#206B49",
            command=self.check_for_updates,
        )
        self.update_button.pack(
            side="bottom",
            fill="x",
            padx=12,
            pady=6,
        )

        self.version_label = ctk.CTkLabel(
            self.sidebar,
            text=f"Wersja {APP_VERSION}",
            text_color=self.muted_color,
            font=ctk.CTkFont(size=11),
        )
        self.version_label.pack(
            side="bottom",
            anchor="w",
            padx=18,
            pady=(6, 4),
        )

    def _create_main_area(self):
        """Tworzy panel zajmujący całą pozostałą przestrzeń."""

        self.main_frame = ctk.CTkFrame(
            self.workspace,
            fg_color=self.main_color,
            corner_radius=0,
        )
        self.main_frame.grid(
            row=0,
            column=1,
            sticky="nsew",
        )

        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        self.page_title = ctk.CTkLabel(
            self.main_frame,
            text="",
            font=ctk.CTkFont(size=27, weight="bold"),
            text_color=self.text_color,
        )
        self.page_title.grid(
            row=0,
            column=0,
            sticky="w",
            padx=30,
            pady=(25, 15),
        )

        self.content_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color="transparent",
            corner_radius=0,
        )
        self.content_frame.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=30,
            pady=(0, 25),
        )

        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

    def _create_status_bar(self):
        """Tworzy pasek statusu u dołu okna."""

        self.status_bar = ctk.CTkFrame(
            self,
            height=34,
            corner_radius=0,
            fg_color="#141C24",
        )
        self.status_bar.grid(
            row=1,
            column=0,
            sticky="ew",
        )
        self.status_bar.grid_propagate(False)

        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text="Citizen: 192.168.130.92 | TCP 9100",
            text_color=self.muted_color,
            font=ctk.CTkFont(size=12),
        )
        self.status_label.pack(
            side="left",
            padx=18,
        )

        self.connection_label = ctk.CTkLabel(
            self.status_bar,
            text="Gotowy",
            text_color="#65D69A",
            font=ctk.CTkFont(size=12),
        )
        self.connection_label.pack(
            side="right",
            padx=18,
        )

    def _create_views(self):
        """Tworzy widoki i przechowuje je w jednym słowniku."""

        self.views = {
            "druk": PrintView(
                self.content_frame,
                self.template_service,
                self.zpl_service,
                self.printer_service,
            ),
            "tworz": TemplateEditorView(
                self.content_frame,
                self.template_service,
                self.zpl_service,
                self.printer_service,
            ),
            "zplcode": ZPLView(
                self.content_frame,
                self.printer_service,
            ),
        }

        for view in self.views.values():
            view.grid(
                row=0,
                column=0,
                sticky="nsew",
            )
            view.grid_remove()

    def show_view(self, view_id):
        """Pokazuje wybrany widok i aktualizuje menu."""

        if view_id not in self.views:
            return

        for view in self.views.values():
            view.grid_remove()

        self.views[view_id].grid()

        # Odświeżamy listę szablonów przy każdym wejściu
        # do zakładki drukowania oraz edytora.
        if view_id == "druk":
            self.views["druk"].refresh_templates()
        elif view_id == "tworz":
            self.views["tworz"].refresh_templates()

        titles = {
            "druk": "Drukuj etykietę",
            "tworz": "Edytor szablonów",
            "zplcode": "Kod ZPL",
        }

        self.page_title.configure(text=titles[view_id])

        for key, button in self.menu_buttons.items():
            if key == view_id:
                button.configure(
                    fg_color=self.accent_color,
                    hover_color=self.accent_color,
                )
            else:
                button.configure(
                    fg_color="transparent",
                    hover_color="#2B3947",
                )

    # =========================================================
    # UPDATE SYSTEM
    # =========================================================

    def _automatic_update_check(self):
        """Sprawdza aktualizacje po uruchomieniu, bez komunikatu gdy brak zmian."""
        if not self.update_in_progress:
            self.check_for_updates(silent=True)

    def check_for_updates(self, silent=False):
        """Uruchamia sprawdzanie najnowszego Release w tle."""

        if self.update_in_progress:
            return

        self.update_in_progress = True
        self.update_button.configure(
            state="disabled",
            text="Sprawdzanie...",
        )
        self.connection_label.configure(
            text="Sprawdzanie aktualizacji...",
            text_color="#E6C76A",
        )

        threading.Thread(
            target=self._check_updates_worker,
            args=(silent,),
            daemon=True,
        ).start()

    def _check_updates_worker(self, silent=False):
        try:
            release_info = self.update_service.check_for_updates()
        except Exception as error:
            self.after(
                0,
                lambda message=str(error), is_silent=silent: self._on_update_check_error(message, is_silent),
            )
            return

        self.after(
            0,
            lambda info=release_info, is_silent=silent: self._on_update_check_complete(info, is_silent),
        )

    def _on_update_check_error(self, error_message, silent=False):
        self._finish_update_operation()

        self.connection_label.configure(
            text="Nie udało się sprawdzić aktualizacji",
            text_color="#F08080",
        )

        if not silent:
            messagebox.showerror(
                "Błąd sprawdzania aktualizacji",
                error_message,
                parent=self,
            )

    def _on_update_check_complete(self, release_info, silent=False):
        if not release_info["update_available"]:
            self._finish_update_operation()

            self.connection_label.configure(
                text="Program jest aktualny",
                text_color="#65D69A",
            )

            if not silent:
                messagebox.showinfo(
                    "Brak aktualizacji",
                    (
                        "Korzystasz z najnowszej dostępnej wersji programu.\n\n"
                        f"Zainstalowana wersja: {release_info['current_version']}"
                    ),
                    parent=self,
                )
            return

        latest_version = release_info["latest_version"]
        release_name = release_info.get("release_name") or latest_version
        release_notes = release_info.get("release_notes", "").strip()

        if not release_notes:
            release_notes = "Brak opisu zmian dla tej wersji."

        details = (
            f"Dostępna jest nowa wersja GreenUp! Label Printer.\n\n"
            f"Zainstalowana wersja: {release_info['current_version']}\n"
            f"Dostępna wersja: {latest_version}\n"
            f"Wydanie: {release_name}\n\n"
            f"Opis zmian:\n{release_notes}\n\n"
            "Czy pobrać i zainstalować aktualizację?"
        )

        install_confirmation = messagebox.askyesno(
            "Dostępna aktualizacja",
            details,
            parent=self,
        )

        if not install_confirmation:
            self._finish_update_operation()
            self.connection_label.configure(
                text="Aktualizacja pominięta",
                text_color=self.muted_color,
            )
            return

        self.update_button.configure(
            text="Pobieranie...",
        )
        self.connection_label.configure(
            text=f"Pobieranie wersji {latest_version}...",
            text_color="#E6C76A",
        )

        threading.Thread(
            target=self._download_update_worker,
            args=(release_info,),
            daemon=True,
        ).start()

    def _download_update_worker(self, release_info):
        try:
            archive_path = self.download_service.download_update(release_info)
        except Exception as error:
            self.after(
                0,
                lambda message=str(error): self._on_update_download_error(message),
            )
            return

        target_version = release_info["latest_version"]
        self.after(
            0,
            lambda path=archive_path, version=target_version:
                self._on_update_download_complete(path, version),
        )

    def _on_update_download_error(self, error_message):
        self._finish_update_operation()

        self.connection_label.configure(
            text="Nie udało się pobrać aktualizacji",
            text_color="#F08080",
        )

        messagebox.showerror(
            "Błąd pobierania aktualizacji",
            error_message,
            parent=self,
        )

    def _on_update_download_complete(self, archive_path, target_version):
        # Instalacja wymaga uruchomionej wersji EXE.
        if not getattr(sys, "frozen", False):
            self._finish_update_operation()
            messagebox.showinfo(
                "Pobieranie zakończone",
                (
                    "Aktualizacja została pobrana i zweryfikowana.\n\n"
                    f"Archiwum:\n{archive_path}\n\n"
                    "Automatyczna instalacja będzie dostępna "
                    "w skompilowanej wersji programu."
                ),
                parent=self,
            )
            return

        install_dir = Path(sys.executable).resolve().parent
        updater_path = install_dir / "Updater.exe"
        app_exe = Path(sys.executable).resolve()

        if not updater_path.is_file():
            self._finish_update_operation()
            messagebox.showerror(
                "Brak aktualizatora",
                (
                    "Nie znaleziono Updater.exe w katalogu programu.\n\n"
                    f"Oczekiwana lokalizacja:\n{updater_path}"
                ),
                parent=self,
            )
            return

        confirmed = messagebox.askyesno(
            "Gotowa do instalacji",
            (
                "Aktualizacja została pobrana i zweryfikowana.\n\n"
                "Program zostanie teraz zamknięty, a aktualizator "
                "zainstaluje nową wersję.\n\n"
                "Czy kontynuować?"
            ),
            parent=self,
        )

        if not confirmed:
            self._finish_update_operation()
            self.connection_label.configure(
                text="Aktualizacja pobrana — instalacja odłożona",
                text_color=self.muted_color,
            )
            messagebox.showinfo(
                "Aktualizacja pobrana",
                (
                    "Archiwum aktualizacji pozostaje zapisane w katalogu "
                    "tymczasowym systemu. Możesz ponownie uruchomić "
                    "sprawdzanie aktualizacji, aby rozpocząć instalację."
                ),
                parent=self,
            )
            return

        command = [
            str(updater_path),
            "--pid",
            str(os.getpid()),
            "--archive",
            str(archive_path),
            "--app-exe",
            str(app_exe),
            "--target-version",
            str(target_version),
        ]

        try:
            subprocess.Popen(
                command,
                cwd=install_dir,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
        except OSError as error:
            self._finish_update_operation()
            messagebox.showerror(
                "Nie można uruchomić aktualizatora",
                str(error),
                parent=self,
            )
            return

        # Updater poczeka na zakończenie tego procesu,
        # a następnie podmieni katalog aplikacji.
        self.destroy()

    def _finish_update_operation(self):
        self.update_in_progress = False

        try:
            self.update_button.configure(
                state="normal",
                text="Sprawdź aktualizacje",
            )
        except (AttributeError, RuntimeError):
            pass



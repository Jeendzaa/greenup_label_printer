
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image as PILImage
import re

from services.preview_service import PreviewService


class ZPLView(ctk.CTkFrame):
    def __init__(self, parent, printer_service):
        super().__init__(parent, fg_color="transparent")

        self.printer_service = printer_service
        self.preview_service = PreviewService(dpi=203)

        self.preview_image = None
        self._preview_images = []
        self.preview_job = None
        self._preview_generation = 0
        self._destroyed = False

        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        self._create_widgets()
        self.bind("<Destroy>", self._on_destroy, add="+")

    def _create_widgets(self):
        description = ctk.CTkLabel(
            self,
            text=(
                "Pisz kod ZPL i sprawdzaj wygląd etykiety "
                "przed wysłaniem go do drukarki."
            ),
            font=ctk.CTkFont(size=14),
            text_color="#AAB7C4",
            wraplength=800,
            justify="left",
        )
        description.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 18),
        )

        # Lewy panel: edytor ZPL
        self.editor_panel = ctk.CTkFrame(
            self,
            fg_color="#2A3744",
            corner_radius=12,
        )
        self.editor_panel.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=(0, 12),
        )
        self.editor_panel.grid_columnconfigure(0, weight=1)
        self.editor_panel.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self.editor_panel,
            text="Edytor kodu ZPL",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=20,
            pady=(20, 12),
        )

        self.zpl_textbox = ctk.CTkTextbox(
            self.editor_panel,
            font=ctk.CTkFont(family="Consolas", size=13),
            wrap="none",
            undo=True,
        )
        self.zpl_textbox.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=12,
            pady=(0, 12),
        )
        self.zpl_textbox.bind(
            "<KeyRelease>",
            self._on_code_changed,
        )
        self.zpl_textbox.bind(
            "<FocusOut>",
            self._on_code_changed,
        )

        editor_buttons = ctk.CTkFrame(
            self.editor_panel,
            fg_color="transparent",
        )
        editor_buttons.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=12,
            pady=(0, 12),
        )
        editor_buttons.grid_columnconfigure((0, 1), weight=1)

        self.preview_button = ctk.CTkButton(
            editor_buttons,
            text="Odśwież podgląd",
            height=38,
            command=self._update_preview_now,
        )
        self.preview_button.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 5),
        )

        self.clear_button = ctk.CTkButton(
            editor_buttons,
            text="Wyczyść kod",
            height=38,
            fg_color="#4A5663",
            hover_color="#5B6876",
            command=self._clear_code,
        )
        self.clear_button.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(5, 0),
        )

        self.send_button = ctk.CTkButton(
            self.editor_panel,
            text="Wyślij ZPL do drukarki",
            height=42,
            fg_color="#27845B",
            hover_color="#206B49",
            command=self._send_zpl,
        )
        self.send_button.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=12,
            pady=(0, 20),
        )

        # Prawy panel: podgląd
        self.preview_panel = ctk.CTkFrame(
            self,
            fg_color="#2A3744",
            corner_radius=12,
        )
        self.preview_panel.grid(
            row=1,
            column=1,
            sticky="nsew",
            padx=(12, 0),
        )
        self.preview_panel.grid_columnconfigure(0, weight=1)
        self.preview_panel.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self.preview_panel,
            text="Podgląd etykiety",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=20,
            pady=(20, 10),
        )

        self.preview_container = ctk.CTkFrame(
            self.preview_panel,
            fg_color="#FFFFFF",
            corner_radius=6,
        )
        self.preview_container.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=20,
            pady=(0, 12),
        )
        self.preview_container.grid_columnconfigure(0, weight=1)
        self.preview_container.grid_rowconfigure(0, weight=1)

        self.preview_label = ctk.CTkLabel(
            self.preview_container,
            text="Wpisz kod ZPL, aby zobaczyć podgląd.",
            text_color="#333333",
            fg_color="#FFFFFF",
            wraplength=350,
        )
        self.preview_label.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=8,
            pady=8,
        )

        self.preview_status = ctk.CTkLabel(
            self.preview_panel,
            text="Podgląd lokalny • 203 DPI",
            text_color="#AAB7C4",
            font=ctk.CTkFont(size=12),
            wraplength=350,
        )
        self.preview_status.grid(
            row=2,
            column=0,
            sticky="w",
            padx=20,
            pady=(0, 15),
        )

    def _on_code_changed(self, _event=None):
        self._schedule_preview()

    def _schedule_preview(self):
        if self._destroyed:
            return

        self._cancel_preview_job()
        generation = self._preview_generation

        self.preview_job = self.after(
            350,
            lambda: self._update_preview(generation),
        )

    def _cancel_preview_job(self):
        self._preview_generation += 1

        if self.preview_job is not None:
            try:
                self.after_cancel(self.preview_job)
            except (ValueError, RuntimeError):
                pass

            self.preview_job = None

    def _update_preview_now(self):
        self._cancel_preview_job()
        self._update_preview(self._preview_generation)

    def _update_preview(self, generation=None):
        self.preview_job = None

        if self._destroyed:
            return

        if (
            generation is not None
            and generation != self._preview_generation
        ):
            return

        zpl = self.zpl_textbox.get("1.0", "end-1c").strip()

        if not zpl:
            self.preview_label.configure(
                image=None,
                text="Wpisz kod ZPL, aby zobaczyć podgląd.",
            )
            self.preview_status.configure(
                text="Brak kodu ZPL",
                text_color="#AAB7C4",
            )
            self.preview_image = None
            return

        try:
            # Modyfikujemy wyłącznie kopię kodu przeznaczoną do podglądu.
            preview_zpl = re.sub(
                r"\^PQ[^^\r\n]*",
                "",
                zpl,
                flags=re.IGNORECASE,
            )

            image = self.preview_service.generate_preview(
                preview_zpl,
                width_mm=75,
                height_mm=49,
)

            # Jeśli w trakcie generowania zmienił się kod,
            # nie pokazujemy już nieaktualnego obrazu.
            if (
                self._destroyed
                or generation != self._preview_generation
            ):
                return

            image.thumbnail(
                (420, 420),
                PILImage.Resampling.LANCZOS,
            )

            new_image = ctk.CTkImage(
                light_image=image,
                dark_image=image,
                size=image.size,
            )

            # Zachowujemy referencję, aby Tkinter nie utracił obrazu.
            self._preview_images.append(new_image)
            self.preview_image = new_image

            self.preview_label.configure(
                image=new_image,
                text="",
                width=420,
                height=420,
            )

            self.preview_status.configure(
                text="Podgląd wygenerowany lokalnie",
                text_color="#65D69A",
            )

        except Exception as error:
            if self._destroyed:
                return

            self.preview_label.configure(
                image=None,
                text=(
                    "Nie można wygenerować podglądu.\n"
                    "Sprawdź składnię ZPL."
                ),
            )

            self.preview_status.configure(
                text=f"Błąd podglądu: {error}",
                text_color="#F08080",
            )

            self.preview_image = None

    def _clear_code(self):
        self._cancel_preview_job()
        self.zpl_textbox.delete("1.0", "end")

        self.preview_label.configure(
            image=None,
            text="Wpisz kod ZPL, aby zobaczyć podgląd.",
        )
        self.preview_status.configure(
            text="Kod wyczyszczony",
            text_color="#AAB7C4",
        )

        self.preview_image = None

    def _send_zpl(self):
        zpl = self.zpl_textbox.get("1.0", "end-1c").strip()

        if not zpl:
            messagebox.showwarning(
                "Brak kodu",
                "Wpisz kod ZPL przed wysłaniem.",
                parent=self,
            )
            return

        upper_zpl = zpl.upper()

        if "^XA" not in upper_zpl or "^XZ" not in upper_zpl:
            messagebox.showwarning(
                "Nieprawidłowy kod ZPL",
                "Kod musi zawierać komendy ^XA oraz ^XZ.",
                parent=self,
            )
            return

        confirmed = messagebox.askyesno(
            "Potwierdź drukowanie",
            "Czy wysłać wpisany kod ZPL do drukarki Citizen?\n\n"
            "Kod może zawierać własną liczbę kopii ^PQ.",
            parent=self,
        )

        if not confirmed:
            return

        self.send_button.configure(
            state="disabled",
            text="Wysyłanie...",
        )

        try:
            # Wysyłamy dokładnie wpisany kod. Nie modyfikujemy ^PQ.
            self.printer_service.send_zpl(zpl)

            self.preview_status.configure(
                text="Dane wysłano do drukarki",
                text_color="#65D69A",
            )

            messagebox.showinfo(
                "Wysyłanie zakończone",
                "Dane ZPL wysłano do drukarki Citizen.\n\n"
                "Sprawdź fizyczny wydruk.",
                parent=self,
            )

        except (ConnectionError, OSError, ValueError) as error:
            self.preview_status.configure(
                text=f"Błąd wysyłania: {error}",
                text_color="#F08080",
            )

            messagebox.showerror(
                "Błąd drukowania",
                str(error),
                parent=self,
            )

        finally:
            if not self._destroyed:
                self.send_button.configure(
                    state="normal",
                    text="Wyślij ZPL do drukarki",
                )

    def _on_destroy(self, event=None):
        if event is not None and event.widget is not self:
            return

        self._destroyed = True
        self._cancel_preview_job()

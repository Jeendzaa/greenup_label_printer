
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image as PILImage

from services.preview_service import PreviewService


class PrintView(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        template_service,
        zpl_service,
        printer_service,
    ):
        super().__init__(parent, fg_color="transparent")

        self.template_service = template_service
        self.zpl_service = zpl_service
        self.printer_service = printer_service
        self.preview_service = PreviewService(dpi=203)

        self.templates_by_name = {}
        self.field_entries = {}

        # Przechowujemy referencje do obrazów, żeby Tkinter
        # nie próbował korzystać z usuniętego zasobu PhotoImage.
        self.preview_image = None
        self._preview_images = []

        self.preview_job = None
        self._preview_generation = 0
        self._destroyed = False

        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        self._create_widgets()
        self._load_templates()

        self.bind("<Destroy>", self._on_destroy, add="+")

    def _create_widgets(self):
        description = ctk.CTkLabel(
            self,
            text="Uzupełnij dane i sprawdź etykietę przed drukowaniem.",
            font=ctk.CTkFont(size=14),
            text_color="#AAB7C4",
            wraplength=700,
            justify="left",
        )
        description.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 18),
        )

        # Lewy panel: formularz
        self.form_panel = ctk.CTkFrame(
            self,
            fg_color="#2A3744",
            corner_radius=12,
        )
        self.form_panel.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=(0, 12),
        )
        self.form_panel.grid_columnconfigure(0, weight=1)
        self.form_panel.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(
            self.form_panel,
            text="Dane etykiety",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=20,
            pady=(20, 12),
        )

        self.template_selector = ctk.CTkComboBox(
            self.form_panel,
            values=["Ładowanie..."],
            state="readonly",
            command=self._on_template_selected,
        )
        self.template_selector.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 12),
        )

        # Ilość drukowanych kopii
        quantity_frame = ctk.CTkFrame(
            self.form_panel,
            fg_color="transparent",
        )
        quantity_frame.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 12),
        )
        quantity_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            quantity_frame,
            text="Ilość sztuk",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 5),
        )

        self.quantity_entry = ctk.CTkEntry(
            quantity_frame,
            height=36,
            placeholder_text="Wpisz ilość kopii",
        )
        self.quantity_entry.grid(
            row=1,
            column=0,
            sticky="ew",
        )
        self.quantity_entry.insert(0, "1")
        self.quantity_entry.bind(
            "<KeyRelease>",
            self._on_quantity_changed,
        )

        # Pola wybranego szablonu
        self.form_frame = ctk.CTkScrollableFrame(
            self.form_panel,
            fg_color="transparent",
        )
        self.form_frame.grid(
            row=3,
            column=0,
            sticky="nsew",
            padx=12,
            pady=(0, 10),
        )
        self.form_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            self.form_panel,
            text="",
            text_color="#AAB7C4",
            wraplength=400,
            justify="left",
        )
        self.status_label.grid(
            row=4,
            column=0,
            sticky="w",
            padx=20,
            pady=8,
        )

        self.print_button = ctk.CTkButton(
            self.form_panel,
            text="Drukuj 1 szt.",
            height=42,
            fg_color="#27845B",
            hover_color="#206B49",
            command=self._print_label,
        )
        self.print_button.grid(
            row=5,
            column=0,
            sticky="ew",
            padx=20,
            pady=(5, 20),
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
            text="Podgląd pojawi się tutaj",
            text_color="#333333",
            fg_color="#FFFFFF",
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
            wraplength=300,
        )
        self.preview_status.grid(
            row=2,
            column=0,
            sticky="w",
            padx=20,
            pady=(0, 15),
        )

    def _load_templates(self):
        try:
            templates = self.template_service.load_templates()

            self.templates_by_name = {
                template["name"]: template
                for template in templates
            }

            names = list(self.templates_by_name.keys())

            if not names:
                self.template_selector.configure(
                    values=["Brak szablonów"],
                    state="disabled",
                )
                self.status_label.configure(
                    text="Nie znaleziono szablonów JSON."
                )
                return

            self.template_selector.configure(
                values=names,
                state="readonly",
            )
            self.template_selector.set(names[0])
            self._on_template_selected(names[0])

        except (OSError, ValueError) as error:
            self.status_label.configure(
                text=f"Błąd wczytywania szablonów: {error}"
            )

    def _on_template_selected(self, template_name):
        template = self.templates_by_name.get(template_name)

        if template is None:
            return

        self._clear_form()

        for row, field in enumerate(template["fields"]):
            label_text = field["label"]

            if field.get("required", False):
                label_text += " *"

            ctk.CTkLabel(
                self.form_frame,
                text=label_text,
                font=ctk.CTkFont(size=13),
            ).grid(
                row=row * 2,
                column=0,
                sticky="w",
                pady=(8, 4),
            )

            entry = ctk.CTkEntry(
                self.form_frame,
                height=36,
                placeholder_text=field["label"],
            )
            entry.grid(
                row=row * 2 + 1,
                column=0,
                sticky="ew",
                pady=(0, 5),
            )

            default = field.get("default", "")
            if default:
                entry.insert(0, default)

            entry.bind("<KeyRelease>", self._on_field_changed)
            entry.bind("<FocusOut>", self._on_field_changed)

            self.field_entries[field["name"]] = entry

        self.status_label.configure(
            text=(
                f"{template['width']} × {template['height']} mm"
                " | Pola oznaczone * są wymagane."
            ),
            text_color="#AAB7C4",
        )

        self._schedule_preview()

    def _clear_form(self):
        self._cancel_preview_job()

        for widget in self.form_frame.winfo_children():
            widget.destroy()

        self.field_entries.clear()

    def _on_field_changed(self, _event=None):
        self._schedule_preview()

    def _on_quantity_changed(self, _event=None):
        quantity_text = self.quantity_entry.get().strip()

        if quantity_text.isdigit() and int(quantity_text) > 0:
            quantity = int(quantity_text)
            self.print_button.configure(
                text=f"Drukuj {quantity} szt."
            )
        else:
            self.print_button.configure(
                text="Drukuj etykiety"
            )

    def _cancel_preview_job(self):
        # Unieważniamy również zadania, które już nie powinny
        # aktualizować podglądu.
        self._preview_generation += 1

        if self.preview_job is not None:
            try:
                self.after_cancel(self.preview_job)
            except (ValueError, RuntimeError):
                pass

            self.preview_job = None

    def _schedule_preview(self):
        if self._destroyed:
            return

        self._cancel_preview_job()
        generation = self._preview_generation

        self.preview_job = self.after(
            300,
            lambda: self._update_preview(generation),
        )

    def _update_preview(self, generation=None):
        self.preview_job = None

        if self._destroyed:
            return

        if generation is not None and generation != self._preview_generation:
            return

        template = self.templates_by_name.get(
            self.template_selector.get()
        )

        if template is None:
            return

        values = {
            name: entry.get()
            for name, entry in self.field_entries.items()
        }

        try:
            zpl = self.zpl_service.generate(template, values)

            image = self.preview_service.generate_preview(
                zpl,
                template["width"],
                template["height"],
            )

            if self._destroyed:
                return

            # Ograniczamy rozmiar obrazu do dostępnego miejsca.
            image.thumbnail(
                (420, 300),
                PILImage.Resampling.LANCZOS,
            )

            new_preview_image = ctk.CTkImage(
                light_image=image,
                dark_image=image,
                size=image.size,
            )

            # Przechowujemy referencję przed przekazaniem obrazu
            # do widżetu, aby nie został usunięty przez GC.
            self._preview_images.append(new_preview_image)
            self.preview_image = new_preview_image

            self.preview_label.configure(
                image=self.preview_image,
                text="",
                width=420,
                height=300,
            )

            self.preview_status.configure(
                text="Podgląd wygenerowany lokalnie",
                text_color="#65D69A",
            )

        except (ValueError, TypeError, OSError, RuntimeError) as error:
            if self._destroyed:
                return

            # Zachowujemy referencje do poprzednich obrazów.
            # Czyścimy widżet, ale nie niszczymy zasobu obrazu
            # podczas aktualizacji GUI.
            self.preview_label.configure(
                text="Nie można wygenerować podglądu.\n"
                     "Sprawdź wprowadzone dane.",
            )

            self.preview_status.configure(
                text=f"Podgląd niedostępny: {error}",
                text_color="#F08080",
            )

    def _on_destroy(self, event=None):
        # Zdarzenie Destroy jest wysyłane również dla dzieci,
        # dlatego reagujemy tylko na zniszczenie tego widoku.
        if event is not None and event.widget is not self:
            return

        self._destroyed = True
        self._cancel_preview_job()

    def _print_label(self):
        template = self.templates_by_name.get(
            self.template_selector.get()
        )

        if template is None:
            messagebox.showerror(
                "Brak szablonu",
                "Wybierz prawidłowy szablon.",
                parent=self,
            )
            return

        quantity_text = self.quantity_entry.get().strip()

        if not quantity_text.isdigit() or int(quantity_text) < 1:
            messagebox.showwarning(
                "Nieprawidłowa ilość",
                "Wpisz liczbę całkowitą większą od zera.",
                parent=self,
            )
            self.quantity_entry.focus_set()
            return

        quantity = int(quantity_text)

        values = {
            name: entry.get().strip()
            for name, entry in self.field_entries.items()
        }

        try:
            zpl = self.zpl_service.generate(template, values)
        except (ValueError, TypeError) as error:
            messagebox.showwarning(
                "Nieprawidłowe dane",
                str(error),
                parent=self,
            )
            return

        confirmed = messagebox.askyesno(
            "Potwierdź drukowanie",
            f"Czy wydrukować {quantity} "
            f"{'kopię' if quantity == 1 else 'kopii'} etykiety?",
            parent=self,
        )

        if not confirmed:
            return

        self.print_button.configure(
            state="disabled",
            text="Wysyłanie...",
        )

        try:
            self.printer_service.send_zpl(
                zpl,
                copies=quantity,
            )

            self.status_label.configure(
                text=f"Wysłano zadanie na {quantity} etykiet.",
                text_color="#65D69A",
            )

            messagebox.showinfo(
                "Wysyłanie zakończone",
                f"Wysłano do drukarki Citizen zadanie "
                f"na {quantity} etykiet.\n\n"
                "Sprawdź fizyczny wydruk.",
                parent=self,
            )

        except (ConnectionError, OSError, ValueError) as error:
            self.status_label.configure(
                text=f"Błąd drukowania: {error}",
                text_color="#F08080",
            )

            messagebox.showerror(
                "Błąd drukowania",
                str(error),
                parent=self,
            )

        finally:
            self.print_button.configure(state="normal")
            self._on_quantity_changed()

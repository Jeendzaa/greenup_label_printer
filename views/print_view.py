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

    # =========================================================
    # UI
    # =========================================================

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

        # -----------------------------------------------------
        # Lewy panel: formularz
        # -----------------------------------------------------

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
        self.form_panel.grid_rowconfigure(4, weight=1)

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

        # Stała informacja o rzeczywistych wymiarach etykiety.
        # Jest niezależna od komunikatów drukowania.
        self.dimensions_label = ctk.CTkLabel(
            self.form_panel,
            text="",
            text_color="#AAB7C4",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.dimensions_label.grid(
            row=2,
            column=0,
            sticky="w",
            padx=20,
            pady=(0, 10),
        )

        # Ilość drukowanych kopii
        quantity_frame = ctk.CTkFrame(
            self.form_panel,
            fg_color="transparent",
        )
        quantity_frame.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 12),
        )
        quantity_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            quantity_frame,
            text="Ilość sztuk",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 5),
            padx=(0, 8),
        )

        ctk.CTkLabel(
            quantity_frame,
            text="Orientacja wydruku",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(
            row=0,
            column=1,
            sticky="w",
            pady=(0, 5),
            padx=(8, 0),
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
            padx=(0, 8),
        )
        self.quantity_entry.insert(0, "1")

        self.orientation_var = ctk.StringVar(value="0° — Oryginalna")
        self.orientation_selector = ctk.CTkOptionMenu(
            quantity_frame,
            variable=self.orientation_var,
            values=[
                "0° — Oryginalna",
                "90° — W prawo",
                "180° — Do góry nogami",
                "270° — W lewo",
            ],
            height=36,
            command=self._on_orientation_changed,
        )
        self.orientation_selector.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(8, 0),
        )
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
            row=4,
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
            row=5,
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
            row=6,
            column=0,
            sticky="ew",
            padx=20,
            pady=(5, 20),
        )

        # -----------------------------------------------------
        # Prawy panel: podgląd
        # -----------------------------------------------------

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

        # Ciemne tło pozwala zobaczyć rzeczywistą krawędź
        # białej etykiety, tak samo jak w edytorze graficznym.
        self.preview_container = ctk.CTkFrame(
            self.preview_panel,
            fg_color="#303B46",
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
            text_color="#AAB7C4",
            fg_color="transparent",
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

    # =========================================================
    # TEMPLATE LOADING
    # =========================================================

    def _load_templates(self):
        """Wczytuje szablony przy pierwszym uruchomieniu widoku."""
        self.refresh_templates()

    def refresh_templates(self):
        """
        Ponownie odczytuje szablony z dysku.

        Zachowuje aktualny wybór, jeśli wybrany szablon nadal istnieje.
        Metoda jest wywoływana przy każdym wejściu do zakładki drukowania.
        """
        if self._destroyed:
            return

        previous_name = self.template_selector.get()

        try:
            templates = self.template_service.load_templates()

            self.templates_by_name = {
                template["name"]: template
                for template in templates
                if isinstance(template, dict) and template.get("name")
            }

            names = list(self.templates_by_name.keys())

            if not names:
                self.template_selector.configure(
                    values=["Brak szablonów"],
                    state="disabled",
                )
                self.template_selector.set("Brak szablonów")

                self._clear_form()

                self.dimensions_label.configure(text="")

                self.preview_label.configure(
                    image=None,
                    text="Brak szablonów do wyświetlenia",
                )
                self.preview_image = None

                self.preview_status.configure(
                    text="Dodaj szablon w zakładce Edytor szablonów.",
                    text_color="#AAB7C4",
                )

                self.status_label.configure(
                    text="Nie znaleziono szablonów JSON.",
                    text_color="#AAB7C4",
                )
                return

            self.template_selector.configure(
                values=names,
                state="readonly",
            )

            selected_name = (
                previous_name
                if previous_name in self.templates_by_name
                else names[0]
            )

            self.template_selector.set(selected_name)
            self._on_template_selected(selected_name)

        except (OSError, ValueError, KeyError, TypeError) as error:
            self.status_label.configure(
                text=f"Błąd wczytywania szablonów: {error}",
                text_color="#F08080",
            )

    def _on_template_selected(self, template_name):
        template = self.templates_by_name.get(template_name)

        if template is None:
            return

        self._clear_form()

        fields = self._get_template_fields(template)

        for row, field in enumerate(fields):
            name = field["name"]
            label = field["label"]

            if field.get("required", False):
                label += " *"

            ctk.CTkLabel(
                self.form_frame,
                text=label,
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
                entry.insert(0, str(default))

            entry.bind(
                "<KeyRelease>",
                self._on_field_changed,
            )
            entry.bind(
                "<FocusOut>",
                self._on_field_changed,
            )

            self.field_entries[name] = entry

        self.dimensions_label.configure(
            text=f"Wymiary etykiety: {template['width']} × {template['height']} mm"
        )

        self.status_label.configure(
            text="Pola oznaczone * są wymagane.",
            text_color="#AAB7C4",
        )

        self._schedule_preview()

    def _get_template_fields(self, template):
        """
        Zwraca wszystkie pola formularza dla wybranego szablonu.

        Obsługiwane są dwa formaty:

        1. Nowy:
           elements -> elementy typu data

        2. Starszy:
           fields -> osobna lista pól danych

        Jeżeli oba formaty zawierają pole o tej samej nazwie,
        pierwszeństwo ma nowe pole z elements.
        """

        result = []
        used_names = set()

        # Nowe pola definiowane bezpośrednio w elementach szablonu.
        for element in template.get("elements", []):
            if not isinstance(element, dict):
                continue

            if element.get("type") != "data":
                continue

            name = element.get("name")

            if not name or name in used_names:
                continue

            result.append({
                "name": name,
                "label": element.get("label", name),
                "default": "",
                "required": element.get("required", True),
            })

            used_names.add(name)

        # Obsługa starszych szablonów.
        for field in template.get("fields", []):
            if not isinstance(field, dict):
                continue

            name = field.get("name")

            if not name or name in used_names:
                continue

            result.append({
                "name": name,
                "label": field.get("label", name),
                "default": field.get("default", ""),
                "required": field.get("required", False),
            })

            used_names.add(name)

        return result

    # =========================================================
    # FORM
    # =========================================================

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

    def _on_orientation_changed(self, _value=None):
        """Odświeża podgląd po zmianie orientacji wydruku."""
        self._schedule_preview()

    def _get_current_values(self):
        return {
            name: entry.get()
            for name, entry in self.field_entries.items()
        }

    def _validate_required_fields(self):
        for field in self._get_selected_template_fields():
            if not field.get("required", False):
                continue

            name = field["name"]
            entry = self.field_entries.get(name)

            if entry is None:
                continue

            if not entry.get().strip():
                return field["label"]

        return None

    def _get_selected_template_fields(self):
        template = self.templates_by_name.get(
            self.template_selector.get()
        )

        if template is None:
            return []

        return self._get_template_fields(template)

    # =========================================================
    # PREVIEW
    # =========================================================

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

        if (
            generation is not None
            and generation != self._preview_generation
        ):
            return

        template = self.templates_by_name.get(
            self.template_selector.get()
        )

        if template is None:
            return

        values = self._get_current_values()

        try:
            zpl = self.zpl_service.generate(
                template,
                values,
            )

            image = self.preview_service.generate_preview(
                zpl,
                template["width"],
                template["height"],
            )

            if self._destroyed:
                return

            # Podgląd musi pokazywać tę samą orientację, która zostanie
            # zastosowana podczas wysyłania zadania do drukarki.
            orientation_labels = {
                "0° — Oryginalna": 0,
                "90° — W prawo": 90,
                "180° — Do góry nogami": 180,
                "270° — W lewo": 270,
            }
            rotation = orientation_labels.get(self.orientation_var.get(), 0)

            transpose = {
                90: PILImage.Transpose.ROTATE_270,
                180: PILImage.Transpose.ROTATE_180,
                270: PILImage.Transpose.ROTATE_90,
            }
            if rotation:
                image = image.transpose(transpose[rotation])

            # Po obrocie nadal dopasowujemy cały obraz do obszaru podglądu.
            # Dzięki temu etykieta nie jest przycinana przy zmianie proporcji.
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

            self.preview_label.configure(
                text=(
                    "Nie można wygenerować podglądu.\n"
                    "Sprawdź wprowadzone dane."
                ),
            )

            self.preview_status.configure(
                text=f"Podgląd niedostępny: {error}",
                text_color="#F08080",
            )

    # =========================================================
    # PRINTING
    # =========================================================

    def _rotate_zpl_for_print(self, zpl, template, rotation):
        """Obraca całą etykietę na potrzeby bieżącego zadania drukowania.

        Szablon pozostaje bez zmian. Etykieta jest renderowana w natywnej
        rozdzielczości podglądu (203 DPI), obracana i wysyłana jako grafika ZPL.
        """
        if rotation not in (90, 180, 270):
            raise ValueError("Nieobsługiwany kąt obrotu etykiety.")

        image = self.preview_service.generate_preview(
            zpl,
            float(template["width"]),
            float(template["height"]),
        )

        transpose = {
            90: PILImage.Transpose.ROTATE_270,
            180: PILImage.Transpose.ROTATE_180,
            270: PILImage.Transpose.ROTATE_90,
        }
        image = image.transpose(transpose[rotation])

        bitmap = (
            image.convert("L")
            .point(lambda pixel: 0 if pixel < 128 else 255)
            .convert("1", dither=PILImage.Dither.NONE)
        )

        width, height = bitmap.size
        row_bytes = (width + 7) // 8
        packed = bytearray(bitmap.tobytes())

        # PIL: 0 = czarny, 1 = biały. ZPL ^GFA: 1 = czarny.
        for index in range(len(packed)):
            packed[index] ^= 0xFF

        # Bity dopełniające poza prawą krawędzią muszą pozostać białe.
        remainder = width % 8
        if remainder:
            padding_mask = (0xFF << (8 - remainder)) & 0xFF
            for row in range(height):
                packed[row * row_bytes + row_bytes - 1] &= padding_mask

        total_bytes = row_bytes * height
        graphic_data = packed.hex().upper()

        return "\n".join((
            "^XA",
            "^CI28",
            f"^PW{width}",
            f"^LL{height}",
            "^LH0,0",
            f"^FO0,0^GFA,{total_bytes},{total_bytes},{row_bytes},{graphic_data}^FS",
            "^XZ",
        ))

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

        # Sprawdzamy pola wymagane.
        missing_field = self._validate_required_fields()

        if missing_field:
            messagebox.showwarning(
                "Brak wymaganych danych",
                f"Uzupełnij wymagane pole:\n\n{missing_field}",
                parent=self,
            )
            return

        values = {
            name: entry.get().strip()
            for name, entry in self.field_entries.items()
        }

        try:
            zpl = self.zpl_service.generate(
                template,
                values,
            )

        except (ValueError, TypeError) as error:
            messagebox.showwarning(
                "Nieprawidłowe dane",
                str(error),
                parent=self,
            )
            return

        orientation_labels = {
            "0° — Oryginalna": 0,
            "90° — W prawo": 90,
            "180° — Do góry nogami": 180,
            "270° — W lewo": 270,
        }
        rotation = orientation_labels.get(self.orientation_var.get(), 0)

        try:
            if rotation:
                zpl = self._rotate_zpl_for_print(
                    zpl,
                    template,
                    rotation,
                )
        except (ValueError, TypeError, OSError, RuntimeError) as error:
            messagebox.showerror(
                "Nie można obrócić etykiety",
                str(error),
                parent=self,
            )
            return

        output_width = template.get("width")
        output_height = template.get("height")
        if rotation in (90, 270):
            output_width, output_height = output_height, output_width

        confirmed = messagebox.askyesno(
            "Potwierdź drukowanie",
            (
                f"Szablon: {template.get('name', 'Etykieta')}\n"
                f"Orientacja: {rotation}°\n"
                f"Wymiary wydruku: {output_width} × {output_height} mm\n"
                f"Liczba etykiet: {quantity}\n\n"
                "Czy wysłać etykiety do drukarki?"
            ),
            parent=self,
        )

        if not confirmed:
            self.orientation_var.set("0° — Oryginalna")
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
                (
                    "Wysłano do drukarki Citizen zadanie "
                    f"na {quantity} etykiet.\n\n"
                    "Sprawdź fizyczny wydruk."
                ),
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
            self.print_button.configure(
                state="normal",
            )
            self.orientation_var.set("0° — Oryginalna")
            self._on_quantity_changed()

    # =========================================================
    # CLEANUP
    # =========================================================

    def _on_destroy(self, event=None):
        # Zdarzenie Destroy jest wysyłane również dla dzieci,
        # dlatego reagujemy tylko na zniszczenie tego widoku.
        if event is not None and event.widget is not self:
            return

        self._destroyed = True
        self._cancel_preview_job()
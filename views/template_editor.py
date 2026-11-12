
import copy
import re
import unicodedata
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont

from services.image_service import ImageService
from services.preview_service import PreviewService


class TemplateEditorView(ctk.CTkFrame):
    """Graficzny edytor szablonów etykiet."""

    DPI = 203

    DEFAULTS = {
        "text": {
            "type": "text",
            "x": 3,
            "y": 3,
            "content": "Nowy tekst",
            "font_size": 3,
            "font_width": 3,
            "rotation": "N",
        },
        "barcode": {
            "type": "barcode",
            "x": 3,
            "y": 3,
            "content": "123456789",
            "height": 15,
            "module_width": 2,
            "barcode_type": "code128",
            "show_text": False,
        },
        "qr": {
            "type": "qr",
            "x": 3,
            "y": 3,
            "content": "GREENUP",
            "magnification": 5,
        },
        "rectangle": {
            "type": "rectangle",
            "x": 3,
            "y": 3,
            "width": 20,
            "height": 10,
            "thickness": 0.3,
        },
        "line": {
            "type": "line",
            "x": 3,
            "y": 3,
            "length": 20,
            "thickness": 0.3,
            "orientation": "horizontal",
        },
        "image": {
            "type": "image",
            "x": 3,
            "y": 3,
            "width": 20,
            "height": 20,
            "preserve_aspect_ratio": True,
            "threshold": 128,
            "dithering": False,
            "rotation": 0,
        },
    }

    PROPERTIES = {
        "text": [
            ("content", "Treść", "str"),
            ("x", "X (mm)", "float"),
            ("y", "Y (mm)", "float"),
            ("font_size", "Wysokość tekstu (mm)", "float"),
            ("font_width", "Szerokość tekstu (mm)", "float"),
            ("width", "Szerokość pola (mm)", "float"),
            ("rotation", "Obrót", "rotation"),
        ],
        "data": [
            ("label", "Nazwa pola", "str"),
            ("sample", "Wartość przykładowa", "str"),
            ("x", "X (mm)", "float"),
            ("y", "Y (mm)", "float"),
            ("font_size", "Wysokość tekstu (mm)", "float"),
            ("font_width", "Szerokość tekstu (mm)", "float"),
            ("width", "Szerokość pola (mm)", "float"),
            ("rotation", "Obrót", "rotation"),
        ],
        "barcode": [
            ("content", "Dane kodu", "str"),
            ("x", "X (mm)", "float"),
            ("y", "Y (mm)", "float"),
            ("height", "Wysokość (mm)", "float"),
            ("module_width", "Szerokość modułu (1–10)", "int"),
            ("barcode_type", "Rodzaj kodu", "barcode_type"),
            ("show_text", "Podpis pod kodem", "barcode_hri"),
        ],
        "qr": [
            ("content", "Dane QR", "str"),
            ("x", "X (mm)", "float"),
            ("y", "Y (mm)", "float"),
            ("magnification", "Powiększenie (1–10)", "int"),
        ],
        "rectangle": [
            ("x", "X (mm)", "float"),
            ("y", "Y (mm)", "float"),
            ("width", "Szerokość (mm)", "float"),
            ("height", "Wysokość (mm)", "float"),
            ("thickness", "Grubość (mm)", "float"),
        ],
        "line": [
            ("x", "X (mm)", "float"),
            ("y", "Y (mm)", "float"),
            ("orientation", "Orientacja", "line_orientation"),
            ("length", "Długość (mm)", "float"),
            ("thickness", "Grubość (mm)", "float"),
        ],
        "image": [
            ("x", "X (mm)", "float"),
            ("y", "Y (mm)", "float"),
            ("width", "Szerokość (mm)", "float"),
            ("height", "Wysokość (mm)", "float"),
            ("threshold", "Próg czerni i bieli (0–255)", "int_range"),
            ("rotation", "Obrót obrazu", "image_rotation"),
        ],
    }

    ELEMENT_LABELS = {
        "text": "Tekst",
        "data": "Pole danych",
        "barcode": "Kod kreskowy",
        "qr": "Kod QR",
        "rectangle": "Prostokąt",
        "line": "Linia",
        "image": "Obraz",
    }

    def __init__(self, parent, template_service, zpl_service, printer_service):
        super().__init__(
            parent,
            fg_color="transparent",
        )

        self.template_service = template_service
        self.zpl_service = zpl_service
        self.printer_service = printer_service
        self.preview_service = PreviewService(dpi=self.DPI)
        self.image_service = ImageService()

        self.template = None
        self.selected_index = None
        self.selected_template_file = None
        self.selected_template_name = None
        self.preview_image = None
        self._preview_job = None
        self._elements_scroll_reset_job = None

        self._build_ui()
        self._new_template()
        self._refresh_templates()

    # =========================================================
    # UI
    # =========================================================

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=0, minsize=205)
        self.grid_columnconfigure(1, weight=1, minsize=300)
        self.grid_columnconfigure(2, weight=0, minsize=260)
        self.grid_rowconfigure(0, weight=1)

        # -----------------------------------------------------
        # LEFT PANEL
        # -----------------------------------------------------

        left = ctk.CTkFrame(
            self,
            corner_radius=10,
        )

        left.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 7),
            pady=2,
        )

        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(
            left,
            text="SZABLON",
            font=ctk.CTkFont(
                size=13,
                weight="bold",
            ),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=12,
            pady=(12, 5),
        )

        self.name_entry = ctk.CTkEntry(
            left,
            placeholder_text="Nazwa szablonu",
        )

        self.name_entry.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=10,
            pady=4,
        )

        dims = ctk.CTkFrame(
            left,
            fg_color="transparent",
        )

        dims.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=8,
            pady=4,
        )

        dims.grid_columnconfigure(
            (0, 1),
            weight=1,
        )

        self.width_entry = ctk.CTkEntry(
            dims,
            placeholder_text="Szerokość mm",
        )

        self.width_entry.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=2,
        )

        self.height_entry = ctk.CTkEntry(
            dims,
            placeholder_text="Wysokość mm",
        )

        self.height_entry.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=2,
        )

        for entry in (
            self.width_entry,
            self.height_entry,
        ):
            entry.bind(
                "<FocusOut>",
                self._dimensions_changed,
            )

            entry.bind(
                "<Return>",
                self._dimensions_changed,
            )

        ctk.CTkLabel(
            left,
            text="ZAPISANE SZABLONY",
            font=ctk.CTkFont(
                size=12,
                weight="bold",
            ),
        ).grid(
            row=3,
            column=0,
            sticky="w",
            padx=12,
            pady=(12, 4),
        )

        self.templates_frame = ctk.CTkScrollableFrame(
            left,
            fg_color="transparent",
        )

        self.templates_frame.grid(
            row=4,
            column=0,
            sticky="nsew",
            padx=5,
            pady=3,
        )

        ctk.CTkButton(
            left,
            text="Odśwież listę szablonów",
            height=30,
            fg_color="#303B46",
            hover_color="#3A4A58",
            command=self.refresh_templates,
        ).grid(
            row=5,
            column=0,
            sticky="ew",
            padx=9,
            pady=(3, 5),
        )

        ctk.CTkButton(
            left,
            text="Usuń wybrany szablon",
            height=30,
            fg_color="#873D42",
            hover_color="#A44A50",
            command=self._delete_template,
        ).grid(
            row=6,
            column=0,
            sticky="ew",
            padx=9,
            pady=(3, 5),
        )

        actions = ctk.CTkFrame(
            left,
            fg_color="transparent",
        )

        actions.grid(
            row=7,
            column=0,
            sticky="ew",
            padx=7,
            pady=5,
        )

        actions.grid_columnconfigure(
            (0, 1),
            weight=1,
        )

        ctk.CTkButton(
            actions,
            text="Nowy",
            command=self._new_template,
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=2,
        )

        ctk.CTkButton(
            actions,
            text="Zapisz",
            fg_color="#27845B",
            hover_color="#1F6B49",
            command=self._save,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=2,
        )

        ctk.CTkButton(
            left,
            text="Drukuj aktualny szablon",
            height=38,
            fg_color="#27845B",
            hover_color="#1F6B49",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._print_current_template,
        ).grid(
            row=8,
            column=0,
            sticky="ew",
            padx=9,
            pady=(2, 10),
        )

        # -----------------------------------------------------
        # CENTER PANEL
        # -----------------------------------------------------

        center = ctk.CTkFrame(
            self,
            corner_radius=10,
        )

        center.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=7,
            pady=2,
        )

        center.grid_columnconfigure(0, weight=1)
        center.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            center,
            text="ELEMENTY ETYKIETY",
            font=ctk.CTkFont(
                size=13,
                weight="bold",
            ),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=12,
            pady=(12, 7),
        )

        add = ctk.CTkFrame(
            center,
            fg_color="transparent",
        )

        add.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=7,
            pady=(0, 8),
        )

        buttons = [
            ("+ Tekst", "text"),
            ("+ Pole danych", "data"),
            ("+ Kod", "barcode"),
            ("+ QR", "qr"),
            ("+ Prostokąt", "rectangle"),
            ("+ Linia", "line"),
            ("+ Obraz", "image"),
        ]

        for index, (label, kind) in enumerate(buttons):
            add.grid_columnconfigure(
                index,
                weight=1,
            )

            ctk.CTkButton(
                add,
                text=label,
                height=32,
                font=ctk.CTkFont(size=10),
                command=lambda k=kind: self._add_element(k),
            ).grid(
                row=0,
                column=index,
                sticky="ew",
                padx=2,
            )

        self.preview_box = ctk.CTkFrame(
            center,
            fg_color="#303B46",
            corner_radius=8,
        )

        self.preview_box.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=12,
            pady=5,
        )

        self.preview_box.grid_columnconfigure(
            0,
            weight=1,
        )

        self.preview_box.grid_rowconfigure(
            0,
            weight=1,
        )

        self.preview_label = ctk.CTkLabel(
            self.preview_box,
            text="Podgląd etykiety",
        )

        self.preview_label.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=10,
            pady=10,
        )

        self.status_label = ctk.CTkLabel(
            center,
            text="Pozycje i wymiary podawane są w milimetrach.",
            text_color="#AAB7C4",
            font=ctk.CTkFont(size=11),
        )

        self.status_label.grid(
            row=3,
            column=0,
            sticky="w",
            padx=12,
            pady=8,
        )

        # -----------------------------------------------------
        # RIGHT PANEL
        # -----------------------------------------------------

        right = ctk.CTkFrame(
            self,
            corner_radius=10,
        )

        right.grid(
            row=0,
            column=2,
            sticky="nsew",
            padx=(7, 0),
            pady=2,
        )

        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            right,
            text="WŁAŚCIWOŚCI",
            font=ctk.CTkFont(
                size=13,
                weight="bold",
            ),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=12,
            pady=(12, 5),
        )

        self.selection_label = ctk.CTkLabel(
            right,
            text="Nie wybrano elementu",
            text_color="#AAB7C4",
            anchor="w",
        )

        self.selection_label.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=12,
            pady=4,
        )

        self.properties_frame = ctk.CTkScrollableFrame(
            right,
            fg_color="transparent",
        )

        self.properties_frame.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=5,
            pady=3,
        )

        ctk.CTkLabel(
            right,
            text="LISTA ELEMENTÓW",
            font=ctk.CTkFont(
                size=12,
                weight="bold",
            ),
        ).grid(
            row=3,
            column=0,
            sticky="w",
            padx=12,
            pady=(8, 3),
        )

        self.elements_frame = ctk.CTkScrollableFrame(
            right,
            height=125,
            fg_color="transparent",
        )

        self.elements_frame.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=5,
            pady=3,
        )

        ctk.CTkButton(
            right,
            text="Usuń zaznaczony element",
            fg_color="#873D42",
            hover_color="#A44A50",
            command=self._delete_element,
        ).grid(
            row=5,
            column=0,
            sticky="ew",
            padx=10,
            pady=10,
        )

    # =========================================================
    # TEMPLATE OPERATIONS
    # =========================================================

    def _new_template(self):
        self.selected_template_file = None
        self.selected_template_name = None

        self.template = {
            "version": 2,
            "id": "nowy_szablon",
            "name": "Nowy szablon",
            "description": "",
            "width": 75,
            "height": 49,
            "fields": [],
            "elements": [],
        }

        self.selected_index = None

        self._set_entry(
            self.name_entry,
            "Nowy szablon",
        )

        self._set_entry(
            self.width_entry,
            "75",
        )

        self._set_entry(
            self.height_entry,
            "49",
        )

        self._refresh_elements(reset_scroll=True)
        self._show_properties()
        self._refresh_templates()
        self._schedule_preview()

    def refresh_templates(self):
        """Publiczne odświeżenie listy szablonów, np. po zmianie widoku."""
        self._refresh_templates()

    def _refresh_templates(self):
        for child in self.templates_frame.winfo_children():
            child.destroy()

        try:
            templates = self.template_service.load_templates()

        except Exception as exc:
            self._status(
                f"Błąd wczytywania szablonów: {exc}"
            )
            return

        for item in templates:
            graphic = item.get("version") == 2

            label = item.get(
                "name",
                item.get("id", "Szablon"),
            )

            if not graphic:
                label += " [ZPL]"

            is_selected = (
                self.selected_template_file is not None
                and self.selected_template_file == item.get("_file")
            )

            ctk.CTkButton(
                self.templates_frame,
                text=label,
                anchor="w",
                height=32,
                fg_color="#27845B" if is_selected else "#303B46",
                hover_color="#3A4A58",
                command=lambda t=item: self._load_template(t),
            ).pack(
                fill="x",
                padx=2,
                pady=2,
            )

    def _load_template(self, item):
        if item.get("version") != 2:
            self.selected_template_file = item.get("_file")
            self.selected_template_name = item.get(
                "name",
                item.get("id", "Szablon ZPL"),
            )
            self._refresh_templates()

            messagebox.showinfo(
                "Szablon ZPL",
                "To starszy szablon z gotowym kodem ZPL. "
                "Nadal można go drukować, ale nie jest "
                "jeszcze edytowalny graficznie.",
                parent=self,
            )
            return

        self.template = copy.deepcopy(item)
        self.selected_template_file = item.get("_file")
        self.selected_template_name = item.get(
            "name",
            item.get("id", "Szablon"),
        )
        self.template.pop("_file", None)

        self.selected_index = None

        self._set_entry(
            self.name_entry,
            self.template["name"],
        )

        self._set_entry(
            self.width_entry,
            str(self.template["width"]),
        )

        self._set_entry(
            self.height_entry,
            str(self.template["height"]),
        )

        self._refresh_elements(reset_scroll=True)
        self._show_properties()
        self._refresh_templates()
        self._schedule_preview()

        self._status(
            f"Wczytano: {self.template['name']}"
        )

    # =========================================================
    # PRINT FROM EDITOR
    # =========================================================

    def _rotate_zpl_for_print(self, zpl, template, rotation):
        """Renderuje całą etykietę do bitmapy i obraca ją przed wydrukiem.

        Obrót dotyczy wyłącznie bieżącego zadania drukowania. Nie zmienia
        szablonu ani jego elementów zapisanych w edytorze.
        """
        if rotation not in (90, 180, 270):
            raise ValueError("Nieobsługiwany kąt obrotu etykiety.")

        image = self.preview_service.generate_preview(
            zpl,
            float(template["width"]),
            float(template["height"]),
        )

        transpose = {
            90: Image.Transpose.ROTATE_270,   # zgodnie z ruchem wskazówek zegara
            180: Image.Transpose.ROTATE_180,
            270: Image.Transpose.ROTATE_90,   # przeciwnie do ruchu wskazówek zegara
        }
        image = image.transpose(transpose[rotation])

        # Konwersja do monochromatycznej bitmapy 1-bitowej w natywnej
        # rozdzielczości podglądu (203 DPI), bez skalowania etykiety.
        bitmap = (
            image.convert("L")
            .point(lambda pixel: 0 if pixel < 128 else 255)
            .convert("1", dither=Image.Dither.NONE)
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

    def _print_current_template(self):
        """Otwiera formularz danych i ilości dla aktualnego stanu edytora."""

        try:
            self._apply_dimensions()

            if not isinstance(self.template, dict):
                raise ValueError("Brak szablonu do wydrukowania.")

            # Drukujemy kopię aktualnego stanu. Nie zapisujemy ani nie
            # modyfikujemy pliku szablonu na dysku.
            template = copy.deepcopy(self.template)
            template["name"] = (
                self.name_entry.get().strip()
                or template.get("name", "Bieżący szablon")
            )

            self._open_print_dialog(template)

        except Exception as exc:
            messagebox.showerror(
                "Nie można przygotować wydruku",
                str(exc),
                parent=self,
            )

    def _open_print_dialog(self, template):
        """Zbiera wartości pól danych oraz liczbę kopii."""

        dialog = ctk.CTkToplevel(self)
        dialog.title("Drukowanie szablonu")
        dialog.geometry("470x620")
        dialog.minsize(400, 430)
        dialog.transient(self.winfo_toplevel()
                         if self.winfo_toplevel() is not self
                         else self)
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            dialog,
            text="DANE DO WYDRUKU",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=20,
            pady=(18, 5),
        )

        fields_frame = ctk.CTkScrollableFrame(
            dialog,
            fg_color="transparent",
        )
        fields_frame.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=12,
            pady=5,
        )
        fields_frame.grid_columnconfigure(0, weight=1)

        field_entries = {}
        field_definitions = []

        # Pola z nowego edytora graficznego.
        for element in template.get("elements", []):
            if element.get("type") != "data":
                continue

            name = element.get("name")
            if not name:
                raise ValueError(
                    "Jedno z pól danych nie ma identyfikatora. "
                    "Uzupełnij jego konfigurację przed drukowaniem."
                )

            if name in field_entries:
                continue

            field_definitions.append({
                "name": name,
                "label": element.get("label") or name,
                "required": element.get("required", True),
            })

        # Zachowujemy również obsługę starszej listy pól, jeśli występuje
        # w szablonie graficznym.
        for field in template.get("fields", []):
            if not isinstance(field, dict):
                continue

            name = field.get("name")
            if not name or any(item["name"] == name for item in field_definitions):
                continue

            field_definitions.append({
                "name": name,
                "label": field.get("label") or name,
                "required": field.get("required", False),
            })

        if not field_definitions:
            ctk.CTkLabel(
                fields_frame,
                text="Ten szablon nie zawiera dodatkowych pól danych.",
                text_color="#AAB7C4",
                wraplength=390,
                justify="left",
            ).grid(
                row=0,
                column=0,
                sticky="w",
                padx=5,
                pady=10,
            )

        for row, field in enumerate(field_definitions):
            label_text = field["label"]
            if field["required"]:
                label_text += " *"

            ctk.CTkLabel(
                fields_frame,
                text=label_text,
                anchor="w",
            ).grid(
                row=row * 2,
                column=0,
                sticky="ew",
                padx=5,
                pady=(8, 2),
            )

            entry = ctk.CTkEntry(
                fields_frame,
                placeholder_text="Wprowadź wartość",
            )
            entry.grid(
                row=row * 2 + 1,
                column=0,
                sticky="ew",
                padx=5,
                pady=(0, 3),
            )
            field_entries[field["name"]] = entry

        ctk.CTkLabel(
            dialog,
            text="ORIENTACJA WYDRUKU",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(
            row=2,
            column=0,
            sticky="w",
            padx=20,
            pady=(8, 3),
        )

        orientation_var = ctk.StringVar(value="0° — Oryginalna")
        orientation_menu = ctk.CTkOptionMenu(
            dialog,
            variable=orientation_var,
            values=[
                "0° — Oryginalna",
                "90° — W prawo",
                "180° — Do góry nogami",
                "270° — W lewo",
            ],
            width=230,
        )
        orientation_menu.grid(
            row=3,
            column=0,
            sticky="w",
            padx=20,
            pady=(0, 8),
        )

        ctk.CTkLabel(
            dialog,
            text="LICZBA SZTUK",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(
            row=4,
            column=0,
            sticky="w",
            padx=20,
            pady=(5, 3),
        )

        quantity_entry = ctk.CTkEntry(
            dialog,
            placeholder_text="Liczba etykiet",
            width=130,
        )
        quantity_entry.insert(0, "1")
        quantity_entry.grid(
            row=5,
            column=0,
            sticky="w",
            padx=20,
            pady=(0, 10),
        )

        buttons = ctk.CTkFrame(
            dialog,
            fg_color="transparent",
        )
        buttons.grid(
            row=6,
            column=0,
            sticky="ew",
            padx=15,
            pady=(0, 15),
        )
        buttons.grid_columnconfigure((0, 1), weight=1)

        def continue_to_confirmation():
            raw_quantity = quantity_entry.get().strip()

            try:
                quantity = int(raw_quantity)
                if quantity < 1:
                    raise ValueError
            except ValueError:
                messagebox.showerror(
                    "Nieprawidłowa ilość",
                    "Podaj liczbę całkowitą większą od zera.",
                    parent=dialog,
                )
                quantity_entry.focus_set()
                return

            values = {
                name: entry.get().strip()
                for name, entry in field_entries.items()
            }

            try:
                # Walidacja i generowanie odbywają się przed pytaniem
                # o ostateczne potwierdzenie. Nic nie jest jeszcze wysyłane.
                zpl = self.zpl_service.generate(template, values)

                orientation_labels = {
                    "0° — Oryginalna": 0,
                    "90° — W prawo": 90,
                    "180° — Do góry nogami": 180,
                    "270° — W lewo": 270,
                }
                rotation = orientation_labels[orientation_var.get()]

                if rotation:
                    zpl = self._rotate_zpl_for_print(
                        zpl,
                        template,
                        rotation,
                    )
            except Exception as exc:
                messagebox.showerror(
                    "Nieprawidłowe dane",
                    str(exc),
                    parent=dialog,
                )
                return

            dialog.grab_release()
            dialog.destroy()

            output_width = template.get("width")
            output_height = template.get("height")
            if rotation in (90, 270):
                output_width, output_height = output_height, output_width

            confirmed = messagebox.askyesno(
                "Potwierdź drukowanie",
                (
                    f"Szablon: {template.get('name', 'Bieżący szablon')}\n"
                    f"Orientacja: {rotation}°\n"
                    f"Wymiary wydruku: {output_width} × "
                    f"{output_height} mm\n"
                    f"Liczba etykiet: {quantity}\n\n"
                    "Czy wysłać etykiety do drukarki?"
                ),
                parent=self.winfo_toplevel(),
            )

            if not confirmed:
                self._status("Drukowanie anulowane.")
                return

            try:
                self.printer_service.send_zpl(
                    zpl,
                    copies=quantity,
                )
            except Exception as exc:
                messagebox.showerror(
                    "Błąd drukowania",
                    str(exc),
                    parent=self,
                )
                self._status("Nie udało się wysłać wydruku.")
                return

            self._status(
                f"Wysłano do drukarki: {quantity} "
                f"szt. | {template.get('name', 'Szablon')}"
            )
            messagebox.showinfo(
                "Wysłano do drukarki",
                f"Wysłano {quantity} "
                f"{'etykietę' if quantity == 1 else 'etykiety' if 2 <= quantity <= 4 else 'etykiet'} "
                "do drukarki.",
                parent=self.winfo_toplevel(),
            )

        ctk.CTkButton(
            buttons,
            text="Anuluj",
            fg_color="#4A5662",
            hover_color="#5B6875",
            command=dialog.destroy,
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=4,
        )

        ctk.CTkButton(
            buttons,
            text="Dalej",
            fg_color="#27845B",
            hover_color="#1F6B49",
            command=continue_to_confirmation,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=4,
        )

        quantity_entry.focus_set()
        dialog.bind("<Return>", lambda _event: continue_to_confirmation())
        dialog.bind("<Escape>", lambda _event: dialog.destroy())

    # =========================================================
    # SAVE
    # =========================================================

    def _save(self):
        try:
            self._apply_dimensions()

            name = self.name_entry.get().strip()

            if not name:
                raise ValueError(
                    "Podaj nazwę szablonu."
                )

            self.template["name"] = name

            if self.template["id"] == "nowy_szablon":
                self.template["id"] = self._make_slug(name)

            try:
                path = self.template_service.save_template(
                    self.template,
                    overwrite=False,
                )

            except FileExistsError:
                overwrite = messagebox.askyesno(
                    "Szablon już istnieje",
                    "Szablon o tej nazwie lub identyfikatorze "
                    "już istnieje.\n\n"
                    "Czy chcesz go nadpisać?",
                    parent=self,
                )

                if not overwrite:
                    self._status(
                        "Zapis anulowany."
                    )
                    return

                path = self.template_service.save_template(
                    self.template,
                    overwrite=True,
                )

            self.selected_template_file = path.name
            self.selected_template_name = name
            self._refresh_templates()

            self._status(
                f"Zapisano: {path}"
            )

            messagebox.showinfo(
                "Zapisano",
                f"Szablon zapisany:\n{path}",
                parent=self,
            )

        except Exception as exc:
            messagebox.showerror(
                "Błąd zapisu",
                str(exc),
                parent=self,
            )

    def _delete_template(self):
        """Usuwa wybrany zapisany szablon po potwierdzeniu użytkownika."""

        if not self.selected_template_file:
            messagebox.showinfo(
                "Nie wybrano szablonu",
                "Najpierw wybierz zapisany szablon z listy.",
                parent=self,
            )
            return

        template_name = (
            self.selected_template_name
            or self.selected_template_file
        )

        confirmed = messagebox.askyesno(
            "Usuń szablon",
            (
                f"Czy na pewno chcesz usunąć szablon "
                f"'{template_name}'?\n\n"
                "Operacji nie można cofnąć. "
                "Niezapisane zmiany w edytorze również zostaną utracone."
            ),
            icon="warning",
            parent=self,
        )

        if not confirmed:
            return

        try:
            deleted_path = self.template_service.delete_template(
                self.selected_template_file
            )
        except Exception as exc:
            messagebox.showerror(
                "Błąd usuwania szablonu",
                str(exc),
                parent=self,
            )
            return

        self._status(f"Usunięto szablon: {template_name}")
        self._new_template()

    @staticmethod
    def _make_slug(value):
        """
        Generuje techniczną nazwę na podstawie tekstu.

        Przykłady:
        Numer partii -> numer_partii
        Odmiana rośliny -> odmiana_rosliny
        Data pakowania -> data_pakowania
        """

        normalized = unicodedata.normalize(
            "NFKD",
            value,
        )

        normalized = "".join(
            char
            for char in normalized
            if not unicodedata.combining(char)
        )

        slug = normalized.lower()
        slug = re.sub(r"[^a-z0-9_]+", "_", slug)
        slug = re.sub(r"_+", "_", slug)
        slug = slug.strip("_")

        if not slug:
            slug = "pole_danych"

        if slug[0].isdigit():
            slug = f"pole_{slug}"

        return slug

    def _unique_field_name(self, label):
        base_name = self._make_slug(label)

        existing_names = {
            element.get("name")
            for element in self.template.get("elements", [])
            if element.get("type") == "data"
        }

        name = base_name
        counter = 2

        while name in existing_names:
            name = f"{base_name}_{counter}"
            counter += 1

        return name

    # =========================================================
    # DIMENSIONS
    # =========================================================

    def _apply_dimensions(self):
        try:
            width = float(
                self.width_entry.get().replace(",", ".")
            )

            height = float(
                self.height_entry.get().replace(",", ".")
            )

        except ValueError:
            raise ValueError(
                "Wymiary etykiety muszą być liczbami."
            )

        if width <= 0 or height <= 0:
            raise ValueError(
                "Wymiary muszą być większe od zera."
            )

        self.template["width"] = width
        self.template["height"] = height

    def _dimensions_changed(self, _event=None):
        try:
            self._apply_dimensions()
            self._schedule_preview()

        except ValueError as exc:
            self._status(str(exc))

    # =========================================================
    # ADD ELEMENTS
    # =========================================================

    def _add_element(self, kind):
        if kind == "data":
            self._add_field()
            return

        if kind == "image":
            self._add_image()
            return

        element = copy.deepcopy(
            self.DEFAULTS[kind]
        )

        self.template["elements"].append(element)

        self.selected_index = (
            len(self.template["elements"]) - 1
        )

        self._refresh_elements()
        self._show_properties()
        self._schedule_preview()

    def _add_image(self):
        """Wybiera obraz i kopiuje go do zasobów szablonów."""

        source_path = filedialog.askopenfilename(
            title="Wybierz obraz etykiety",
            filetypes=[
                ("Pliki graficzne", "*.png *.jpg *.jpeg *.bmp"),
                ("PNG", "*.png"),
                ("JPEG", "*.jpg *.jpeg"),
                ("Bitmapa", "*.bmp"),
            ],
            parent=self,
        )

        if not source_path:
            return

        try:
            relative_path = self.template_service.import_template_image(
                source_path
            )

            element = copy.deepcopy(self.DEFAULTS["image"])
            element["image"] = relative_path
            element["source_name"] = Path(source_path).name

            self.template["elements"].append(element)
            self.selected_index = len(self.template["elements"]) - 1

            self._refresh_elements()
            self._show_properties()
            self._schedule_preview()

            self._status(
                f"Dodano obraz do bieżącego szablonu: {Path(source_path).name}"
            )

        except Exception as exc:
            messagebox.showerror(
                "Nie można dodać obrazu",
                str(exc),
                parent=self,
            )

    def _replace_selected_image(self):
        """Zastępuje plik aktualnie zaznaczonego obrazu."""

        if self.selected_index is None:
            return

        element = self.template["elements"][self.selected_index]
        if element.get("type") != "image":
            return

        source_path = filedialog.askopenfilename(
            title="Wybierz nowy obraz",
            filetypes=[
                ("Pliki graficzne", "*.png *.jpg *.jpeg *.bmp"),
                ("PNG", "*.png"),
                ("JPEG", "*.jpg *.jpeg"),
                ("Bitmapa", "*.bmp"),
            ],
            parent=self,
        )

        if not source_path:
            return

        try:
            element["image"] = self.template_service.import_template_image(
                source_path
            )
            element["source_name"] = Path(source_path).name
            self._show_properties()
            self._schedule_preview()
            self._status(f"Zmieniono obraz: {Path(source_path).name}")
        except Exception as exc:
            messagebox.showerror(
                "Nie można zmienić obrazu",
                str(exc),
                parent=self,
            )

    def _add_field(self):
        """
        Dodaje własne pole danych.

        Użytkownik podaje wyłącznie nazwę widoczną
        oraz wartość przykładową. Nazwa techniczna
        jest generowana automatycznie.
        """

        label = simpledialog.askstring(
            "Nowe pole danych",
            "Podaj nazwę pola, np. Numer partii:",
            parent=self,
        )

        if label is None:
            return

        label = label.strip()

        if not label:
            messagebox.showerror(
                "Brak nazwy",
                "Nazwa pola nie może być pusta.",
                parent=self,
            )
            return

        sample = simpledialog.askstring(
            "Wartość przykładowa",
            "Podaj przykładową wartość do podglądu:",
            parent=self,
        )

        if sample is None:
            return

        required = messagebox.askyesno(
            "Pole wymagane",
            "Czy użytkownik będzie musiał uzupełnić "
            "to pole przed drukowaniem?",
            parent=self,
        )

        technical_name = self._unique_field_name(label)

        element = {
            "type": "data",
            "name": technical_name,
            "label": label,
            "sample": sample,
            "required": required,
            "x": 3,
            "y": 3,
            "font_size": 3,
            "font_width": 3,
            "rotation": "N",
        }

        self.template["elements"].append(element)

        self.selected_index = (
            len(self.template["elements"]) - 1
        )

        self._refresh_elements()
        self._show_properties()
        self._schedule_preview()

        self._status(
            f"Dodano pole '{label}' ({technical_name})."
        )

    # =========================================================
    # ELEMENT LIST
    # =========================================================

    def _refresh_elements(self, reset_scroll=False):
        for child in self.elements_frame.winfo_children():
            child.destroy()

        for index, element in enumerate(
            self.template["elements"]
        ):
            kind = element.get("type", "element")
            label = self.ELEMENT_LABELS.get(
                kind,
                kind,
            )

            if kind == "data":
                label = element.get(
                    "label",
                    "Pole danych",
                )

            text = f"{index + 1}. {label}"

            if kind == "data":
                text += f"  ({element.get('name', '')})"

            ctk.CTkButton(
                self.elements_frame,
                text=text,
                anchor="w",
                height=29,
                fg_color=(
                    "#27845B"
                    if index == self.selected_index
                    else "#303B46"
                ),
                hover_color="#3A4A58",
                command=lambda i=index: self._select_element(i),
            ).pack(
                fill="x",
                padx=2,
                pady=2,
            )

        if reset_scroll:
            self._schedule_elements_scroll_reset()

    def _schedule_elements_scroll_reset(self):
        """Planuje reset przewijania po przebudowaniu i przeliczeniu listy."""
        if self._elements_scroll_reset_job is not None:
            try:
                self.after_cancel(self._elements_scroll_reset_job)
            except Exception:
                pass

        # CTkScrollableFrame aktualizuje rozmiar zawartości asynchronicznie.
        # Krótkie opóźnienie pozwala Tk przeliczyć geometrię i scrollregion.
        self._elements_scroll_reset_job = self.after(
            50,
            self._reset_elements_scroll,
        )

    def _reset_elements_scroll(self):
        """Przewija listę elementów na samą górę po aktualizacji zawartości."""
        self._elements_scroll_reset_job = None

        if not self.elements_frame.winfo_exists():
            return

        canvas = self.elements_frame._parent_canvas

        # Najpierw przelicz geometrię, następnie odśwież obszar przewijania.
        self.update_idletasks()
        canvas.update_idletasks()

        try:
            canvas.configure(scrollregion=canvas.bbox("all"))
        except Exception:
            pass

        canvas.yview_moveto(0.0)
        canvas.update_idletasks()
        canvas.yview_moveto(0.0)

    def _select_element(self, index):
        self.selected_index = index

        self._refresh_elements()
        self._show_properties()

    def _delete_element(self):
        if self.selected_index is None:
            return

        del self.template["elements"][
            self.selected_index
        ]

        self.selected_index = None

        self._refresh_elements()
        self._show_properties()
        self._schedule_preview()

    # =========================================================
    # PROPERTIES
    # =========================================================

    def _show_properties(self):
        for child in self.properties_frame.winfo_children():
            child.destroy()

        if self.selected_index is None:
            self.selection_label.configure(
                text="Nie wybrano elementu"
            )

            ctk.CTkLabel(
                self.properties_frame,
                text="Dodaj element lub wybierz go z listy.",
                text_color="#AAB7C4",
                wraplength=215,
                justify="left",
            ).pack(
                anchor="w",
                padx=8,
                pady=8,
            )

            return

        element = self.template["elements"][
            self.selected_index
        ]

        kind = element["type"]

        if kind == "image":
            self.selection_label.configure(
                text="Element: obraz"
            )

            ctk.CTkLabel(
                self.properties_frame,
                text=element.get("source_name", "Obraz szablonu"),
                text_color="#AAB7C4",
                wraplength=215,
                justify="left",
            ).pack(
                anchor="w",
                padx=7,
                pady=(5, 8),
            )

            ctk.CTkLabel(
                self.properties_frame,
                text="Plik jest kopiowany do katalogu zasobów szablonów.",
                text_color="#AAB7C4",
                wraplength=215,
                justify="left",
                font=ctk.CTkFont(size=10),
            ).pack(
                anchor="w",
                padx=7,
                pady=(0, 8),
            )

            ctk.CTkButton(
                self.properties_frame,
                text="Zmień obraz",
                command=self._replace_selected_image,
            ).pack(
                fill="x",
                padx=7,
                pady=(0, 8),
            )

        if kind == "data":
            self.selection_label.configure(
                text="Element: własne pole danych"
            )
        else:
            self.selection_label.configure(
                text=f"Element: {kind}"
            )

        # Technical name is generated automatically.
        if kind == "data":
            ctk.CTkLabel(
                self.properties_frame,
                text=f"ID: {element.get('name', '')}",
                text_color="#AAB7C4",
                wraplength=215,
                justify="left",
                font=ctk.CTkFont(size=10),
            ).pack(
                anchor="w",
                padx=7,
                pady=(5, 8),
            )

        for key, label, value_type in self.PROPERTIES[kind]:
            if key == "width" and key not in element:
                continue

            ctk.CTkLabel(
                self.properties_frame,
                text=label,
                anchor="w",
                font=ctk.CTkFont(size=11),
                wraplength=215,
            ).pack(
                fill="x",
                padx=7,
                pady=(7, 2),
            )

            if value_type == "line_orientation":
                orientation_labels = {
                    "horizontal": "Pozioma",
                    "vertical": "Pionowa",
                }
                current_orientation = element.get(
                    key,
                    "horizontal",
                )
                widget = ctk.CTkOptionMenu(
                    self.properties_frame,
                    values=["Pozioma", "Pionowa"],
                    command=lambda value, k=key: self._set_property(
                        k,
                        "vertical" if value == "Pionowa" else "horizontal",
                    ),
                )
                widget.set(
                    orientation_labels.get(
                        current_orientation,
                        "Pozioma",
                    )
                )

            elif value_type == "barcode_type":
                barcode_types = {
                    "code128": "Code 128",
                    "code39": "Code 39",
                    "ean13": "EAN-13",
                    "ean8": "EAN-8",
                    "upca": "UPC-A",
                    "i2of5": "Interleaved 2 of 5",
                }
                current_type = element.get(key, "code128")
                widget = ctk.CTkOptionMenu(
                    self.properties_frame,
                    values=list(barcode_types.values()),
                    command=lambda value, k=key, options=barcode_types:
                    self._set_property(
                        k,
                        next(code for code, label in options.items() if label == value),
                    ),
                )
                widget.set(barcode_types.get(current_type, "Code 128"))

            elif value_type == "barcode_hri":
                widget = ctk.CTkOptionMenu(
                    self.properties_frame,
                    values=["Nie", "Tak"],
                    command=lambda value, k=key: self._set_property(
                        k,
                        value == "Tak",
                    ),
                )
                widget.set("Tak" if element.get(key, False) else "Nie")

            elif value_type == "image_rotation":
                widget = ctk.CTkOptionMenu(
                    self.properties_frame,
                    values=["0°", "90°", "180°", "270°"],
                    command=lambda value, k=key: self._set_property(
                        k, int(value.replace("°", ""))
                    ),
                )
                widget.set(f"{int(element.get(key, 0))}°")

            elif value_type == "rotation":
                widget = ctk.CTkOptionMenu(
                    self.properties_frame,
                    values=["N", "R", "I", "B"],
                    command=lambda value, k=key: self._set_property(
                        k,
                        value,
                    ),
                )

                widget.set(
                    str(element.get(key, "N"))
                )

            else:
                widget = ctk.CTkEntry(
                    self.properties_frame
                )

                widget.insert(
                    0,
                    str(element.get(key, "")),
                )

                # Aktualizuj model i podgląd również podczas pisania.
                # Błędy niekompletnych wartości nie powinny wyświetlać
                # okna dialogowego przy każdym wpisanym znaku.
                widget.bind(
                    "<KeyRelease>",
                    lambda _event, k=key, w=widget, t=value_type:
                    self._entry_property_changed(k, w, t, show_error=False),
                )

                widget.bind(
                    "<FocusOut>",
                    lambda _event, k=key, w=widget, t=value_type:
                    self._entry_property_changed(k, w, t, show_error=True),
                )

                widget.bind(
                    "<Return>",
                    lambda _event, k=key, w=widget, t=value_type:
                    self._entry_property_changed(k, w, t, show_error=True),
                )

            widget.pack(
                fill="x",
                padx=7,
                pady=(0, 2),
            )

        if kind == "image":
            aspect_var = tk.BooleanVar(
                value=element.get("preserve_aspect_ratio", True)
            )

            ctk.CTkCheckBox(
                self.properties_frame,
                text="Zachowaj proporcje",
                variable=aspect_var,
                command=lambda v=aspect_var: self._set_property(
                    "preserve_aspect_ratio",
                    bool(v.get()),
                ),
            ).pack(
                anchor="w",
                padx=7,
                pady=(10, 5),
            )

            dithering_var = tk.BooleanVar(
                value=element.get("dithering", False)
            )

            ctk.CTkCheckBox(
                self.properties_frame,
                text="Dithering",
                variable=dithering_var,
                command=lambda v=dithering_var: self._set_property(
                    "dithering",
                    bool(v.get()),
                ),
            ).pack(
                anchor="w",
                padx=7,
                pady=5,
            )

            ctk.CTkLabel(
                self.properties_frame,
                text="Konwersja i podgląd obrazu zostaną aktywowane w kolejnym etapie.",
                text_color="#AAB7C4",
                wraplength=215,
                justify="left",
                font=ctk.CTkFont(size=10),
            ).pack(
                anchor="w",
                padx=7,
                pady=8,
            )

        if kind == "data":
            required_var = tk.BooleanVar(
                value=element.get("required", True)
            )

            checkbox = ctk.CTkCheckBox(
                self.properties_frame,
                text="Pole wymagane",
                variable=required_var,
                command=lambda v=required_var: self._set_property(
                    "required",
                    bool(v.get()),
                ),
            )

            checkbox.pack(
                anchor="w",
                padx=7,
                pady=(12, 8),
            )

            ctk.CTkLabel(
                self.properties_frame,
                text=(
                    "Wartość przykładowa jest używana "
                    "wyłącznie w podglądzie etykiety."
                ),
                text_color="#AAB7C4",
                wraplength=215,
                justify="left",
                font=ctk.CTkFont(size=10),
            ).pack(
                anchor="w",
                padx=7,
                pady=8,
            )

        else:
            ctk.CTkLabel(
                self.properties_frame,
                text="Placeholder pola danych: {{nazwa_pola}}",
                text_color="#AAB7C4",
                wraplength=215,
                font=ctk.CTkFont(size=10),
            ).pack(
                anchor="w",
                padx=7,
                pady=10,
            )

    def _entry_property_changed(
        self,
        key,
        widget,
        value_type,
        show_error=False,
    ):
        if self.selected_index is None:
            return

        raw = widget.get().strip()

        try:
            if value_type == "float":
                value = float(
                    raw.replace(",", ".")
                )

                if value < 0:
                    raise ValueError(
                        "Wartość nie może być ujemna."
                    )

            elif value_type == "int":
                value = int(raw)

                if value <= 0:
                    raise ValueError(
                        "Wartość musi być większa od zera."
                    )

            elif value_type == "int_range":
                value = int(raw)

                if not 0 <= value <= 255:
                    raise ValueError(
                        "Wartość musi mieścić się w zakresie 0–255."
                    )

            else:
                value = raw

            self.template["elements"][
                self.selected_index
            ][key] = value

            self._refresh_elements()
            self._schedule_preview()

        except ValueError as exc:
            if show_error:
                messagebox.showerror(
                    "Nieprawidłowa wartość",
                    str(exc),
                    parent=self,
                )
            else:
                self._status(
                    "Nieprawidłowa wartość właściwości — popraw ją, aby odświeżyć podgląd."
                )

    def _set_property(self, key, value):
        if self.selected_index is None:
            return

        self.template["elements"][
            self.selected_index
        ][key] = value

        self._refresh_elements()
        self._schedule_preview()

    # =========================================================
    # PREVIEW
    # =========================================================

    def _schedule_preview(self):
        if self._preview_job:
            self.after_cancel(
                self._preview_job
            )

        self._preview_job = self.after(
            300,
            self._update_preview,
        )

    def _update_preview(self):
        self._preview_job = None

        try:
            self._apply_dimensions()

            values = {
                element["name"]: element.get("sample", "")
                for element in self.template.get("elements", [])
                if element.get("type") == "data"
            }

            # Starszy format szablonów może przechowywać pola osobno.
            for field in self.template.get("fields", []):
                if not isinstance(field, dict):
                    continue
                name = field.get("name")
                if name and name not in values:
                    values[name] = field.get("default", "")

            # Podgląd korzysta z kopii szablonu. Nie zmieniamy właściwego
            # szablonu ani zasad walidacji używanych podczas zapisu i druku.
            preview_template = copy.deepcopy(self.template)

            # Wartości przykładowe mogą być puste, a pola wymagane zostaną
            # uzupełnione dopiero w formularzu drukowania. Nie blokuje to
            # samego podglądu etykiety.
            for field in preview_template.get("fields", []):
                if isinstance(field, dict):
                    field["required"] = False

            preview_elements = []
            code39_elements = []
            preview_warnings = []
            for element in preview_template.get("elements", []):
                kind = element.get("type")

                # Obrazy nakładamy na gotowy podgląd jako osobną warstwę.
                if kind == "image":
                    continue

                if kind == "data":
                    element["required"] = False

                # Renderer ZPL wymaga, aby oba wymiary czcionki skalowalnej
                # miały co najmniej 10 dots. Przy 203 DPI jest to nieco
                # ponad 1,25 mm. Korekta dotyczy wyłącznie kopii podglądu:
                # wartości w edytowanym szablonie i wydruku pozostają bez zmian.
                if kind in ("text", "data"):
                    minimum_font_mm = (10 * 25.4 / self.DPI) + 0.01
                    for dimension in ("font_size", "font_width"):
                        if dimension in element:
                            element[dimension] = max(
                                float(element[dimension]),
                                minimum_font_mm,
                            )

                # Pusty kod kreskowy lub QR (np. {{numer_partii}} bez
                # utworzonego jeszcze pola danych) jest pomijany w podglądzie.
                # Właściwy szablon pozostaje bez zmian.
                if kind in ("barcode", "qr"):
                    content = self.zpl_service._resolve_content(
                        element.get("content", ""),
                        values,
                    )
                    if not str(content).strip():
                        continue

                # EAN-13 przyjmuje wyłącznie cyfry. Nieprawidłowa wartość
                # (np. numer partii PL-00/00/W/000003) nie może przerwać
                # renderowania całej etykiety. Pomijamy tylko ten kod w
                # podglądzie i informujemy o przyczynie w pasku statusu.
                if (
                    kind == "barcode"
                    and element.get("barcode_type", "code128") == "ean13"
                ):
                    ean_content = str(
                        self.zpl_service._resolve_content(
                            element.get("content", ""), values
                        ) or ""
                    ).strip()
                    if re.fullmatch(r"[0-9]{12,13}", ean_content) is None:
                        preview_warnings.append(
                            "EAN-13 pominięty: wymagane 12 lub 13 cyfr"
                        )
                        continue

                # zplkit nie obsługuje poprawnie komendy ^B3. Code 39
                # rysujemy osobno w PIL, z zachowaniem pozycji, wysokości,
                # szerokości modułu i opcji podpisu. Do renderera ZPL trafiają
                # pozostałe elementy etykiety.
                if (
                    kind == "barcode"
                    and element.get("barcode_type", "code128") == "code39"
                ):
                    code39_elements.append((
                        copy.deepcopy(element),
                        self.zpl_service._resolve_content(
                            element.get("content", ""), values
                        ),
                    ))
                    continue

                preview_elements.append(element)

            preview_template["elements"] = preview_elements

            zpl = self.zpl_service.generate(preview_template, values)
            image = self.preview_service.generate_preview(
                zpl,
                self.template["width"],
                self.template["height"],
            )

            self._overlay_code39_barcodes(image, code39_elements)
            self._overlay_images_on_preview(image)

            image.thumbnail((650, 450), Image.Resampling.LANCZOS)
            self.preview_image = ctk.CTkImage(
                light_image=image,
                dark_image=image,
                size=image.size,
            )
            self.preview_label.configure(image=self.preview_image, text="")

            image_count = sum(
                1 for element in self.template.get("elements", [])
                if element.get("type") == "image"
            )
            status = (
                f"Podgląd | {self.template['width']} × "
                f"{self.template['height']} mm | 203 DPI"
            )
            if image_count:
                status += f" | obrazy: {image_count}"
            if preview_warnings:
                status += " | " + "; ".join(dict.fromkeys(preview_warnings))
            self._status(status)

        except Exception as exc:
            self.preview_image = None
            self.preview_label.configure(
                image=None,
                text=f"Nie można wygenerować podglądu:\n{exc}",
            )
            self._status(
                "Podgląd niedostępny — sprawdź właściwości elementów."
            )

    def _overlay_images_on_preview(self, preview):
        """Nakłada czarne piksele obrazów na bazowy podgląd etykiety."""

        templates_dir = Path(self.template_service.templates_dir).resolve()
        for element in self.template.get("elements", []):
            if element.get("type") != "image":
                continue

            relative_path = element.get("image")
            if not relative_path:
                raise ValueError("Element obrazu nie ma wskazanego pliku.")

            asset_path = (templates_dir / relative_path).resolve()
            try:
                asset_path.relative_to(templates_dir)
            except ValueError as error:
                raise ValueError(
                    "Ścieżka obrazu wychodzi poza katalog zasobów szablonów."
                ) from error

            width_dots = self._mm_to_dots(element.get("width", 20))
            height_dots = self._mm_to_dots(element.get("height", 20))
            x_dots = self._mm_to_dots(element.get("x", 0))
            y_dots = self._mm_to_dots(element.get("y", 0))

            prepared = self.image_service.load_and_prepare(
                asset_path,
                width_dots,
                height_dots,
                preserve_aspect_ratio=element.get(
                    "preserve_aspect_ratio", True
                ),
                threshold=element.get("threshold", 128),
                dithering=element.get("dithering", False),
                rotation=element.get("rotation", 0),
            )

            # Białe piksele bitmapy oznaczają brak nadruku. Dzięki temu
            # obraz nie zasłania elementów znajdujących się pod nim.
            black_mask = prepared.point(
                lambda pixel: 255 if pixel == 0 else 0,
                mode="L",
            )
            preview.paste((0, 0, 0), (x_dots, y_dots), black_mask)

    # Wzorce Code 39: dziewięć naprzemiennych elementów (bar/space),
    # gdzie "w" oznacza element szeroki, a "n" wąski.
    _CODE39_PATTERNS = {
        "0": "nnnwwnwnn", "1": "wnnwnnnnw", "2": "nnwwnnnnw",
        "3": "wnwwnnnnn", "4": "nnnwwnnnw", "5": "wnnwwnnnn",
        "6": "nnwwwnnnn", "7": "nnnwnnwnw", "8": "wnnwnnwnn",
        "9": "nnwwnnwnn", "A": "wnnnnwnnw", "B": "nnwnnwnnw",
        "C": "wnwnnwnnn", "D": "nnnnwwnnw", "E": "wnnnwwnnn",
        "F": "nnwnwwnnn", "G": "nnnnnwwnw", "H": "wnnnnwwnn",
        "I": "nnwnnwwnn", "J": "nnnnwwwnn", "K": "wnnnnnnww",
        "L": "nnwnnnnww", "M": "wnwnnnnwn", "N": "nnnnwnnww",
        "O": "wnnnwnnwn", "P": "nnwnwnnwn", "Q": "nnnnnnwww",
        "R": "wnnnnnwwn", "S": "nnwnnnwwn", "T": "nnnnwnwwn",
        "U": "wwnnnnnnw", "V": "nwwnnnnnw", "W": "wwwnnnnnn",
        "X": "nwnnwnnnw", "Y": "wwnnwnnnn", "Z": "nwwnwnnnn",
        "-": "nwnnnnwnw", ".": "wwnnnnwnn", " ": "nwwnnnwnn",
        "$": "nwnwnwnnn", "/": "nwnwnnnwn", "+": "nwnnnwnwn",
        "%": "nnnwnwnwn", "*": "nwnnwnwnn",
    }

    def _overlay_code39_barcodes(self, preview, elements):
        """Rysuje Code 39 na obrazie podglądu, niezależnie od zplkit."""
        if not elements:
            return

        draw = ImageDraw.Draw(preview)
        font = ImageFont.load_default()

        for element, raw_content in elements:
            content = str(raw_content or "")
            if not content:
                continue

            # Code 39 nie koduje małych liter ani polskich znaków.
            # Nie przerywamy przez to podglądu pozostałych elementów.
            if any(char not in self._CODE39_PATTERNS or char == "*" for char in content):
                continue

            module = int(element.get("module_width", 2))
            if not 1 <= module <= 10:
                continue

            x = self._mm_to_dots(element.get("x", 0))
            y = self._mm_to_dots(element.get("y", 0))
            bar_height = max(1, self._mm_to_dots(element.get("height", 15)))
            wide = module * 3  # domyślny stosunek szerokości Code 39 w ^BY
            sequence = "*" + content + "*"

            # Dziesięć modułów wolnej przestrzeni po obu stronach kodu.
            cursor = x + (10 * module)
            bars_start = cursor
            top = y
            bottom = y + bar_height - 1

            for char_index, char in enumerate(sequence):
                pattern = self._CODE39_PATTERNS[char]
                for index, width_code in enumerate(pattern):
                    element_width = module if width_code == "n" else wide
                    if index % 2 == 0:
                        left = cursor
                        right = cursor + element_width - 1
                        draw.rectangle((left, top, right, bottom), fill="black")
                    cursor += element_width

                # Jedna wąska przerwa między znakami.
                if char_index < len(sequence) - 1:
                    cursor += module

            if element.get("show_text", False):
                text_y = y + bar_height + 2
                text_width = draw.textbbox((0, 0), content, font=font)[2]
                bars_width = cursor - bars_start
                text_x = bars_start + max(0, (bars_width - text_width) // 2)
                draw.text((text_x, text_y), content, fill="black", font=font)

    @staticmethod
    def _mm_to_dots(value):
        return round(float(value) * 203 / 25.4)

    # =========================================================
    # HELPERS
    # =========================================================

    @staticmethod
    def _set_entry(entry, value):
        entry.delete(
            0,
            "end",
        )

        entry.insert(
            0,
            value,
        )

    def _status(self, text):
        self.status_label.configure(
            text=str(text)
        )


import copy
import re
import unicodedata
import tkinter as tk
from tkinter import messagebox, simpledialog

import customtkinter as ctk
from PIL import Image

from services.preview_service import PreviewService
from services.zpl_service import ZPLService


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
            ("length", "Długość (mm)", "float"),
            ("thickness", "Grubość (mm)", "float"),
        ],
    }

    ELEMENT_LABELS = {
        "text": "Tekst",
        "data": "Pole danych",
        "barcode": "Kod kreskowy",
        "qr": "Kod QR",
        "rectangle": "Prostokąt",
        "line": "Linia",
    }

    def __init__(self, parent, template_service):
        super().__init__(
            parent,
            fg_color="transparent",
        )

        self.template_service = template_service
        self.zpl_service = ZPLService()
        self.preview_service = PreviewService(dpi=self.DPI)

        self.template = None
        self.selected_index = None
        self.preview_image = None
        self._preview_job = None

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

        actions = ctk.CTkFrame(
            left,
            fg_color="transparent",
        )

        actions.grid(
            row=5,
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

        self._refresh_elements()
        self._show_properties()
        self._refresh_templates()
        self._schedule_preview()

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
                graphic
                and self.template.get("id") == item.get("id")
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
            messagebox.showinfo(
                "Szablon ZPL",
                "To starszy szablon z gotowym kodem ZPL. "
                "Nadal można go drukować, ale nie jest "
                "jeszcze edytowalny graficznie.",
                parent=self,
            )
            return

        self.template = copy.deepcopy(item)
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

        self._refresh_elements()
        self._show_properties()
        self._refresh_templates()
        self._schedule_preview()

        self._status(
            f"Wczytano: {self.template['name']}"
        )

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

    def _refresh_elements(self):
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

            if value_type == "rotation":
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

                widget.bind(
                    "<FocusOut>",
                    lambda _event, k=key, w=widget, t=value_type:
                    self._entry_property_changed(k, w, t),
                )

                widget.bind(
                    "<Return>",
                    lambda _event, k=key, w=widget, t=value_type:
                    self._entry_property_changed(k, w, t),
                )

            widget.pack(
                fill="x",
                padx=7,
                pady=(0, 2),
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

            else:
                value = raw

            self.template["elements"][
                self.selected_index
            ][key] = value

            self._refresh_elements()
            self._schedule_preview()

        except ValueError as exc:
            messagebox.showerror(
                "Nieprawidłowa wartość",
                str(exc),
                parent=self,
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

            # New custom data elements use their own sample values.
            values = {
                element["name"]: element.get("sample", "")
                for element in self.template.get("elements", [])
                if element.get("type") == "data"
            }

            # Compatibility with older graphic templates
            # that stored fields in the separate "fields" list.
            for field in self.template.get("fields", []):
                if not isinstance(field, dict):
                    continue

                name = field.get("name")

                if name and name not in values:
                    values[name] = field.get("default", "")

            zpl = self.zpl_service.generate(
                self.template,
                values,
            )

            image = self.preview_service.generate_preview(
                zpl,
                self.template["width"],
                self.template["height"],
            )

            image.thumbnail(
                (650, 450),
                Image.Resampling.LANCZOS,
            )

            self.preview_image = ctk.CTkImage(
                light_image=image,
                dark_image=image,
                size=image.size,
            )

            self.preview_label.configure(
                image=self.preview_image,
                text="",
            )

            self._status(
                f"Podgląd | {self.template['width']} × "
                f"{self.template['height']} mm | 203 DPI"
            )

        except Exception as exc:
            self.preview_image = None

            self.preview_label.configure(
                image=None,
                text=f"Nie można wygenerować podglądu:\n{exc}",
            )

            self._status(
                "Podgląd niedostępny — sprawdź właściwości elementów."
            )

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

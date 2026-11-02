
import re


class ZPLService:
    PLACEHOLDER_PATTERN = re.compile(
        r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}"
    )

    DPI = 203

    def generate(self, template, values):
        self._validate_values(template, values)

        # Obsługa dotychczasowych szablonów.
        if "zpl" in template:
            return self._generate_legacy(template, values)

        # Obsługa nowych szablonów graficznych.
        if template.get("version") == 2:
            return self._generate_graphic(template, values)

        raise ValueError(
            "Nieobsługiwany format szablonu."
        )

    # =========================================================
    # LEGACY TEMPLATES
    # =========================================================

    def _generate_legacy(self, template, values):
        zpl = template["zpl"]

        def replace_placeholder(match):
            field_name = match.group(1)

            return self._safe_value(
                values.get(field_name, "")
            )

        return self.PLACEHOLDER_PATTERN.sub(
            replace_placeholder,
            zpl,
        )

    # =========================================================
    # GRAPHIC TEMPLATES
    # =========================================================

    def _generate_graphic(self, template, values):
        width = self._mm_to_dots(
            template["width"]
        )

        height = self._mm_to_dots(
            template["height"]
        )

        commands = [
            "^XA",
            "^CI28",
            f"^PW{width}",
            f"^LL{height}",
            "^LH0,0",
        ]

        for element in template.get("elements", []):
            commands.append(
                self._generate_element(
                    element,
                    values,
                )
            )

        commands.append("^XZ")

        return "\n".join(commands)

    def _generate_element(self, element, values):
        element_type = element["type"]

        x = self._mm_to_dots(
            element["x"]
        )

        y = self._mm_to_dots(
            element["y"]
        )

        if element_type == "text":
            return self._generate_text(
                element,
                values,
                x,
                y,
            )

        if element_type == "data":
            return self._generate_data(
                element,
                values,
                x,
                y,
            )

        if element_type == "barcode":
            return self._generate_barcode(
                element,
                values,
                x,
                y,
            )

        if element_type == "qr":
            return self._generate_qr(
                element,
                values,
                x,
                y,
            )

        if element_type == "rectangle":
            return self._generate_rectangle(
                element,
                x,
                y,
            )

        if element_type == "line":
            return self._generate_line(
                element,
                x,
                y,
            )

        raise ValueError(
            f"Nieobsługiwany element: {element_type}"
        )

    # =========================================================
    # TEXT
    # =========================================================

    def _generate_text(self, element, values, x, y):
        content = self._resolve_content(
            element.get("content", ""),
            values,
        )

        return self._generate_text_command(
            element,
            content,
            x,
            y,
        )

    # =========================================================
    # CUSTOM DATA FIELDS
    # =========================================================

    def _generate_data(self, element, values, x, y):
        """
        Generuje tekst na podstawie własnego pola danych.

        Przykład elementu:
        {
            "type": "data",
            "name": "numer_partii",
            "label": "Numer partii",
            "sample": "00/00/W/000003",
            "x": 3,
            "y": 3,
            "font_size": 3,
            "font_width": 3,
            "rotation": "N"
        }

        Wartość pobierana jest z:
        values["numer_partii"]
        """

        field_name = element.get("name")

        if not field_name:
            raise ValueError(
                "Pole danych nie posiada identyfikatora 'name'."
            )

        content = values.get(
            field_name,
            "",
        )

        if content is None:
            content = ""

        return self._generate_text_command(
            element,
            content,
            x,
            y,
        )

    def _generate_text_command(self, element, content, x, y):
        """
        Wspólna metoda generowania tekstu dla zwykłych
        elementów tekstowych oraz dynamicznych pól danych.
        """

        font_size = self._mm_to_dots(
            element.get("font_size", 3)
        )

        font_width = self._mm_to_dots(
            element.get("font_width", 3)
        )

        rotation = element.get(
            "rotation",
            "N",
        )

        if rotation not in ("N", "R", "I", "B"):
            raise ValueError(
                "Nieprawidłowy obrót tekstu."
            )

        commands = [
            f"^FO{x},{y}",
            f"^A0{rotation},{font_size},{font_width}",
        ]

        text_width = element.get("width")

        if text_width:
            width_dots = self._mm_to_dots(
                text_width
            )

            commands.append(
                f"^FB{width_dots},1,0,L,0"
            )

        commands.append(
            f"^FD{self._safe_value(content)}^FS"
        )

        return "".join(commands)

    # =========================================================
    # BARCODE
    # =========================================================

    def _generate_barcode(self, element, values, x, y):
        content = self._resolve_content(
            element.get("content", ""),
            values,
        )

        barcode_height = self._mm_to_dots(
            element.get("height", 15)
        )

        module_width = element.get(
            "module_width",
            2,
        )

        if (
            isinstance(module_width, bool)
            or not isinstance(module_width, int)
            or not 1 <= module_width <= 10
        ):
            raise ValueError(
                "Szerokość modułu kodu kreskowego "
                "musi być liczbą od 1 do 10."
            )

        return (
            f"^FO{x},{y}"
            f"^BY{module_width}"
            f"^BCN,{barcode_height},N,N,N"
            f"^FD{self._safe_value(content)}^FS"
        )

    # =========================================================
    # QR CODE
    # =========================================================

    def _generate_qr(self, element, values, x, y):
        content = self._resolve_content(
            element.get("content", ""),
            values,
        )

        magnification = element.get(
            "magnification",
            5,
        )

        if (
            isinstance(magnification, bool)
            or not isinstance(magnification, int)
            or not 1 <= magnification <= 10
        ):
            raise ValueError(
                "Powiększenie QR musi wynosić od 1 do 10."
            )

        return (
            f"^FO{x},{y}"
            f"^BQN,2,{magnification}"
            f"^FDLA,{self._safe_value(content)}^FS"
        )

    # =========================================================
    # RECTANGLE
    # =========================================================

    def _generate_rectangle(self, element, x, y):
        width = self._mm_to_dots(
            element.get("width", 10)
        )

        height = self._mm_to_dots(
            element.get("height", 10)
        )

        thickness = self._mm_to_dots(
            element.get("thickness", 0.3)
        )

        return (
            f"^FO{x},{y}"
            f"^GB{width},{height},{max(1, thickness)}^FS"
        )

    # =========================================================
    # LINE
    # =========================================================

    def _generate_line(self, element, x, y):
        length = self._mm_to_dots(
            element.get("length", 10)
        )

        thickness = self._mm_to_dots(
            element.get("thickness", 0.3)
        )

        return (
            f"^FO{x},{y}"
            f"^GB{length},{max(1, thickness)},"
            f"{max(1, thickness)}^FS"
        )

    # =========================================================
    # PLACEHOLDERS
    # =========================================================

    def _resolve_content(self, content, values):
        def replace_placeholder(match):
            field_name = match.group(1)

            return self._safe_value(
                values.get(field_name, "")
            )

        return self.PLACEHOLDER_PATTERN.sub(
            replace_placeholder,
            str(content),
        )

    # =========================================================
    # HELPERS
    # =========================================================

    @staticmethod
    def _safe_value(value):
        """
        Usuwa znaki, które mogłyby zostać potraktowane
        jako komendy ZPL.
        """

        value = str(value)

        value = re.sub(
            r"[\r\n\t]",
            " ",
            value,
        )

        return (
            value
            .replace("^", " ")
            .replace("~", " ")
        )

    @classmethod
    def _mm_to_dots(cls, value):
        return round(
            float(value) * cls.DPI / 25.4
        )

    # =========================================================
    # VALIDATION
    # =========================================================

    @staticmethod
    def _validate_values(template, values):
        if not isinstance(values, dict):
            raise TypeError(
                "Wartości pól muszą być słownikiem."
            )

        missing_fields = []

        # Stare pola z osobnej listy "fields".
        for field in template.get("fields", []):
            name = field["name"]

            if field.get("required", False):
                value = values.get(
                    name,
                    "",
                )

                if value is None or not str(value).strip():
                    missing_fields.append(
                        field["label"]
                    )

        # Nowe pola z listy "elements".
        for element in template.get("elements", []):
            if element.get("type") != "data":
                continue

            if not element.get("required", True):
                continue

            name = element.get("name")

            if not name:
                raise ValueError(
                    "Pole danych nie posiada identyfikatora."
                )

            value = values.get(
                name,
                "",
            )

            if value is None or not str(value).strip():
                missing_fields.append(
                    element.get("label", name)
                )

        if missing_fields:
            raise ValueError(
                "Uzupełnij wymagane pola: "
                + ", ".join(missing_fields)
            )

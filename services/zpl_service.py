
import re
from pathlib import Path

from config import get_templates_dir
from services.image_service import ImageService


class ZPLService:
    PLACEHOLDER_PATTERN = re.compile(
        r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}"
    )

    DPI = 203

    def __init__(self, templates_dir=None, image_service=None):
        self.templates_dir = Path(templates_dir or get_templates_dir()).resolve()
        self.image_service = image_service or ImageService()

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

        if element_type == "image":
            return self._generate_image(
                element,
                x,
                y,
            )

        raise ValueError(
            f"Nieobsługiwany element: {element_type}"
        )

    # =========================================================
    # IMAGE
    # =========================================================

    def _generate_image(self, element, x, y):
        """Generuje obraz monochromatyczny w formacie ZPL ^GFA."""
        relative_path = element.get("image")
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ValueError("Element obrazu nie zawiera ścieżki pliku.")

        image_path = (self.templates_dir / relative_path).resolve()
        try:
            image_path.relative_to(self.templates_dir)
        except ValueError as error:
            raise ValueError("Ścieżka obrazu wychodzi poza katalog szablonów.") from error

        if not image_path.is_file():
            raise FileNotFoundError(f"Nie znaleziono obrazu szablonu: {image_path}")

        width_dots = self._mm_to_dots(element.get("width", 20))
        height_dots = self._mm_to_dots(element.get("height", 20))
        if width_dots < 1 or height_dots < 1:
            raise ValueError("Wymiary obrazu po przeliczeniu na punkty drukarki są zbyt małe.")

        bitmap = self.image_service.load_and_prepare(
            image_path=image_path,
            width_dots=width_dots,
            height_dots=height_dots,
            preserve_aspect_ratio=element.get("preserve_aspect_ratio", True),
            threshold=element.get("threshold", 128),
            dithering=element.get("dithering", False),
            rotation=element.get("rotation", 0),
        )

        # W PIL mode "1": 1 = biały, 0 = czarny.
        # W ZPL: 1 = czarny punkt, 0 = biały.
        row_bytes = (bitmap.width + 7) // 8
        raw = bitmap.tobytes()
        packed = bytearray(raw)

        for index in range(len(packed)):
            packed[index] ^= 0xFF

        # Wyzeruj bity dopełniające poza prawą krawędzią bitmapy.
        remainder = bitmap.width % 8
        if remainder:
            padding_mask = (0xFF << (8 - remainder)) & 0xFF
            for row in range(bitmap.height):
                packed[row * row_bytes + row_bytes - 1] &= padding_mask

        total_bytes = row_bytes * bitmap.height
        hex_data = packed.hex().upper()

        return (
            f"^FO{x},{y}"
            f"^GFA,{total_bytes},{total_bytes},{row_bytes},{hex_data}^FS"
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

        barcode_type = element.get("barcode_type", "code128")
        show_text = element.get("show_text", False)

        if barcode_type not in {
            "code128",
            "code39",
            "ean13",
            "ean8",
            "upca",
            "i2of5",
        }:
            raise ValueError(
                "Nieobsługiwany rodzaj kodu kreskowego."
            )

        if not isinstance(show_text, bool):
            raise ValueError(
                "Opcja podpisu kodu kreskowego musi być wartością logiczną."
            )

        human_readable = "Y" if show_text else "N"

        barcode_commands = {
            "code128": f"^BCN,{barcode_height},{human_readable},N,N",
            "code39": f"^B3N,{barcode_height},{human_readable},N,N",
            "ean13": f"^BEN,{barcode_height},{human_readable}",
            "ean8": f"^B8N,{barcode_height},{human_readable}",
            "upca": f"^BUN,{barcode_height},{human_readable}",
            "i2of5": f"^B2N,{barcode_height},{human_readable},N",
        }

        return (
            f"^FO{x},{y}"
            f"^BY{module_width}"
            f"{barcode_commands[barcode_type]}"
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

        orientation = element.get("orientation", "horizontal")
        if orientation == "horizontal":
            width = length
            height = max(1, thickness)
        elif orientation == "vertical":
            width = max(1, thickness)
            height = length
        else:
            raise ValueError(
                "Nieprawidłowa orientacja linii. "
                "Dozwolone wartości: horizontal, vertical."
            )

        return (
            f"^FO{x},{y}"
            f"^GB{width},{height},{max(1, thickness)}^FS"
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

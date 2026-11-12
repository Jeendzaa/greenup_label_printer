
import json
import math
import re
import shutil
import uuid
from pathlib import Path

from config import (
    get_templates_dir,
    get_bundled_templates_dir,
)


class TemplateService:
    def __init__(self, templates_dir=None):
        self.templates_dir = Path(
            templates_dir or get_templates_dir()
        )

        self.templates_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._migrate_templates()

    def _migrate_templates(self):
        """
        Kopiuje szablony z katalogu aplikacji do katalogu użytkownika.

        Istniejące pliki użytkownika nigdy nie są nadpisywane.
        """

        source_dir = get_bundled_templates_dir()

        if not source_dir.is_dir():
            return

        for source_file in source_dir.glob("*.json"):
            destination = self.templates_dir / source_file.name

            if destination.exists():
                continue

            try:
                shutil.copy2(source_file, destination)
            except OSError as error:
                print(
                    f"Nie udało się skopiować szablonu "
                    f"{source_file.name}: {error}"
                )

    def import_template_image(self, source_path):
        """
        Kopiuje obraz do katalogu zasobów szablonów i zwraca
        ścieżkę względną, którą można zapisać w JSON.

        Zasoby są przechowywane w templates/_assets/, dzięki czemu
        nie zależą od lokalizacji pliku źródłowego.
        """
        source = Path(source_path)

        allowed_extensions = {".png", ".jpg", ".jpeg", ".bmp"}

        if not source.is_file():
            raise FileNotFoundError(
                f"Nie znaleziono pliku obrazu: {source}"
            )

        if source.suffix.lower() not in allowed_extensions:
            raise ValueError(
                "Obsługiwane formaty obrazów: PNG, JPG, JPEG i BMP."
            )

        asset_id = uuid.uuid4().hex
        asset_dir = self.templates_dir / "_assets" / asset_id
        asset_dir.mkdir(parents=True, exist_ok=True)

        filename = f"image{source.suffix.lower()}"
        destination = asset_dir / filename

        try:
            shutil.copy2(source, destination)
        except OSError:
            shutil.rmtree(asset_dir, ignore_errors=True)
            raise

        return (Path("_assets") / asset_id / filename).as_posix()

    def load_templates(self):
        if not self.templates_dir.is_dir():
            self.templates_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

        templates = []

        for file_path in sorted(
            self.templates_dir.glob("*.json")
        ):
            try:
                with file_path.open(
                    "r",
                    encoding="utf-8",
                ) as file:
                    template = json.load(file)

                self._validate_template(template)

                template["_file"] = file_path.name
                templates.append(template)

            except (json.JSONDecodeError, ValueError) as error:
                print(
                    f"Błąd szablonu '{file_path.name}': {error}"
                )

        return templates

    def get_template_by_id(self, template_id):
        for template in self.load_templates():
            if template["id"] == template_id:
                return template

        return None

    def save_template(self, template, overwrite=False):
        """
        Zapisuje szablon JSON.

        Jeżeli istnieje szablon o tej samej nazwie lub ID,
        wymaga jawnego potwierdzenia przez overwrite=True.
        """

        self._validate_template(template)

        existing_by_id = None
        existing_by_name = None

        for existing in self.load_templates():
            if existing.get("id") == template.get("id"):
                existing_by_id = existing

            existing_name = existing.get("name", "").strip().casefold()
            new_name = template["name"].strip().casefold()

            if existing_name == new_name:
                existing_by_name = existing

        existing = existing_by_id or existing_by_name

        if existing is not None:
            if not overwrite:
                raise FileExistsError(
                    f"Szablon '{existing['name']}' już istnieje."
                )

            filename = (
                existing.get("_file")
                or self._make_filename(existing["id"])
            )

            # Zachowujemy identyfikator istniejącego szablonu.
            template["id"] = existing["id"]

        else:
            filename = self._make_filename(template["id"])

        file_path = self.templates_dir / filename

        data = {
            key: value
            for key, value in template.items()
            if key != "_file"
        }

        with file_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=4,
            )

        return file_path

    def delete_template(self, filename):
        """
        Usuwa zapisany szablon JSON z katalogu użytkownika.

        Przyjmuje wyłącznie nazwę pliku, a nie dowolną ścieżkę.
        """
        if not isinstance(filename, str) or not filename.strip():
            raise ValueError("Nieprawidłowa nazwa pliku szablonu.")

        relative_path = Path(filename)

        if (
            relative_path.name != filename
            or relative_path.suffix.lower() != ".json"
            or filename in {".", ".."}
        ):
            raise ValueError("Można usuwać wyłącznie pliki JSON z katalogu szablonów.")

        templates_dir = self.templates_dir.resolve()
        file_path = (templates_dir / relative_path).resolve()

        if file_path.parent != templates_dir:
            raise ValueError("Plik szablonu znajduje się poza katalogiem szablonów.")

        if not file_path.is_file():
            raise FileNotFoundError(
                f"Nie znaleziono szablonu: {filename}"
            )

        file_path.unlink()
        return file_path

    @staticmethod
    def _make_filename(template_id):
        """
        Tworzy bezpieczną nazwę pliku na podstawie ID.
        """

        filename = re.sub(
            r"[^a-zA-Z0-9_-]",
            "_",
            template_id,
        )

        if not filename:
            raise ValueError(
                "Nieprawidłowy identyfikator szablonu."
            )

        return f"{filename}.json"

    @staticmethod
    def _validate_number(value, description, minimum=None):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError(
                f"{description} musi być prawidłową liczbą."
            )

        if minimum is not None and value < minimum:
            raise ValueError(
                f"{description} musi wynosić co najmniej {minimum}."
            )

    @staticmethod
    def _validate_template(template):
        if not isinstance(template, dict):
            raise ValueError(
                "Główna zawartość JSON musi być obiektem."
            )

        required_keys = {
            "id",
            "name",
            "width",
            "height",
        }

        missing_keys = required_keys - template.keys()

        if missing_keys:
            raise ValueError(
                "Brak wymaganych kluczy: "
                + ", ".join(sorted(missing_keys))
            )

        for key in ("id", "name"):
            value = template[key]

            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"Pole '{key}' musi być niepustym tekstem."
                )

        for key in ("width", "height"):
            TemplateService._validate_number(
                template[key],
                f"Pole '{key}'",
                minimum=0.001,
            )

        # Starszy format: gotowy kod ZPL i lista pól.
        if "zpl" in template:
            TemplateService._validate_legacy_template(template)
            return

        # Nowy format: graficzne elementy szablonu.
        if template.get("version") == 2:
            TemplateService._validate_graphic_template(template)
            return

        raise ValueError(
            "Szablon musi zawierać pole 'zpl' "
            "lub mieć version=2."
        )

    @staticmethod
    def _validate_legacy_template(template):
        if not isinstance(template["zpl"], str):
            raise ValueError(
                "Pole 'zpl' musi być tekstem."
            )

        if not template["zpl"].strip():
            raise ValueError(
                "Kod ZPL nie może być pusty."
            )

        if not isinstance(template.get("fields"), list):
            raise ValueError(
                "Pole 'fields' musi być listą."
            )

        field_names = set()

        for field in template["fields"]:
            if not isinstance(field, dict):
                raise ValueError(
                    "Każde pole w 'fields' musi być obiektem."
                )

            name = field.get("name")
            label = field.get("label")

            if not isinstance(name, str) or not re.fullmatch(
                r"[a-zA-Z_][a-zA-Z0-9_]*",
                name,
            ):
                raise ValueError(
                    f"Nieprawidłowa nazwa pola: '{name}'."
                )

            if name in field_names:
                raise ValueError(
                    f"Powtórzona nazwa pola: '{name}'."
                )

            field_names.add(name)

            if not isinstance(label, str) or not label.strip():
                raise ValueError(
                    f"Pole '{name}' musi mieć etykietę."
                )

        placeholders = set(
            re.findall(
                r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}",
                template["zpl"],
            )
        )

        undefined_fields = placeholders - field_names

        if undefined_fields:
            raise ValueError(
                "ZPL odwołuje się do niezdefiniowanych pól: "
                + ", ".join(sorted(undefined_fields))
            )

    @staticmethod
    def _validate_graphic_template(template):
        if not isinstance(template.get("fields", []), list):
            raise ValueError(
                "Pole 'fields' musi być listą."
            )

        elements = template.get("elements")

        if not isinstance(elements, list):
            raise ValueError(
                "Szablon graficzny musi zawierać listę 'elements'."
            )

        supported_types = {
            "text",
            "data",
            "barcode",
            "qr",
            "rectangle",
            "line",
            "image",
        }

        data_names = set()

        for index, element in enumerate(elements):
            element_number = index + 1

            if not isinstance(element, dict):
                raise ValueError(
                    f"Element {element_number} musi być obiektem."
                )

            element_type = element.get("type")

            if element_type not in supported_types:
                raise ValueError(
                    f"Nieobsługiwany typ elementu: {element_type}."
                )

            for coordinate in ("x", "y"):
                TemplateService._validate_number(
                    element.get(coordinate),
                    f"Element {element_number}: współrzędna {coordinate}",
                    minimum=0,
                )

            if element_type == "text":
                TemplateService._validate_text_element(
                    element,
                    element_number,
                )

            elif element_type == "data":
                TemplateService._validate_data_element(
                    element,
                    element_number,
                    data_names,
                )

            elif element_type == "barcode":
                TemplateService._validate_barcode_element(
                    element,
                    element_number,
                )

            elif element_type == "qr":
                TemplateService._validate_qr_element(
                    element,
                    element_number,
                )

            elif element_type == "rectangle":
                TemplateService._validate_rectangle_element(
                    element,
                    element_number,
                )

            elif element_type == "line":
                TemplateService._validate_line_element(
                    element,
                    element_number,
                )

            elif element_type == "image":
                TemplateService._validate_image_element(
                    element,
                    element_number,
                )

    @staticmethod
    def _validate_text_element(element, index):
        content = element.get("content", "")

        if not isinstance(content, str):
            raise ValueError(
                f"Element {index}: treść tekstu musi być tekstem."
            )

        TemplateService._validate_text_properties(
            element,
            index,
        )

    @staticmethod
    def _validate_data_element(element, index, used_names):
        """
        Waliduje dowolne pole danych zdefiniowane przez użytkownika.

        Nie korzysta z żadnego globalnego rejestru pól.
        """

        name = element.get("name")
        label = element.get("label")
        sample = element.get("sample", "")
        required = element.get("required", False)

        if not isinstance(name, str) or not re.fullmatch(
            r"[a-zA-Z_][a-zA-Z0-9_]*",
            name,
        ):
            raise ValueError(
                f"Element {index}: nieprawidłowy identyfikator pola danych."
            )

        if name in used_names:
            raise ValueError(
                f"Element {index}: powtórzona nazwa pola danych '{name}'."
            )

        used_names.add(name)

        if not isinstance(label, str) or not label.strip():
            raise ValueError(
                f"Element {index}: pole danych musi mieć etykietę."
            )

        if not isinstance(sample, str):
            raise ValueError(
                f"Element {index}: wartość przykładowa musi być tekstem."
            )

        if not isinstance(required, bool):
            raise ValueError(
                f"Element {index}: właściwość 'required' musi być wartością logiczną."
            )

        TemplateService._validate_text_properties(
            element,
            index,
        )

    @staticmethod
    def _validate_text_properties(element, index):
        rotation = element.get("rotation", "N")

        if rotation not in ("N", "R", "I", "B"):
            raise ValueError(
                f"Element {index}: nieprawidłowy obrót tekstu."
            )

        for property_name in ("font_size", "font_width"):
            TemplateService._validate_number(
                element.get(property_name, 3),
                f"Element {index}: {property_name}",
                minimum=0.001,
            )

        if "width" in element:
            TemplateService._validate_number(
                element["width"],
                f"Element {index}: szerokość pola",
                minimum=0.001,
            )

    @staticmethod
    def _validate_barcode_element(element, index):
        content = element.get("content", "")

        if not isinstance(content, str):
            raise ValueError(
                f"Element {index}: dane kodu kreskowego muszą być tekstem."
            )

        TemplateService._validate_number(
            element.get("height", 15),
            f"Element {index}: wysokość kodu kreskowego",
            minimum=0.001,
        )

        TemplateService._validate_number(
            element.get("module_width", 2),
            f"Element {index}: szerokość modułu",
            minimum=1,
        )

        barcode_type = element.get("barcode_type", "code128")
        if barcode_type not in {
            "code128",
            "code39",
            "ean13",
            "ean8",
            "upca",
            "i2of5",
        }:
            raise ValueError(
                f"Element {index}: nieobsługiwany rodzaj kodu kreskowego."
            )

        if not isinstance(element.get("show_text", False), bool):
            raise ValueError(
                f"Element {index}: właściwość 'show_text' musi być wartością logiczną."
            )

    @staticmethod
    def _validate_qr_element(element, index):
        content = element.get("content", "")

        if not isinstance(content, str):
            raise ValueError(
                f"Element {index}: dane kodu QR muszą być tekstem."
            )

        TemplateService._validate_number(
            element.get("magnification", 5),
            f"Element {index}: powiększenie kodu QR",
            minimum=1,
        )

    @staticmethod
    def _validate_rectangle_element(element, index):
        for property_name in ("width", "height", "thickness"):
            TemplateService._validate_number(
                element.get(property_name),
                f"Element {index}: {property_name}",
                minimum=0.001,
            )

    @staticmethod
    def _validate_line_element(element, index):
        for property_name in ("length", "thickness"):
            TemplateService._validate_number(
                element.get(property_name),
                f"Element {index}: {property_name}",
                minimum=0.001,
            )

        orientation = element.get("orientation", "horizontal")
        if orientation not in ("horizontal", "vertical"):
            raise ValueError(
                f"Element {index}: orientacja linii musi mieć "
                "wartość 'horizontal' albo 'vertical'."
            )

    @staticmethod
    def _validate_image_element(element, index):
        image_path = element.get("image")

        if not isinstance(image_path, str) or not image_path.strip():
            raise ValueError(
                f"Element {index}: brak ścieżki do obrazu."
            )

        relative_path = Path(image_path)

        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError(
                f"Element {index}: ścieżka obrazu musi być względna "
                "i nie może wychodzić poza katalog szablonów."
            )

        if relative_path.suffix.lower() not in {
            ".png", ".jpg", ".jpeg", ".bmp"
        }:
            raise ValueError(
                f"Element {index}: nieobsługiwany format obrazu."
            )

        for property_name in ("width", "height"):
            TemplateService._validate_number(
                element.get(property_name),
                f"Element {index}: {property_name}",
                minimum=0.001,
            )

        threshold = element.get("threshold", 128)
        TemplateService._validate_number(
            threshold,
            f"Element {index}: threshold",
            minimum=0,
        )

        if threshold > 255 or int(threshold) != threshold:
            raise ValueError(
                f"Element {index}: threshold musi być liczbą całkowitą 0–255."
            )

        for property_name in ("preserve_aspect_ratio", "dithering"):
            if not isinstance(element.get(property_name, False), bool):
                raise ValueError(
                    f"Element {index}: {property_name} musi być wartością logiczną."
                )


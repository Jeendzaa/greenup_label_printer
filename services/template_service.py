import json
import re
from pathlib import Path

"""Loads and verifies label templates saved in JSON"""
class TemplateService:

    def __init__(self, templates_dir=None):
        if templates_dir is None:
            project_dir = Path(__file__).resolve().parent.parent
            templates_dir = project_dir / "templates"
        self.templates_dir = Path(templates_dir)

    def load_templates(self):
        if not self.templates_dir.is_dir():
            raise FileNotFoundError(f"Nie znaleziono folderów szablonów: {self.templates_dir}")
        templates = []
        for file_path in sorted(self.templates_dir.glob("*.json")):
            try:
                with file_path.open("r", encoding="utf-8") as file:
                    template = json.load(file)
                self._validate_template(template)
                template["_file"] = file_path.name
                templates.append(template)
            except (json.JSONDecodeError, ValueError) as error:
                print(f"Błąd szablonu '{file_path.name}': {error}")
            return templates

    def get_template_by_id(self, template_id):
        for template in self.load_templates():
            if template["id"] == template_id:
                return template
        return None

    @staticmethod
    def _validate_template(template):
        if not isinstance(template, dict):
            raise ValueError("Główna zawartość JSON musi być obiektem")
        
        required_keys = {
            "id",
            "name",
            "width",
            "height",
            "fields",
            "zpl",
        }

        missing_keys = required_keys - template.keys()

        if missing_keys:
            raise ValueError(f"Brak wymaganych kluczy:, ".join(sorted(missing_keys)))

        for key in ("id", "name", "zpl"):
            value = template[key]

            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Pole {key} musi być niepustym tekstem")

        for key in ("width", "height"):
            value = template[key]

            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or value <= 0
            ):
                raise ValueError(
                    f"Pole '{key}' musi być liczbą większą od zera."
                )

        if not isinstance(template["fields"], list):
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

            if not isinstance(name, str) or not name.strip():
                raise ValueError(
                    "Każde pole musi mieć niepustą nazwę."
                )

            if not re.fullmatch(
                r"[a-zA-Z_][a-zA-Z0-9_]*", name
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

            if (
                "default" in field
                and not isinstance(field["default"], str)
            ):
                raise ValueError(
                    f"'default' pola '{name}' musi być tekstem."
                )

            if (
                "required" in field
                and not isinstance(field["required"], bool)
            ):
                raise ValueError(
                    f"'required' pola '{name}' musi być wartością bool."
                )

        # Sprawdzenie, czy wszystkie zmienne ZPL mają definicje.
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
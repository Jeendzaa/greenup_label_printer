import re

class ZPLService:
    PLACEHOLDER_PATTERN = re.compile(r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}")

    def generate(self, template, values):
        
        self._validate_values(template, values)
        zpl = template["zpl"]
        
        def replace_placeholder(match):
            field_name = match.group(1)
            value = str(values.get(field_name, ""))
            value = re.sub(r"[\r\n\t]", " ", value)
            value = value.replace("^"," ").replace("~", " ")
            return value

        return self.PLACEHOLDER_PATTERN.sub(replace_placeholder, zpl)

    @staticmethod
    def _validate_values(templates, values):
        
        if not isinstance(values, dict):
            raise TypeError("Wartości pól muszą być słownikiem.")
        
        missing_fields = []

        for field in templates["fields"]:
            name = field["name"]

            if field.get("required", False):
                value = values.get(name, "")

                if value is None or not str(value).strip():
                    missing_fields.append(field["label"])

        if missing_fields:
            raise ValueError(
                "Uzupełnij wymagane pola: "
                + ", ".join(missing_fields)
            )

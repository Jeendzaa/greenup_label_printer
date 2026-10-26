from services.template_service import TemplateService

def main():
    template_service = TemplateService()
    templates = template_service.load_templates()

    print(f"Liczba szablonów: {len(templates)}")
    for template in templates:
        print(f"\nNazwa: {template['name']}")
        print(f"ID: {template['id']}")
        print(f"Plik: {template['_file']}")
        print(
            f"Wymiary: {template['width']} × "
            f"{template['height']} mm"
        )

        print("Pola:")

        for field in template["fields"]:
            print(
                f"  {field['label']} "
                f"(domyślnie: {field.get('default', '')})"
            )


if __name__ == "__main__":
    main()
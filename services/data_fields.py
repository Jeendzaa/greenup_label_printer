
"""
Rejestr dynamicznych pól danych wykorzystywanych w szablonach etykiet.

Każde pole posiada:
- klucz techniczny wykorzystywany w kodzie,
- etykietę wyświetlaną użytkownikowi,
- przykładową wartość wykorzystywaną w podglądzie.
"""

DATA_FIELDS = {
    "batch_number": {
        "label": "Numer partii",
        "sample": "00/00/W/000003",
    },
    "plant_name": {
        "label": "Nazwa rośliny",
        "sample": "Solanum lycopersicum L.",
    },
    "supplier_number": {
        "label": "Numer dostawcy",
        "sample": "PL-00/00/00",
    },
    "country": {
        "label": "Kraj pochodzenia",
        "sample": "Polska",
    },
    "production_date": {
        "label": "Data produkcji",
        "sample": "02.11.2026",
    },
}


def get_data_field_options():
    """
    Zwraca listę etykiet pól do wyświetlenia w menu wyboru.
    """

    return [
        field["label"]
        for field in DATA_FIELDS.values()
    ]


def get_data_field_sample(field_name):
    """
    Zwraca przykładową wartość danego pola.

    field_name: klucz techniczny, np. batch_number.
    """

    field = DATA_FIELDS.get(field_name)

    if field is None:
        return ""

    return field["sample"]


def get_data_field_label(field_name):
    """
    Zwraca etykietę użytkową danego pola.
    """

    field = DATA_FIELDS.get(field_name)

    if field is None:
        return field_name

    return field["label"]


def get_data_field_key(label):
    """
    Zamienia etykietę wyświetlaną użytkownikowi
    na klucz techniczny pola.
    """

    for key, field in DATA_FIELDS.items():
        if field["label"] == label:
            return key

    return None


def is_valid_data_field(field_name):
    """
    Sprawdza, czy podany klucz pola istnieje w rejestrze.
    """

    return field_name in DATA_FIELDS

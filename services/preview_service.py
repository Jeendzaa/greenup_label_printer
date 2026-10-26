
from io import BytesIO
import re
import unicodedata

from PIL import Image
from zplkit import Options, render


class PreviewService:
    """Generuje lokalny podgląd etykiety na podstawie kodu ZPL."""

    def __init__(self, dpi=203):
        self.dpi = dpi

    def generate_preview(self, zpl, width_mm, height_mm):
        """Zwraca obraz PIL gotowy do wyświetlenia w GUI."""

        if not isinstance(zpl, str) or not zpl.strip():
            raise ValueError("Kod ZPL nie może być pusty.")

        width = self._get_dimension(zpl, "PW", width_mm)
        height = self._get_dimension(zpl, "LL", height_mm)

        options = Options(
            profile="specification",
            width=width,
            height=height,
            dpi=self.dpi,
        )

        try:
            document = render(zpl.encode("utf-8"), options)
        except Exception as error:
            if "glyph" not in str(error).lower():
                raise

            # Fallback dotyczy wyłącznie lokalnego podglądu.
            # Oryginalny ZPL wysyłany do drukarki nie jest zmieniany.
            preview_zpl = self._normalize_preview_text(zpl)
            document = render(preview_zpl.encode("utf-8"), options)

        if not document.labels:
            raise ValueError(
                "Renderer nie wygenerował podglądu etykiety."
            )

        image_data = document.labels[0].png()

        with Image.open(BytesIO(image_data)) as image:
            return image.convert("RGB").copy()

    @staticmethod
    def _normalize_preview_text(zpl):
        """Usuwa znaki diakrytyczne tylko w kopii do podglądu."""

        def replace_text(match):
            text = match.group(1)
            normalized = unicodedata.normalize("NFKD", text)
            ascii_text = normalized.encode(
                "ascii",
                "ignore",
            ).decode("ascii")

            return "^FD" + ascii_text + "^FS"

        return re.sub(
            r"\^FD(.*?)\^FS",
            replace_text,
            zpl,
            flags=re.IGNORECASE | re.DOTALL,
        )

    def _get_dimension(self, zpl, command, fallback_mm):
        """Pobiera wymiar z ZPL lub wylicza go z milimetrów."""

        match = re.search(
            rf"\^{command}\s*(\d+)",
            zpl,
            re.IGNORECASE,
        )

        if match:
            return int(match.group(1))

        return round(fallback_mm * self.dpi / 25.4)

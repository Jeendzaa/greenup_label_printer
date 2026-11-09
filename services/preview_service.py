
from io import BytesIO
import re
import unicodedata

from PIL import Image, ImageOps
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

        # zplkit 0.3.2 nie renderuje ^GFA. Wyciągamy bitmapy,
        # renderujemy pozostałą część ZPL, a obrazy nakładamy w PIL.
        preview_zpl, graphics = self._extract_graphics(zpl)

        try:
            document = render(preview_zpl.encode("utf-8"), options)
        except Exception as error:
            if "glyph" not in str(error).lower():
                raise

            # Fallback dotyczy wyłącznie lokalnego podglądu.
            # Oryginalny ZPL wysyłany do drukarki nie jest zmieniany.
            preview_zpl = self._normalize_preview_text(preview_zpl)
            document = render(preview_zpl.encode("utf-8"), options)

        if not document.labels:
            raise ValueError(
                "Renderer nie wygenerował podglądu etykiety."
            )

        image_data = document.labels[0].png()

        with Image.open(BytesIO(image_data)) as image:
            result = image.convert("RGB").copy()

        for graphic in graphics:
            self._overlay_graphic(result, graphic)

        return result

    @staticmethod
    def _extract_graphics(zpl):
        """
        Usuwa komendy ^GFA z kopii ZPL przekazywanej do zplkit.
        Zwraca listę bitmap do późniejszego nałożenia na podgląd.
        """
        pattern = re.compile(
            r"\^FO(\d+),(\d+)\^GFA,(\d+),(\d+),(\d+),([0-9A-Fa-f]+)\^FS",
            re.IGNORECASE,
        )
        graphics = []

        def replace(match):
            x, y, total, _binary_count, row_bytes = (
                int(match.group(index)) for index in range(1, 6)
            )
            hex_data = match.group(6)

            if len(hex_data) % 2:
                raise ValueError("Nieprawidłowe dane bitmapy ^GFA.")

            raw = bytes.fromhex(hex_data)
            expected = total

            if len(raw) != expected or row_bytes < 1 or total % row_bytes:
                raise ValueError("Nieprawidłowy rozmiar bitmapy ^GFA.")

            height = total // row_bytes
            graphics.append({
                "x": x,
                "y": y,
                "width": row_bytes * 8,
                "height": height,
                "row_bytes": row_bytes,
                "data": raw,
            })
            return ""

        cleaned = pattern.sub(replace, zpl)
        return cleaned, graphics

    @staticmethod
    def _overlay_graphic(canvas, graphic):
        """Nakłada czarne punkty bitmapy ZPL na obraz podglądu."""
        width = graphic["width"]
        height = graphic["height"]

        # W ZPL bit 1 oznacza czarny. PIL mode 1 interpretuje
        # bit 1 jako biały, dlatego odwracamy dane przed dekodowaniem.
        inverted = bytes(value ^ 0xFF for value in graphic["data"])
        bitmap = Image.frombytes("1", (width, height), inverted)

        # ZPL przechowuje szerokość w pełnych bajtach, więc piksele
        # dopełniające po prawej stronie nie mogą wyjść poza grafikę.
        mask = ImageOps.invert(bitmap.convert("L"))
        black = Image.new("RGB", (width, height), (0, 0, 0))
        canvas.paste(black, (graphic["x"], graphic["y"]), mask)

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

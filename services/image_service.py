from pathlib import Path

from PIL import Image, ImageOps


class ImageService:
    """
    Wczytuje i przygotowuje obrazy do wykorzystania na etykietach.

    Serwis nie generuje ZPL i nie komunikuje się z drukarką.
    Jego zadaniem jest przygotowanie obrazu jako bitmapy 1-bitowej,
    gotowej do późniejszego zakodowania przez ZPLService.
    """

    SUPPORTED_FORMATS = {
        ".png",
        ".jpg",
        ".jpeg",
        ".bmp",
    }

    DEFAULT_THRESHOLD = 128
    MAX_IMAGE_PIXELS = 20_000_000

    def open_image(self, image_path):
        """
        Otwiera obraz z dysku i zwraca niezależną kopię w trybie RGB/RGBA.

        Przezroczystość zostaje zachowana na tym etapie, aby można ją było
        poprawnie połączyć z białym tłem podczas przygotowania do druku.
        """

        path = Path(image_path)

        if not path.is_file():
            raise FileNotFoundError(
                f"Nie znaleziono pliku obrazu: {path}"
            )

        if path.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise ValueError(
                "Nieobsługiwany format obrazu. "
                "Dozwolone formaty: PNG, JPG, JPEG i BMP."
            )

        try:
            with Image.open(path) as source:
                if source.width * source.height > self.MAX_IMAGE_PIXELS:
                    raise ValueError(
                        "Obraz jest zbyt duży. Maksymalny rozmiar "
                        "to 20 megapikseli."
                    )

                source.load()

                if "A" in source.getbands():
                    return source.convert("RGBA").copy()

                return source.convert("RGB").copy()

        except (OSError, Image.DecompressionBombError) as error:
            raise ValueError(
                f"Nie udało się odczytać obrazu: {error}"
            ) from error

    def prepare_for_print(
        self,
        image,
        width_dots,
        height_dots,
        preserve_aspect_ratio=True,
        threshold=DEFAULT_THRESHOLD,
        dithering=False,
        rotation=0,
    ):
        """
        Przygotowuje obraz do druku termicznego.

        Args:
            image: Obiekt PIL.Image.
            width_dots: Docelowa szerokość w punktach drukarki.
            height_dots: Docelowa wysokość w punktach drukarki.
            preserve_aspect_ratio: Zachowuje proporcje i centruje obraz
                na białym tle, jeśli True.
            threshold: Próg binaryzacji w zakresie 0-255.
            dithering: Włącza dithering Floyd-Steinberg.
            rotation: Obrót zgodnie z ruchem wskazówek zegara: 0, 90, 180 lub 270.

        Returns:
            Obraz PIL w trybie "1" (bitmapa czarno-biała).
        """

        self._validate_dimensions(width_dots, height_dots)
        self._validate_threshold(threshold)

        if not isinstance(image, Image.Image):
            raise TypeError(
                "Parametr image musi być obiektem PIL.Image."
            )

        if isinstance(rotation, bool) or rotation not in (0, 90, 180, 270):
            raise ValueError("Obrót obrazu musi wynosić 0, 90, 180 lub 270 stopni.")

        working = self._composite_on_white(image)
        if rotation:
            # PIL obraca przeciwnie do ruchu wskazówek zegara, stąd minus.
            working = working.rotate(-rotation, expand=True)

        resampling = Image.Resampling.LANCZOS

        if preserve_aspect_ratio:
            working.thumbnail(
                (width_dots, height_dots),
                resampling,
            )

            canvas = Image.new(
                "L",
                (width_dots, height_dots),
                255,
            )

            x = (width_dots - working.width) // 2
            y = (height_dots - working.height) // 2

            canvas.paste(working, (x, y))

        else:
            canvas = working.resize(
                (width_dots, height_dots),
                resampling,
            )

        if dithering:
            return canvas.convert(
                "1",
                dither=Image.Dither.FLOYDSTEINBERG,
            )

        return canvas.point(
            lambda pixel: 255 if pixel >= threshold else 0,
            mode="1",
        )

    def load_and_prepare(
        self,
        image_path,
        width_dots,
        height_dots,
        preserve_aspect_ratio=True,
        threshold=DEFAULT_THRESHOLD,
        dithering=False,
        rotation=0,
    ):
        """Wygodna metoda łącząca wczytanie i przygotowanie obrazu."""

        image = self.open_image(image_path)

        return self.prepare_for_print(
            image=image,
            width_dots=width_dots,
            height_dots=height_dots,
            preserve_aspect_ratio=preserve_aspect_ratio,
            threshold=threshold,
            dithering=dithering,
            rotation=rotation,
        )

    @staticmethod
    def _composite_on_white(image):
        """
        Łączy przezroczyste piksele z białym tłem i zwraca obraz w skali
        szarości. Białe tło jest właściwym punktem wyjścia dla druku
        monochromatycznego.
        """

        if image.mode in ("RGBA", "LA") or "transparency" in image.info:
            rgba = image.convert("RGBA")
            background = Image.new(
                "RGBA",
                rgba.size,
                (255, 255, 255, 255),
            )
            return Image.alpha_composite(
                background,
                rgba,
            ).convert("L")

        return image.convert("L")

    @staticmethod
    def _validate_dimensions(width_dots, height_dots):
        for value, label in (
            (width_dots, "Szerokość"),
            (height_dots, "Wysokość"),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 1
            ):
                raise ValueError(
                    f"{label} obrazu musi być dodatnią liczbą całkowitą."
                )

    @staticmethod
    def _validate_threshold(threshold):
        if (
            isinstance(threshold, bool)
            or not isinstance(threshold, int)
            or not 0 <= threshold <= 255
        ):
            raise ValueError(
                "Próg binaryzacji musi być liczbą całkowitą od 0 do 255."
            )
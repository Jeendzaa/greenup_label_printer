
import hashlib
import re
import tempfile
import urllib.error
import urllib.request
import zipfile

from pathlib import Path
from urllib.parse import urlparse


class DownloadService:
    """
    Odpowiada za pobieranie archiwum aktualizacji,
    weryfikację SHA-256 i sprawdzenie poprawności ZIP.
    """

    def __init__(self, timeout=30):
        self.timeout = timeout

    @staticmethod
    def _normalize_version(version):
        """
        Normalizuje wersję, np. v1.0.0 -> 1.0.0.
        """

        version = version.strip()

        if version.startswith(("v", "V")):
            version = version[1:]

        if not re.fullmatch(r"\d+\.\d+(?:\.\d+)?", version):
            raise ValueError(
                f"Nieprawidłowy numer wersji: {version}"
            )

        return version

    
    @staticmethod
    def _find_windows_asset(release_info):
        """
        Wyszukuje archiwum Windows dla konkretnego Release.
        Akceptuje równoważne wersje, np. 1.0 i 1.0.0.
        """

        def version_tuple(version):
            normalized = DownloadService._normalize_version(version)
            parts = [int(part) for part in normalized.split(".")]

            while len(parts) < 3:
                parts.append(0)

            return tuple(parts)

        latest_version = version_tuple(
            release_info["latest_version"]
        )

        pattern = re.compile(
            r"^GreenUpLabelPrinter-v?(\d+\.\d+(?:\.\d+)?)-Windows\.zip$",
            re.IGNORECASE
        )

        for asset in release_info.get("assets", []):
            asset_name = asset.get("name", "")
            match = pattern.fullmatch(asset_name)

            if not match:
                continue

            asset_version = version_tuple(match.group(1))

            if asset_version == latest_version:
                return asset

        raise RuntimeError(
            "Nie znaleziono archiwum Windows dla wersji "
            f"{release_info['latest_version']} w najnowszym Release."
        )

    @staticmethod
    def _calculate_sha256(file_path):
        """
        Oblicza sumę kontrolną SHA-256 pliku.
        """

        sha256 = hashlib.sha256()

        with open(file_path, "rb") as file:
            for chunk in iter(
                lambda: file.read(1024 * 1024),
                b""
            ):
                sha256.update(chunk)

        return sha256.hexdigest()

    def _download_file(self, url, destination):
        """
        Pobiera plik na dysk.
        """

        parsed_url = urlparse(url)

        if parsed_url.scheme != "https":
            raise RuntimeError(
                "Pobieranie aktualizacji wymaga połączenia HTTPS."
            )

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "GreenUpLabelPrinter"
            }
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout
            ) as response:
                with open(destination, "wb") as file:
                    while True:
                        chunk = response.read(1024 * 1024)

                        if not chunk:
                            break

                        file.write(chunk)

        except urllib.error.HTTPError as error:
            raise RuntimeError(
                f"Błąd pobierania HTTP: {error.code}"
            )

        except urllib.error.URLError as error:
            raise RuntimeError(
                f"Nie można pobrać aktualizacji: {error.reason}"
            )

    @staticmethod
    def _verify_zip(file_path):
        """
        Sprawdza poprawność struktury ZIP i CRC plików.
        """

        if not zipfile.is_zipfile(file_path):
            raise RuntimeError(
                "Pobrany plik nie jest poprawnym archiwum ZIP."
            )

        try:
            with zipfile.ZipFile(file_path, "r") as archive:
                corrupted_file = archive.testzip()

                if corrupted_file:
                    raise RuntimeError(
                        f"Uszkodzony plik w archiwum: {corrupted_file}"
                    )

        except zipfile.BadZipFile:
            raise RuntimeError(
                "Nie można odczytać archiwum ZIP."
            )

    def download_update(self, release_info):
        """
        Pobiera aktualizację i weryfikuje jej poprawność.

        Zwraca ścieżkę do pobranego archiwum.
        """

        asset = self._find_windows_asset(release_info)

        download_url = asset.get("download_url")

        if not download_url:
            raise RuntimeError(
                "Release nie zawiera adresu pobierania archiwum."
            )

        file_name = asset["name"]

        download_dir = (
            Path(tempfile.gettempdir())
            / "GreenUpLabelPrinter"
            / "updates"
        )

        download_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        destination = download_dir / file_name
        temporary_file = destination.with_suffix(".zip.part")

        try:
            self._download_file(
                download_url,
                temporary_file
            )

            expected_size = asset.get("size")

            if (
                expected_size is not None
                and temporary_file.stat().st_size != expected_size
            ):
                raise RuntimeError(
                    "Rozmiar pobranego pliku jest niezgodny "
                    "z informacjami GitHub."
                )

            digest = asset.get("digest")

            if digest:
                algorithm, separator, expected_hash = digest.partition(":")

                if algorithm.lower() != "sha256" or not separator:
                    raise RuntimeError(
                        "GitHub udostępnił nieobsługiwany format digest."
                    )

                actual_hash = self._calculate_sha256(
                    temporary_file
                )

                if actual_hash.lower() != expected_hash.lower():
                    raise RuntimeError(
                        "Weryfikacja SHA-256 nie powiodła się. "
                        "Plik może być uszkodzony lub zmodyfikowany."
                    )

            self._verify_zip(temporary_file)

            temporary_file.replace(destination)

            return destination

        except Exception:
            if temporary_file.exists():
                temporary_file.unlink()

            raise
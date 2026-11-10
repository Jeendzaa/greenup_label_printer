
import json
import re
import urllib.error
import urllib.request

from config import APP_VERSION, GITHUB_API_URL


class UpdateService:
    """
    Odpowiada za sprawdzanie dostępności nowych wersji
    aplikacji na GitHub Releases.
    """

    def __init__(self, timeout=10):
        self.timeout = timeout

    @staticmethod
    def _parse_version(version):
        """
        Zamienia numer wersji na krotkę liczb.

        Obsługiwane formaty:
        1.0
        1.0.0
        v1.0
        v1.0.0
        """

        if not isinstance(version, str):
            raise ValueError("Numer wersji musi być tekstem.")

        version = version.strip()

        match = re.fullmatch(
            r"v?(\d+)\.(\d+)(?:\.(\d+))?",
            version,
            re.IGNORECASE
        )

        if not match:
            raise ValueError(
                f"Nieprawidłowy numer wersji: {version}"
            )

        major = int(match.group(1))
        minor = int(match.group(2))
        patch = int(match.group(3) or 0)

        return major, minor, patch

    def _fetch_latest_release(self):
        """
        Pobiera informacje o najnowszym stabilnym Release.
        """

        request = urllib.request.Request(
            GITHUB_API_URL,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "GreenUpLabelPrinter"
            }
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout
            ) as response:
                data = json.loads(response.read().decode("utf-8"))

        except urllib.error.HTTPError as error:
            if error.code == 404:
                raise RuntimeError(
                    "Nie znaleziono żadnego Release na GitHubie."
                )

            if error.code == 403:
                raise RuntimeError(
                    "GitHub ograniczył liczbę zapytań API. "
                    "Spróbuj ponownie później."
                )

            raise RuntimeError(
                f"GitHub API zwróciło błąd HTTP {error.code}."
            )

        except urllib.error.URLError as error:
            raise RuntimeError(
                f"Nie można połączyć się z GitHubem: {error.reason}"
            )

        except json.JSONDecodeError:
            raise RuntimeError(
                "GitHub zwrócił nieprawidłową odpowiedź."
            )

        tag_name = data.get("tag_name")

        if not tag_name:
            raise RuntimeError(
                "Release nie zawiera numeru wersji (tag_name)."
            )

        assets = []

        for asset in data.get("assets", []):
            assets.append({
                "name": asset.get("name"),
                "download_url": asset.get("browser_download_url"),
                "size": asset.get("size"),
                "digest": asset.get("digest")
            })

        return {
            "tag_name": tag_name,
            "name": data.get("name"),
            "release_notes": data.get("body") or "",
            "release_url": data.get("html_url"),
            "assets": assets
        }

    def check_for_updates(self):
        """
        Sprawdza, czy na GitHubie dostępna jest nowsza wersja.

        Zwraca słownik zawierający informacje o aktualizacji.
        """

        current_version = self._parse_version(APP_VERSION)

        release = self._fetch_latest_release()

        latest_version = self._parse_version(
            release["tag_name"]
        )

        return {
            "update_available": latest_version > current_version,
            "current_version": APP_VERSION,
            "latest_version": release["tag_name"],
            "release_name": release["name"],
            "release_notes": release["release_notes"],
            "release_url": release["release_url"],
            "assets": release["assets"]
        }
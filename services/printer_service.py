
import socket


class PrinterService:
    """Odpowiada za wysyłanie kodu ZPL do drukarki sieciowej."""

    def __init__(self, host="192.168.130.92", port=9100, timeout=5):
        self.host = host
        self.port = port
        self.timeout = timeout

    def send_zpl(self, zpl):
        """
        Wysyła kod ZPL do drukarki.

        Zwraca True, jeśli dane zostały wysłane.
        W przypadku błędu zgłasza wyjątek.
        """

        if not isinstance(zpl, str) or not zpl.strip():
            raise ValueError("Kod ZPL nie może być pusty.")

        if "^XA" not in zpl or "^XZ" not in zpl:
            raise ValueError(
                "Kod ZPL musi zawierać komendy ^XA oraz ^XZ."
            )

        try:
            with socket.create_connection(
                (self.host, self.port),
                timeout=self.timeout,
            ) as printer_socket:

                printer_socket.sendall(zpl.encode("utf-8"))

            return True

        except (OSError, TimeoutError) as error:
            raise ConnectionError(
                f"Nie udało się wysłać danych do drukarki "
                f"{self.host}:{self.port}. "
                f"Szczegóły: {error}"
            ) from error

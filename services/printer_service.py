
import re
import socket


class PrinterService:
    """Wysyła zadania ZPL do drukarki przez TCP."""

    def __init__(
        self,
        host="192.168.130.92",
        port=9100,
        timeout=5,
    ):
        self.host = host
        self.port = port
        self.timeout = timeout

    def send_zpl(self, zpl, copies=1):
        """Wysyła etykietę ZPL z określoną liczbą kopii."""

        if not isinstance(zpl, str) or not zpl.strip():
            raise ValueError("Kod ZPL nie może być pusty.")

        if not isinstance(copies, int) or isinstance(copies, bool):
            raise ValueError("Ilość sztuk musi być liczbą całkowitą.")

        if copies < 1:
            raise ValueError("Ilość sztuk musi wynosić co najmniej 1.")

        if "^XA" not in zpl.upper() or "^XZ" not in zpl.upper():
            raise ValueError(
                "Kod ZPL musi zawierać komendy ^XA oraz ^XZ."
            )

        zpl_with_quantity = self._set_quantity(zpl, copies)

        try:
            with socket.create_connection(
                (self.host, self.port),
                timeout=self.timeout,
            ) as printer_socket:
                printer_socket.sendall(
                    zpl_with_quantity.encode("utf-8")
                )

        except OSError as error:
            raise ConnectionError(
                f"Nie udało się wysłać danych do drukarki "
                f"{self.host}:{self.port}: {error}"
            ) from error

        return True

    @staticmethod
    def _set_quantity(zpl, copies):
        """Ustawia liczbę kopii w komendzie ^PQ."""

        # Usuwamy istniejące komendy ^PQ, aby nie dublować ilości.
        zpl = re.sub(
            r"\^PQ[^^\r\n]*",
            "",
            zpl,
            flags=re.IGNORECASE,
        )

        # Wstawiamy nową komendę przed ostatnim ^XZ.
        end_position = zpl.upper().rfind("^XZ")

        if end_position == -1:
            raise ValueError("Nie znaleziono końcowej komendy ^XZ.")

        return (
            zpl[:end_position]
            + f"^PQ{copies}\n"
            + zpl[end_position:]
        )

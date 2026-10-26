
import re
import socket


class PrinterService:
    def __init__(self, host="192.168.130.92", port=9100, timeout=5):
        self.host = host
        self.port = port
        self.timeout = timeout

    def send_zpl(self, zpl, copies=None):
        if not isinstance(zpl, str) or not zpl.strip():
            raise ValueError("Kod ZPL nie może być pusty.")

        if copies is not None:
            if not isinstance(copies, int) or isinstance(copies, bool):
                raise ValueError(
                    "Ilość sztuk musi być liczbą całkowitą."
                )

            if copies < 1:
                raise ValueError(
                    "Ilość sztuk musi wynosić co najmniej 1."
                )

        upper_zpl = zpl.upper()

        if "^XA" not in upper_zpl or "^XZ" not in upper_zpl:
            raise ValueError(
                "Kod ZPL musi zawierać komendy ^XA oraz ^XZ."
            )

        # Jeżeli podano copies, nadpisujemy ^PQ.
        # Jeżeli copies=None, pozostawiamy kod ZPL bez zmian.
        if copies is not None:
            zpl = self._set_quantity(zpl, copies)

        try:
            with socket.create_connection(
                (self.host, self.port),
                timeout=self.timeout,
            ) as printer_socket:
                printer_socket.sendall(zpl.encode("utf-8"))

        except OSError as error:
            raise ConnectionError(
                f"Nie udało się wysłać danych do drukarki "
                f"{self.host}:{self.port}: {error}"
            ) from error

        return True

    @staticmethod
    def _set_quantity(zpl, copies):
        # Usuwamy istniejące ^PQ, aby nie występowały dwie
        # sprzeczne komendy określające liczbę kopii.
        zpl = re.sub(
            r"\^PQ[^^\r\n]*",
            "",
            zpl,
            flags=re.IGNORECASE,
        )

        end_position = zpl.upper().rfind("^XZ")

        if end_position == -1:
            raise ValueError(
                "Nie znaleziono końcowej komendy ^XZ."
            )

        return (
            zpl[:end_position]
            + f"^PQ{copies}\n"
            + zpl[end_position:]
        )

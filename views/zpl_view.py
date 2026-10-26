import customtkinter as ctk

class ZPLView(ctk.CTkFrame):
    def __init__(self, parent, printer_service):
        super.__init__(parent, fg_color="transparent")
        self.printer_service = printer_service
        self._create_widgets()

    def _create_widgets(self):
        title = ctk.CTkLabel(
            self,
            text="Kod ZPL",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(anchor="w", pady=(0, 8))

        description = ctk.CTkLabel(
            self,
            text="Wklej kod ZPL, aby wysłać go bezpośrednio do drukarki.",
            font=ctk.CTkFont(size=14),
            text_color="#AAB7C4",
        )
        description.pack(anchor="w", pady=(0, 15))

        self.zpl_textbox = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Consolas", size=13),
        )
        self.zpl_textbox.pack(
            fill="both",
            expand=True,
            pady=(0, 15),
        )

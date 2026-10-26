
import customtkinter as ctk


class ZPLView(ctk.CTkFrame):
    def __init__(self, parent, printer_service):
        super().__init__(parent, fg_color="transparent")

        self.printer_service = printer_service

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._create_widgets()

    def _create_widgets(self):
        description = ctk.CTkLabel(
            self,
            text="Wklej własny kod ZPL, aby przygotować go do wysłania.",
            font=ctk.CTkFont(size=14),
            text_color="#AAB7C4",
            wraplength=700,
            justify="left",
        )
        description.grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 15),
        )

        editor_label = ctk.CTkLabel(
            self,
            text="Kod ZPL",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        editor_label.grid(
            row=1,
            column=0,
            sticky="w",
            pady=(0, 8),
        )

        self.zpl_textbox = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Consolas", size=13),
        )
        self.zpl_textbox.grid(
            row=2,
            column=0,
            sticky="nsew",
        )

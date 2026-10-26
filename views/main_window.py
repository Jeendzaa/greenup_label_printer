
import customtkinter as ctk

from views.print_view import PrintView
from views.template_editor import TemplateEditorView
from views.zpl_view import ZPLView
from pathlib import Path


class MainWindow(ctk.CTk):
    def __init__(
        self,
        template_service,
        zpl_service,
        printer_service,
    ):
        super().__init__()

        icon_path = (
            Path(__file__).resolve().parent.parent
            / "assets"
            / "greenup_label_printer_icon.ico"
        )

        self.iconbitmap(str(icon_path))

        self.template_service = template_service
        self.zpl_service = zpl_service
        self.printer_service = printer_service

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("GreenUp! Label Printer")
        self.geometry("1100x700")
        self.minsize(900, 600)

        self.sidebar_color = "#18212B"
        self.main_color = "#222D38"
        self.accent_color = "#27845B"
        self.text_color = "#F3F6F8"
        self.muted_color = "#AAB7C4"

        self.configure(fg_color=self.main_color)

        # Główny układ okna: treść + pasek statusu.
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        self._create_workspace()
        self._create_status_bar()
        self._create_views()

        self.show_view("druk")

    def _create_workspace(self):
        """Tworzy obszar roboczy z menu i panelem treści."""

        self.workspace = ctk.CTkFrame(
            self,
            fg_color=self.main_color,
            corner_radius=0,
        )
        self.workspace.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        self.workspace.grid_columnconfigure(0, weight=0)
        self.workspace.grid_columnconfigure(1, weight=1)
        self.workspace.grid_rowconfigure(0, weight=1)

        self._create_sidebar()
        self._create_main_area()

    def _create_sidebar(self):
        """Tworzy menu boczne."""

        self.sidebar = ctk.CTkFrame(
            self.workspace,
            width=230,
            corner_radius=0,
            fg_color=self.sidebar_color,
        )
        self.sidebar.grid(
            row=0,
            column=0,
            sticky="nsew",
        )
        self.sidebar.grid_propagate(False)

        logo = ctk.CTkLabel(
            self.sidebar,
            text="GREENUP!\nLABEL PRINTER",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=self.text_color,
            justify="left",
        )
        logo.pack(
            anchor="w",
            padx=22,
            pady=(28, 35),
        )

        self.menu_buttons = {}

        menu_items = [
            ("druk", "Drukuj etykietę"),
            ("tworz", "Edytor szablonów"),
            ("zplcode", "Kod ZPL"),
        ]

        for view_id, label in menu_items:
            button = ctk.CTkButton(
                self.sidebar,
                text=label,
                height=42,
                anchor="w",
                corner_radius=8,
                fg_color="transparent",
                hover_color="#2B3947",
                text_color=self.text_color,
                font=ctk.CTkFont(size=14),
                command=lambda v=view_id: self.show_view(v),
            )
            button.pack(
                fill="x",
                padx=12,
                pady=4,
            )

            self.menu_buttons[view_id] = button

        exit_button = ctk.CTkButton(
            self.sidebar,
            text="Zamknij program",
            height=40,
            corner_radius=8,
            fg_color="#873D42",
            hover_color="#A44A50",
            command=self.destroy,
        )
        exit_button.pack(
            side="bottom",
            fill="x",
            padx=12,
            pady=18,
        )

    def _create_main_area(self):
        """Tworzy panel zajmujący całą pozostałą przestrzeń."""

        self.main_frame = ctk.CTkFrame(
            self.workspace,
            fg_color=self.main_color,
            corner_radius=0,
        )
        self.main_frame.grid(
            row=0,
            column=1,
            sticky="nsew",
        )

        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        self.page_title = ctk.CTkLabel(
            self.main_frame,
            text="",
            font=ctk.CTkFont(size=27, weight="bold"),
            text_color=self.text_color,
        )
        self.page_title.grid(
            row=0,
            column=0,
            sticky="w",
            padx=30,
            pady=(25, 15),
        )

        self.content_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color="transparent",
            corner_radius=0,
        )
        self.content_frame.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=30,
            pady=(0, 25),
        )

        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

    def _create_status_bar(self):
        """Tworzy pasek statusu u dołu okna."""

        self.status_bar = ctk.CTkFrame(
            self,
            height=34,
            corner_radius=0,
            fg_color="#141C24",
        )
        self.status_bar.grid(
            row=1,
            column=0,
            sticky="ew",
        )
        self.status_bar.grid_propagate(False)

        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text="Citizen: 192.168.130.92 | TCP 9100",
            text_color=self.muted_color,
            font=ctk.CTkFont(size=12),
        )
        self.status_label.pack(
            side="left",
            padx=18,
        )

        self.connection_label = ctk.CTkLabel(
            self.status_bar,
            text="Gotowy",
            text_color="#65D69A",
            font=ctk.CTkFont(size=12),
        )
        self.connection_label.pack(
            side="right",
            padx=18,
        )

    def _create_views(self):
        """Tworzy widoki i przechowuje je w jednym słowniku."""

        self.views = {
            "druk": PrintView(
                self.content_frame,
                self.template_service,
                self.zpl_service,
                self.printer_service,
            ),
            "tworz": TemplateEditorView(
                self.content_frame,
                self.template_service,
            ),
            "zplcode": ZPLView(
                self.content_frame,
                self.printer_service,
            ),
        }

        for view in self.views.values():
            view.grid(
                row=0,
                column=0,
                sticky="nsew",
            )
            view.grid_remove()

    def show_view(self, view_id):
        """Pokazuje wybrany widok i aktualizuje menu."""

        if view_id not in self.views:
            return

        for view in self.views.values():
            view.grid_remove()

        self.views[view_id].grid()

        titles = {
            "druk": "Drukuj etykietę",
            "tworz": "Edytor szablonów",
            "zplcode": "Kod ZPL",
        }

        self.page_title.configure(text=titles[view_id])

        for key, button in self.menu_buttons.items():
            if key == view_id:
                button.configure(
                    fg_color=self.accent_color,
                    hover_color=self.accent_color,
                )
            else:
                button.configure(
                    fg_color="transparent",
                    hover_color="#2B3947",
                )
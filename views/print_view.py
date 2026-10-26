import customtkinter as ctk

class PrintView(ctk.CTkFrame):
    def __init__(self, parent, template_service, zpl_service, printer_service):
        super().__init__(parent, fg_color="transparent")
        self.template_service = self.template_service
        self.zpl_service = zpl_service
        self.printer_service = printer_service
        self.grid_columnconfigure(0, weight=1)
        self._create_widget()

    def _create_widget(self):
        title = ctk.CTkLabel(
            self,text="Drukuj etykiete",
            font=ctk.CTkFont(size=24, weight="bold")
            )
        title.grid(row=0, column=0, sticky="w", pady=(0,8))

        description = ctk.CTkLabel(
            self,
            text="Wybierz szablon i przygotuj etykietę do druku.",
            font=ctk.CTkFont(size=14),
            text_color="#AAB7C4"
        )
        description.grid(row=1, column=0, sticky="w", pady=(0,25))

        templates = self.template_service.load_templates()
        template_names = [templates["name"] for template in templates]

        self.templates_by_name = {
            template["name"]: template
            for template in templates
            }

        self.template_selector = ctk.CTkComboBox(
            self,
            values=template_names or ["Brak szablonów"],
            state="readonly",
            width=350,
        )

        self.template_selector.grid(row=2, column=0, sticky="w")

        if template_names:
            self.template_selector.set(template_names[0])
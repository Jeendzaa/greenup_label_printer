import customtkinter as ctk

class TemplateEditorView(ctk.CTkFrame):
    def __init__(self, parent, template_service):
        super().__init__(parent, fg_color="transparent")

        self.template_service = template_service
        self._create_widgets()

    def _create_widgets(self):
        title = ctk.CTkLabel(
            self,
            text="Edytor szablonów",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(anchor="w", pady=(0,8))

        description = ctk.CTkLabel(
            self,
            text="Tutaj będziesz tworzyć i edytować szablony etykiet.",
            text_color="#AAB7C4",
        )
        description.pack(anchor="w", pady=(0, 20))

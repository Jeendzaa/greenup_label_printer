
import customtkinter as ctk


class TemplateEditorView(ctk.CTkFrame):
    def __init__(self, parent, template_service):
        super().__init__(parent, fg_color="transparent")

        self.template_service = template_service

        self._create_widgets()

    def _create_widgets(self):
        description = ctk.CTkLabel(
            self,
            text=(
                "Tutaj będziesz tworzyć i edytować "
                "szablony etykiet."
            ),
            font=ctk.CTkFont(size=14),
            text_color="#AAB7C4",
            wraplength=700,
            justify="left",
        )
        description.pack(
            anchor="w",
            pady=(0, 20),
        )

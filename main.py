
from services.template_service import TemplateService
from services.zpl_service import ZPLService
from services.printer_service import PrinterService
from views.main_window import MainWindow


def main():
    template_service = TemplateService()
    zpl_service = ZPLService()
    printer_service = PrinterService()

    app = MainWindow(
        template_service=template_service,
        zpl_service=zpl_service,
        printer_service=printer_service,
    )

    app.mainloop()


if __name__ == "__main__":
    main()

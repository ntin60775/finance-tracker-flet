import flet as ft
from finance_tracker.views.main_window import MainWindow
from finance_tracker.database import init_db
from finance_tracker.utils.logger import setup_logging, get_logger

logger = get_logger(__name__)


def _ensure_flet_page_dialog_compatibility() -> None:
    """Добавляет совместимые методы page.open/page.close для новых версий Flet."""
    if not hasattr(ft.Page, "open"):
        def _open(self: ft.Page, dialog):
            self.show_dialog(dialog)

        setattr(ft.Page, "open", _open)

    if not hasattr(ft.Page, "close"):
        def _close(self: ft.Page, _dialog=None):
            self.pop_dialog()

        setattr(ft.Page, "close", _close)


def main(page: ft.Page):
    _ensure_flet_page_dialog_compatibility()

    # 1. Настройка логирования
    setup_logging()
    logger.info("Запуск приложения Finance Tracker Flet")

    # 2. Инициализация БД
    try:
        init_db()
        logger.info("База данных успешно инициализирована")
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")
        page.add(ft.Text(f"Критическая ошибка: {e}", color=ft.Colors.ERROR))
        return

    # 3. Инициализация главного окна
    # MainWindow сам настроит page.appbar и вернет основной layout в build()
    app_window = MainWindow(page)
    
    # Добавляем основной layout на страницу
    page.add(app_window)
    
    page.update()

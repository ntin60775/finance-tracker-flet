import flet as ft
from finance_tracker.views.main_window import MainWindow
from finance_tracker.database import init_db
from finance_tracker.utils.logger import setup_logging, get_logger

logger = get_logger(__name__)

def main(page: ft.Page):
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

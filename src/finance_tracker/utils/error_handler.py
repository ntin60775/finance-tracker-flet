"""
Модуль централизованной обработки ошибок.
Предоставляет инструменты для перехвата, логирования и отображения ошибок в UI.
"""

import logging
import traceback
from typing import Callable, Optional
import flet as ft

from finance_tracker.utils.exceptions import (
    ValidationError,
    BusinessLogicError,
    DatabaseError
)

logger = logging.getLogger(__name__)

class ErrorHandler:
    """
    Класс для централизованной обработки ошибок.
    """

    def __init__(self, page: Optional[ft.Page] = None):
        self.page = page

    def handle(self, exception: Exception, context_message: str = ""):
        """
        Обрабатывает возникшее исключение: логирует и показывает уведомление пользователю.
        
        Args:
            exception: Исключение, которое нужно обработать.
            context_message: Дополнительное сообщение о контексте ошибки.
        """
        error_message = self._get_user_message(exception)
        log_message = f"{context_message}: {str(exception)}" if context_message else str(exception)

        # Логирование
        if isinstance(exception, (ValidationError, BusinessLogicError)):
            logger.warning(f"User error: {log_message}")
        else:
            logger.error(f"System error: {log_message}\n{traceback.format_exc()}")

        # Отображение в UI (если есть доступ к странице)
        if self.page:
            self._show_error_dialog(error_message)

    def _get_user_message(self, exception: Exception) -> str:
        """Возвращает понятное пользователю сообщение об ошибке."""
        if isinstance(exception, ValidationError):
            return f"Ошибка ввода: {str(exception)}"
        elif isinstance(exception, BusinessLogicError):
            return f"Невозможно выполнить операцию: {str(exception)}"
        elif isinstance(exception, DatabaseError):
            return "Произошла ошибка при работе с базой данных. Попробуйте позже."
        else:
            return f"Произошла непредвиденная ошибка: {str(exception)}"

    def _show_error_dialog(self, message: str):
        """Показывает диалог с ошибкой."""
        snack_bar = ft.SnackBar(
            content=ft.Text(message, color=ft.Colors.WHITE),
            bgcolor=ft.Colors.ERROR,
            action="OK",
        )
        self.page.snack_bar = snack_bar
        snack_bar.open = True
        self.page.update()


def safe_handler(page_getter: Callable[[], Optional[ft.Page]] = None):
    """
    Декоратор для обработчиков событий UI.
    Автоматически перехватывает ошибки и передает их в ErrorHandler.
    
    Args:
        page_getter: Опциональная функция, возвращающая текущий объект ft.Page.
                     Если не указана, пытается получить page из self (первого аргумента).
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Пытаемся получить page
                page = None
                try:
                    # Если первый аргумент self, и у него есть page
                    if args and hasattr(args[0], 'page'):
                        page = args[0].page
                    # Иначе пробуем page_getter
                    if not page and callable(page_getter):
                        page = page_getter()
                except Exception:
                    # Если не удалось получить page, просто логируем, 
                    # но ErrorHandler обработает это (без UI части, если page=None)
                    pass
                
                handler = ErrorHandler(page)
                handler.handle(e, context_message=f"Error in {func.__name__}")
        return wrapper
    return decorator

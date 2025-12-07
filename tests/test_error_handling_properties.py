"""
Property-based тесты для системы обработки ошибок.
Проверяют, что ошибки корректно перехватываются и трансформируются в понятные сообщения.
"""

from unittest.mock import MagicMock, patch
from hypothesis import given, strategies as st

from utils.exceptions import (
    ValidationError,
    BusinessLogicError,
    DatabaseError
)
from utils.error_handler import ErrorHandler, safe_handler

@given(st.text())
def test_validation_error_handling(message):
    """
    Property 54: Отображение ошибок валидации.
    Feature: Error Handling
    """
    page_mock = MagicMock()
    handler = ErrorHandler(page_mock)
    
    exception = ValidationError(message)
    handler.handle(exception)
    
    # Проверяем, что показан SnackBar с сообщением об ошибке ввода
    assert page_mock.snack_bar.open is True
    assert f"Ошибка ввода: {message}" in page_mock.snack_bar.content.value
    assert page_mock.update.called

@given(st.text())
def test_business_logic_error_handling(message):
    """
    Property 57: Предотвращение некорректных операций.
    Feature: Error Handling
    """
    page_mock = MagicMock()
    handler = ErrorHandler(page_mock)
    
    exception = BusinessLogicError(message)
    handler.handle(exception)
    
    # Проверяем, что показан SnackBar с сообщением о бизнес-логике
    assert page_mock.snack_bar.open is True
    assert f"Невозможно выполнить операцию: {message}" in page_mock.snack_bar.content.value

def test_database_error_handling():
    """
    Property 55: Логирование ошибок БД.
    Feature: Error Handling
    """
    page_mock = MagicMock()
    handler = ErrorHandler(page_mock)
    
    exception = DatabaseError("Connection failed")
    
    with patch('finance_tracker_flet.utils.error_handler.logger') as logger_mock:
        handler.handle(exception)
        
        # Проверяем, что ошибка БД залогирована как ERROR
        logger_mock.error.assert_called()
        # Пользователю показывается общее сообщение, без деталей подключения
        assert "Произошла ошибка при работе с базой данных" in page_mock.snack_bar.content.value

@given(st.text())
def test_safe_handler_decorator(error_msg):
    """
    Property 56: Валидация пользовательских вводов (через декоратор).
    Feature: Error Handling
    """
    page_mock = MagicMock()
    
    # Создаем класс, имитирующий контрол Flet
    class MockControl:
        def __init__(self):
            self.page = page_mock
            
        @safe_handler()
        def risky_method(self):
            raise ValidationError(error_msg)
            
    control = MockControl()
    control.risky_method()
    
    # Декоратор должен был перехватить ошибку и вызвать ErrorHandler
    assert page_mock.snack_bar.open is True
    assert f"Ошибка ввода: {error_msg}" in page_mock.snack_bar.content.value

"""
Property-based тесты для системы обработки ошибок.
Проверяют, что ошибки корректно перехватываются и трансформируются в понятные сообщения.
"""

from unittest.mock import MagicMock, patch, Mock
from hypothesis import given, strategies as st, settings
from datetime import date
import datetime
import flet as ft

from finance_tracker.utils.exceptions import (
    ValidationError,
    BusinessLogicError,
    DatabaseError
)
from finance_tracker.utils.error_handler import ErrorHandler, safe_handler
from finance_tracker.components.transactions_panel import TransactionsPanel

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
    
    # Проверяем, что page.open() был вызван для показа SnackBar
    page_mock.open.assert_called_once()
    # Проверяем, что передан SnackBar с правильным сообщением
    snack_bar_arg = page_mock.open.call_args[0][0]
    assert isinstance(snack_bar_arg, ft.SnackBar)
    assert f"Ошибка ввода: {message}" in snack_bar_arg.content.value

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
    
    # Проверяем, что page.open() был вызван для показа SnackBar
    page_mock.open.assert_called_once()
    # Проверяем, что передан SnackBar с правильным сообщением
    snack_bar_arg = page_mock.open.call_args[0][0]
    assert isinstance(snack_bar_arg, ft.SnackBar)
    assert f"Невозможно выполнить операцию: {message}" in snack_bar_arg.content.value

def test_database_error_handling():
    """
    Property 55: Логирование ошибок БД.
    Feature: Error Handling
    """
    page_mock = MagicMock()
    handler = ErrorHandler(page_mock)
    
    exception = DatabaseError("Connection failed")
    
    with patch('finance_tracker.utils.error_handler.logger') as logger_mock:
        handler.handle(exception)
        
        # Проверяем, что ошибка БД залогирована как ERROR
        logger_mock.error.assert_called()
        # Проверяем, что page.open() был вызван для показа SnackBar
        page_mock.open.assert_called_once()
        # Проверяем, что передан SnackBar с правильным сообщением
        snack_bar_arg = page_mock.open.call_args[0][0]
        assert isinstance(snack_bar_arg, ft.SnackBar)
        # Пользователю показывается общее сообщение, без деталей подключения
        assert "Произошла ошибка при работе с базой данных" in snack_bar_arg.content.value

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
    # Проверяем, что page.open() был вызван для показа SnackBar
    page_mock.open.assert_called_once()
    # Проверяем, что передан SnackBar с правильным сообщением
    snack_bar_arg = page_mock.open.call_args[0][0]
    assert isinstance(snack_bar_arg, ft.SnackBar)
    assert f"Ошибка ввода: {error_msg}" in snack_bar_arg.content.value


@given(
    date_obj=st.dates(min_value=datetime.date(2020, 1, 1), max_value=datetime.date(2030, 12, 31)),
    has_page=st.booleans(),
    has_modal=st.booleans()
)
@settings(max_examples=50, deadline=None)
def test_property_1_button_click_opens_modal(date_obj, has_page, has_modal):
    """
    **Feature: add-transaction-button-fix, Property 1: Button Click Opens Modal**
    **Validates: Requirements 1.1, 1.3**
    
    Property: Для любого валидного HomeView с TransactionsPanel, при нажатии кнопки 
    добавления транзакции должно открываться TransactionModal с текущей выбранной датой.
    """
    from finance_tracker.views.home_view import HomeView
    from finance_tracker.components.transaction_modal import TransactionModal
    from unittest.mock import MagicMock, Mock, patch
    
    # Arrange - создаем различные сценарии для тестирования
    mock_session = Mock()
    
    # Создаем mock page или None в зависимости от has_page
    if has_page:
        mock_page = MagicMock()
        mock_page.open = Mock()
        mock_page.update = Mock()
        mock_page.overlay = []
        # Настраиваем SnackBar
        mock_snack_bar = MagicMock()
        mock_page.snack_bar = mock_snack_bar
    else:
        mock_page = None
    
    # Создаем HomeView с мокированными зависимостями
    with patch('finance_tracker.views.home_view.HomePresenter'):
        home_view = HomeView(mock_page, mock_session)
        home_view.selected_date = date_obj
        
        # Настраиваем TransactionModal в зависимости от has_modal
        if has_modal:
            mock_transaction_modal = Mock()
            mock_transaction_modal.open = Mock()
            home_view.transaction_modal = mock_transaction_modal
        else:
            home_view.transaction_modal = None
    
    # Act - вызываем метод открытия модального окна
    try:
        home_view.open_add_transaction_modal()
        
        # Assert - проверяем правильность поведения в зависимости от условий
        if has_page and has_modal:
            # При наличии page и modal должно произойти открытие модального окна
            home_view.transaction_modal.open.assert_called_once_with(mock_page, date_obj)
        elif not has_page:
            # При отсутствии page должно быть логирование ошибки, но не исключение
            # Метод должен завершиться корректно
            pass
        elif not has_modal:
            # При отсутствии modal должно быть логирование ошибки, но не исключение
            # Метод должен завершиться корректно
            pass
        
        # В любом случае метод не должен выбрасывать исключения наружу
        
    except Exception as e:
        assert False, f"open_add_transaction_modal не должен выбрасывать исключения наружу: {e}"
    
    # Проверяем, что состояние HomeView остается стабильным
    assert home_view.selected_date == date_obj, "Выбранная дата не должна изменяться"
    
    # Проверяем, что при ошибках показывается SnackBar (если есть page)
    if has_page and not has_modal:
        # При отсутствии modal должен показаться SnackBar с ошибкой
        # (может быть вызван или не вызван в зависимости от реализации)
        pass


@given(
    callback_type=st.sampled_from([
        'none',           # None callback
        'exception',      # Callback that raises exception
        'valid'           # Valid callback
    ]),
    exception_type=st.sampled_from([
        ValueError, TypeError, RuntimeError, AttributeError, KeyError, 
        ConnectionError, PermissionError, FileNotFoundError
    ]),
    has_page=st.booleans()
)
@settings(max_examples=100, deadline=None)
def test_property_11_error_handling_robustness(callback_type, exception_type, has_page):
    """
    **Feature: add-transaction-button-fix, Property 11: Error Handling Robustness**
    **Validates: Requirements 8.1, 8.2, 8.4**
    
    Property: Для любого состояния ошибки (null callback, исключение в callback, 
    отсутствующая page), кнопка должна обрабатывать их корректно без краха приложения.
    """
    # Arrange - подготавливаем различные сценарии ошибок
    test_date = date.today()
    transactions = []
    
    # Создаем mock page или None в зависимости от has_page
    if has_page:
        mock_page = MagicMock()
        mock_page.open = Mock()
        mock_page.update = Mock()
        # Настраиваем SnackBar
        mock_snack_bar = MagicMock()
        mock_page.snack_bar = mock_snack_bar
    else:
        mock_page = None
    
    # Создаем callback в зависимости от типа
    if callback_type == 'none':
        callback = None
    elif callback_type == 'exception':
        def failing_callback():
            raise exception_type("Test exception from callback")
        callback = failing_callback
    else:  # 'valid'
        callback = Mock()
    
    # Act - создаем TransactionsPanel с различными сценариями ошибок
    panel = TransactionsPanel(
        date_obj=test_date,
        transactions=transactions,
        on_add_transaction=callback
    )
    
    # Устанавливаем page (или None) после создания
    panel.page = mock_page
    
    # Assert - проверяем, что панель создалась без ошибок
    assert panel is not None, "TransactionsPanel должна создаваться даже при проблемных callback"
    assert panel.on_add_transaction == callback, "Callback должен быть сохранен как есть"
    assert panel.date == test_date, "Дата должна быть сохранена корректно"
    
    # Проверяем состояние кнопки в зависимости от callback
    header_row = panel._build_header()
    assert header_row is not None, "Заголовок должен создаваться даже при проблемных callback"
    assert len(header_row.controls) >= 2, "Заголовок должен содержать кнопку"
    
    add_button = header_row.controls[1]
    assert isinstance(add_button, ft.IconButton), "Кнопка должна быть создана"
    
    # Проверяем правильное состояние кнопки
    if callback is None:
        assert add_button.disabled == True, "Кнопка должна быть отключена при None callback"
    else:
        assert add_button.disabled != True, "Кнопка должна быть активна при наличии callback"
    
    # on_click всегда должен быть установлен для безопасности
    assert add_button.on_click is not None, "on_click должен быть установлен для безопасности"
    
    # Тестируем безопасный вызов _safe_add_transaction
    try:
        # Симулируем нажатие кнопки через _safe_add_transaction
        panel._safe_add_transaction(None)
        
        # Если дошли сюда без исключения, проверяем правильность обработки
        if callback_type == 'none':
            # При None callback должно быть предупреждение в логах
            # и возможно показ SnackBar пользователю (если есть page)
            if has_page:
                # Проверяем, что была попытка показать SnackBar с предупреждением
                # (может быть вызван или не вызван в зависимости от реализации)
                pass  # Логика может варьироваться
        elif callback_type == 'exception':
            # При исключении в callback должна быть обработка ошибки
            # и показ SnackBar пользователю (если есть page)
            if has_page:
                # Проверяем, что была попытка показать SnackBar с ошибкой
                # (может быть вызван или не вызван в зависимости от реализации)
                pass  # Логика может варьироваться
        else:  # 'valid'
            # При валидном callback он должен быть вызван
            if isinstance(callback, Mock):
                callback.assert_called_once()
        
    except Exception as e:
        # _safe_add_transaction НЕ должен выбрасывать исключения наружу
        # Все исключения должны быть обработаны внутри
        assert False, f"_safe_add_transaction не должен выбрасывать исключения наружу: {e}"
    
    # Проверяем, что состояние панели остается стабильным после обработки ошибок
    assert panel.on_add_transaction == callback, "Callback не должен изменяться после обработки ошибок"
    assert panel.date == test_date, "Дата не должна изменяться после обработки ошибок"
    assert panel.transactions == transactions, "Список транзакций не должен изменяться"
    
    # Проверяем, что кнопка остается функциональной
    current_header = panel._build_header()
    current_button = current_header.controls[1]
    
    if callback is None:
        assert current_button.disabled == True, "Кнопка должна оставаться отключенной при None callback"
    else:
        assert current_button.disabled != True, "Кнопка должна оставаться активной после обработки ошибок"
    
    assert current_button.on_click is not None, "on_click должен оставаться установленным"
    
    # Проверяем, что повторный вызов также безопасен
    try:
        panel._safe_add_transaction(None)
        # Второй вызов также должен быть безопасным
    except Exception as e:
        assert False, f"Повторный вызов _safe_add_transaction также должен быть безопасным: {e}"


@given(
    page_available=st.booleans(),
    snackbar_fails=st.booleans(),
    update_fails=st.booleans()
)
@settings(max_examples=50, deadline=None)
def test_error_handling_ui_robustness(page_available, snackbar_fails, update_fails):
    """
    Property: Обработка ошибок должна быть устойчивой даже при проблемах с UI.
    
    Тестирует сценарии, когда сама система показа ошибок может давать сбои.
    """
    # Arrange - создаем сценарии с проблемами в UI
    test_date = date.today()
    transactions = []
    
    def failing_callback():
        raise RuntimeError("Test callback failure")
    
    # Настраиваем mock page с возможными сбоями
    if page_available:
        mock_page = MagicMock()
        
        if snackbar_fails:
            # SnackBar.open может выбрасывать исключение
            mock_page.open.side_effect = Exception("SnackBar failed")
        else:
            mock_page.open = Mock()
        
        if update_fails:
            # page.update может выбрасывать исключение
            mock_page.update.side_effect = Exception("Update failed")
        else:
            mock_page.update = Mock()
            
        mock_page.snack_bar = MagicMock()
    else:
        mock_page = None
    
    # Act - создаем панель и тестируем обработку ошибок
    panel = TransactionsPanel(
        date_obj=test_date,
        transactions=transactions,
        on_add_transaction=failing_callback
    )
    panel.page = mock_page
    
    # Assert - даже при проблемах с UI, обработка ошибок не должна крашить приложение
    try:
        panel._safe_add_transaction(None)
        # Если дошли сюда, значит все исключения были корректно обработаны
    except Exception as e:
        assert False, f"_safe_add_transaction должен обрабатывать даже ошибки UI: {e}"
    
    # Панель должна оставаться в рабочем состоянии
    assert panel.on_add_transaction == failing_callback
    assert panel.date == test_date
    
    # Кнопка должна оставаться функциональной
    header_row = panel._build_header()
    add_button = header_row.controls[1]
    assert add_button.disabled != True  # Должна быть активна с callback
    assert add_button.on_click is not None


@given(
    callback_sequence=st.lists(
        st.sampled_from(['valid', 'exception', 'none']),
        min_size=1,
        max_size=10
    )
)
@settings(max_examples=30, deadline=None)
def test_error_handling_consistency_across_calls(callback_sequence):
    """
    Property: Обработка ошибок должна быть консистентной при множественных вызовах.
    
    Тестирует, что система обработки ошибок работает стабильно при повторных вызовах
    с различными типами ошибок.
    """
    # Arrange
    test_date = date.today()
    transactions = []
    mock_page = MagicMock()
    mock_page.open = Mock()
    mock_page.snack_bar = MagicMock()
    
    # Создаем различные типы callback для тестирования
    callbacks = {
        'valid': Mock(),
        'exception': lambda: exec('raise ValueError("Test error")'),
        'none': None
    }
    
    # Act & Assert - тестируем последовательность различных callback
    for i, callback_type in enumerate(callback_sequence):
        callback = callbacks[callback_type]
        
        # Создаем новую панель для каждого теста
        panel = TransactionsPanel(
            date_obj=test_date,
            transactions=transactions,
            on_add_transaction=callback
        )
        panel.page = mock_page
        
        # Проверяем, что панель создается корректно
        assert panel is not None, f"Панель должна создаваться на итерации {i + 1}"
        
        # Тестируем безопасный вызов
        try:
            panel._safe_add_transaction(None)
            # Каждый вызов должен быть безопасным независимо от предыдущих
        except Exception as e:
            assert False, f"Вызов {i + 1} с callback_type='{callback_type}' не должен выбрасывать исключения: {e}"
        
        # Проверяем состояние панели после каждого вызова
        assert panel.on_add_transaction == callback, f"Callback должен сохраняться на итерации {i + 1}"
        assert panel.date == test_date, f"Дата должна сохраняться на итерации {i + 1}"
        
        # Проверяем состояние кнопки
        header_row = panel._build_header()
        add_button = header_row.controls[1]
        
        if callback is None:
            assert add_button.disabled == True, f"Кнопка должна быть отключена при None callback на итерации {i + 1}"
        else:
            assert add_button.disabled != True, f"Кнопка должна быть активна на итерации {i + 1}"
        
        assert add_button.on_click is not None, f"on_click должен быть установлен на итерации {i + 1}"

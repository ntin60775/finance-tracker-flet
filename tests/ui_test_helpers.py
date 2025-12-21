"""
Вспомогательные функции для тестирования UI компонентов Finance Tracker.

Содержит:
- Assertion helpers для проверки состояния модальных окон
- Генераторы тестовых данных для транзакций
- Утилиты для работы с Flet UI компонентами
- Функции для проверки состояния кнопок и форм
"""
from unittest.mock import Mock, MagicMock
from typing import Optional, List, Dict, Any, Union
from datetime import date, datetime
from decimal import Decimal
import uuid
import flet as ft

from finance_tracker.models.models import (
    CategoryDB, TransactionDB, TransactionCreate, 
    PlannedTransactionDB, LenderDB, LoanDB
)
from finance_tracker.models.enums import (
    TransactionType, LenderType, LoanType, 
    LoanStatus, RecurrenceType
)


# =============================================================================
# Assertion Helpers для модальных окон
# =============================================================================

def assert_modal_opened(page_mock: MagicMock, modal_type: Optional[type] = None) -> None:
    """
    Проверяет, что модальное окно было открыто.
    
    Args:
        page_mock: Мок объекта page
        modal_type: Ожидаемый тип модального окна (опционально)
        
    Raises:
        AssertionError: Если модальное окно не было открыто или тип не совпадает
        
    Example:
        assert_modal_opened(mock_page, ft.AlertDialog)
    """
    # Проверяем, что page.open был вызван
    page_mock.open.assert_called()
    
    if modal_type is not None:
        # Получаем аргумент вызова page.open
        call_args = page_mock.open.call_args
        if call_args and call_args[0]:
            opened_dialog = call_args[0][0]
            assert isinstance(opened_dialog, modal_type), \
                f"Ожидался тип {modal_type.__name__}, получен {type(opened_dialog).__name__}"


def assert_modal_not_opened(page_mock: MagicMock) -> None:
    """
    Проверяет, что модальное окно не было открыто.
    
    Args:
        page_mock: Мок объекта page
        
    Raises:
        AssertionError: Если модальное окно было открыто
        
    Example:
        assert_modal_not_opened(mock_page)
    """
    page_mock.open.assert_not_called()


def assert_modal_closed(page_mock: MagicMock) -> None:
    """
    Проверяет, что модальное окно было закрыто.
    
    Args:
        page_mock: Мок объекта page
        
    Raises:
        AssertionError: Если модальное окно не было закрыто
        
    Example:
        assert_modal_closed(mock_page)
    """
    page_mock.close.assert_called()


def assert_modal_state(modal, is_open: bool, has_errors: bool = False) -> None:
    """
    Проверяет состояние модального окна.
    
    ВАЖНО: Используется СОВРЕМЕННЫЙ Flet Dialog API (>= 0.25.0):
    - page.open(dialog) - для открытия диалогов
    - page.close(dialog) - для закрытия диалогов
    
    Используется СОВРЕМЕННЫЙ Flet Dialog API (>= 0.25.0):
    - ✅ page.open(modal) - для открытия
    - ✅ page.close(modal) - для закрытия
    
    Args:
        modal: Экземпляр модального окна
        is_open: Ожидаемое состояние открытости
        has_errors: Ожидается ли наличие ошибок валидации
        
    Raises:
        AssertionError: Если состояние не соответствует ожидаемому
        
    Example:
        assert_modal_state(transaction_modal, is_open=True, has_errors=False)
    """
    # Проверяем наличие ошибок валидации
    if has_errors:
        if hasattr(modal, 'validation_errors'):
            assert len(modal.validation_errors) > 0, "Ожидались ошибки валидации, но их нет"
    else:
        # Проверяем отсутствие ошибок
        if hasattr(modal, 'validation_errors'):
            assert len(modal.validation_errors) == 0, f"Неожиданные ошибки валидации: {modal.validation_errors}"
    
    # Примечание: Проверка is_open должна выполняться через page.open/close вызовы
    # (современный Flet API >= 0.25.0)


def assert_form_field_value(field, expected_value: Any, field_name: str = "field") -> None:
    """
    Проверяет значение поля формы.
    
    Args:
        field: Поле формы (TextField, Dropdown, etc.)
        expected_value: Ожидаемое значение
        field_name: Название поля для сообщения об ошибке
        
    Raises:
        AssertionError: Если значение не соответствует ожидаемому
        
    Example:
        assert_form_field_value(modal.amount_field, "100.50", "amount")
    """
    actual_value = getattr(field, 'value', None)
    assert actual_value == expected_value, f"Поле {field_name}: ожидалось '{expected_value}', получено '{actual_value}'"


def assert_button_state(button, is_enabled: bool, button_name: str = "button") -> None:
    """
    Проверяет состояние кнопки (активна/неактивна).
    
    Args:
        button: Кнопка для проверки
        is_enabled: Ожидаемое состояние (True = активна, False = неактивна)
        button_name: Название кнопки для сообщения об ошибке
        
    Raises:
        AssertionError: Если состояние не соответствует ожидаемому
        
    Example:
        assert_button_state(modal.save_button, is_enabled=False, "save")
    """
    is_disabled = getattr(button, 'disabled', False)
    actual_enabled = not is_disabled
    assert actual_enabled == is_enabled, f"Кнопка {button_name}: ожидалось enabled={is_enabled}, получено {actual_enabled}"


def assert_snackbar_shown(page_mock: MagicMock, message_contains: Optional[str] = None) -> None:
    """
    Проверяет, что был показан SnackBar с определенным сообщением.
    
    Args:
        page_mock: Мок объекта page
        message_contains: Подстрока, которая должна содержаться в сообщении
        
    Raises:
        AssertionError: Если SnackBar не был показан или сообщение не содержит подстроку
        
    Example:
        assert_snackbar_shown(mock_page, "успешно сохранено")
    """
    page_mock.open.assert_called()
    
    if message_contains is not None:
        # Ищем вызов с SnackBar, содержащим нужное сообщение
        found = False
        for call in page_mock.open.call_args_list:
            if call[0]:  # Есть позиционные аргументы
                arg = call[0][0]
                if isinstance(arg, ft.SnackBar):
                    # Получаем текст из SnackBar
                    if hasattr(arg.content, 'value'):
                        text = arg.content.value
                        if message_contains.lower() in text.lower():
                            found = True
                            break
        
        assert found, f"SnackBar с сообщением, содержащим '{message_contains}', не найден"


# =============================================================================
# Генераторы тестовых данных
# =============================================================================

def create_test_category(
    category_type: TransactionType = TransactionType.EXPENSE,
    name: Optional[str] = None,
    is_system: bool = False
) -> CategoryDB:
    """
    Создает тестовую категорию.
    
    Args:
        category_type: Тип категории (доход/расход)
        name: Название категории (генерируется автоматически если None)
        is_system: Признак системной категории
        
    Returns:
        CategoryDB: Созданная категория
        
    Example:
        category = create_test_category(TransactionType.EXPENSE, "Тестовая категория")
    """
    if name is None:
        type_name = "Доход" if category_type == TransactionType.INCOME else "Расход"
        name = f"Тест {type_name} {uuid.uuid4().hex[:8]}"
    
    return CategoryDB(
        id=str(uuid.uuid4()),
        name=name,
        type=category_type,
        is_system=is_system,
        created_at=datetime.now()
    )


def create_test_transaction(
    amount: Optional[Decimal] = None,
    transaction_type: TransactionType = TransactionType.EXPENSE,
    category_id: Optional[str] = None,
    description: Optional[str] = None,
    transaction_date: Optional[date] = None
) -> TransactionDB:
    """
    Создает тестовую транзакцию.
    
    Args:
        amount: Сумма транзакции (генерируется автоматически если None)
        transaction_type: Тип транзакции
        category_id: ID категории (генерируется автоматически если None)
        description: Описание транзакции
        transaction_date: Дата транзакции (сегодня если None)
        
    Returns:
        TransactionDB: Созданная транзакция
        
    Example:
        transaction = create_test_transaction(Decimal('100.50'), TransactionType.EXPENSE)
    """
    if amount is None:
        amount = Decimal('100.00')
    
    if category_id is None:
        category_id = str(uuid.uuid4())
    
    if transaction_date is None:
        transaction_date = date.today()
    
    if description is None:
        description = f"Тестовая транзакция {uuid.uuid4().hex[:8]}"
    
    return TransactionDB(
        id=str(uuid.uuid4()),
        amount=amount,
        type=transaction_type,
        category_id=category_id,
        description=description,
        transaction_date=transaction_date,
        created_at=datetime.now()
    )


def create_test_transaction_create_data(
    amount: Optional[Decimal] = None,
    transaction_type: TransactionType = TransactionType.EXPENSE,
    category_id: Optional[str] = None,
    description: Optional[str] = None,
    transaction_date: Optional[date] = None
) -> TransactionCreate:
    """
    Создает тестовые данные для создания транзакции (Pydantic модель).
    
    Args:
        amount: Сумма транзакции
        transaction_type: Тип транзакции
        category_id: ID категории
        description: Описание транзакции
        transaction_date: Дата транзакции
        
    Returns:
        TransactionCreate: Данные для создания транзакции
        
    Example:
        data = create_test_transaction_create_data(Decimal('50.25'))
    """
    if amount is None:
        amount = Decimal('100.00')
    
    if category_id is None:
        category_id = str(uuid.uuid4())
    
    if transaction_date is None:
        transaction_date = date.today()
    
    return TransactionCreate(
        amount=amount,
        type=transaction_type,
        category_id=category_id,
        description=description,
        transaction_date=transaction_date
    )


def create_test_categories_list(
    expense_count: int = 3,
    income_count: int = 2
) -> Dict[str, List[CategoryDB]]:
    """
    Создает список тестовых категорий.
    
    Args:
        expense_count: Количество категорий расходов
        income_count: Количество категорий доходов
        
    Returns:
        Dict: Словарь с категориями по типам
        
    Example:
        categories = create_test_categories_list(expense_count=5, income_count=3)
    """
    expense_categories = []
    for i in range(expense_count):
        expense_categories.append(
            create_test_category(
                TransactionType.EXPENSE,
                f"Расход {i+1}",
                is_system=(i == 0)  # Первая категория системная
            )
        )
    
    income_categories = []
    for i in range(income_count):
        income_categories.append(
            create_test_category(
                TransactionType.INCOME,
                f"Доход {i+1}",
                is_system=(i == 0)  # Первая категория системная
            )
        )
    
    return {
        'expense': expense_categories,
        'income': income_categories,
        'all': expense_categories + income_categories
    }


def create_test_transactions_list(
    count: int = 5,
    category_ids: Optional[List[str]] = None,
    date_range_days: int = 30
) -> List[TransactionDB]:
    """
    Создает список тестовых транзакций.
    
    Args:
        count: Количество транзакций
        category_ids: Список ID категорий (генерируются автоматически если None)
        date_range_days: Диапазон дат в днях от сегодня назад
        
    Returns:
        List[TransactionDB]: Список созданных транзакций
        
    Example:
        transactions = create_test_transactions_list(count=10, date_range_days=7)
    """
    if category_ids is None:
        category_ids = [str(uuid.uuid4()) for _ in range(3)]
    
    transactions = []
    for i in range(count):
        # Чередуем типы транзакций
        transaction_type = TransactionType.EXPENSE if i % 2 == 0 else TransactionType.INCOME
        
        # Варьируем суммы
        amount = Decimal(str(50.0 + i * 25.5))
        
        # Варьируем даты в пределах диапазона
        days_back = i % date_range_days
        transaction_date = date.today()
        if days_back > 0:
            from datetime import timedelta
            transaction_date = transaction_date - timedelta(days=days_back)
        
        # Выбираем случайную категорию
        category_id = category_ids[i % len(category_ids)]
        
        transactions.append(
            create_test_transaction(
                amount=amount,
                transaction_type=transaction_type,
                category_id=category_id,
                description=f"Тестовая транзакция #{i+1}",
                transaction_date=transaction_date
            )
        )
    
    return transactions


# =============================================================================
# Утилиты для работы с UI компонентами
# =============================================================================

def simulate_button_click(button, event_data: Optional[Any] = None) -> None:
    """
    Симулирует нажатие на кнопку.
    
    Args:
        button: Кнопка для нажатия
        event_data: Данные события (обычно None для Flet)
        
    Example:
        simulate_button_click(modal.save_button)
    """
    if hasattr(button, 'on_click') and button.on_click:
        button.on_click(event_data)


def simulate_text_input(text_field, value: str) -> None:
    """
    Симулирует ввод текста в поле.
    
    Args:
        text_field: Текстовое поле
        value: Вводимое значение
        
    Example:
        simulate_text_input(modal.amount_field, "150.75")
    """
    text_field.value = value
    # Симулируем событие изменения, если есть обработчик
    if hasattr(text_field, 'on_change') and text_field.on_change:
        text_field.on_change(None)


def simulate_dropdown_selection(dropdown, value: Any) -> None:
    """
    Симулирует выбор значения в выпадающем списке.
    
    Args:
        dropdown: Выпадающий список
        value: Выбираемое значение
        
    Example:
        simulate_dropdown_selection(modal.category_dropdown, "category-id-123")
    """
    dropdown.value = value
    # Симулируем событие изменения, если есть обработчик
    if hasattr(dropdown, 'on_change') and dropdown.on_change:
        dropdown.on_change(None)


def get_button_from_container(container, button_index: int = 0):
    """
    Извлекает кнопку из контейнера по индексу.
    
    Args:
        container: Контейнер с кнопками
        button_index: Индекс кнопки в контейнере
        
    Returns:
        Кнопка или None если не найдена
        
    Example:
        add_button = get_button_from_container(header_row, 1)
    """
    if hasattr(container, 'controls') and len(container.controls) > button_index:
        return container.controls[button_index]
    return None


def find_control_by_type(container, control_type: type):
    """
    Находит первый контрол указанного типа в контейнере.
    
    Args:
        container: Контейнер для поиска
        control_type: Тип искомого контрола
        
    Returns:
        Найденный контрол или None
        
    Example:
        text_field = find_control_by_type(form_container, ft.TextField)
    """
    if hasattr(container, 'controls'):
        for control in container.controls:
            if isinstance(control, control_type):
                return control
            # Рекурсивный поиск в дочерних контейнерах
            if hasattr(control, 'controls'):
                found = find_control_by_type(control, control_type)
                if found:
                    return found
    return None


def extract_validation_errors(modal) -> Dict[str, str]:
    """
    Извлекает ошибки валидации из модального окна.
    
    Args:
        modal: Модальное окно для проверки
        
    Returns:
        Dict: Словарь с ошибками валидации по полям
        
    Example:
        errors = extract_validation_errors(transaction_modal)
        assert "amount" in errors
    """
    errors = {}
    
    # Проверяем различные способы хранения ошибок
    if hasattr(modal, 'validation_errors'):
        errors.update(modal.validation_errors)
    
    # Проверяем ошибки в отдельных полях
    error_fields = [
        ('amount_error', 'amount'),
        ('category_error', 'category'),
        ('description_error', 'description'),
        ('date_error', 'date')
    ]
    
    for error_attr, field_name in error_fields:
        if hasattr(modal, error_attr):
            error_field = getattr(modal, error_attr)
            if hasattr(error_field, 'value') and error_field.value:
                errors[field_name] = error_field.value
    
    return errors


# =============================================================================
# Вспомогательные функции для создания моков
# =============================================================================

def create_mock_callback() -> Mock:
    """
    Создает мок для callback функции.
    
    Returns:
        Mock: Настроенный мок callback
        
    Example:
        callback = create_mock_callback()
        panel = TransactionsPanel(on_add_transaction=callback)
    """
    return Mock()


def create_mock_db_context_manager(session: Optional[Mock] = None) -> Mock:
    """
    Создает мок для context manager get_db_session().
    
    Args:
        session: Мок сессии для возврата
        
    Returns:
        Mock: Мок context manager'а
        
    Example:
        mock_cm = create_mock_db_context_manager(mock_session)
        with patch('module.get_db_session', return_value=mock_cm):
            # Тестируемый код
    """
    if session is None:
        session = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        session.close = Mock()
        session.query = Mock()
    
    mock_cm = Mock()
    mock_cm.__enter__ = Mock(return_value=session)
    mock_cm.__exit__ = Mock(return_value=None)
    return mock_cm


def setup_mock_service_responses(
    mock_service: Mock,
    return_values: Dict[str, Any]
) -> None:
    """
    Настраивает ответы мок сервиса для различных методов.
    
    Args:
        mock_service: Мок сервиса
        return_values: Словарь с возвращаемыми значениями по методам
        
    Example:
        setup_mock_service_responses(mock_category_service, {
            'get_all_categories': [category1, category2],
            'create_category': new_category
        })
    """
    for method_name, return_value in return_values.items():
        if hasattr(mock_service, method_name):
            getattr(mock_service, method_name).return_value = return_value
        else:
            setattr(mock_service, method_name, Mock(return_value=return_value))
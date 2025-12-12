"""
Генераторы данных для property-based тестирования с Hypothesis.

Содержит стратегии генерации для:
- Финансовых данных (суммы, даты, описания)
- UI данных (состояния кнопок, callback функций)
- Транзакций и категорий
- Граничных случаев и ошибок
"""
from hypothesis import strategies as st
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
import uuid

from finance_tracker.models.enums import TransactionType, LenderType, LoanType


# =============================================================================
# Базовые генераторы для финансовых данных
# =============================================================================

def valid_amounts() -> st.SearchStrategy[Decimal]:
    """
    Генерирует валидные суммы для транзакций.
    
    Returns:
        SearchStrategy[Decimal]: Стратегия для положительных сумм от 0.01 до 999999.99
        
    Example:
        @given(amount=valid_amounts())
        def test_transaction_amount(amount):
            assert amount > 0
    """
    return st.decimals(
        min_value=Decimal('0.01'),
        max_value=Decimal('999999.99'),
        places=2
    )


@st.composite
def invalid_amounts(draw) -> Decimal:
    """
    Генерирует невалидные суммы для тестирования ошибок.
    
    Returns:
        Decimal: Отрицательная сумма или ноль
        
    Example:
        @given(amount=invalid_amounts())
        def test_invalid_transaction_amount(amount):
            with pytest.raises(ValidationError):
                TransactionCreate(amount=amount, ...)
    """
    return draw(st.one_of(
        st.decimals(max_value=Decimal('0'), places=2),  # Отрицательные и ноль
        st.decimals(min_value=Decimal('-999999.99'), max_value=Decimal('-0.01'), places=2)
    ))


@st.composite
def transaction_dates(draw) -> date:
    """
    Генерирует валидные даты для транзакций.
    
    Returns:
        date: Дата от 2020-01-01 до сегодня
        
    Example:
        @given(transaction_date=transaction_dates())
        def test_transaction_date(transaction_date):
            assert transaction_date <= date.today()
    """
    return draw(st.dates(
        min_value=date(2020, 1, 1),
        max_value=date.today()
    ))


@st.composite
def future_dates(draw) -> date:
    """
    Генерирует будущие даты для тестирования ошибок.
    
    Returns:
        date: Дата от завтра до 2030-12-31
        
    Example:
        @given(future_date=future_dates())
        def test_future_transaction_date(future_date):
            # Должно вызывать ошибку валидации
            pass
    """
    tomorrow = date.today() + timedelta(days=1)
    return draw(st.dates(
        min_value=tomorrow,
        max_value=date(2030, 12, 31)
    ))


@st.composite
def transaction_descriptions(draw) -> Optional[str]:
    """
    Генерирует описания для транзакций.
    
    Returns:
        Optional[str]: Описание или None
        
    Example:
        @given(description=transaction_descriptions())
        def test_transaction_description(description):
            # Тест с различными описаниями
            pass
    """
    return draw(st.one_of(
        st.none(),
        st.text(min_size=1, max_size=500, alphabet=st.characters(
            blacklist_categories=['Cc'],  # Исключаем управляющие символы
            blacklist_characters=['\x00', '\n', '\r', '\t']
        ))
    ))


@st.composite
def category_names(draw) -> str:
    """
    Генерирует названия категорий.
    
    Returns:
        str: Валидное название категории
        
    Example:
        @given(name=category_names())
        def test_category_name(name):
            category = CategoryCreate(name=name, type=TransactionType.EXPENSE)
    """
    return draw(st.text(
        min_size=1,
        max_size=100,
        alphabet=st.characters(
            whitelist_categories=['Lu', 'Ll', 'Nd', 'Zs'],  # Буквы, цифры, пробелы
            whitelist_characters=['_', '-', '(', ')', '.', ',']
        )
    ).filter(lambda x: x.strip() != ''))  # Исключаем строки только из пробелов


def uuid_strings() -> st.SearchStrategy[str]:
    """
    Генерирует валидные UUID строки.
    
    Returns:
        SearchStrategy[str]: Стратегия для валидных UUID
        
    Example:
        @given(category_id=uuid_strings())
        def test_transaction_with_category_id(category_id):
            # Тест с валидным UUID
            pass
    """
    return st.just(str(uuid.uuid4()))


@st.composite
def invalid_uuid_strings(draw) -> str:
    """
    Генерирует невалидные UUID строки для тестирования ошибок.
    
    Returns:
        str: Невалидный UUID
        
    Example:
        @given(invalid_id=invalid_uuid_strings())
        def test_invalid_category_id(invalid_id):
            with pytest.raises(ValidationError):
                TransactionCreate(category_id=invalid_id, ...)
    """
    return draw(st.one_of(
        st.text(min_size=1, max_size=35),  # Слишком короткие
        st.text(min_size=37, max_size=50),  # Слишком длинные
        st.just("not-a-uuid"),
        st.just("12345678-1234-1234-1234-12345678901"),  # Неправильный формат
        st.just(""),  # Пустая строка
    ))


# =============================================================================
# Генераторы для UI данных
# =============================================================================

def button_states() -> st.SearchStrategy[bool]:
    """
    Генерирует состояния кнопок (активна/неактивна).
    
    Returns:
        SearchStrategy[bool]: Стратегия для состояний кнопок
        
    Example:
        @given(enabled=button_states())
        def test_button_state(enabled):
            button.disabled = not enabled
    """
    return st.booleans()


@st.composite
def callback_functions(draw) -> Optional[callable]:
    """
    Генерирует callback функции или None.
    
    Returns:
        Optional[callable]: Функция или None
        
    Example:
        @given(callback=callback_functions())
        def test_button_with_callback(callback):
            button = Button(on_click=callback)
    """
    return draw(st.one_of(
        st.none(),
        st.just(lambda: None),  # Простая функция
        st.just(lambda x: x),   # Функция с параметром
    ))


@st.composite
def form_field_values(draw) -> Dict[str, Any]:
    """
    Генерирует значения для полей формы транзакции.
    
    Returns:
        Dict[str, Any]: Словарь с значениями полей
        
    Example:
        @given(form_data=form_field_values())
        def test_form_validation(form_data):
            # Тест валидации формы с различными данными
            pass
    """
    return {
        'amount': draw(st.one_of(
            valid_amounts(),
            invalid_amounts(),
            st.text(),  # Нечисловые значения
            st.none()
        )),
        'category_id': draw(st.one_of(
            uuid_strings(),
            invalid_uuid_strings(),
            st.none()
        )),
        'description': draw(transaction_descriptions()),
        'transaction_date': draw(st.one_of(
            transaction_dates(),
            future_dates(),
            st.none()
        )),
        'type': draw(st.sampled_from(TransactionType))
    }


# =============================================================================
# Генераторы для комплексных объектов
# =============================================================================

@st.composite
def transaction_create_data(draw) -> Dict[str, Any]:
    """
    Генерирует валидные данные для создания транзакции.
    
    Returns:
        Dict[str, Any]: Данные для TransactionCreate
        
    Example:
        @given(data=transaction_create_data())
        def test_transaction_creation(data):
            transaction = TransactionCreate(**data)
    """
    return {
        'amount': draw(valid_amounts()),
        'type': draw(st.sampled_from(TransactionType)),
        'category_id': draw(uuid_strings()),
        'description': draw(transaction_descriptions()),
        'transaction_date': draw(transaction_dates())
    }


@st.composite
def category_data(draw) -> Dict[str, Any]:
    """
    Генерирует данные для создания категории.
    
    Returns:
        Dict[str, Any]: Данные для CategoryCreate
        
    Example:
        @given(data=category_data())
        def test_category_creation(data):
            category = CategoryCreate(**data)
    """
    return {
        'name': draw(category_names()),
        'type': draw(st.sampled_from(TransactionType)),
        'is_system': draw(st.booleans())
    }


@st.composite
def transaction_lists(draw, min_size: int = 0, max_size: int = 10) -> List[Dict[str, Any]]:
    """
    Генерирует списки транзакций.
    
    Args:
        min_size: Минимальный размер списка
        max_size: Максимальный размер списка
    
    Returns:
        List[Dict[str, Any]]: Список данных транзакций
        
    Example:
        @given(transactions=transaction_lists(min_size=1, max_size=5))
        def test_transaction_list_processing(transactions):
            # Тест обработки списка транзакций
            pass
    """
    return draw(st.lists(
        transaction_create_data(),
        min_size=min_size,
        max_size=max_size
    ))


@st.composite
def date_ranges(draw) -> Dict[str, date]:
    """
    Генерирует диапазоны дат.
    
    Returns:
        Dict[str, date]: Словарь с start_date и end_date
        
    Example:
        @given(date_range=date_ranges())
        def test_date_range_filtering(date_range):
            start, end = date_range['start_date'], date_range['end_date']
            assert start <= end
    """
    start_date = draw(st.dates(
        min_value=date(2020, 1, 1),
        max_value=date.today() - timedelta(days=1)
    ))
    
    end_date = draw(st.dates(
        min_value=start_date,
        max_value=date.today()
    ))
    
    return {
        'start_date': start_date,
        'end_date': end_date
    }


# =============================================================================
# Генераторы для граничных случаев
# =============================================================================

@st.composite
def edge_case_amounts(draw) -> Decimal:
    """
    Генерирует граничные случаи для сумм.
    
    Returns:
        Decimal: Граничные значения сумм
        
    Example:
        @given(amount=edge_case_amounts())
        def test_edge_case_amounts(amount):
            # Тест с граничными значениями
            pass
    """
    return draw(st.one_of(
        st.just(Decimal('0.01')),      # Минимальная сумма
        st.just(Decimal('999999.99')), # Максимальная сумма
        st.just(Decimal('0.00')),      # Ноль (невалидно)
        st.just(Decimal('1000000.00')), # Превышение лимита
        st.decimals(min_value=Decimal('0.01'), max_value=Decimal('0.99')),  # Мелкие суммы
        st.decimals(min_value=Decimal('100000'), max_value=Decimal('999999.99'))  # Крупные суммы
    ))


@st.composite
def edge_case_strings(draw) -> str:
    """
    Генерирует граничные случаи для строк.
    
    Returns:
        str: Граничные значения строк
        
    Example:
        @given(text=edge_case_strings())
        def test_edge_case_strings(text):
            # Тест с граничными строками
            pass
    """
    return draw(st.one_of(
        st.just(""),                    # Пустая строка
        st.just(" "),                   # Только пробел
        st.just("   "),                 # Несколько пробелов
        st.text(min_size=1, max_size=1), # Один символ
        st.text(min_size=500, max_size=500), # Максимальная длина
        st.just("Тест с русскими символами"),
        st.just("Test with English"),
        st.just("123456789"),           # Только цифры
        st.just("!@#$%^&*()"),         # Специальные символы
    ))


@st.composite
def error_scenarios(draw) -> Dict[str, Any]:
    """
    Генерирует сценарии ошибок для тестирования.
    
    Returns:
        Dict[str, Any]: Данные, которые должны вызывать ошибки
        
    Example:
        @given(error_data=error_scenarios())
        def test_error_handling(error_data):
            with pytest.raises(Exception):
                # Код, который должен вызвать ошибку
                pass
    """
    return draw(st.one_of(
        # Невалидные суммы
        st.fixed_dictionaries({
            'type': st.just('invalid_amount'),
            'amount': invalid_amounts(),
            'category_id': uuid_strings(),
            'transaction_date': transaction_dates()
        }),
        # Невалидные UUID
        st.fixed_dictionaries({
            'type': st.just('invalid_uuid'),
            'amount': valid_amounts(),
            'category_id': invalid_uuid_strings(),
            'transaction_date': transaction_dates()
        }),
        # Будущие даты
        st.fixed_dictionaries({
            'type': st.just('future_date'),
            'amount': valid_amounts(),
            'category_id': uuid_strings(),
            'transaction_date': future_dates()
        }),
        # Пустые обязательные поля
        st.fixed_dictionaries({
            'type': st.just('missing_required'),
            'amount': st.none(),
            'category_id': st.none(),
            'transaction_date': st.none()
        })
    ))


# =============================================================================
# Утилиты для генераторов
# =============================================================================

def assume_valid_transaction_data(data: Dict[str, Any]) -> bool:
    """
    Проверяет, что данные транзакции валидны для использования в тестах.
    
    Args:
        data: Данные транзакции для проверки
        
    Returns:
        bool: True если данные валидны
        
    Example:
        @given(data=transaction_create_data())
        def test_valid_transaction(data):
            assume(assume_valid_transaction_data(data))
            # Тест только с валидными данными
    """
    try:
        # Проверяем основные требования
        if not data.get('amount') or data['amount'] <= 0:
            return False
        
        if not data.get('category_id'):
            return False
        
        # Проверяем UUID
        uuid.UUID(data['category_id'])
        
        # Проверяем дату
        if data.get('transaction_date') and data['transaction_date'] > date.today():
            return False
        
        return True
    except (ValueError, TypeError, KeyError):
        return False


def filter_valid_amounts(amounts: List[Decimal]) -> List[Decimal]:
    """
    Фильтрует список сумм, оставляя только валидные.
    
    Args:
        amounts: Список сумм для фильтрации
        
    Returns:
        List[Decimal]: Отфильтрованный список валидных сумм
        
    Example:
        valid_amounts = filter_valid_amounts([Decimal('100'), Decimal('-50'), Decimal('0')])
        # Результат: [Decimal('100')]
    """
    return [amount for amount in amounts if amount > 0 and amount <= Decimal('999999.99')]


def generate_realistic_transaction_scenario() -> st.SearchStrategy[Dict[str, Any]]:
    """
    Генерирует реалистичные сценарии транзакций.
    
    Returns:
        SearchStrategy: Стратегия для генерации реалистичных данных
        
    Example:
        @given(scenario=generate_realistic_transaction_scenario())
        def test_realistic_scenario(scenario):
            # Тест с реалистичными данными
            pass
    """
    return st.fixed_dictionaries({
        'transactions': st.lists(
            transaction_create_data(),
            min_size=1,
            max_size=20
        ),
        'categories': st.lists(
            category_data(),
            min_size=3,
            max_size=10
        ),
        'date_range': date_ranges(),
        'user_actions': st.lists(
            st.sampled_from(['add', 'edit', 'delete', 'view']),
            min_size=1,
            max_size=10
        )
    })
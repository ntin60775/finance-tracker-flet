# Руководство по UI тестированию

Это руководство описывает использование вспомогательных функций для тестирования UI компонентов Finance Tracker.

## Обзор созданных файлов

### `conftest.py` - Фикстуры pytest
Расширенные фикстуры для тестирования:
- `mock_page` - Мок объекта Flet Page
- `mock_session` - Мок SQLAlchemy Session
- `sample_categories` - Тестовые категории в БД
- `sample_transactions` - Тестовые транзакции в БД

### `ui_test_helpers.py` - Вспомогательные функции
Содержит:
- **Assertion helpers** - функции для проверки состояния UI
- **Генераторы тестовых данных** - создание объектов для тестов
- **Утилиты UI** - симуляция пользовательских действий

### `property_generators.py` - Генераторы для Hypothesis
Стратегии генерации данных для property-based тестирования:
- Финансовые данные (суммы, даты, описания)
- UI данные (состояния кнопок, callback функций)
- Граничные случаи и ошибки

### `test_view_base.py` - Базовый класс для тестов
Расширенный базовый класс `ViewTestBase` с дополнительными методами для UI тестирования.

## Примеры использования

### 1. Тестирование кнопки с использованием фикстур

```python
import unittest
from unittest.mock import patch
from tests.test_view_base import ViewTestBase
from tests.ui_test_helpers import assert_modal_opened, simulate_button_click

class TestTransactionsPanel(ViewTestBase):
    def setUp(self):
        super().setUp()
        # Используем фикстуры из базового класса
        # self.page и self.mock_session уже доступны
        
    def test_add_button_opens_modal(self):
        """Тест открытия модального окна при нажатии кнопки."""
        # Arrange
        callback = self.create_mock_callback()
        panel = TransactionsPanel(on_add_transaction=callback)
        
        # Act
        add_button = panel._build_header().controls[1]
        simulate_button_click(add_button)
        
        # Assert
        callback.assert_called_once()
```

### 2. Использование генераторов тестовых данных

```python
from tests.ui_test_helpers import (
    create_test_category, create_test_transaction,
    create_test_categories_list
)

def test_with_generated_data():
    """Тест с сгенерированными данными."""
    # Создание одной категории
    category = create_test_category(
        category_type=TransactionType.EXPENSE,
        name="Тестовая категория"
    )
    
    # Создание транзакции
    transaction = create_test_transaction(
        amount=Decimal('150.50'),
        category_id=category.id
    )
    
    # Создание списка категорий
    categories = create_test_categories_list(
        expense_count=3,
        income_count=2
    )
```

### 3. Property-based тестирование

```python
from hypothesis import given
from tests.property_generators import (
    valid_amounts, transaction_dates, transaction_create_data
)

class TestTransactionProperties:
    @given(amount=valid_amounts())
    def test_valid_amount_property(self, amount):
        """Property: Любая валидная сумма должна проходить валидацию."""
        # Arrange
        modal = TransactionModal(mock_session, mock_callback)
        
        # Act
        modal.amount_field.value = str(amount)
        is_valid = modal._validate_amount()
        
        # Assert
        assert is_valid == True
    
    @given(data=transaction_create_data())
    def test_transaction_creation_property(self, data):
        """Property: Любые валидные данные должны создавать транзакцию."""
        # Test implementation
        pass
```

### 4. Assertion helpers для модальных окон

```python
from tests.ui_test_helpers import (
    assert_modal_opened, assert_modal_state,
    assert_form_field_value, assert_button_state
)

def test_modal_workflow(self):
    """Тест полного workflow модального окна."""
    # Arrange
    modal = TransactionModal(self.mock_session, self.mock_callback)
    
    # Act - открытие модального окна
    modal.open(self.page, date.today())
    
    # Assert - проверка открытия
    assert_modal_opened(self.page, ft.AlertDialog)
    assert_modal_state(modal, is_open=True, has_errors=False)
    
    # Act - заполнение формы
    simulate_text_input(modal.amount_field, "100.50")
    simulate_dropdown_selection(modal.category_dropdown, "category-id")
    
    # Assert - проверка значений полей
    assert_form_field_value(modal.amount_field, "100.50", "amount")
    assert_button_state(modal.save_button, is_enabled=True, "save")
```

### 5. Использование фикстур pytest

```python
def test_with_sample_data(sample_categories, sample_transactions):
    """Тест с использованием готовых тестовых данных."""
    # sample_categories содержит готовые категории в БД
    expense_categories = sample_categories['expense']
    income_categories = sample_categories['income']
    
    # sample_transactions содержит готовые транзакции в БД
    assert len(sample_transactions) == 3
    
    # Используем данные в тесте
    view = HomeView(mock_page, db_session)
    view.load_transactions(date.today())

def test_with_mocks(mock_page, mock_session):
    """Тест с использованием моков."""
    # mock_page и mock_session готовы к использованию
    view = SomeView(mock_page, mock_session)
    
    # Проверяем взаимодействие с моками
    view.some_action()
    mock_session.commit.assert_called_once()
```

## Структура тестового файла

Рекомендуемая структура для новых тестовых файлов:

```python
"""
Тесты для [ComponentName].
"""
import unittest
from unittest.mock import Mock, patch
from tests.test_view_base import ViewTestBase
from tests.ui_test_helpers import (
    assert_modal_opened, create_test_category,
    simulate_button_click
)

class Test[ComponentName](ViewTestBase):
    """Тесты для [ComponentName]."""
    
    def setUp(self):
        """Настройка перед каждым тестом."""
        super().setUp()
        # Дополнительная настройка если нужна
        
    def test_initialization(self):
        """Тест инициализации компонента."""
        # Arrange, Act, Assert
        pass
        
    def test_user_interaction(self):
        """Тест пользовательского взаимодействия."""
        # Arrange, Act, Assert
        pass

# Property-based тесты в отдельном классе
class Test[ComponentName]Properties:
    """Property-based тесты для [ComponentName]."""
    
    @given(data=some_generator())
    def test_some_property(self, data):
        """
        **Feature: feature_name, Property N: description**
        **Validates: Requirements X.Y**
        """
        # Property test implementation
        pass
```

## Лучшие практики

### 1. Использование базового класса
- Наследуйтесь от `ViewTestBase` для UI тестов
- Используйте методы `create_mock_page()` и `create_mock_session()`
- Применяйте `add_patcher()` для автоматической очистки патчей

### 2. Генерация тестовых данных
- Используйте `create_test_*` функции для создания объектов
- Применяйте фикстуры `sample_categories` и `sample_transactions` для готовых данных
- Для property-based тестов используйте генераторы из `property_generators.py`

### 3. Проверка состояния UI
- Используйте `assert_*` функции для проверки состояния
- Применяйте `simulate_*` функции для имитации пользовательских действий
- Проверяйте как успешные, так и ошибочные сценарии

### 4. Изоляция тестов
- Каждый тест должен быть независимым
- Используйте моки для внешних зависимостей
- Очищайте состояние после каждого теста

### 5. Читаемость тестов
- Используйте описательные имена тестов
- Следуйте паттерну Arrange-Act-Assert
- Добавляйте комментарии для сложной логики

## Запуск тестов

```bash
# Запуск всех UI тестов
pytest tests/test_*_view.py tests/test_*_modal.py -v

# Запуск property-based тестов
pytest tests/test_*_properties.py -v

# Запуск с покрытием кода
pytest tests/ --cov=src/finance_tracker --cov-report=html

# Запуск конкретного теста
pytest tests/test_transaction_modal.py::TestTransactionModal::test_save_button -v
```

## Отладка тестов

### Проблемы с моками
```python
# Проверка вызовов мока
print(mock_object.call_args_list)
print(mock_object.call_count)

# Сброс мока
mock_object.reset_mock()
```

### Проблемы с фикстурами
```python
# Проверка содержимого БД
def test_debug_db(db_session):
    categories = db_session.query(CategoryDB).all()
    print(f"Categories in DB: {len(categories)}")
    for cat in categories:
        print(f"  {cat.name} ({cat.type})")
```

### Проблемы с Hypothesis
```python
# Добавление отладочной информации
@given(data=some_generator())
def test_with_debug(data):
    print(f"Generated data: {data}")
    # Test logic
```

Это руководство поможет эффективно использовать созданные вспомогательные функции для тестирования UI компонентов Finance Tracker.
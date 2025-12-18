# UI Testing Guidelines

## Overview

Руководство по тестированию пользовательского интерфейса в Finance Tracker Flet. Описывает best practices, паттерны и подходы для тестирования UI компонентов, модальных окон и пользовательских взаимодействий.

## UI Testing Philosophy

**Принципы UI тестирования:**
1. **Изоляция** - каждый тест должен быть независимым
2. **Реалистичность** - тесты должны имитировать реальное поведение пользователя
3. **Стабильность** - тесты не должны зависеть от внешних факторов
4. **Читаемость** - тесты должны быть понятными как документация
5. **Скорость** - тесты должны выполняться быстро для частого запуска

## Test Structure Patterns

### View Component Testing

**Базовый паттерн для тестирования View:**
```python
class TestHomeView(unittest.TestCase):
    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_page = MagicMock()
        self.mock_session = Mock()
        self.view = HomeView(self.mock_page, self.mock_session)
    
    def test_initialization(self):
        """Тест инициализации View."""
        # Проверяем создание основных компонентов
        self.assertIsNotNone(self.view.calendar_widget)
        self.assertIsNotNone(self.view.transactions_panel)
        
    def test_button_interaction(self):
        """Тест взаимодействия с кнопкой."""
        # Arrange - подготовка
        callback_called = False
        def mock_callback():
            nonlocal callback_called
            callback_called = True
            
        # Act - действие
        self.view.on_add_transaction = mock_callback
        self.view.open_add_transaction_modal()
        
        # Assert - проверка
        self.assertTrue(callback_called)
```

### Modal Testing Pattern

**Паттерн для тестирования модальных окон:**
```python
class TestTransactionModal(unittest.TestCase):
    def setUp(self):
        self.mock_page = MagicMock()
        self.mock_session = Mock()
        self.modal = TransactionModal(self.mock_session, self.mock_callback)
    
    def test_modal_opening(self):
        """Тест открытия модального окна."""
        test_date = date(2024, 12, 11)
        
        self.modal.open(self.mock_page, test_date)
        
        # Проверяем предустановку даты
        self.assertEqual(self.modal.date_field.value, "2024-12-11")
        # Проверяем вызов page.open()
        self.mock_page.open.assert_called_once()
    
    def test_form_validation(self):
        """Тест валидации формы."""
        # Тест с невалидными данными
        self.modal.amount_field.value = "-100"
        self.modal.category_dropdown.value = None
        
        is_valid = self.modal._validate_form()
        
        self.assertFalse(is_valid)
        self.assertTrue(self.modal.save_button.disabled)
        
    def test_successful_save(self):
        """Тест успешного сохранения."""
        # Подготовка валидных данных
        self.modal.amount_field.value = "100.50"
        self.modal.category_dropdown.value = "1"
        self.modal.description_field.value = "Test transaction"
        
        # Мокируем успешное сохранение
        with patch('finance_tracker.services.transaction_service.create_transaction') as mock_create:
            mock_create.return_value = Mock(id="test-uuid")
            
            self.modal._save_transaction()
            
            # Проверяем вызов сервиса
            mock_create.assert_called_once()
            # Проверяем закрытие модального окна
            self.assertFalse(self.modal.open)
```

### Button Testing Patterns

**Специализированные паттерны для тестирования кнопок:**

```python
def test_add_transaction_button_attributes(self):
    """Тест атрибутов кнопки добавления транзакции."""
    panel = TransactionsPanel(
        date_obj=date.today(),
        transactions=[],
        on_add_transaction=Mock()
    )
    
    # Получаем кнопку из заголовка
    header_row = panel._build_header()
    add_button = header_row.controls[1]  # Вторая кнопка в заголовке
    
    # Проверяем атрибуты кнопки
    self.assertEqual(add_button.icon, ft.Icons.ADD)
    self.assertEqual(add_button.tooltip, "Добавить транзакцию")
    self.assertEqual(add_button.bgcolor, ft.Colors.PRIMARY)
    self.assertIsNotNone(add_button.on_click)

def test_button_click_callback(self):
    """Тест вызова callback при нажатии кнопки."""
    mock_callback = Mock()
    panel = TransactionsPanel(
        date_obj=date.today(),
        transactions=[],
        on_add_transaction=mock_callback
    )
    
    # Симулируем нажатие кнопки
    header_row = panel._build_header()
    add_button = header_row.controls[1]
    add_button.on_click(None)  # Flet передает event, но мы его не используем
    
    # Проверяем вызов callback
    mock_callback.assert_called_once()

@given(st.booleans())
def test_button_state_property(enabled):
    """Property: Кнопка должна корректно отражать свое состояние."""
    panel = TransactionsPanel(
        date_obj=date.today(),
        transactions=[],
        on_add_transaction=Mock() if enabled else None
    )
    
    header_row = panel._build_header()
    add_button = header_row.controls[1]
    
    if enabled:
        assert add_button.disabled != True  # Кнопка активна
        assert add_button.on_click is not None
    else:
        # При отсутствии callback кнопка должна быть безопасной
        assert add_button.on_click is not None  # Но не None для избежания ошибок
```

## Property-Based UI Testing

### UI Property Patterns

**Универсальные свойства для UI компонентов:**

```python
@given(st.dates(), st.lists(st.text()))
def test_view_initialization_property(date_obj, transaction_descriptions):
    """Property: View должен инициализироваться с любыми валидными данными."""
    mock_transactions = [
        Mock(description=desc, amount=Decimal('100'), type=TransactionType.INCOME)
        for desc in transaction_descriptions
    ]
    
    view = HomeView(Mock(), Mock())
    view.update_transactions(date_obj, mock_transactions, [])
    
    # View должен обработать любые валидные данные без ошибок
    assert view.selected_date == date_obj
    assert len(view.transactions_panel.transactions) == len(mock_transactions)

@given(st.decimals(min_value=Decimal('0.01'), max_value=Decimal('999999.99')))
def test_amount_validation_property(amount):
    """Property: Любая положительная сумма должна проходить валидацию."""
    modal = TransactionModal(Mock(), Mock())
    modal.amount_field.value = str(amount)
    
    validation_result = modal._validate_amount()
    
    assert validation_result.is_valid == True
    assert len(validation_result.errors) == 0

@given(st.text(min_size=1, max_size=500))
def test_description_handling_property(description):
    """Property: Любое валидное описание должно обрабатываться корректно."""
    modal = TransactionModal(Mock(), Mock())
    modal.description_field.value = description
    
    # Описание не должно вызывать ошибок валидации
    validation_result = modal._validate_description()
    
    assert validation_result.is_valid == True
```

### Error Handling Properties

**Свойства для обработки ошибок:**

```python
@given(st.one_of(st.none(), st.text()))
def test_null_callback_handling_property(callback_value):
    """Property: Компонент должен безопасно обрабатывать null callback."""
    callback = Mock() if callback_value else None
    
    panel = TransactionsPanel(
        date_obj=date.today(),
        transactions=[],
        on_add_transaction=callback
    )
    
    # Компонент должен создаться без ошибок
    assert panel is not None
    
    # Нажатие кнопки не должно вызывать исключений
    try:
        header_row = panel._build_header()
        add_button = header_row.controls[1]
        add_button.on_click(None)
        # Если callback None, ничего не должно произойти
        # Если callback есть, он должен быть вызван
        if callback:
            callback.assert_called_once()
    except Exception as e:
        pytest.fail(f"Button click with callback={callback_value} raised {e}")
```

## Mock Strategies

### Flet Page Mocking

**Стратегии мокирования Flet Page:**

```python
def create_mock_page():
    """Создает полностью настроенный mock объект для Flet Page."""
    mock_page = MagicMock()
    
    # Настройка основных методов
    mock_page.open = Mock()
    mock_page.close = Mock()
    mock_page.update = Mock()
    mock_page.add = Mock()
    mock_page.remove = Mock()
    
    # Настройка свойств
    mock_page.width = 1200
    mock_page.height = 800
    mock_page.theme_mode = "light"
    
    # Настройка диалогов
    mock_page.dialog = None
    mock_page.snack_bar = None
    
    return mock_page

def create_mock_session():
    """Создает mock объект для database session."""
    mock_session = MagicMock()
    
    # Настройка основных методов
    mock_session.add = Mock()
    mock_session.commit = Mock()
    mock_session.rollback = Mock()
    mock_session.query = Mock()
    mock_session.close = Mock()
    
    # Настройка context manager
    mock_session.__enter__ = Mock(return_value=mock_session)
    mock_session.__exit__ = Mock(return_value=None)
    
    return mock_session
```

### Service Mocking

**Мокирование сервисов для изоляции UI тестов:**

```python
@patch('finance_tracker.services.transaction_service.create_transaction')
@patch('finance_tracker.services.category_service.get_categories')
def test_modal_with_mocked_services(mock_get_categories, mock_create_transaction):
    """Тест модального окна с мокированными сервисами."""
    # Настройка mock данных
    mock_categories = [
        Mock(id="cat1", name="Еда", type=TransactionType.EXPENSE),
        Mock(id="cat2", name="Зарплата", type=TransactionType.INCOME)
    ]
    mock_get_categories.return_value = mock_categories
    
    mock_transaction = Mock(id="trans1", amount=Decimal('100.50'))
    mock_create_transaction.return_value = mock_transaction
    
    # Тест
    modal = TransactionModal(Mock(), Mock())
    modal.open(Mock(), date.today())
    
    # Проверяем загрузку категорий
    mock_get_categories.assert_called_once()
    assert len(modal.category_dropdown.options) == 2
    
    # Симулируем сохранение
    modal.amount_field.value = "100.50"
    modal.category_dropdown.value = "cat1"
    modal._save_transaction()
    
    # Проверяем вызов сервиса создания
    mock_create_transaction.assert_called_once()
```

## Integration Testing Patterns

### End-to-End UI Scenarios

**Паттерны для интеграционного тестирования UI:**

```python
def test_complete_transaction_creation_flow(self):
    """Интеграционный тест: полный сценарий создания транзакции."""
    # Arrange - подготовка реальных компонентов
    with get_db() as session:
        # Создаем реальную категорию в БД
        category = CategoryDB(
            id=str(uuid4()),
            name="Тестовая категория",
            type=TransactionType.EXPENSE
        )
        session.add(category)
        session.commit()
        
        # Создаем реальные UI компоненты
        mock_page = create_mock_page()
        home_view = HomeView(mock_page, session)
        
        # Act - выполнение полного сценария
        # 1. Нажатие кнопки добавления
        home_view.open_add_transaction_modal()
        
        # 2. Заполнение формы
        modal = home_view.transaction_modal
        modal.amount_field.value = "150.75"
        modal.category_dropdown.value = str(category.id)
        modal.description_field.value = "Интеграционный тест"
        modal.date_field.value = "2024-12-11"
        
        # 3. Сохранение транзакции
        modal._save_transaction()
        
        # Assert - проверка результатов
        # Проверяем создание транзакции в БД
        transactions = session.query(TransactionDB).all()
        self.assertEqual(len(transactions), 1)
        
        created_transaction = transactions[0]
        self.assertEqual(created_transaction.amount, Decimal('150.75'))
        self.assertEqual(created_transaction.category_id, str(category.id))
        self.assertEqual(created_transaction.description, "Интеграционный тест")
        
        # Проверяем закрытие модального окна
        self.assertFalse(modal.open)
        
        # Проверяем обновление UI
        mock_page.update.assert_called()
```

## Error Scenarios Testing

### UI Error Handling

**Тестирование обработки ошибок в UI:**

```python
def test_network_error_handling(self):
    """Тест обработки сетевых ошибок."""
    with patch('finance_tracker.services.transaction_service.create_transaction') as mock_create:
        # Симулируем сетевую ошибку
        mock_create.side_effect = ConnectionError("Network unavailable")
        
        modal = TransactionModal(Mock(), Mock())
        modal.amount_field.value = "100"
        modal.category_dropdown.value = "cat1"
        
        # Попытка сохранения должна обработать ошибку
        modal._save_transaction()
        
        # Проверяем отображение ошибки пользователю
        self.assertTrue(modal.error_message.visible)
        self.assertIn("Ошибка сети", modal.error_message.value)
        
        # Модальное окно должно остаться открытым
        self.assertTrue(modal.open)

def test_validation_error_display(self):
    """Тест отображения ошибок валидации."""
    modal = TransactionModal(Mock(), Mock())
    
    # Вводим невалидные данные
    modal.amount_field.value = "abc"  # Не число
    modal.category_dropdown.value = None  # Не выбрана категория
    
    # Попытка сохранения
    modal._save_transaction()
    
    # Проверяем отображение ошибок
    self.assertTrue(modal.amount_error.visible)
    self.assertTrue(modal.category_error.visible)
    self.assertIn("Некорректная сумма", modal.amount_error.value)
    self.assertIn("Выберите категорию", modal.category_error.value)
    
    # Кнопка сохранения должна быть неактивна
    self.assertTrue(modal.save_button.disabled)
```

## Performance Testing

### UI Performance Guidelines

**Рекомендации по тестированию производительности UI:**

```python
def test_large_transaction_list_performance(self):
    """Тест производительности с большим списком транзакций."""
    import time
    
    # Создаем большой список транзакций
    large_transaction_list = [
        Mock(
            id=f"trans-{i}",
            amount=Decimal(str(i * 10.5)),
            description=f"Transaction {i}",
            type=TransactionType.EXPENSE
        )
        for i in range(1000)
    ]
    
    # Измеряем время обновления UI
    start_time = time.time()
    
    panel = TransactionsPanel(
        date_obj=date.today(),
        transactions=large_transaction_list,
        on_add_transaction=Mock()
    )
    panel._update_view()
    
    end_time = time.time()
    update_time = end_time - start_time
    
    # UI должен обновляться быстро даже с большим количеством данных
    self.assertLess(update_time, 1.0, "UI update took too long")

@pytest.mark.slow
def test_modal_opening_performance(self):
    """Тест производительности открытия модального окна."""
    modal = TransactionModal(Mock(), Mock())
    
    # Измеряем время открытия модального окна
    start_time = time.time()
    
    for _ in range(100):
        modal.open(Mock(), date.today())
        modal.close()
    
    end_time = time.time()
    avg_time = (end_time - start_time) / 100
    
    # Открытие модального окна должно быть быстрым
    self.assertLess(avg_time, 0.1, "Modal opening is too slow")
```

## Adding New Tests to the System

### Step-by-Step Guide for Creating New Tests

#### 1. Определение типа теста

**Выберите подходящий тип теста:**
- **Unit тест** - для изолированного тестирования одного компонента
- **Property-based тест** - для проверки универсальных свойств
- **Integration тест** - для тестирования взаимодействия компонентов
- **UI тест** - для тестирования пользовательского интерфейса

#### 2. Выбор местоположения файла

**Следуйте конвенции именования:**
```
tests/
├── test_*_service.py        # Тесты сервисов
├── test_*_view.py           # Тесты View компонентов  
├── test_*_modal.py          # Тесты модальных окон
├── test_*_properties.py     # Property-based тесты
├── test_integration*.py     # Интеграционные тесты
└── test_*.py               # Другие тесты
```

**Примеры правильного именования:**
- `test_transaction_service.py` - тесты для TransactionService
- `test_home_view.py` - тесты для HomeView
- `test_transaction_modal.py` - тесты для TransactionModal
- `test_loan_properties.py` - property-based тесты для кредитов

#### 3. Создание нового тестового файла

**Шаблон для unit теста:**
```python
"""
Тесты для [ComponentName].
"""
import unittest
from unittest.mock import Mock, MagicMock, patch
import datetime
from decimal import Decimal

# Импорты тестируемого компонента
from finance_tracker.views.home_view import HomeView
from finance_tracker.models.enums import TransactionType

class Test[ComponentName](unittest.TestCase):
    """Тесты для [ComponentName]."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_page = MagicMock()
        self.mock_session = Mock()
        # Инициализация тестируемого компонента
        self.component = ComponentName(self.mock_page, self.mock_session)

    def tearDown(self):
        """Очистка после каждого теста."""
        # Освобождение ресурсов если необходимо
        pass
        
    def test_initialization(self):
        """Тест инициализации компонента."""
        # Arrange, Act, Assert
        self.assertIsNotNone(self.component)
        
    def test_specific_functionality(self):
        """Тест конкретной функциональности."""
        # Arrange - подготовка
        expected_result = "expected_value"
        
        # Act - выполнение
        actual_result = self.component.some_method()
        
        # Assert - проверка
        self.assertEqual(actual_result, expected_result)

if __name__ == '__main__':
    unittest.main()
```

**Шаблон для property-based теста:**
```python
"""
Property-based тесты для [Domain].
"""
import pytest
from hypothesis import given, strategies as st, assume
from decimal import Decimal
from datetime import date

from finance_tracker.models.models import TransactionCreate
from finance_tracker.models.enums import TransactionType

class Test[Domain]Properties:
    """Property-based тесты для [Domain]."""

    @given(st.decimals(min_value=Decimal('0.01'), max_value=Decimal('999999.99')))
    def test_property_name(self, amount):
        """
        **Feature: [feature_name], Property [number]: [property_description]**
        **Validates: Requirements [requirement_numbers]**
        
        Property: [Описание универсального свойства]
        """
        # Arrange - подготовка с использованием сгенерированных данных
        
        # Act - выполнение операции
        
        # Assert - проверка свойства
        assert condition_that_should_always_be_true
```

#### 4. Добавление фикстур и вспомогательных функций

**Если нужны новые фикстуры, добавьте их в `conftest.py`:**
```python
@pytest.fixture
def mock_[component_name]():
    """Mock объект для [ComponentName]."""
    mock_obj = MagicMock()
    # Настройка mock объекта
    return mock_obj

@pytest.fixture
def sample_[data_type]_data():
    """Образцы данных для тестирования [DataType]."""
    return [
        # Тестовые данные
    ]
```

**Создайте вспомогательные функции в тестовом файле:**
```python
def create_test_[entity](self, **kwargs):
    """Создает тестовый объект [Entity] с заданными параметрами."""
    defaults = {
        'id': 'test-id',
        'name': 'Test Entity',
        # другие значения по умолчанию
    }
    defaults.update(kwargs)
    return EntityClass(**defaults)

def assert_[specific_condition](self, actual, expected):
    """Проверяет специфичное условие для тестов."""
    # Кастомная логика проверки
    self.assertEqual(actual.some_field, expected.some_field)
```

#### 5. Интеграция с существующей системой тестов

**Убедитесь, что новые тесты:**
1. **Используют существующие фикстуры** из `conftest.py`
2. **Следуют паттернам мокирования** из других тестов
3. **Используют правильные импорты** согласно структуре проекта
4. **Помечены соответствующими маркерами** pytest:
   ```python
   @pytest.mark.slow  # для медленных тестов
   @pytest.mark.integration  # для интеграционных тестов
   @pytest.mark.ui  # для UI тестов
   ```

#### 6. Запуск и проверка новых тестов

**Последовательность проверки:**
```bash
# 1. Запустите только новый тест
pytest tests/test_your_new_file.py -v

# 2. Проверьте, что тест проходит
pytest tests/test_your_new_file.py::TestYourClass::test_your_method -v

# 3. Запустите все тесты категории
pytest tests/test_*_view.py  # если это UI тест

# 4. Проверьте покрытие кода
pytest tests/test_your_new_file.py --cov=src/finance_tracker/your_module

# 5. Запустите полный набор тестов
pytest tests/ --tb=short
```

#### 7. Документирование новых тестов

**Обновите документацию:**
1. **Добавьте описание** в комментарии к тестовому классу
2. **Укажите связь с требованиями** в property-based тестах
3. **Обновите README.md** если добавлен новый тип тестов
4. **Добавьте примеры команд** для запуска новых тестов

### Checklist для добавления нового теста

**Перед созданием теста:**
- [ ] Определен тип теста (Unit/Property/Integration/UI)
- [ ] Выбрано правильное имя файла согласно конвенции
- [ ] Изучены существующие тесты аналогичного типа
- [ ] Определены необходимые mock объекты и фикстуры

**При создании теста:**
- [ ] Использован подходящий шаблон
- [ ] Добавлены docstring с описанием на русском языке
- [ ] Следуется паттерн Arrange-Act-Assert
- [ ] Используются существующие фикстуры из conftest.py
- [ ] Добавлены необходимые импорты

**После создания теста:**
- [ ] Тест проходит при изолированном запуске
- [ ] Тест проходит в составе всего набора тестов
- [ ] Проверено покрытие кода новым тестом
- [ ] Добавлены маркеры pytest если необходимо
- [ ] Обновлена документация при необходимости

**Для property-based тестов дополнительно:**
- [ ] Указана связь с требованиями в формате "**Validates: Requirements X.Y**"
- [ ] Добавлен комментарий с номером и описанием свойства
- [ ] Настроены подходящие генераторы данных
- [ ] Проверено, что тест находит ошибки при намеренном нарушении свойства

### Common Patterns для разных типов компонентов

#### Тестирование новых View компонентов

```python
class TestNewView(unittest.TestCase):
    def setUp(self):
        self.mock_page = create_mock_page()  # Используем helper из conftest
        self.mock_session = create_mock_session()
        
        # Мокируем зависимости View
        with patch('finance_tracker.views.new_view.SomeService') as mock_service:
            self.view = NewView(self.mock_page, self.mock_session)
            self.mock_service = mock_service

    def test_initialization(self):
        """Тест инициализации View."""
        # Стандартные проверки для всех View
        self.assertIsNotNone(self.view.page)
        self.assertIsNotNone(self.view.session)
        # Специфичные проверки для данного View
        
    def test_data_loading(self):
        """Тест загрузки данных."""
        # Мокируем данные сервиса
        self.mock_service.get_data.return_value = [test_data]
        
        # Вызываем загрузку данных
        self.view.load_data()
        
        # Проверяем вызов сервиса и обновление UI
        self.mock_service.get_data.assert_called_once()
```

#### Тестирование новых Service функций

```python
class TestNewService(unittest.TestCase):
    def setUp(self):
        # Используем in-memory БД из conftest
        self.session = create_test_db_session()
        
    def test_create_entity(self):
        """Тест создания новой сущности."""
        # Подготовка тестовых данных
        entity_data = EntityCreate(
            name="Test Entity",
            amount=Decimal('100.50')
        )
        
        # Вызов тестируемой функции
        result = create_entity(self.session, entity_data)
        
        # Проверки
        self.assertIsNotNone(result.id)
        self.assertEqual(result.name, "Test Entity")
        
        # Проверка сохранения в БД
        saved_entity = self.session.query(EntityDB).filter_by(id=result.id).first()
        self.assertIsNotNone(saved_entity)
```

#### Тестирование новых Modal компонентов

```python
class TestNewModal(unittest.TestCase):
    def setUp(self):
        self.mock_page = create_mock_page()
        self.mock_session = create_mock_session()
        self.mock_callback = Mock()
        self.modal = NewModal(self.mock_session, self.mock_callback)

    def test_modal_opening(self):
        """Тест открытия модального окна."""
        test_data = create_test_entity()
        
        self.modal.open(self.mock_page, test_data)
        
        # Проверяем предзаполнение полей
        self.assertEqual(self.modal.name_field.value, test_data.name)
        # Проверяем вызов page.open
        self.mock_page.open.assert_called_once()
        
    def test_form_validation(self):
        """Тест валидации формы."""
        # Тест с невалидными данными
        self.modal.name_field.value = ""  # Пустое обязательное поле
        
        is_valid = self.modal._validate_form()
        
        self.assertFalse(is_valid)
        self.assertTrue(self.modal.save_button.disabled)
```

## Delete Operations Testing

### Delete Button Testing Patterns

**Специализированные паттерны для тестирования кнопок удаления:**

```python
def test_delete_button_attributes(self):
    """Тест атрибутов кнопки удаления транзакции."""
    transaction = Mock(id="test-id", description="Test transaction")
    panel = TransactionsPanel(
        date_obj=date.today(),
        transactions=[transaction],
        on_delete_transaction=Mock()
    )
    
    # Получаем строку транзакции
    transaction_row = panel._build_transaction_row(transaction)
    delete_button = transaction_row.controls[-1]  # Последняя кнопка в строке
    
    # Проверяем атрибуты кнопки удаления
    self.assertEqual(delete_button.icon, ft.Icons.DELETE)
    self.assertEqual(delete_button.tooltip, "Удалить транзакцию")
    self.assertEqual(delete_button.bgcolor, ft.Colors.ERROR)
    self.assertIsNotNone(delete_button.on_click)

def test_delete_button_click_callback(self):
    """Тест вызова callback при нажатии кнопки удаления."""
    mock_delete_callback = Mock()
    transaction = Mock(id="test-id", description="Test transaction")
    
    panel = TransactionsPanel(
        date_obj=date.today(),
        transactions=[transaction],
        on_delete_transaction=mock_delete_callback
    )
    
    # Симулируем нажатие кнопки удаления
    transaction_row = panel._build_transaction_row(transaction)
    delete_button = transaction_row.controls[-1]
    delete_button.on_click(None)
    
    # Проверяем вызов callback с правильным ID транзакции
    mock_delete_callback.assert_called_once_with(transaction.id)

@given(st.booleans())
def test_delete_button_state_property(has_delete_permission):
    """Property: Кнопка удаления должна корректно отражать права доступа."""
    transaction = Mock(id="test-id", description="Test transaction")
    callback = Mock() if has_delete_permission else None
    
    panel = TransactionsPanel(
        date_obj=date.today(),
        transactions=[transaction],
        on_delete_transaction=callback
    )
    
    transaction_row = panel._build_transaction_row(transaction)
    delete_button = transaction_row.controls[-1]
    
    if has_delete_permission:
        assert delete_button.disabled != True  # Кнопка активна
        assert delete_button.on_click is not None
    else:
        # При отсутствии прав кнопка должна быть неактивна или скрыта
        assert delete_button.disabled == True or delete_button.visible == False
```

### Confirmation Dialog Testing

**Паттерны для тестирования диалогов подтверждения удаления:**

```python
class TestDeleteConfirmationDialog(unittest.TestCase):
    def setUp(self):
        self.mock_page = create_mock_page()
        self.mock_session = create_mock_session()
        self.mock_delete_callback = Mock()
        self.home_view = HomeView(self.mock_page, self.mock_session)

    def test_delete_confirmation_dialog_creation(self):
        """Тест создания диалога подтверждения удаления."""
        transaction = Mock(id="test-id", description="Test transaction", amount=Decimal('100.50'))
        
        # Вызываем показ диалога подтверждения
        self.home_view._show_delete_confirmation_dialog(transaction)
        
        # Проверяем создание диалога
        self.assertIsNotNone(self.home_view.delete_confirmation_dialog)
        
        # Проверяем содержимое диалога
        dialog = self.home_view.delete_confirmation_dialog
        self.assertIn("Удалить транзакцию", dialog.title.value)
        self.assertIn(transaction.description, dialog.content.value)
        self.assertIn(str(transaction.amount), dialog.content.value)
        
        # Проверяем наличие кнопок
        actions = dialog.actions
        self.assertEqual(len(actions), 2)  # Отмена и Удалить
        
        cancel_button = actions[0]
        delete_button = actions[1]
        
        self.assertEqual(cancel_button.text, "Отмена")
        self.assertEqual(delete_button.text, "Удалить")
        self.assertEqual(delete_button.bgcolor, ft.Colors.ERROR)

    def test_delete_confirmation_dialog_display(self):
        """Тест отображения диалога подтверждения."""
        transaction = Mock(id="test-id", description="Test transaction")
        
        self.home_view._show_delete_confirmation_dialog(transaction)
        
        # Проверяем вызов page.open() для отображения диалога
        self.mock_page.open.assert_called_once()
        
        # Проверяем, что диалог передан в page.open()
        call_args = self.mock_page.open.call_args[0]
        self.assertEqual(call_args[0], self.home_view.delete_confirmation_dialog)

    def test_delete_confirmation_cancel_action(self):
        """Тест отмены удаления в диалоге подтверждения."""
        transaction = Mock(id="test-id", description="Test transaction")
        
        self.home_view._show_delete_confirmation_dialog(transaction)
        dialog = self.home_view.delete_confirmation_dialog
        
        # Симулируем нажатие кнопки "Отмена"
        cancel_button = dialog.actions[0]
        cancel_button.on_click(None)
        
        # Проверяем закрытие диалога
        self.assertFalse(dialog.open)
        
        # Проверяем, что удаление НЕ было вызвано
        with patch('finance_tracker.services.transaction_service.delete_transaction') as mock_delete:
            mock_delete.assert_not_called()

    def test_delete_confirmation_confirm_action(self):
        """Тест подтверждения удаления в диалоге."""
        transaction = Mock(id="test-id", description="Test transaction")
        
        with patch('finance_tracker.services.transaction_service.delete_transaction') as mock_delete:
            mock_delete.return_value = True
            
            self.home_view._show_delete_confirmation_dialog(transaction)
            dialog = self.home_view.delete_confirmation_dialog
            
            # Симулируем нажатие кнопки "Удалить"
            delete_button = dialog.actions[1]
            delete_button.on_click(None)
            
            # Проверяем вызов сервиса удаления
            mock_delete.assert_called_once_with(self.mock_session, transaction.id)
            
            # Проверяем закрытие диалога
            self.assertFalse(dialog.open)

    @given(st.text(min_size=1, max_size=100))
    def test_delete_dialog_content_property(self, transaction_description):
        """Property: Диалог удаления должен отображать информацию о любой транзакции."""
        transaction = Mock(
            id="test-id", 
            description=transaction_description,
            amount=Decimal('100.50')
        )
        
        self.home_view._show_delete_confirmation_dialog(transaction)
        dialog = self.home_view.delete_confirmation_dialog
        
        # Диалог должен содержать описание транзакции
        assert transaction_description in dialog.content.value
        assert str(transaction.amount) in dialog.content.value
        assert dialog.title.value is not None
        assert len(dialog.actions) == 2
```

### Cascade Updates Testing

**Паттерны для тестирования каскадных обновлений после удаления:**

```python
class TestDeleteCascadeUpdates(unittest.TestCase):
    def setUp(self):
        self.mock_page = create_mock_page()
        self.mock_session = create_mock_session()
        self.home_view = HomeView(self.mock_page, self.mock_session)

    def test_delete_transaction_updates_transactions_panel(self):
        """Тест обновления панели транзакций после удаления."""
        # Подготовка: создаем транзакции
        transactions = [
            Mock(id="trans1", description="Transaction 1", amount=Decimal('100')),
            Mock(id="trans2", description="Transaction 2", amount=Decimal('200'))
        ]
        
        self.home_view.transactions_panel.transactions = transactions
        
        with patch('finance_tracker.services.transaction_service.delete_transaction') as mock_delete:
            with patch.object(self.home_view, '_refresh_data') as mock_refresh:
                mock_delete.return_value = True
                
                # Выполняем удаление
                self.home_view.delete_transaction("trans1")
                
                # Проверяем вызов обновления данных
                mock_refresh.assert_called_once()

    def test_delete_transaction_updates_calendar_widget(self):
        """Тест обновления календаря после удаления транзакции."""
        transaction_id = "test-trans-id"
        
        with patch('finance_tracker.services.transaction_service.delete_transaction') as mock_delete:
            with patch.object(self.home_view.calendar_widget, 'update_data') as mock_calendar_update:
                mock_delete.return_value = True
                
                # Выполняем удаление
                self.home_view.delete_transaction(transaction_id)
                
                # Проверяем обновление календаря
                mock_calendar_update.assert_called_once()

    def test_delete_transaction_updates_balance_forecast(self):
        """Тест обновления прогноза баланса после удаления."""
        transaction_id = "test-trans-id"
        
        with patch('finance_tracker.services.transaction_service.delete_transaction') as mock_delete:
            with patch('finance_tracker.services.balance_forecast_service.get_balance_forecast') as mock_forecast:
                mock_delete.return_value = True
                mock_forecast.return_value = []
                
                # Выполняем удаление
                self.home_view.delete_transaction(transaction_id)
                
                # Проверяем пересчет прогноза баланса
                mock_forecast.assert_called()

    def test_delete_transaction_updates_category_statistics(self):
        """Тест обновления статистики категорий после удаления."""
        transaction_id = "test-trans-id"
        
        with patch('finance_tracker.services.transaction_service.delete_transaction') as mock_delete:
            with patch('finance_tracker.services.category_service.get_category_statistics') as mock_stats:
                mock_delete.return_value = True
                mock_stats.return_value = {}
                
                # Выполняем удаление
                self.home_view.delete_transaction(transaction_id)
                
                # Проверяем пересчет статистики категорий
                mock_stats.assert_called()

    @given(st.lists(st.text(min_size=1), min_size=1, max_size=10))
    def test_cascade_updates_property(self, transaction_ids):
        """Property: Удаление любой транзакции должно вызывать каскадные обновления."""
        for transaction_id in transaction_ids:
            with patch('finance_tracker.services.transaction_service.delete_transaction') as mock_delete:
                with patch.object(self.home_view, '_refresh_data') as mock_refresh:
                    mock_delete.return_value = True
                    
                    # Выполняем удаление
                    self.home_view.delete_transaction(transaction_id)
                    
                    # Проверяем, что обновление данных было вызвано
                    assert mock_refresh.called
                    assert mock_delete.called
```

### Delete Error Handling Testing

**Паттерны для тестирования обработки ошибок при удалении:**

```python
class TestDeleteErrorHandling(unittest.TestCase):
    def setUp(self):
        self.mock_page = create_mock_page()
        self.mock_session = create_mock_session()
        self.home_view = HomeView(self.mock_page, self.mock_session)

    def test_delete_nonexistent_transaction_error(self):
        """Тест обработки ошибки при удалении несуществующей транзакции."""
        nonexistent_id = "nonexistent-id"
        
        with patch('finance_tracker.services.transaction_service.delete_transaction') as mock_delete:
            mock_delete.return_value = False  # Транзакция не найдена
            
            # Выполняем удаление
            result = self.home_view.delete_transaction(nonexistent_id)
            
            # Проверяем обработку ошибки
            self.assertFalse(result)
            
            # Проверяем отображение сообщения об ошибке
            self.mock_page.show_snack_bar.assert_called()
            snack_bar_call = self.mock_page.show_snack_bar.call_args[0][0]
            self.assertIn("не найдена", snack_bar_call.content.value.lower())

    def test_delete_database_error_handling(self):
        """Тест обработки ошибки базы данных при удалении."""
        transaction_id = "test-id"
        
        with patch('finance_tracker.services.transaction_service.delete_transaction') as mock_delete:
            mock_delete.side_effect = SQLAlchemyError("Database error")
            
            # Выполняем удаление
            result = self.home_view.delete_transaction(transaction_id)
            
            # Проверяем обработку ошибки
            self.assertFalse(result)
            
            # Проверяем отображение сообщения об ошибке
            self.mock_page.show_snack_bar.assert_called()
            snack_bar_call = self.mock_page.show_snack_bar.call_args[0][0]
            self.assertIn("ошибка", snack_bar_call.content.value.lower())

    def test_delete_rollback_on_error(self):
        """Тест отката изменений при ошибке удаления."""
        transaction_id = "test-id"
        
        with patch('finance_tracker.services.transaction_service.delete_transaction') as mock_delete:
            mock_delete.side_effect = SQLAlchemyError("Database error")
            
            # Сохраняем исходное состояние
            original_transactions = self.home_view.transactions_panel.transactions.copy()
            
            # Выполняем удаление (должно завершиться ошибкой)
            self.home_view.delete_transaction(transaction_id)
            
            # Проверяем, что состояние не изменилось
            self.assertEqual(
                self.home_view.transactions_panel.transactions,
                original_transactions
            )

    @given(st.text(min_size=1))
    def test_delete_error_handling_property(self, transaction_id):
        """Property: Любая ошибка при удалении должна обрабатываться корректно."""
        with patch('finance_tracker.services.transaction_service.delete_transaction') as mock_delete:
            mock_delete.side_effect = Exception("Unexpected error")
            
            # Удаление не должно вызывать необработанных исключений
            try:
                result = self.home_view.delete_transaction(transaction_id)
                # Результат должен быть False при ошибке
                assert result == False
            except Exception as e:
                pytest.fail(f"Delete operation raised unhandled exception: {e}")
```

### Integration Testing for Delete Operations

**Интеграционные тесты для операций удаления:**

```python
def test_complete_delete_transaction_flow(self):
    """Интеграционный тест: полный сценарий удаления транзакции."""
    # Arrange - подготовка реальных компонентов
    with get_db() as session:
        # Создаем реальную транзакцию в БД
        category = CategoryDB(
            id=str(uuid4()),
            name="Тестовая категория",
            type=TransactionType.EXPENSE
        )
        session.add(category)
        
        transaction = TransactionDB(
            id=str(uuid4()),
            amount=Decimal('150.75'),
            description="Транзакция для удаления",
            date=date.today(),
            category_id=str(category.id),
            type=TransactionType.EXPENSE
        )
        session.add(transaction)
        session.commit()
        
        # Создаем реальные UI компоненты
        mock_page = create_mock_page()
        home_view = HomeView(mock_page, session)
        
        # Act - выполнение полного сценария удаления
        # 1. Нажатие кнопки удаления
        home_view._show_delete_confirmation_dialog(transaction)
        
        # 2. Подтверждение удаления
        dialog = home_view.delete_confirmation_dialog
        delete_button = dialog.actions[1]  # Кнопка "Удалить"
        delete_button.on_click(None)
        
        # Assert - проверка результатов
        # Проверяем удаление транзакции из БД
        deleted_transaction = session.query(TransactionDB).filter_by(id=transaction.id).first()
        self.assertIsNone(deleted_transaction)
        
        # Проверяем закрытие диалога
        self.assertFalse(dialog.open)
        
        # Проверяем обновление UI
        mock_page.update.assert_called()

def test_delete_with_cascade_effects_integration(self):
    """Интеграционный тест: удаление с каскадными эффектами."""
    with get_db() as session:
        # Создаем транзакцию с связанными данными
        category = CategoryDB(id=str(uuid4()), name="Категория", type=TransactionType.EXPENSE)
        session.add(category)
        
        transaction = TransactionDB(
            id=str(uuid4()),
            amount=Decimal('100.00'),
            description="Транзакция с каскадными эффектами",
            date=date.today(),
            category_id=str(category.id),
            type=TransactionType.EXPENSE
        )
        session.add(transaction)
        session.commit()
        
        # Получаем исходные данные для сравнения
        initial_balance = get_balance_for_date(session, date.today())
        initial_category_stats = get_category_statistics(session, category.id)
        
        # Выполняем удаление
        mock_page = create_mock_page()
        home_view = HomeView(mock_page, session)
        result = home_view.delete_transaction(transaction.id)
        
        # Проверяем успешность удаления
        self.assertTrue(result)
        
        # Проверяем каскадные обновления
        final_balance = get_balance_for_date(session, date.today())
        final_category_stats = get_category_statistics(session, category.id)
        
        # Баланс должен увеличиться на сумму удаленного расхода
        self.assertEqual(final_balance, initial_balance + transaction.amount)
        
        # Статистика категории должна обновиться
        self.assertNotEqual(initial_category_stats, final_category_stats)
```

### Delete Operations Checklist

**Специализированный checklist для тестирования операций удаления:**

#### Перед тестированием delete операций:
- [ ] Определены все UI компоненты с кнопками удаления
- [ ] Изучены диалоги подтверждения удаления
- [ ] Выявлены все каскадные обновления после удаления
- [ ] Определены возможные ошибки при удалении

#### Тестирование кнопок удаления:
- [ ] Проверены атрибуты кнопки (icon, tooltip, color)
- [ ] Протестирован вызов callback при нажатии
- [ ] Проверено состояние кнопки в зависимости от прав доступа
- [ ] Протестирована безопасность при null callback

#### Тестирование диалогов подтверждения:
- [ ] Проверено создание диалога с правильным содержимым
- [ ] Протестировано отображение диалога через page.open()
- [ ] Проверена функциональность кнопки "Отмена"
- [ ] Протестирована функциональность кнопки "Удалить"
- [ ] Проверено закрытие диалога после действий

#### Тестирование каскадных обновлений:
- [ ] Протестировано обновление списка транзакций
- [ ] Проверено обновление календаря
- [ ] Протестировано обновление прогноза баланса
- [ ] Проверено обновление статистики категорий
- [ ] Протестированы другие связанные компоненты

#### Тестирование обработки ошибок:
- [ ] Протестировано удаление несуществующей записи
- [ ] Проверена обработка ошибок базы данных
- [ ] Протестирован rollback при ошибках
- [ ] Проверено отображение сообщений об ошибках пользователю
- [ ] Протестирована стабильность UI при ошибках

#### Property-based тесты для удаления:
- [ ] Написаны свойства для консистентности данных
- [ ] Протестированы инварианты после удаления
- [ ] Проверены свойства UI состояния
- [ ] Протестированы граничные случаи

#### Интеграционные тесты:
- [ ] Протестирован полный цикл удаления через UI
- [ ] Проверены каскадные эффекты в реальной БД
- [ ] Протестированы сценарии с множественными удалениями
- [ ] Проверена производительность при больших объемах данных

#### Регрессионные тесты:
- [ ] Протестированы исправления известных проблем
- [ ] Проверено использование правильного Flet API
- [ ] Протестирована совместимость с другими операциями
- [ ] Проверена стабильность после изменений

## Best Practices Summary

### DO's ✅

1. **Изолируйте тесты** - используйте mock объекты для внешних зависимостей
2. **Тестируйте поведение** - фокусируйтесь на том, что делает компонент, а не как
3. **Используйте реалистичные данные** - тестовые данные должны быть похожи на реальные
4. **Проверяйте граничные случаи** - пустые списки, null значения, большие объемы данных
5. **Тестируйте ошибки** - убедитесь, что UI корректно обрабатывает ошибки
6. **Используйте property-based тесты** - для проверки универсальных свойств
7. **Группируйте связанные тесты** - используйте классы для организации тестов
8. **Пишите понятные имена тестов** - имя должно объяснять, что тестируется
9. **Тестируйте диалоги подтверждения** - убедитесь, что пользователь может отменить удаление
10. **Проверяйте каскадные обновления** - все связанные данные должны обновляться

### DON'Ts ❌

1. **Не тестируйте implementation details** - не проверяйте внутреннюю структуру компонентов
2. **Не делайте тесты зависимыми** - каждый тест должен работать независимо
3. **Не используйте реальную БД** - используйте in-memory базу или mock объекты
4. **Не игнорируйте медленные тесты** - помечайте их и запускайте отдельно
5. **Не тестируйте Flet framework** - тестируйте только свой код
6. **Не дублируйте логику** - используйте вспомогательные функции для общего кода
7. **Не пишите слишком сложные тесты** - простые тесты легче понимать и поддерживать
8. **Не забывайте про cleanup** - освобождайте ресурсы после тестов
9. **Не пропускайте тестирование отмены** - пользователь должен иметь возможность отменить удаление
10. **Не игнорируйте каскадные эффекты** - удаление влияет на множество компонентов
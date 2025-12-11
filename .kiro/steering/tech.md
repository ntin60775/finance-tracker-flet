# Technology Stack

## Core Technologies

- **Python**: >= 3.9
- **UI Framework**: Flet >= 0.25.0 (Flutter-based cross-platform UI)
- **Database**: SQLite via SQLAlchemy >= 2.0.0
- **Validation**: Pydantic >= 2.0.0

## Development Dependencies

- **Testing**: pytest >= 7.0.0, pytest-asyncio >= 0.21.0
- **Coverage**: pytest-cov >= 4.0.0
- **Property-based testing**: hypothesis >= 6.80.0
- **Build**: PyInstaller (для создания .exe)

## Project Structure

```
src/finance_tracker/
├── __main__.py          # Entry point (python -m finance_tracker)
├── app.py               # Main application logic
├── config.py            # Configuration (Singleton pattern)
├── database.py          # DB initialization and session management
├── models/              # SQLAlchemy + Pydantic models
│   ├── models.py        # DB models (Base, CategoryDB, TransactionDB, etc.)
│   └── enums.py         # Enums (TransactionType, RecurrenceType, etc.)
├── services/            # Business logic layer (CRUD operations)
│   ├── transaction_service.py
│   ├── loan_service.py
│   ├── planned_transaction_service.py
│   └── ...
├── views/               # UI screens (Flet views)
│   ├── main_window.py
│   ├── home_view.py
│   └── ...
├── components/          # Reusable UI components (modals, widgets)
│   ├── transaction_modal.py
│   ├── calendar_widget.py
│   └── ...
├── utils/               # Utilities
│   ├── logger.py
│   ├── error_handler.py
│   └── cache.py
└── mobile/              # Export/import and sync
    ├── export_service.py
    ├── import_service.py
    └── sync_proprietary/  # Git submodule (private)
```

## Common Commands

### Development

```bash
# Install package in editable mode
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"

# Run application
python -m finance_tracker
# or
python main.py
```

### Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src/finance_tracker --cov-report=html

# Run specific test categories
pytest tests/test_*_view.py              # UI tests
pytest tests/test_*_properties.py        # Property-based tests
pytest tests/test_transaction_service.py # Specific service

# Run with verbose output
pytest tests/ -v

# Stop on first failure
pytest tests/ -x

# Filter by test name
pytest tests/ -k "test_load_data"
```

### Building

```bash
# Build standalone executable
pyinstaller finance_tracker.spec

# Output: dist/FinanceTracker.exe
```

## Architecture Patterns

### Database Access

- **Session management**: Context manager `get_db_session()` в database.py
- **Dependency Injection**: Все сервисы принимают `session: Session` как параметр
- **Auto-rollback**: При ошибках транзакция откатывается автоматически

```python
from finance_tracker.database import get_db_session

with get_db_session() as session:
    result = some_service_function(session, params)
```

### Service Layer

- Все бизнес-логика в `services/`
- Функции, не классы (functional approach)
- Логирование всех операций
- Валидация через Pydantic models

### Models

- **SQLAlchemy models**: `*DB` классы (CategoryDB, TransactionDB) для БД
- **Pydantic models**: для валидации и API (TransactionCreate, TransactionUpdate)
- **Enums**: централизованы в `models/enums.py`

### Configuration

- **Singleton pattern**: `Config` класс в config.py
- **Global instance**: `settings = Config()`
- **Persistence**: Автоматическое сохранение в `.finance_tracker_data/config.json`

### Logging

- **Structured logging**: через `utils/logger.py`
- **Russian messages**: все логи на русском
- **Context**: логируются входные параметры, состояние системы
- **Levels**: ERROR (требует внимания), WARNING (потенциальная проблема), INFO (важные события), DEBUG (детали)

## Flet UI Guidelines

### Color Usage

**CRITICAL**: Используй только существующие цвета из `ft.Colors`. Несуществующие атрибуты вызывают `AttributeError`.

**Корректные цвета для фона контейнеров:**
- `ft.Colors.SURFACE` - основной цвет поверхности (рекомендуется для карточек)
- `ft.Colors.PRIMARY_CONTAINER` - контейнер с primary цветом
- `ft.Colors.SECONDARY_CONTAINER` - контейнер с secondary цветом
- `ft.Colors.ERROR_CONTAINER` - контейнер для ошибок
- Или не указывай `bgcolor` - будет использован цвет по умолчанию

**Корректные цвета для текста:**
- `ft.Colors.ON_SURFACE` - текст на поверхности
- `ft.Colors.ON_SURFACE_VARIANT` - вторичный текст на поверхности
- `ft.Colors.ON_PRIMARY` - текст на primary фоне
- `ft.Colors.ON_SECONDARY` - текст на secondary фоне
- `ft.Colors.ERROR` - текст ошибки
- `ft.Colors.PRIMARY` - акцентный текст

**ЗАПРЕЩЕНО использовать (не существуют в Flet):**
- ❌ `ft.Colors.SURFACE_VARIANT` - НЕ СУЩЕСТВУЕТ
- ❌ `ft.Colors.SURFACE_CONTAINER` - НЕ СУЩЕСТВУЕТ
- ❌ `ft.Colors.SURFACE_CONTAINER_HIGH` - НЕ СУЩЕСТВУЕТ

**Правило:** Перед использованием нового цвета проверь, что он существует в документации Flet или используй стандартные цвета из списка выше.

## Testing Strategy

### Test Types and Organization

**Unit Tests** - изолированное тестирование компонентов:
- **Services** (`test_*_service.py`) - бизнес-логика, CRUD операции
- **Views** (`test_*_view.py`) - UI компоненты, инициализация, взаимодействие
- **Modals** (`test_*_modal.py`) - модальные окна, формы, валидация
- **Utilities** (`test_*_utils.py`) - вспомогательные функции

**Property-Based Tests** (`test_*_properties.py`) - универсальные свойства:
- **Hypothesis library** для генерации случайных данных
- **Минимум 100 итераций** для каждого property
- **Инварианты** бизнес-логики (балансы, суммы, состояния)
- **Round-trip properties** для сериализации/десериализации
- **Error handling** для граничных случаев

**Integration Tests** (`test_integration*.py`) - взаимодействие компонентов:
- **End-to-end scenarios** - полные пользовательские сценарии
- **Component integration** - View ↔ Service ↔ Database
- **Regression tests** - предотвращение повторных ошибок

**UI Tests** - специализированные тесты интерфейса:
- **Button interactions** - нажатия, callbacks, состояния
- **Modal workflows** - открытие, заполнение, сохранение, отмена
- **Form validation** - проверка пользовательского ввода
- **Navigation** - переходы между экранами

### Test Infrastructure

**Database Testing:**
- **In-memory SQLite** (`sqlite:///:memory:`) для изоляции тестов
- **Централизованная фикстура** `db_session` в `conftest.py`
- **Автоматический rollback** после каждого теста
- **Test data factories** для создания тестовых объектов

**Mock Objects:**
- **Flet Page mocking** для изоляции от UI framework
- **Service mocking** для unit тестов View компонентов
- **Database mocking** для тестов без БД
- **External API mocking** для стабильности тестов

**Fixtures and Utilities:**
```python
# Основные фикстуры в conftest.py
@pytest.fixture
def db_session():
    """In-memory database session for testing."""

@pytest.fixture  
def mock_page():
    """Mocked Flet Page object."""

@pytest.fixture
def sample_transaction_data():
    """Sample transaction data for tests."""
```

**Assertion Helpers:**
```python
def assert_modal_opened(mock_page, expected_modal_type):
    """Проверяет открытие модального окна."""

def assert_transaction_created(session, expected_data):
    """Проверяет создание транзакции в БД."""

def assert_ui_updated(view, expected_state):
    """Проверяет обновление UI компонента."""
```

### Property-Based Testing Guidelines

**Generator Strategies:**
```python
from hypothesis import strategies as st

# Генераторы для финансовых данных
amounts = st.decimals(min_value=Decimal('0.01'), max_value=Decimal('999999.99'))
dates = st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31))
descriptions = st.text(max_size=500, alphabet=st.characters(blacklist_categories=['Cc']))

# Генераторы для UI данных
valid_callbacks = st.functions(like=lambda: None, returns=st.none())
button_states = st.booleans()
```

**Property Patterns:**
- **Invariants**: `balance_after_transaction = balance_before + transaction_amount`
- **Round-trips**: `parse(format(data)) == data`
- **Idempotence**: `f(f(x)) == f(x)`
- **Monotonicity**: `sorted(list) == sorted(sorted(list))`
- **Error boundaries**: Invalid inputs should raise specific exceptions

### UI Testing Best Practices

**Button Testing Pattern:**
```python
def test_button_click_opens_modal(mock_page, mock_session):
    """Тест нажатия кнопки открывает модальное окно."""
    # Arrange
    view = HomeView(mock_page, mock_session)
    
    # Act
    view.transactions_panel._build_header().controls[1].on_click(None)
    
    # Assert
    assert_modal_opened(mock_page, TransactionModal)
```

**Modal Testing Pattern:**
```python
def test_modal_form_validation(mock_page, mock_session):
    """Тест валидации формы модального окна."""
    # Arrange
    modal = TransactionModal(mock_session, lambda x: None)
    
    # Act - invalid data
    modal.amount_field.value = "-100"
    modal._validate_form()
    
    # Assert
    assert modal.save_button.disabled == True
    assert "Сумма должна быть положительной" in modal.error_messages
```

**Property-Based UI Testing:**
```python
@given(st.decimals(min_value=Decimal('0.01')))
def test_transaction_amount_validation_property(amount):
    """Property: Любая положительная сумма должна проходить валидацию."""
    modal = TransactionModal(mock_session, lambda x: None)
    modal.amount_field.value = str(amount)
    
    result = modal._validate_amount()
    
    assert result.is_valid == True
    assert result.errors == []
```

### Test Execution Strategy

**Development Workflow:**
1. **Red**: Написать failing тест для новой функциональности
2. **Green**: Реализовать минимальный код для прохождения теста
3. **Refactor**: Улучшить код, сохраняя прохождение тестов
4. **Property**: Добавить property-based тесты для универсальных свойств

**CI/CD Pipeline:**
1. **Smoke tests**: Быстрые unit тесты для раннего обнаружения ошибок
2. **Full test suite**: Все тесты с покрытием кода
3. **Property tests**: Длительные property-based тесты
4. **Integration tests**: End-to-end сценарии

**Performance Considerations:**
- **Parallel execution**: `pytest -n auto` для ускорения
- **Test categorization**: Маркировка медленных тестов `@pytest.mark.slow`
- **Selective running**: Запуск только измененных компонентов
- **Caching**: Кэширование результатов для повторных запусков

### Adding New Tests

**Quick Reference для создания новых тестов:**

1. **Выберите тип теста**: Unit/Property-based/Integration/UI
2. **Следуйте конвенции именования**: `test_*_service.py`, `test_*_view.py`, `test_*_properties.py`
3. **Используйте шаблоны**: Базовые шаблоны для каждого типа теста
4. **Интегрируйтесь с системой**: Используйте существующие фикстуры и паттерны
5. **Проверьте результат**: Запустите тесты изолированно и в составе всего набора

**Подробное руководство**: См. `.kiro/steering/ui-testing.md` раздел "Adding New Tests to the System"

**Checklist для нового теста:**
- [ ] Правильное имя файла и класса
- [ ] Docstring на русском языке  
- [ ] Использование фикстур из `conftest.py`
- [ ] Паттерн Arrange-Act-Assert
- [ ] Проверка покрытия кода
- [ ] Маркеры pytest при необходимости

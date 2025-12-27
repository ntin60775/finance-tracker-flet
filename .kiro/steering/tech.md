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

**КРИТИЧЕСКИ ВАЖНО - Правила запуска тестов:**

1. **ВСЕГДА ждать завершения всех тестов** - не прерывать выполнение
2. **НЕ использовать сокращённые версии** команд (например, `-q`, `--tb=short`)
3. **НЕ указывать таймаут** при запуске тестов - дать им завершиться естественным образом
4. **Дождаться полного вывода** всех результатов тестирования

**Причина:** Property-based тесты (Hypothesis) могут выполняться долго (100+ итераций на тест). Прерывание или таймаут приведёт к неполным результатам и пропущенным ошибкам.

```bash
# Run all tests - ПРАВИЛЬНО (дождаться завершения!)
pytest tests/

# Run with coverage - ПРАВИЛЬНО
pytest tests/ --cov=src/finance_tracker --cov-report=html

# Run specific test categories
pytest tests/test_*_view.py              # UI tests
pytest tests/test_*_properties.py        # Property-based tests (могут быть медленными!)
pytest tests/test_transaction_service.py # Specific service

# Run with verbose output - ПРАВИЛЬНО
pytest tests/ -v

# Stop on first failure - использовать осторожно
pytest tests/ -x

# Filter by test name
pytest tests/ -k "test_load_data"

# ❌ НЕПРАВИЛЬНО - не использовать:
# pytest tests/ -q                    # Сокращённый вывод - скрывает детали
# pytest tests/ --tb=short            # Короткий traceback - теряется контекст
# pytest tests/ --timeout=30          # Таймаут - прервёт property-based тесты
```

**Ожидаемое время выполнения:**
- Unit тесты: ~10-30 секунд
- Property-based тесты: ~1-5 минут (100+ итераций на тест)
- Integration тесты: ~30-60 секунд
- Полный набор: ~2-7 минут

**Если тесты выполняются дольше 10 минут** - это может указывать на проблему, но всё равно дождись завершения для получения полной информации.

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

### CRITICAL: Modern Flet API Requirement

**ОБЯЗАТЕЛЬНО:** Всегда использовать СОВРЕМЕННУЮ версию Flet API (>= 0.25.0).

**Flet API постоянно развивается.** Перед использованием любого Flet компонента или метода:
1. **Проверь актуальность API** через Context7 или официальную документацию
2. **Не полагайся на устаревшие примеры** из интернета или памяти
3. **При сомнениях** - всегда сверяйся с документацией

**Типичные изменения в Flet API:**
- Переименование классов и методов
- Изменение сигнатур функций
- Удаление deprecated атрибутов
- Новые способы работы с диалогами и модальными окнами

**Правило:** Если код использует Flet API и падает с `AttributeError` или `TypeError` - первым делом проверь, не изменился ли API в новой версии.

### Dialog Management Standard (ОБЯЗАТЕЛЬНЫЙ СТАНДАРТ)

**КРИТИЧЕСКИ ВАЖНО:** В проекте используется ТОЛЬКО современный способ работы с диалогами через `page.open()` и `page.close()`. Это обязательное требование для всего кода (production и тесты).

#### Почему это критически важно

Flet постоянно развивается, и старый API (`page.dialog =`, `dialog.open = True`) является deprecated. Использование современного API:
- Гарантирует совместимость с новыми версиями Flet
- Упрощает код и делает его более читаемым
- Предотвращает ошибки и неожиданное поведение
- Соответствует best practices Flet

#### Правильное использование (✅ ТОЛЬКО ЭТО)

**Открытие диалога:**
```python
def open_dialog(e):
    page.open(dialog)  # Открываем диалог через page.open()
```

**Закрытие диалога:**
```python
def close_dialog(e):
    page.close(dialog)  # Закрываем диалог через page.close()
```

**Полный пример с модальным окном:**
```python
class TransactionModal(ft.UserControl):
    def __init__(self, session, on_save_callback):
        super().__init__()
        self.session = session
        self.on_save_callback = on_save_callback
        self.dialog = ft.AlertDialog(
            title=ft.Text("Новая транзакция"),
            content=ft.Column([...]),
            actions=[
                ft.TextButton("Отмена", on_click=self.close_dialog),
                ft.TextButton("Сохранить", on_click=self.save_dialog),
            ]
        )
    
    def open(self, page):
        """Открыть модальное окно."""
        page.open(self.dialog)  # ✅ ПРАВИЛЬНО
    
    def close_dialog(self, e):
        """Закрыть модальное окно."""
        self.page.close(self.dialog)  # ✅ ПРАВИЛЬНО
    
    def save_dialog(self, e):
        """Сохранить и закрыть."""
        # ... логика сохранения ...
        self.page.close(self.dialog)  # ✅ ПРАВИЛЬНО
```

#### Неправильное использование (❌ ЗАПРЕЩЕНО)

**❌ НЕПРАВИЛЬНО - Устаревший API:**
```python
# ЗАПРЕЩЕНО в этом проекте!
def open_dialog(e):
    page.dialog = dialog          # ❌ Устаревший способ
    dialog.open = True            # ❌ Устаревший способ
    page.update()                 # ❌ Избыточный вызов
```

**❌ НЕПРАВИЛЬНО - Смешивание API:**
```python
# ЗАПРЕЩЕНО - не смешивай старый и новый API!
page.open(dialog)                 # ✅ Новый API
dialog.open = False               # ❌ Старый API - КОНФЛИКТ!
```

**❌ НЕПРАВИЛЬНО - Забыл закрыть:**
```python
# ЗАПРЕЩЕНО - диалог останется открытым!
def close_dialog(e):
    pass  # ❌ Диалог не закрывается
```

#### Применяется к

**Все overlay компоненты должны использовать `page.open()` и `page.close()`:**
- `ft.AlertDialog` - диалоги подтверждения
- `ft.BottomSheet` - нижние панели
- `ft.SnackBar` - уведомления
- Любые другие overlay компоненты

#### В тестах

**Mock объекты ДОЛЖНЫ иметь методы `page.open()` и `page.close()`:**
```python
def create_mock_page():
    """Создает mock Page с методами для диалогов."""
    mock_page = MagicMock()
    mock_page.open = Mock()   # ✅ Обязательно
    mock_page.close = Mock()  # ✅ Обязательно
    return mock_page
```

**Проверки в тестах:**
```python
def test_modal_opening(self):
    """Тест открытия модального окна."""
    modal = TransactionModal(self.mock_session, self.mock_callback)
    
    modal.open(self.mock_page)
    
    # ✅ ПРАВИЛЬНО - проверяем вызов page.open()
    self.mock_page.open.assert_called_once()
    
    # ❌ НЕПРАВИЛЬНО - не проверяем старый API
    # self.assertIsNotNone(self.mock_page.dialog)  # ❌ Не делай так!
    # self.assertTrue(modal.dialog.open)           # ❌ Не делай так!
```

**Что НЕ проверять:**
- ❌ `page.dialog` атрибут
- ❌ `dialog.open` атрибут
- ❌ `page.update()` вызовы после диалогов

#### Checklist для Dialog Management

**Перед написанием UI кода:**
- [ ] Проверена актуальная версия Flet API в `pyproject.toml`
- [ ] Mock объекты имеют методы `page.open()` и `page.close()`
- [ ] Код не использует deprecated методы (`page.dialog =`, `dialog.open = True`)
- [ ] **Используется ТОЛЬКО `page.open()` и `page.close()` для диалогов**
- [ ] При сомнениях - проверена документация Flet

**При работе с диалогами:**
- [ ] Диалог открывается через `page.open(dialog)`
- [ ] Диалог закрывается через `page.close(dialog)`
- [ ] Не используется `page.dialog =` присваивание
- [ ] Не используется `dialog.open = True/False`
- [ ] Не используется `page.update()` после работы с диалогами
- [ ] Mock проверяет вызов `page.open.assert_called()`
- [ ] Mock проверяет вызов `page.close.assert_called()`

**Для SnackBar:**
- [ ] SnackBar открывается через `page.open(snack_bar)`
- [ ] SnackBar закрывается через `page.close(snack_bar)`
- [ ] Не используется `snack_bar.open = True`

**Для BottomSheet:**
- [ ] BottomSheet открывается через `page.open(bottom_sheet)`
- [ ] BottomSheet закрывается через `page.close(bottom_sheet)`
- [ ] Не используется `bottom_sheet.open = True`

#### Типичные ошибки и как их избежать

**Ошибка 1: Использование старого API**
```python
# ❌ НЕПРАВИЛЬНО
page.dialog = my_dialog
my_dialog.open = True
page.update()

# ✅ ПРАВИЛЬНО
page.open(my_dialog)
```
**Как избежать:** Всегда используй `page.open()` для открытия и `page.close()` для закрытия.

**Ошибка 2: Забыл закрыть диалог**
```python
# ❌ НЕПРАВИЛЬНО
def on_button_click(e):
    page.open(dialog)  # Открыли, но не закрыли!

# ✅ ПРАВИЛЬНО
def on_cancel_click(e):
    page.close(dialog)  # Закрыли диалог

def on_save_click(e):
    # ... логика сохранения ...
    page.close(dialog)  # Закрыли диалог
```
**Как избежать:** Убедись, что у каждого диалога есть кнопка закрытия, которая вызывает `page.close()`.

**Ошибка 3: Смешивание старого и нового API**
```python
# ❌ НЕПРАВИЛЬНО
page.open(dialog)      # Новый API
dialog.open = False    # Старый API - КОНФЛИКТ!

# ✅ ПРАВИЛЬНО
page.open(dialog)      # Открыли
page.close(dialog)     # Закрыли - только новый API
```
**Как избежать:** Используй ТОЛЬКО `page.open()` и `page.close()`, никогда не смешивай с `dialog.open`.

**Ошибка 4: Неправильный mock в тестах**
```python
# ❌ НЕПРАВИЛЬНО
mock_page = MagicMock()
# Забыли настроить методы!
modal.open(mock_page)
# Тест упадет с AttributeError

# ✅ ПРАВИЛЬНО
mock_page = MagicMock()
mock_page.open = Mock()   # Настроили метод
mock_page.close = Mock()  # Настроили метод
modal.open(mock_page)
mock_page.open.assert_called_once()
```
**Как избежать:** Используй helper функцию `create_mock_page()` из `conftest.py`.

**Ошибка 5: Проверка старого API в тестах**
```python
# ❌ НЕПРАВИЛЬНО
def test_modal_opening(self):
    modal.open(self.mock_page)
    
    # Проверяем старый API - НЕПРАВИЛЬНО!
    self.assertIsNotNone(self.mock_page.dialog)
    self.assertTrue(modal.dialog.open)

# ✅ ПРАВИЛЬНО
def test_modal_opening(self):
    modal.open(self.mock_page)
    
    # Проверяем новый API - ПРАВИЛЬНО!
    self.mock_page.open.assert_called_once()
```
**Как избежать:** Проверяй только вызовы `page.open()` и `page.close()`, не проверяй атрибуты диалога.

#### Миграция старого кода

Если ты находишь старый код, использующий `page.dialog =` и `dialog.open = True`:

1. **Замени на новый API:**
   ```python
   # Было
   page.dialog = dialog
   dialog.open = True
   page.update()
   
   # Стало
   page.open(dialog)
   ```

2. **Обнови тесты:**
   ```python
   # Было
   self.assertIsNotNone(mock_page.dialog)
   
   # Стало
   mock_page.open.assert_called_once()
   ```

3. **Проверь, что все работает:**
   ```bash
   pytest tests/ -v
   ```

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

**CRITICAL: Modern Flet API in Tests**

**ОБЯЗАТЕЛЬНО:** Все UI тесты должны использовать СОВРЕМЕННУЮ версию Flet API.

**Правила для тестов:**
1. **Перед написанием теста** - проверь актуальный Flet API через Context7 или документацию
2. **Не копируй устаревшие паттерны** - API Flet часто меняется между версиями
3. **При падении теста с AttributeError/TypeError** - первым делом проверь актуальность API
4. **Mock объекты** должны соответствовать текущей структуре Flet компонентов

**Типичные проблемы с устаревшим API в тестах:**
- Неправильные имена методов Page (например, `page.dialog` vs `page.open()`)
- Устаревшие атрибуты компонентов
- Изменённые сигнатуры конструкторов
- Удалённые или переименованные классы

**Checklist перед написанием UI теста:**
- [ ] Проверена актуальная версия Flet в проекте (pyproject.toml)
- [ ] Изучен современный API тестируемого компонента
- [ ] Mock объекты соответствуют текущей структуре Flet

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

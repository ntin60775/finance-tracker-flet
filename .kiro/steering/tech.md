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

- **Unit tests**: для сервисов и бизнес-логики
- **Property-based tests**: Hypothesis для проверки инвариантов
- **UI tests**: для View компонентов
- **In-memory DB**: `sqlite:///:memory:` в фикстурах
- **Централизованная фикстура**: `db_session` в conftest.py

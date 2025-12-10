# Design Document

## Overview

Этот документ описывает дизайн системы регрессионного тестирования для предотвращения критических ошибок, которые были обнаружены и исправлены в Finance Tracker Flet. Система включает в себя создание новых тестов для покрытия найденных ошибок и исправление существующих тестов, которые сломались из-за изменений в архитектуре.

## Architecture

### Тестовая архитектура

```
tests/
├── test_error_regression/
│   ├── test_offstage_control_prevention.py     # Тесты для предотвращения Offstage ошибок
│   ├── test_json_serialization_safety.py      # Тесты для безопасной JSON сериализации
│   ├── test_interface_type_safety.py          # Тесты для безопасности типов в интерфейсах
│   └── test_initialization_order.py           # Тесты для правильного порядка инициализации
├── test_home_presenter.py                     # Исправленные тесты HomePresenter
├── test_home_view.py                          # Исправленные тесты HomeView
└── test_integration_regression.py             # Интеграционные тесты для предотвращения регрессий
```

### Компоненты системы

1. **Error Prevention Tests** - Тесты для предотвращения конкретных ошибок
2. **Fixed Existing Tests** - Исправленные существующие тесты
3. **Property-Based Tests** - Тесты на основе свойств для широкого покрытия
4. **Integration Tests** - Тесты полного цикла инициализации

## Components and Interfaces

### 1. Offstage Control Prevention Tests

**Цель:** Предотвратить ошибки "Offstage Control must be added to the page first"

**Компоненты:**
- `TestOffstageControlPrevention` - основной тестовый класс
- Mock объекты для Page и UI компонентов
- Тесты порядка инициализации

**Интерфейсы:**
```python
class TestOffstageControlPrevention:
    def test_home_view_initialization_order(self)
    def test_main_window_did_mount_sequence(self)
    def test_dialog_opening_after_page_ready(self)
    def test_snackbar_showing_safety(self)
    def test_error_handling_without_dialogs(self)
```

### 2. JSON Serialization Safety Tests

**Цель:** Предотвратить ошибки JSON сериализации в логах

**Компоненты:**
- `TestJSONSerializationSafety` - основной тестовый класс
- `JsonFormatter` тесты
- Property-based тесты для различных типов данных

**Интерфейсы:**
```python
class TestJSONSerializationSafety:
    def test_date_serialization(self)
    def test_datetime_serialization(self)
    def test_decimal_serialization(self)
    def test_object_with_attributes_serialization(self)
    def test_logging_with_context_safety(self)
```

### 3. Interface Type Safety Tests

**Цель:** Предотвратить ошибки несоответствия типов в интерфейсах

**Компоненты:**
- `TestInterfaceTypeSafety` - основной тестовый класс
- Тесты для `IHomeViewCallbacks`
- Тесты для `PendingPaymentsWidget`

**Интерфейсы:**
```python
class TestInterfaceTypeSafety:
    def test_pending_payments_widget_statistics_type(self)
    def test_home_view_callbacks_interface(self)
    def test_home_presenter_callback_calls(self)
    def test_statistics_format_consistency(self)
```

### 4. Fixed Existing Tests

**Цель:** Исправить сломанные тесты после изменений

**Изменения в существующих тестах:**
- `test_home_presenter.py` - обновить ожидания для statistics (Dict вместо Tuple)
- `test_home_view.py` - убрать ожидание load_initial_data в конструкторе
- Property-based тесты - обновить под новые интерфейсы

## Data Models

### Тестовые данные

```python
# Для тестирования statistics
StatisticsDict = Dict[str, Any]  # Новый формат
StatisticsTuple = Tuple[int, float]  # Старый формат (deprecated)

# Для тестирования сериализации
SerializableTypes = Union[date, datetime, Decimal, Any]

# Для тестирования инициализации
InitializationState = Enum["not_started", "in_progress", "completed", "error"]
```

### Mock объекты

```python
class MockPage:
    """Mock для ft.Page с контролем состояния инициализации"""
    def __init__(self):
        self.is_initialized = False
        self.controls = []
        self.dialogs = []
    
    def add(self, control): ...
    def open(self, dialog): ...
    def update(self): ...

class MockHomeViewCallbacks:
    """Mock для IHomeViewCallbacks с проверкой типов"""
    def update_pending_payments(self, payments: List[Any], statistics: Dict[str, Any]): ...
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: UI Initialization Order Safety
*For any* UI component initialization sequence, dialogs and SnackBars should only be shown after the component is fully added to the page
**Validates: Requirements 1.1, 1.2, 1.3, 1.4**

### Property 2: JSON Serialization Completeness  
*For any* object that needs to be logged, JSON serialization should never fail regardless of the object's type or content
**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**

### Property 3: Interface Type Consistency
*For any* data passed between components, the actual type should match the expected interface type
**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

### Property 4: Statistics Format Invariant
*For any* statistics data returned by services, the format should be consistently Dict[str, Any] across all components
**Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**

### Property 5: Initialization Sequence Correctness
*For any* View component, load_initial_data should be called after the component is mounted, not during construction
**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**

### Property 6: Component Lifecycle Consistency
*For any* UI component, the lifecycle methods (did_mount, will_unmount) should be called in the correct order
**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**

### Property 7: Logging Safety Under All Conditions
*For any* combination of data types in logging context, serialization should succeed without exceptions
**Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**

### Property 8: Cross-Component Interface Compatibility
*For any* data exchange between Presenter and View, the interface contracts should be maintained
**Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5**

### Property 9: Application Startup Robustness
*For any* application startup sequence, all components should initialize without Offstage or serialization errors
**Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5**

### Property 10: Test Isolation Effectiveness
*For any* component test, mocking should prevent errors in one component from affecting tests of other components
**Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5**

### Property 11: Error Handling Graceful Degradation
*For any* error condition in critical operations, the system should continue functioning with appropriate error messages
**Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5**

### Property 12: Performance Consistency Under Testing
*For any* test execution, the performance should remain within acceptable bounds without degradation
**Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5**

## Error Handling

### Стратегии обработки ошибок в тестах

1. **Graceful Test Failures** - тесты должны падать с понятными сообщениями
2. **Error Context Preservation** - сохранение контекста ошибки для отладки
3. **Isolation of Failures** - изоляция падений одного теста от других
4. **Regression Detection** - автоматическое обнаружение регрессий

### Обработка специфических ошибок

```python
# Offstage Control Error
try:
    page.open(dialog)
except AssertionError as e:
    if "Offstage Control" in str(e):
        # Специальная обработка для Offstage ошибок
        handle_offstage_error(e)

# JSON Serialization Error  
try:
    json.dumps(log_data)
except TypeError as e:
    if "not JSON serializable" in str(e):
        # Fallback сериализация
        handle_serialization_error(e, log_data)

# Interface Type Mismatch
try:
    widget.set_payments(payments, statistics)
except AttributeError as e:
    if "has no attribute 'get'" in str(e):
        # Проверка типов интерфейса
        handle_interface_mismatch(e, statistics)
```

## Testing Strategy

### Dual Testing Approach

**Unit Tests и Property-Based Tests являются комплементарными:**
- Unit tests проверяют конкретные сценарии и граничные случаи
- Property tests проверяют универсальные свойства на широком диапазоне входных данных
- Вместе они обеспечивают комплексное покрытие: unit tests ловят конкретные баги, property tests проверяют общую корректность

### Unit Testing Requirements

Unit tests покрывают:
- Конкретные примеры исправленных ошибок
- Граничные случаи инициализации компонентов  
- Интеграционные точки между компонентами
- Специфические сценарии обработки ошибок

### Property-Based Testing Requirements

**Библиотека:** Hypothesis для Python
**Минимальные итерации:** 100 для каждого property test
**Теги:** Каждый property-based test помечается комментарием с ссылкой на correctness property

**Формат тегов:**
```python
def test_ui_initialization_order_safety():
    """**Feature: error-regression-testing, Property 1: UI Initialization Order Safety**"""
    
def test_json_serialization_completeness():
    """**Feature: error-regression-testing, Property 2: JSON Serialization Completeness**"""
```

### Test Categories

1. **Regression Prevention Tests** - предотвращение повторения исправленных ошибок
2. **Interface Compatibility Tests** - проверка совместимости интерфейсов
3. **Initialization Order Tests** - проверка правильного порядка инициализации
4. **Error Handling Tests** - проверка graceful degradation
5. **Performance Regression Tests** - предотвращение деградации производительности

### Test Execution Strategy

```python
# Последовательность выполнения тестов
1. Unit tests для конкретных исправлений
2. Property-based tests для общих свойств  
3. Integration tests для полных сценариев
4. Performance tests для проверки деградации
```

### Continuous Integration

- Все regression tests должны выполняться при каждом commit
- Property-based tests должны использовать фиксированный seed для воспроизводимости
- Падение любого regression test блокирует merge
- Performance tests отслеживают тренды и предупреждают о деградации
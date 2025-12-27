# Design Document

## Overview

Данный дизайн описывает исправление неработающей кнопки "Показать все" в виджете плановых транзакций на главном экране. Проблема заключается в том, что метод `on_show_all_occurrences` в HomeView содержит только TODO комментарий без реализации. Решение включает:

1. Передачу метода навигации из MainWindow в HomeView при инициализации
2. Реализацию метода `on_show_all_occurrences` с вызовом навигации на индекс 1 (PlannedTransactionsView)
3. Обработку ошибок при отсутствии метода навигации

## Architecture

### Текущая архитектура

```
MainWindow
├── Navigation Rail (индексы 0-7)
├── Content Area
│   └── HomeView (индекс 0)
│       └── PlannedTransactionsWidget
│           └── Кнопка "Показать все" → on_show_all() → HomeView.on_show_all_occurrences()
└── navigate(index) метод
```

**Проблема:** HomeView не имеет доступа к методу `navigate()` из MainWindow, поэтому `on_show_all_occurrences()` не может переключить раздел.

### Новая архитектура

```
MainWindow
├── Navigation Rail (индексы 0-7)
├── Content Area
│   └── HomeView (индекс 0, получает navigate_callback)
│       └── PlannedTransactionsWidget
│           └── Кнопка "Показать все" → on_show_all() → HomeView.on_show_all_occurrences() → navigate_callback(1)
└── navigate(index) метод
```

**Решение:** MainWindow передаёт свой метод `navigate` в HomeView при инициализации через новый параметр `navigate_callback`.

## Components and Interfaces

### 1. MainWindow

**Изменения:**
- Добавить передачу `self.navigate` в конструктор HomeView

**Сигнатура:**
```python
def init_ui(self):
    self.home_view = HomeView(
        self.page, 
        self.home_view_session,
        navigate_callback=self.navigate  # НОВЫЙ параметр
    )
```

### 2. HomeView

**Изменения:**
- Добавить параметр `navigate_callback: Optional[Callable[[int], None]]` в конструктор
- Сохранить callback как атрибут экземпляра
- Реализовать метод `on_show_all_occurrences()` с вызовом callback

**Сигнатура:**
```python
def __init__(
    self, 
    page: ft.Page, 
    session: Session,
    navigate_callback: Optional[Callable[[int], None]] = None
):
    self.navigate_callback = navigate_callback
    # ... остальная инициализация
```

**Реализация метода:**
```python
def on_show_all_occurrences(self):
    """Переход к разделу всех плановых транзакций."""
    if self.navigate_callback:
        try:
            self.navigate_callback(1)  # Индекс PlannedTransactionsView
            logger.info("Переход к разделу плановых транзакций")
        except Exception as e:
            logger.error(f"Ошибка при навигации к плановым транзакциям: {e}")
    else:
        logger.warning("Метод навигации не доступен в HomeView")
```

### 3. PlannedTransactionsWidget

**Изменения:** Нет. Виджет уже корректно вызывает `on_show_all()` callback, который передаётся из HomeView.

## Data Models

Изменений в моделях данных не требуется.

## Correctness Properties

*Свойство (property) - это характеристика или поведение, которое должно выполняться для всех валидных выполнений системы. Свойства служат мостом между человеко-читаемыми спецификациями и машинно-проверяемыми гарантиями корректности.*

### Property 1: Навигация вызывается при нажатии кнопки

*Для любого* HomeView с заданным navigate_callback, при вызове метода on_show_all_occurrences callback должен быть вызван с индексом 1.

**Validates: Requirements 1.1, 2.2**

### Property 2: Безопасность при отсутствии навигации

*Для любого* HomeView без navigate_callback (None), при вызове метода on_show_all_occurrences не должно возникать необработанных исключений.

**Validates: Requirements 3.1, 3.3**

### Property 3: Логирование при ошибках навигации

*Для любого* HomeView с navigate_callback, который выбрасывает исключение, при вызове on_show_all_occurrences ошибка должна быть залогирована.

**Validates: Requirements 3.2**

## Error Handling

### 1. Отсутствие метода навигации

**Сценарий:** HomeView создан без `navigate_callback` (значение None).

**Обработка:**
- Логировать предупреждение: "Метод навигации не доступен в HomeView"
- Не выполнять переключение раздела
- Не выбрасывать исключение

### 2. Ошибка при вызове навигации

**Сценарий:** Метод `navigate_callback` выбрасывает исключение.

**Обработка:**
- Перехватить исключение в try-except блоке
- Логировать ошибку с полным контекстом: "Ошибка при навигации к плановым транзакциям: {e}"
- Не выбрасывать исключение дальше (graceful degradation)

### 3. Некорректный индекс навигации

**Сценарий:** Передан неверный индекс раздела (не существует).

**Обработка:**
- Ответственность MainWindow.navigate() - он должен обрабатывать некорректные индексы
- HomeView передаёт константный индекс 1, который всегда валиден

## Testing Strategy

### Unit Tests

**Тесты для HomeView.on_show_all_occurrences:**

1. **test_on_show_all_occurrences_calls_navigate_with_index_1**
   - Создать HomeView с mock navigate_callback
   - Вызвать on_show_all_occurrences()
   - Проверить, что navigate_callback был вызван с аргументом 1

2. **test_on_show_all_occurrences_without_callback_logs_warning**
   - Создать HomeView без navigate_callback (None)
   - Вызвать on_show_all_occurrences()
   - Проверить, что залогировано предупреждение
   - Проверить, что не возникло исключений

3. **test_on_show_all_occurrences_handles_navigation_error**
   - Создать HomeView с mock navigate_callback, который выбрасывает исключение
   - Вызвать on_show_all_occurrences()
   - Проверить, что ошибка залогирована
   - Проверить, что исключение не распространяется дальше

**Тесты для MainWindow:**

4. **test_main_window_passes_navigate_to_home_view**
   - Создать MainWindow
   - Проверить, что HomeView был создан с параметром navigate_callback
   - Проверить, что navigate_callback является callable

### Property-Based Tests

**Feature: planned-transaction-show-all-button**

5. **Property 1: Навигация вызывается при нажатии кнопки**
   - Генерировать случайные mock callbacks
   - Создавать HomeView с этими callbacks
   - Вызывать on_show_all_occurrences()
   - Проверять, что callback был вызван ровно один раз с индексом 1

6. **Property 2: Безопасность при отсутствии навигации**
   - Создавать HomeView с navigate_callback=None
   - Вызывать on_show_all_occurrences() множество раз
   - Проверять, что не возникает исключений

7. **Property 3: Логирование при ошибках навигации**
   - Генерировать случайные исключения
   - Создавать mock callbacks, которые выбрасывают эти исключения
   - Вызывать on_show_all_occurrences()
   - Проверять, что ошибка залогирована и не распространяется

### Integration Tests

8. **test_show_all_button_navigates_to_planned_transactions_view**
   - Создать полный MainWindow с реальными компонентами
   - Получить HomeView из content_area
   - Вызвать on_show_all_occurrences()
   - Проверить, что rail.selected_index = 1
   - Проверить, что content_area.content является PlannedTransactionsView
   - Проверить, что settings.last_selected_index = 1

### Тестовая конфигурация

- **Минимум 100 итераций** для каждого property-based теста
- **Теги:** `Feature: planned-transaction-show-all-button, Property {number}: {property_text}`
- **Библиотека:** Hypothesis для property-based тестов
- **Фреймворк:** pytest для всех тестов

## Implementation Notes

### Константы

Рекомендуется вынести индексы навигации в константы для улучшения читаемости:

```python
# В MainWindow или отдельном файле констант
NAVIGATION_INDEX_HOME = 0
NAVIGATION_INDEX_PLANNED_TRANSACTIONS = 1
NAVIGATION_INDEX_LOANS = 2
NAVIGATION_INDEX_PENDING_PAYMENTS = 3
NAVIGATION_INDEX_PLAN_FACT = 4
NAVIGATION_INDEX_LENDERS = 5
NAVIGATION_INDEX_CATEGORIES = 6
NAVIGATION_INDEX_SETTINGS = 7
```

Использование:
```python
def on_show_all_occurrences(self):
    if self.navigate_callback:
        self.navigate_callback(NAVIGATION_INDEX_PLANNED_TRANSACTIONS)
```

### Обратная совместимость

Параметр `navigate_callback` в HomeView является опциональным (Optional), что обеспечивает обратную совместимость:
- Существующие тесты, создающие HomeView без этого параметра, продолжат работать
- Новая функциональность активируется только при передаче callback

### Аналогичная функциональность

Виджет PendingPaymentsWidget также имеет кнопку "Показать все". Проверить, реализована ли навигация для неё:
- Если нет - применить аналогичное решение
- Если да - использовать тот же паттерн для консистентности

## Alternatives Considered

### Альтернатива 1: Глобальный singleton для навигации

**Описание:** Создать глобальный объект NavigationManager, доступный из любого места приложения.

**Плюсы:**
- Не нужно передавать callback через конструкторы
- Упрощает доступ к навигации из любого компонента

**Минусы:**
- Глобальное состояние усложняет тестирование
- Нарушает принцип Dependency Injection
- Создаёт скрытые зависимости между компонентами

**Решение:** Отклонено в пользу явной передачи callback.

### Альтернатива 2: Event Bus для навигации

**Описание:** Использовать паттерн Event Bus для публикации событий навигации.

**Плюсы:**
- Полная развязка компонентов
- Гибкость в обработке событий

**Минусы:**
- Избыточная сложность для простой задачи
- Сложнее отследить поток выполнения
- Требует дополнительной инфраструктуры

**Решение:** Отклонено как over-engineering для данной задачи.

### Альтернатива 3: Прямой доступ к MainWindow через page

**Описание:** Хранить ссылку на MainWindow в page и получать к ней доступ из HomeView.

**Плюсы:**
- Не нужно передавать callback

**Минусы:**
- Создаёт тесную связь между компонентами
- Нарушает инкапсуляцию
- Усложняет тестирование

**Решение:** Отклонено в пользу явной передачи callback.

## Выбранное решение

Передача метода `navigate` через параметр конструктора `navigate_callback` является оптимальным решением, так как:
- Явно показывает зависимости компонента
- Легко тестируется через mock объекты
- Следует принципу Dependency Injection
- Минимальные изменения в существующем коде
- Обратно совместимо (опциональный параметр)

# Design Document: Planned Widget Overview Mode

## Overview

Рефакторинг виджета плановых транзакций (`PlannedTransactionsWidget`) для преобразования его в обзорный режим. Основная цель — устранить дублирование функционала с панелью транзакций (`TransactionsPanel`), разделив ответственность:

- **Planned_Widget (левая колонка)** — обзор ближайших плановых операций, навигация по клику
- **Transactions_Panel (правая колонка)** — рабочая область для действий с операциями конкретного дня

## Architecture

### Текущая архитектура

```
HomeView
├── PlannedTransactionsWidget (левая колонка)
│   ├── Список вхождений с кнопками [Исполнить] [Пропустить]
│   ├── Кнопка "+" (добавить)
│   └── Кнопка "Показать все"
│
├── CalendarWidget (центральная колонка)
│
└── TransactionsPanel (правая колонка)
    ├── Плановые вхождения с кнопками [Исполнить] [Пропустить]
    └── Фактические транзакции
```

### Целевая архитектура

```
HomeView
├── PlannedTransactionsWidget (левая колонка) — ОБЗОРНЫЙ РЕЖИМ
│   ├── Список вхождений БЕЗ кнопок действий
│   │   └── Клик на элемент → переход к дате в календаре
│   ├── Кнопка "+" (добавить) — СОХРАНЯЕТСЯ
│   └── Кнопка "Показать все" — СОХРАНЯЕТСЯ
│
├── CalendarWidget (центральная колонка)
│   └── Получает событие выбора даты от PlannedTransactionsWidget
│
└── TransactionsPanel (правая колонка) — РАБОЧАЯ ОБЛАСТЬ
    ├── Плановые вхождения с кнопками [Исполнить] [Пропустить]
    └── Фактические транзакции
```

### Поток данных

```
1. Пользователь кликает на вхождение в PlannedTransactionsWidget
   ↓
2. PlannedTransactionsWidget вызывает on_occurrence_click(occurrence)
   ↓
3. HomeView.on_occurrence_clicked(occurrence)
   ↓
4. HomeView вызывает presenter.on_date_selected(occurrence.occurrence_date)
   ↓
5. CalendarWidget обновляет выбранную дату
   ↓
6. TransactionsPanel обновляется данными для новой даты
```

## Components and Interfaces

### PlannedTransactionsWidget (изменения)

```python
class PlannedTransactionsWidget(ft.Container):
    """
    Виджет для отображения ближайших плановых вхождений в обзорном режиме.
    
    Изменения:
    - Убраны кнопки "Исполнить" и "Пропустить" из карточек
    - Добавлен клик на карточку для навигации к дате
    - Callbacks on_execute и on_skip игнорируются (для обратной совместимости)
    """
    
    def __init__(
        self,
        session: Session,
        on_execute: Callable[[PlannedOccurrence], None],  # Игнорируется
        on_skip: Callable[[PlannedOccurrence], None],      # Игнорируется
        on_show_all: Callable[[], None],
        on_add_planned_transaction: Optional[Callable[[], None]] = None,
        on_occurrence_click: Optional[Callable[[PlannedOccurrence], None]] = None,  # НОВЫЙ
    ):
        ...
    
    def _build_occurrence_card(
        self,
        occurrence: PlannedOccurrence,
        category_name: str,
        tx_type: TransactionType
    ) -> ft.Container:
        """
        Создание карточки вхождения в обзорном режиме.
        
        Изменения:
        - Убраны кнопки действий
        - Добавлен on_click для навигации
        - Добавлен hover-эффект для индикации кликабельности
        """
        ...
    
    def _build_action_buttons(self, occurrence: PlannedOccurrence) -> List[ft.Control]:
        """
        УДАЛЁН или возвращает пустой список.
        """
        return []
```

### HomeView (изменения)

```python
class HomeView(ft.Column, IHomeViewCallbacks):
    """
    Изменения:
    - Добавлен обработчик on_occurrence_clicked для навигации
    - PlannedTransactionsWidget инициализируется с новым callback
    """
    
    def __init__(self, ...):
        ...
        self.planned_widget = PlannedTransactionsWidget(
            session=self.session,
            on_execute=self.on_execute_occurrence,      # Игнорируется виджетом
            on_skip=self.on_skip_occurrence,            # Игнорируется виджетом
            on_show_all=self.on_show_all_occurrences,
            on_add_planned_transaction=self.on_add_planned_transaction,
            on_occurrence_click=self.on_occurrence_clicked,  # НОВЫЙ
        )
    
    def on_occurrence_clicked(self, occurrence: PlannedOccurrence):
        """
        Обработка клика на плановое вхождение в обзорном виджете.
        Переключает календарь на дату вхождения.
        """
        self.presenter.on_date_selected(occurrence.occurrence_date)
```

### TransactionsPanel (без изменений)

Панель транзакций сохраняет текущий функционал без изменений:
- Кнопки "Исполнить" и "Пропустить" для плановых вхождений
- Отображение вхождений только для выбранной даты

## Data Models

Изменения в моделях данных не требуются. Используются существующие:

- `PlannedOccurrence` — плановое вхождение
- `OccurrenceStatus` — статус вхождения (PENDING, EXECUTED, SKIPPED)
- `TransactionType` — тип транзакции (INCOME, EXPENSE)

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Карточки вхождений не содержат кнопок действий

*For any* плановое вхождение в PlannedTransactionsWidget, карточка этого вхождения не должна содержать кнопки "Исполнить" или "Пропустить".

**Validates: Requirements 1.1, 5.2**

### Property 2: Карточки содержат всю необходимую информацию

*For any* плановое вхождение в PlannedTransactionsWidget, карточка должна содержать: название категории, дату, сумму и статус.

**Validates: Requirements 1.2**

### Property 3: Клик на вхождение вызывает callback с правильной датой

*For any* плановое вхождение в PlannedTransactionsWidget, клик на карточку должен вызвать callback `on_occurrence_click` с этим вхождением, что приведёт к выбору даты `occurrence.occurrence_date` в календаре.

**Validates: Requirements 2.1, 2.2**

### Property 4: Просроченные вхождения визуально выделены

*For any* плановое вхождение с датой меньше текущей, карточка должна иметь визуальное выделение (цвет, рамка) и содержать метку "(просрочено)" в тексте даты.

**Validates: Requirements 4.1, 4.2**

### Property 5: Просроченные вхождения сортируются первыми

*For any* список плановых вхождений, после сортировки все просроченные вхождения должны находиться в начале списка, отсортированные по дате.

**Validates: Requirements 4.3**

### Property 6: Панель транзакций показывает вхождения только для выбранной даты

*For any* выбранная дата в календаре, TransactionsPanel должна отображать только те плановые вхождения, у которых `occurrence_date` равна выбранной дате.

**Validates: Requirements 3.2**

### Property 7: Синхронизация виджетов при изменении статуса

*For any* изменение статуса вхождения (исполнение или пропуск) в TransactionsPanel, PlannedTransactionsWidget должен обновить свой список, исключив или обновив это вхождение.

**Validates: Requirements 3.3**

## Error Handling

### Обработка отсутствующего callback

```python
def _on_card_click(self, occurrence: PlannedOccurrence):
    """Обработка клика на карточку вхождения."""
    if self.on_occurrence_click:
        try:
            self.on_occurrence_click(occurrence)
        except Exception as e:
            logger.error(f"Ошибка при обработке клика на вхождение: {e}")
    else:
        logger.warning("Callback on_occurrence_click не установлен")
```

### Обработка невалидных данных

```python
def _build_occurrence_card(self, occurrence, category_name, tx_type):
    """Безопасное создание карточки с fallback значениями."""
    try:
        occ_date = occurrence.occurrence_date
    except AttributeError:
        logger.error(f"Вхождение без даты: {occurrence}")
        occ_date = datetime.date.today()
    
    try:
        amount = occurrence.amount
    except AttributeError:
        logger.error(f"Вхождение без суммы: {occurrence}")
        amount = 0.0
```

## Testing Strategy

### Unit Tests

1. **PlannedTransactionsWidget**
   - Тест инициализации с новым callback `on_occurrence_click`
   - Тест, что `_build_action_buttons` возвращает пустой список
   - Тест hover-эффекта на карточках
   - Тест сортировки просроченных вхождений

2. **HomeView**
   - Тест `on_occurrence_clicked` вызывает `presenter.on_date_selected`
   - Тест интеграции PlannedTransactionsWidget с новым callback

### Property-Based Tests

Используется библиотека **Hypothesis** для Python.

1. **Property 1**: Для любого сгенерированного вхождения, карточка не содержит кнопок действий
2. **Property 4**: Для любой даты в прошлом, карточка содержит метку "(просрочено)"
3. **Property 5**: Для любого списка вхождений, просроченные идут первыми

### Integration Tests

1. Клик на вхождение в PlannedTransactionsWidget → обновление CalendarWidget и TransactionsPanel
2. Исполнение вхождения в TransactionsPanel → обновление PlannedTransactionsWidget

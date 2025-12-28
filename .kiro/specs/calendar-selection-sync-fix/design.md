# Design Document

## Overview

Данный дизайн описывает решение проблемы синхронизации визуального выделения даты в календаре при клике на карточку плановой транзакции. Проблема заключается в том, что при клике на плановую транзакцию обновляется панель транзакций, но календарь не обновляет визуальное выделение выбранного дня.

**Текущее поведение:**
1. Пользователь кликает на карточку плановой транзакции
2. Вызывается `on_occurrence_clicked` в HomeView
3. HomeView делегирует в `presenter.on_date_selected(occurrence.occurrence_date)`
4. Presenter обновляет `selected_date` и вызывает `update_transactions`
5. Presenter вызывает `update_calendar_selection`
6. HomeView получает callback `update_calendar_selection` и вызывает `calendar_widget.select_date(date_obj)`
7. **ПРОБЛЕМА:** Calendar_Widget обновляет `selected_date`, но не перерисовывает сетку календаря

**Ожидаемое поведение:**
- Календарь должен визуально выделить дату вхождения
- Если дата в другом месяце, календарь должен переключиться на этот месяц
- Все компоненты должны быть синхронизированы

## Architecture

### Компоненты системы

```
┌─────────────────────────────────────────────────────────────┐
│                         HomeView                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Planned    │  │   Calendar   │  │   Transactions   │  │
│  │  Transactions│  │    Widget    │  │      Panel       │  │
│  │    Widget    │  │              │  │                  │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────┘  │
│         │                 │                                 │
│         │  on_occurrence  │                                 │
│         │    _clicked     │                                 │
│         └────────┬────────┘                                 │
│                  │                                           │
│                  ▼                                           │
│         ┌────────────────┐                                  │
│         │  HomePresenter │                                  │
│         └────────┬───────┘                                  │
│                  │                                           │
│                  │ update_calendar_selection                │
│                  │                                           │
│                  ▼                                           │
│         ┌────────────────┐                                  │
│         │ Calendar_Widget│                                  │
│         │  .select_date()│                                  │
│         └────────────────┘                                  │
└─────────────────────────────────────────────────────────────┘
```

### Последовательность вызовов

```
User Click on Planned Transaction Card
    │
    ▼
PlannedTransactionsWidget._on_card_click(occurrence)
    │
    ▼
HomeView.on_occurrence_clicked(occurrence)
    │
    ▼
HomePresenter.on_date_selected(occurrence.occurrence_date)
    │
    ├─▶ update selected_date
    │
    ├─▶ load transactions for date
    │
    ├─▶ callbacks.update_transactions(date, transactions, occurrences)
    │       │
    │       ▼
    │   TransactionsPanel.set_data(date, transactions, occurrences)
    │
    └─▶ callbacks.update_calendar_selection(date)
            │
            ▼
        CalendarWidget.select_date(date)
            │
            ├─▶ update selected_date
            │
            ├─▶ check if month changed
            │       │
            │       ├─▶ if yes: update current_date
            │       │           update_cash_gaps()
            │       │           update_pending_payments()
            │       │           update_loan_payments()
            │       │
            │       └─▶ if no: skip data reload
            │
            └─▶ _update_calendar() ← КРИТИЧЕСКИ ВАЖНО!
```


## Components and Interfaces

### CalendarWidget

**Текущая реализация метода `select_date`:**
```python
def select_date(self, date_obj: datetime.date):
    """
    Программный выбор даты (без вызова callback).
    
    Используется для синхронизации выделения при выборе даты из других компонентов.
    
    Args:
        date_obj: Дата для выбора
    """
    self.selected_date = date_obj
    
    # Если дата в другом месяце, переключаем месяц
    if date_obj.year != self.current_date.year or date_obj.month != self.current_date.month:
        self.current_date = date_obj.replace(day=1)
        # Обновляем данные для нового месяца
        self._update_cash_gaps()
        self._update_pending_payments()
        self._update_loan_payments()
    
    self._update_calendar()  # Перерисовываем для обновления выделения
```

**Проблема:** Метод `_update_calendar()` вызывается, но проверка `if not self.page:` в начале метода может блокировать перерисовку.

**Решение:** Убедиться, что `self.page` доступен и метод `update()` вызывается корректно.

### HomeView

**Реализация callback `update_calendar_selection`:**
```python
def update_calendar_selection(self, date_obj: datetime.date) -> None:
    """Обновить выделение даты в календаре."""
    self.calendar_widget.select_date(date_obj)
```

**Проблема:** Метод делегирует в `calendar_widget.select_date()`, но не проверяет результат.

**Решение:** Добавить логирование и обработку ошибок.

### HomePresenter

**Реализация `on_date_selected`:**
```python
def on_date_selected(self, selected_date: date) -> None:
    """Обработать выбор даты."""
    try:
        self.selected_date = selected_date
        transactions = transaction_service.get_transactions_by_date(self.session, selected_date)
        occurrences = planned_transaction_service.get_occurrences_by_date(self.session, selected_date)
        
        # Обновляем транзакции
        if hasattr(self.callbacks, 'update_transactions'):
            try:
                self.callbacks.update_transactions(selected_date, transactions, occurrences)
            except Exception as callback_error:
                logger.warning(f"Не удалось обновить транзакции: {callback_error}")
        
        # Обновляем выделение в календаре
        if hasattr(self.callbacks, 'update_calendar_selection'):
            try:
                self.callbacks.update_calendar_selection(selected_date)
            except Exception as callback_error:
                logger.warning(f"Не удалось обновить выделение в календаре: {callback_error}")
    except Exception as e:
        self._handle_error("Ошибка загрузки данных для выбранной даты", e)
```

**Проблема:** Обработка ошибок есть, но нет гарантии, что `update_calendar_selection` вызывается после `update_transactions`.

**Решение:** Убедиться в правильном порядке вызовов.


## Data Models

Не требуется изменений в моделях данных. Используются существующие модели:
- `PlannedOccurrence` - плановое вхождение с датой
- `datetime.date` - дата для выбора в календаре

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Синхронизация выделения календаря

*For any* плановое вхождение с датой, при клике на карточку вхождения календарь должен визуально выделить эту дату.

**Validates: Requirements 1.1, 1.3**

### Property 2: Переключение месяца при необходимости

*For any* дата вхождения, если дата находится в другом месяце, календарь должен переключиться на этот месяц и выделить дату.

**Validates: Requirements 1.4, 1.5**

### Property 3: Программное обновление без callback

*For any* дата, при вызове `select_date` программно, callback `on_date_selected` НЕ должен вызываться.

**Validates: Requirements 2.3**

### Property 4: Перерисовка календаря

*For any* дата, при вызове `select_date` метод `_update_calendar` должен быть вызван для перерисовки сетки.

**Validates: Requirements 2.4**

### Property 5: Последовательность обновлений

*For any* выбранная дата, Presenter должен сначала обновить транзакции, затем обновить выделение календаря.

**Validates: Requirements 3.2, 3.3, 3.4**

## Error Handling

### Ошибки при обновлении календаря

**Сценарий:** `calendar_widget.select_date()` вызывается, но `self.page` не инициализирован.

**Обработка:**
1. Метод `_update_calendar()` проверяет `if not self.page: return`
2. Логируется предупреждение в HomePresenter
3. Работа приложения продолжается без прерывания

### Ошибки при переключении месяца

**Сценарий:** Дата вхождения в другом месяце, но данные для нового месяца не загружаются.

**Обработка:**
1. Метод `select_date` вызывает `_update_cash_gaps()`, `_update_pending_payments()`, `_update_loan_payments()`
2. Каждый метод обрабатывает ошибки внутри `try-except`
3. При ошибке логируется сообщение и устанавливается пустой список
4. Календарь перерисовывается с доступными данными

### Ошибки в callback

**Сценарий:** `update_calendar_selection` вызывается, но возникает исключение.

**Обработка:**
1. HomePresenter оборачивает вызов в `try-except`
2. Логируется предупреждение с деталями ошибки
3. Работа продолжается, транзакции уже обновлены


## Testing Strategy

### Unit Tests

**CalendarWidget.select_date:**
- Тест выбора даты текущего месяца
- Тест выбора даты другого месяца
- Тест обновления `selected_date`
- Тест вызова `_update_calendar()`
- Тест НЕ вызова `on_date_selected` callback

**HomeView.update_calendar_selection:**
- Тест делегирования в `calendar_widget.select_date()`
- Тест с корректной датой
- Тест с датой другого месяца

**HomePresenter.on_date_selected:**
- Тест обновления `selected_date`
- Тест вызова `update_transactions`
- Тест вызова `update_calendar_selection`
- Тест правильного порядка вызовов
- Тест обработки ошибок

### Integration Tests

**Полный сценарий клика на плановую транзакцию:**
1. Создать HomeView с mock компонентами
2. Создать плановое вхождение с датой
3. Симулировать клик на карточку вхождения
4. Проверить, что `calendar_widget.select_date()` вызван с правильной датой
5. Проверить, что `transactions_panel.set_data()` вызван с правильной датой
6. Проверить, что `calendar_widget._update_calendar()` вызван

**Сценарий переключения месяца:**
1. Установить текущий месяц в календаре
2. Кликнуть на вхождение из другого месяца
3. Проверить, что календарь переключился на новый месяц
4. Проверить, что данные для нового месяца загружены
5. Проверить, что дата выделена в новом месяце

### Property-Based Tests

**Property 1: Синхронизация выделения для любой даты**
```python
@given(st.dates())
def test_calendar_selection_sync_property(date_obj):
    """
    **Feature: calendar-selection-sync-fix, Property 1: Синхронизация выделения календаря**
    **Validates: Requirements 1.1, 1.3**
    
    Property: For any дата, при клике на вхождение с этой датой,
    календарь должен выделить эту дату.
    """
    # Arrange
    mock_page = create_mock_page()
    mock_session = create_mock_session()
    home_view = HomeView(mock_page, mock_session)
    
    occurrence = Mock(occurrence_date=date_obj)
    
    # Act
    home_view.on_occurrence_clicked(occurrence)
    
    # Assert
    assert home_view.calendar_widget.selected_date == date_obj
```

**Property 2: Переключение месяца для любой даты**
```python
@given(st.dates(), st.dates())
def test_month_switch_property(current_date, target_date):
    """
    **Feature: calendar-selection-sync-fix, Property 2: Переключение месяца при необходимости**
    **Validates: Requirements 1.4, 1.5**
    
    Property: For any две даты, если они в разных месяцах,
    календарь должен переключиться на месяц целевой даты.
    """
    assume(current_date.month != target_date.month or current_date.year != target_date.year)
    
    # Arrange
    mock_page = create_mock_page()
    calendar = CalendarWidget(on_date_selected=Mock(), initial_date=current_date)
    calendar.page = mock_page
    
    # Act
    calendar.select_date(target_date)
    
    # Assert
    assert calendar.current_date.month == target_date.month
    assert calendar.current_date.year == target_date.year
    assert calendar.selected_date == target_date
```

**Property 3: Программное обновление без callback**
```python
@given(st.dates())
def test_select_date_no_callback_property(date_obj):
    """
    **Feature: calendar-selection-sync-fix, Property 3: Программное обновление без callback**
    **Validates: Requirements 2.3**
    
    Property: For any дата, при вызове select_date программно,
    callback on_date_selected НЕ должен вызываться.
    """
    # Arrange
    mock_callback = Mock()
    mock_page = create_mock_page()
    calendar = CalendarWidget(on_date_selected=mock_callback)
    calendar.page = mock_page
    
    # Act
    calendar.select_date(date_obj)
    
    # Assert
    mock_callback.assert_not_called()
```

### Test Configuration

- **Минимум 100 итераций** для каждого property-based теста
- **Hypothesis settings:** `max_examples=100, deadline=None`
- **Маркировка тестов:** `@pytest.mark.ui` для UI тестов
- **Coverage target:** 90%+ для изменённых компонентов


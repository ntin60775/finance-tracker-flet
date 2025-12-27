# Design Document: Flet Icon API Fix

## Overview

Исправление использования устаревшего Flet API для передачи иконок в компоненты `SegmentedButton` и `ft.Tab`. Проблема заключалась в том, что иконки передавались напрямую как `ft.Icons.XXX`, что вызывало ошибку при попытке Flet обработать их внутренним методом `_set_attr_internal`.

## Root Cause Analysis

### Проблема

При открытии модального окна плановой транзакции или использовании фильтров возникала ошибка:
```
AttributeError: 'Icons' object has no attribute '_set_attr_internal'
```

### Причина

В Flet >= 0.25.0 изменился способ передачи иконок в компоненты:
- **Старый способ (неправильный)**: `icon=ft.Icons.ARROW_CIRCLE_DOWN`
- **Новый способ (правильный)**: `icon=ft.Icon(ft.Icons.ARROW_CIRCLE_DOWN)`

Проблема возникала в следующих компонентах:
1. `SegmentedButton` в `planned_transaction_modal.py`
2. `SegmentedButton` в `categories_view.py`
3. `ft.Tab` в `categories_view.py`
4. `ft.Tab` в `planned_transactions_view.py`
5. `ft.Tab` в `pending_payments_view.py`
6. `ft.Tab` в `loan_details_view.py`

## Architecture

### Affected Components

```
src/finance_tracker/
├── components/
│   └── planned_transaction_modal.py  # SegmentedButton с иконками
└── views/
    ├── categories_view.py            # SegmentedButton + ft.Tab с иконками
    ├── planned_transactions_view.py  # ft.Tab с иконками
    ├── pending_payments_view.py      # ft.Tab с иконками
    └── loan_details_view.py          # ft.Tab с иконками
```

### Changes Required

Для каждого компонента необходимо обернуть иконки в `ft.Icon()`:

**SegmentedButton:**
```python
# Было (неправильно)
ft.Segment(
    value=TransactionType.EXPENSE.value,
    label=ft.Text("Расход"),
    icon=ft.Icons.ARROW_CIRCLE_DOWN,  # ❌
)

# Стало (правильно)
ft.Segment(
    value=TransactionType.EXPENSE.value,
    label=ft.Text("Расход"),
    icon=ft.Icon(ft.Icons.ARROW_CIRCLE_DOWN),  # ✅
)
```

**ft.Tab:**
```python
# Было (неправильно)
ft.Tab(text="Расходы", icon=ft.Icons.ARROW_CIRCLE_DOWN)  # ❌

# Стало (правильно)
ft.Tab(text="Расходы", icon=ft.Icon(ft.Icons.ARROW_CIRCLE_DOWN))  # ✅
```

## Components and Interfaces

### Modified Files

1. **planned_transaction_modal.py**
   - Компонент: `PlannedTransactionModal.__init__`
   - Изменение: `self.type_segment` - обёртка иконок в `ft.Icon()`

2. **categories_view.py**
   - Компонент: `CategoryDialog.__init__`
   - Изменение: `self.type_segment` - обёртка иконок в `ft.Icon()`
   - Компонент: `CategoriesView.__init__`
   - Изменение: `self.filter_tabs` - обёртка иконок в `ft.Icon()`

3. **planned_transactions_view.py**
   - Компонент: `PlannedTransactionsView.__init__`
   - Изменение: `self.type_filter_tabs` - обёртка иконок в `ft.Icon()`

4. **pending_payments_view.py**
   - Компонент: `PendingPaymentsView.__init__`
   - Изменение: `self.date_filter_tabs` - обёртка иконок в `ft.Icon()`

5. **loan_details_view.py**
   - Компонент: `LoanDetailsView.__init__`
   - Изменение: `self.tabs` - обёртка иконок в `ft.Icon()`

## Data Models

Изменения не затрагивают модели данных.

## Correctness Properties

*Свойство - это характеристика или поведение, которое должно выполняться во всех валидных выполнениях системы.*

### Property 1: Иконки в SegmentedButton корректно отображаются

*For any* SegmentedButton с иконками, все иконки должны быть обёрнуты в `ft.Icon()` и отображаться без ошибок.

**Validates: Requirements 1.2, 1.3**

### Property 2: Иконки в ft.Tab корректно отображаются

*For any* ft.Tab с иконками, все иконки должны быть обёрнуты в `ft.Icon()` и отображаться без ошибок.

**Validates: Requirements 2.1, 2.2, 2.3**

### Property 3: Модальные окна открываются без ошибок

*For any* модальное окно с SegmentedButton, открытие окна не должно вызывать `AttributeError`.

**Validates: Requirements 1.1**

### Property 4: Совместимость с Flet API

*For any* компонент, использующий иконки, должен использовать актуальный Flet API (>= 0.25.0).

**Validates: Requirements 3.1, 3.2, 3.3**

## Error Handling

### Предотвращённые ошибки

1. **AttributeError при открытии модальных окон**
   - Причина: Неправильная передача иконок в SegmentedButton
   - Решение: Обёртка иконок в `ft.Icon()`

2. **AttributeError при переключении вкладок**
   - Причина: Неправильная передача иконок в ft.Tab
   - Решение: Обёртка иконок в `ft.Icon()`

### Обработка ошибок

Изменения не требуют дополнительной обработки ошибок, так как исправляют корневую причину проблемы.

## Testing Strategy

### Unit Tests

Не требуются, так как это исправление синтаксиса API, а не логики.

### Manual Testing

1. **Тест открытия модального окна плановой транзакции:**
   - Открыть главный экран
   - Нажать кнопку "+" для добавления плановой транзакции
   - Проверить, что модальное окно открывается без ошибок
   - Проверить, что SegmentedButton с иконками отображается корректно

2. **Тест фильтров в разделе категорий:**
   - Открыть раздел "Категории"
   - Переключить вкладки "Все" → "Расходы" → "Доходы"
   - Проверить, что иконки отображаются корректно
   - Проверить отсутствие ошибок в логах

3. **Тест фильтров в разделе плановых транзакций:**
   - Открыть раздел "Плановые транзакции"
   - Переключить вкладки с фильтрами
   - Проверить корректное отображение иконок

4. **Тест фильтров в разделе отложенных платежей:**
   - Открыть раздел "Отложенные платежи"
   - Переключить вкладки с фильтрами
   - Проверить корректное отображение иконок

5. **Тест вкладок в деталях кредита:**
   - Открыть любой кредит
   - Переключить вкладки "График платежей" ↔ "История"
   - Проверить корректное отображение иконок

### Regression Testing

Убедиться, что исправление не сломало существующую функциональность:
- Все модальные окна открываются корректно
- Все фильтры работают как ожидается
- Иконки отображаются во всех компонентах

## Implementation Notes

### Best Practices

1. **Всегда обёртывать иконки в ft.Icon()** при передаче в компоненты Flet
2. **Проверять актуальность API** перед использованием новых компонентов
3. **Тестировать UI изменения** вручную перед коммитом

### Future Considerations

При добавлении новых компонентов с иконками:
- Использовать `ft.Icon(ft.Icons.XXX)` вместо `ft.Icons.XXX`
- Проверять документацию Flet для актуального синтаксиса
- Добавлять проверку в code review

## References

- Flet Documentation: https://flet.dev/docs/
- Flet Icons: https://flet.dev/docs/controls/icon
- Flet SegmentedButton: https://flet.dev/docs/controls/segmentedbutton
- Flet Tabs: https://flet.dev/docs/controls/tabs

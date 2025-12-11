# Design Document

## Overview

Данный документ описывает дизайн решения для исправления неработающей кнопки добавления транзакции в HomeView и создания комплексных тестов для предотвращения регрессий. Проблема заключается в том, что кнопка с иконкой "+" в правом верхнем углу панели транзакций не открывает модальное окно создания транзакции при нажатии.

Решение включает:
1. Диагностику и исправление проблемы с кнопкой
2. Создание unit-тестов для кнопки и её взаимодействия с модальным окном
3. Создание интеграционных тестов для проверки полного пользовательского сценария
4. Создание property-based тестов для универсальных свойств

## Architecture

### Компоненты системы

```
HomeView
├── TransactionsPanel (правая колонка)
│   ├── Header Row
│   │   ├── Date Text
│   │   └── Add Button (+) ← ПРОБЛЕМНАЯ КНОПКА
│   ├── Summary Row
│   └── Transactions List
├── TransactionModal (модальное окно)
└── HomePresenter (бизнес-логика)
```

### Поток данных при нажатии кнопки

```
1. User clicks Add Button
2. TransactionsPanel.on_add_transaction() callback
3. HomeView.open_add_transaction_modal()
4. TransactionModal.open(page, selected_date)
5. Modal opens with pre-filled date
6. User fills form and saves
7. HomeView.on_transaction_saved(data)
8. HomePresenter.create_transaction(data)
9. UI updates with new transaction
```

## Components and Interfaces

### TransactionsPanel

**Ответственность:** Отображение списка транзакций за выбранный день и предоставление кнопки для добавления новой транзакции.

**Ключевые методы:**
- `__init__(on_add_transaction: Callable[[], None])` - инициализация с callback
- `_build_header()` - создание заголовка с кнопкой добавления
- `set_data(date, transactions, occurrences)` - обновление данных

**Кнопка добавления:**
```python
ft.IconButton(
    icon=ft.Icons.ADD,
    on_click=lambda _: self.on_add_transaction(),
    tooltip="Добавить транзакцию",
    bgcolor=ft.Colors.PRIMARY,
    icon_color=ft.Colors.ON_PRIMARY,
)
```

### HomeView

**Ответственность:** Координация взаимодействия между компонентами и управление модальными окнами.

**Ключевые методы:**
- `open_add_transaction_modal()` - открытие модального окна создания транзакции
- `on_transaction_saved(data)` - обработка сохранения новой транзакции

### TransactionModal

**Ответственность:** Предоставление интерфейса для создания/редактирования транзакций.

**Ключевые методы:**
- `open(page, date)` - открытие модального окна с предустановленной датой
- `_validate_form()` - валидация данных формы
- `_save_transaction()` - сохранение транзакции

## Data Models

### TransactionCreate (Pydantic модель)

```python
class TransactionCreate(BaseModel):
    amount: Decimal = Field(gt=0, description="Сумма транзакции (больше 0)")
    type: TransactionType = Field(description="Тип транзакции (доход/расход)")
    category_id: int = Field(description="ID категории")
    description: Optional[str] = Field(None, max_length=500, description="Описание")
    date: date = Field(description="Дата транзакции")
```

### UI State Models

```python
class ModalState:
    is_open: bool = False
    mode: str = "create"  # "create" | "edit"
    selected_date: Optional[date] = None
    validation_errors: Dict[str, str] = {}

class ButtonState:
    is_visible: bool = True
    is_enabled: bool = True
    callback: Optional[Callable] = None
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Button Click Opens Modal
*For any* valid HomeView with TransactionsPanel, when the add transaction button is clicked, the TransactionModal should open with the current selected date
**Validates: Requirements 1.1, 1.3**

### Property 2: Callback Integration
*For any* valid callback function passed to TransactionsPanel, when the add button is clicked, that callback should be invoked exactly once
**Validates: Requirements 3.1, 3.2**

### Property 3: Modal Parameter Passing
*For any* valid date and page object, when TransactionModal.open() is called, both parameters should be correctly stored and used for form initialization
**Validates: Requirements 3.3, 3.4**

### Property 4: Button Initialization Robustness
*For any* valid callback function, when TransactionsPanel is created with that callback, the add button should be properly initialized and functional
**Validates: Requirements 4.1, 4.3**

### Property 5: Multiple Click Handling
*For any* sequence of button clicks, each click should trigger the callback independently without interference
**Validates: Requirements 4.4**

### Property 6: Form Validation State
*For any* combination of form field values, the save button state should correctly reflect whether all validation rules are satisfied
**Validates: Requirements 5.2, 6.5**

### Property 7: Transaction Creation Round Trip
*For any* valid transaction data, when saved through the modal, the transaction should be created in the database and appear in the UI
**Validates: Requirements 5.3, 5.5**

### Property 8: Modal Closure Behavior
*For any* method of closing the modal (save, cancel, escape), the modal should close and the UI should return to the correct state
**Validates: Requirements 5.4, 7.1**

### Property 9: Data Persistence on Cancel
*For any* transaction list state, when the modal is cancelled without saving, the original transaction list should remain unchanged
**Validates: Requirements 7.4**

### Property 10: Form Reset on Cancel
*For any* form data entered in the modal, when cancelled, all form fields should be cleared for the next use
**Validates: Requirements 7.5**

### Property 11: Error Handling Robustness
*For any* error condition (null callback, exception in callback, missing page), the button should handle it gracefully without crashing the application
**Validates: Requirements 8.1, 8.2, 8.4**

## Error Handling

### Button-Level Error Handling

1. **Null Callback Protection:**
   ```python
   on_click=lambda _: self.on_add_transaction() if self.on_add_transaction else None
   ```

2. **Exception Wrapping:**
   ```python
   def safe_open_modal(self):
       try:
           self.open_add_transaction_modal()
       except Exception as e:
           logger.error(f"Ошибка при открытии модального окна: {e}")
           self.show_error("Не удалось открыть форму создания транзакции")
   ```

### Modal-Level Error Handling

1. **Validation Error Display:**
   - Показ ошибок валидации рядом с соответствующими полями
   - Блокировка кнопки сохранения при наличии ошибок

2. **Database Error Handling:**
   - Обработка ошибок сохранения в базу данных
   - Показ пользователю понятных сообщений об ошибках

3. **UI State Recovery:**
   - Восстановление корректного состояния UI при ошибках
   - Предотвращение "зависания" модального окна

## Testing Strategy

### Unit Tests

**Цель:** Проверка изолированной функциональности отдельных компонентов.

**Тесты для TransactionsPanel:**
- Инициализация кнопки с корректными атрибутами
- Вызов callback при нажатии на кнопку
- Обработка null callback

**Тесты для HomeView:**
- Передача корректного callback в TransactionsPanel
- Открытие TransactionModal с правильными параметрами
- Обработка сохранения транзакции

**Тесты для TransactionModal:**
- Инициализация формы с предустановленной датой
- Валидация полей формы
- Сохранение валидных данных
- Отмена без сохранения

### Property-Based Tests

**Цель:** Проверка универсальных свойств системы на большом количестве случайных входных данных.

**Используемая библиотека:** Hypothesis для Python

**Конфигурация:** Минимум 50 итераций для каждого property-теста

**Генераторы данных:**
```python
@given(
    date=st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31)),
    amount=st.decimals(min_value=Decimal('0.01'), max_value=Decimal('999999.99')),
    description=st.text(max_size=500)
)
```

**Property тесты:**
- Button Click Opens Modal (Property 1)
- Callback Integration (Property 2)
- Modal Parameter Passing (Property 3)
- Button Initialization Robustness (Property 4)
- Multiple Click Handling (Property 5)
- Form Validation State (Property 6)
- Transaction Creation Round Trip (Property 7)
- Modal Closure Behavior (Property 8)
- Data Persistence on Cancel (Property 9)
- Form Reset on Cancel (Property 10)
- Error Handling Robustness (Property 11)

### Integration Tests

**Цель:** Проверка полного пользовательского сценария от нажатия кнопки до создания транзакции.

**Сценарии:**
1. **Happy Path:** Нажатие кнопки → заполнение формы → сохранение → обновление UI
2. **Validation Errors:** Нажатие кнопки → некорректные данные → показ ошибок → исправление → сохранение
3. **Cancellation:** Нажатие кнопки → заполнение формы → отмена → проверка неизменности данных
4. **Error Recovery:** Нажатие кнопки → ошибка сохранения → показ ошибки → повторная попытка

### Test Infrastructure

**Mock Objects:**
- Mock Page для изоляции от Flet UI
- Mock Session для изоляции от базы данных
- Mock Services для изоляции от бизнес-логики

**Test Fixtures:**
- `mock_page` - мокированная страница Flet
- `mock_session` - мокированная сессия БД
- `sample_transaction_data` - тестовые данные транзакций
- `mock_categories` - тестовые категории

**Assertion Helpers:**
```python
def assert_modal_opened(mock_page, expected_date):
    """Проверяет, что модальное окно было открыто с правильной датой."""
    
def assert_transaction_created(mock_session, expected_data):
    """Проверяет, что транзакция была создана с правильными данными."""
    
def assert_ui_updated(home_view, expected_transaction_count):
    """Проверяет, что UI был обновлен после создания транзакции."""
```
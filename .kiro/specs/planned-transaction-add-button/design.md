# Design Document: Кнопка добавления плановых транзакций

## Обзор

Данный документ описывает дизайн функциональности добавления кнопки для создания новых плановых транзакций на панели плановых транзакций главного экрана. Функциональность позволяет пользователю быстро создавать плановые транзакции без перехода в отдельный раздел.

## Архитектура

### Паттерн MVP

Реализация следует паттерну MVP (Model-View-Presenter), уже используемому в HomeView:

```
┌─────────────────────────────────────────────────────────────────┐
│                         HomeView                                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ PlannedTransactionsWidget                               │    │
│  │  ┌─────────────────────────────────────────────────────┐│    │
│  │  │ Header: [Title] [+Add] [Show All]                   ││    │
│  │  └─────────────────────────────────────────────────────┘│    │
│  │  ┌─────────────────────────────────────────────────────┐│    │
│  │  │ Occurrences List                                    ││    │
│  │  └─────────────────────────────────────────────────────┘│    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ PlannedTransactionModal                                 │    │
│  │  - Форма создания плановой транзакции                   │    │
│  │  - Правила повторения                                   │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       HomePresenter                             │
│  - create_planned_transaction(data)                             │
│  - refresh_data()                                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 planned_transaction_service                     │
│  - create_planned_transaction(session, data)                    │
└─────────────────────────────────────────────────────────────────┘
```

### Поток данных

1. Пользователь нажимает кнопку "+" в виджете плановых транзакций
2. `PlannedTransactionsWidget` вызывает callback `on_add_planned_transaction`
3. `HomeView.on_add_planned_transaction()` открывает `PlannedTransactionModal`
4. Пользователь заполняет форму и нажимает "Сохранить"
5. `PlannedTransactionModal` вызывает callback `on_save` с данными `PlannedTransactionCreate`
6. `HomeView.on_planned_transaction_saved()` делегирует в `HomePresenter.create_planned_transaction()`
7. `HomePresenter` вызывает `planned_transaction_service.create_planned_transaction()`
8. При успехе `HomePresenter` вызывает `refresh_data()` для обновления всех компонентов
9. `HomeView` показывает SnackBar с сообщением об успехе

## Компоненты и интерфейсы

### PlannedTransactionsWidget (модификация)

```python
class PlannedTransactionsWidget(ft.Container):
    """
    Виджет для отображения ближайших плановых вхождений.
    
    Изменения:
    - Добавлен callback on_add_planned_transaction
    - Добавлена кнопка "+" в заголовок
    """
    
    def __init__(
        self,
        session: Session,
        on_execute: Callable[[PlannedOccurrence], None],
        on_skip: Callable[[PlannedOccurrence], None],
        on_show_all: Callable[[], None],
        on_add_planned_transaction: Optional[Callable[[], None]] = None,  # НОВЫЙ
    ):
        """
        Args:
            on_add_planned_transaction: Callback для добавления новой плановой транзакции.
                                        Если None, кнопка добавления не отображается.
        """
        ...
    
    def _build_header(self) -> ft.Row:
        """
        Построение заголовка виджета.
        
        Returns:
            Row с заголовком, кнопкой добавления и кнопкой "Показать все"
        """
        controls = [self.title_text]
        
        # Кнопка добавления (если callback задан)
        if self.on_add_planned_transaction:
            add_button = ft.IconButton(
                icon=ft.Icons.ADD,
                icon_color=ft.Colors.PRIMARY,
                tooltip="Добавить плановую транзакцию",
                on_click=lambda _: self.on_add_planned_transaction()
            )
            controls.append(add_button)
        
        controls.append(self.show_all_button)
        
        return ft.Row(
            controls=controls,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
```

### HomeView (модификация)

```python
class HomeView(ft.Column, IHomeViewCallbacks):
    """
    Главный экран приложения.
    
    Изменения:
    - Добавлен PlannedTransactionModal
    - Добавлен метод on_add_planned_transaction
    - Добавлен метод on_planned_transaction_saved
    - Обновлена инициализация PlannedTransactionsWidget
    """
    
    def __init__(self, page: ft.Page, session: Session):
        ...
        # Модальное окно плановых транзакций
        self.planned_transaction_modal = PlannedTransactionModal(
            session=self.session,
            on_save=self.on_planned_transaction_saved
        )
        
        # Обновлённый виджет с callback добавления
        self.planned_widget = PlannedTransactionsWidget(
            session=self.session,
            on_execute=self.on_execute_occurrence,
            on_skip=self.on_skip_occurrence,
            on_show_all=self.on_show_all_occurrences,
            on_add_planned_transaction=self.on_add_planned_transaction  # НОВЫЙ
        )
    
    def on_add_planned_transaction(self):
        """
        Открытие модального окна добавления плановой транзакции.
        
        Вызывается при нажатии кнопки "+" в виджете плановых транзакций.
        """
        try:
            logger.debug("Открытие модального окна добавления плановой транзакции")
            
            if not self.page:
                logger.error("Page не инициализирована")
                return
                
            self.planned_transaction_modal.open(self.page, self.selected_date)
            logger.info("Модальное окно добавления плановой транзакции открыто")
            
        except Exception as e:
            logger.error(f"Ошибка при открытии модального окна: {e}", exc_info=True)
            self.show_error("Не удалось открыть форму добавления плановой транзакции")
    
    def on_planned_transaction_saved(self, data: PlannedTransactionCreate):
        """
        Обработка сохранения новой плановой транзакции.
        
        Args:
            data: Данные для создания плановой транзакции.
        """
        self.presenter.create_planned_transaction(data)
```

### HomePresenter (модификация)

```python
class HomePresenter:
    """
    Presenter для главного экрана.
    
    Изменения:
    - Добавлен метод create_planned_transaction
    """
    
    def create_planned_transaction(self, data: PlannedTransactionCreate):
        """
        Создание новой плановой транзакции.
        
        Args:
            data: Данные для создания плановой транзакции.
        """
        try:
            logger.info(f"Создание плановой транзакции: {data.description or 'без описания'}")
            
            # Создаём плановую транзакцию через сервис
            planned_tx = create_planned_transaction(self.session, data)
            
            logger.info(f"Плановая транзакция создана: {planned_tx.id}")
            
            # Обновляем все данные
            self.refresh_data()
            
            # Показываем уведомление об успехе
            self.view.show_message("Плановая транзакция успешно создана")
            
        except Exception as e:
            logger.error(f"Ошибка при создании плановой транзакции: {e}", exc_info=True)
            self.view.show_error(f"Ошибка при создании плановой транзакции: {e}")
```

## Модели данных

Используются существующие модели:

- `PlannedTransactionCreate` - Pydantic модель для создания плановой транзакции
- `RecurrenceRuleCreate` - Pydantic модель для правила повторения
- `PlannedTransactionDB` - SQLAlchemy модель плановой транзакции
- `PlannedOccurrence` - Pydantic модель вхождения

## Correctness Properties

*Свойство (property) — это характеристика или поведение, которое должно выполняться для всех валидных входных данных системы. Свойства служат мостом между человекочитаемыми спецификациями и машинно-проверяемыми гарантиями корректности.*

### Property 1: Callback вызывается при нажатии кнопки добавления

*Для любого* виджета `PlannedTransactionsWidget` с заданным callback `on_add_planned_transaction`, при нажатии кнопки добавления callback должен быть вызван ровно один раз.

**Validates: Requirements 1.2, 3.2**

### Property 2: Создание плановой транзакции сохраняет данные в БД

*Для любых* валидных данных `PlannedTransactionCreate`, после вызова `create_planned_transaction` в базе данных должна появиться запись с соответствующими полями (amount, type, category_id, start_date).

**Validates: Requirements 1.3**

### Property 3: После создания транзакции обновляются все зависимые компоненты

*Для любой* успешно созданной плановой транзакции, система должна вызвать методы обновления виджета плановых транзакций и календаря.

**Validates: Requirements 1.4, 3.3, 4.1, 4.2**

### Property 4: При ошибке создания показывается сообщение и модальное окно остаётся открытым

*Для любой* ошибки при создании плановой транзакции (ошибка БД, валидации), система должна показать сообщение об ошибке пользователю, и модальное окно должно остаться открытым для исправления данных.

**Validates: Requirements 3.4, 5.2, 5.3**

## Обработка ошибок

### Ошибки валидации

- Обрабатываются в `PlannedTransactionModal._validate_fields()`
- Отображаются как `error_text` на соответствующих полях
- Модальное окно остаётся открытым

### Ошибки базы данных

- Перехватываются в `HomePresenter.create_planned_transaction()`
- Логируются с полным контекстом
- Отображаются пользователю через `view.show_error()`

### Ошибки UI

- Перехватываются в `HomeView.on_add_planned_transaction()`
- Логируются с exc_info
- Отображаются через SnackBar

## Стратегия тестирования

### Unit тесты

1. **Тесты PlannedTransactionsWidget:**
   - Проверка наличия кнопки добавления в заголовке
   - Проверка атрибутов кнопки (icon, tooltip)
   - Проверка вызова callback при нажатии
   - Проверка отсутствия кнопки при callback=None

2. **Тесты HomeView:**
   - Проверка инициализации PlannedTransactionModal
   - Проверка открытия модального окна
   - Проверка делегирования в Presenter

3. **Тесты HomePresenter:**
   - Проверка вызова сервиса создания
   - Проверка вызова refresh_data после создания
   - Проверка обработки ошибок

### Property-based тесты

Используется библиотека **Hypothesis** для Python.

1. **Property 1:** Генерация случайных callback функций, проверка вызова
2. **Property 2:** Генерация случайных PlannedTransactionCreate, проверка создания в БД
3. **Property 3:** Генерация случайных транзакций, проверка вызовов обновления
4. **Property 4:** Симуляция ошибок, проверка поведения

### Интеграционные тесты

1. Полный цикл создания плановой транзакции через UI
2. Проверка обновления виджета после создания
3. Проверка отображения вхождений в календаре

## Зависимости

- `PlannedTransactionModal` - уже реализован, использует современный Flet API
- `planned_transaction_service.create_planned_transaction` - уже реализован
- `HomePresenter` - требует добавления метода `create_planned_transaction`
- `PlannedTransactionsWidget` - требует модификации для добавления кнопки
- `HomeView` - требует модификации для интеграции

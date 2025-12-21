# Design Document: Кнопка добавления отложенных платежей

## Обзор

Данный дизайн описывает реализацию функционала добавления кнопки для создания новых отложенных платежей на панели отложенных платежей главного экрана, а также исправление нерабочей кнопки "Показать всё".

## Архитектура

### Паттерн MVP

Проект использует паттерн Model-View-Presenter:
- **Model**: `PendingPaymentDB`, `PendingPaymentCreate` (уже существуют)
- **View**: `HomeView`, `PendingPaymentsWidget` (требуют модификации)
- **Presenter**: `HomePresenter` (требует добавления метода)

### Компоненты

1. **PendingPaymentsWidget** - виджет отображения отложенных платежей
2. **PendingPaymentModal** - модальное окно создания/редактирования платежа (уже существует)
3. **HomeView** - главный экран приложения
4. **HomePresenter** - презентер с бизнес-логикой
5. **pending_payment_service** - сервис работы с БД (уже существует)

## Компоненты и интерфейсы

### 1. PendingPaymentsWidget

**Изменения:**
- Добавить кнопку "Добавить платёж" в заголовок
- Добавить callback `on_add_payment` в конструктор
- Обновить layout заголовка

**Новый интерфейс:**
```python
class PendingPaymentsWidget(ft.Container):
    def __init__(
        self,
        session: Session,
        on_execute: Callable[[PendingPaymentDB], None],
        on_cancel: Callable[[PendingPaymentDB], None],
        on_delete: Callable[[int], None],
        on_show_all: Callable[[], None],
        on_add_payment: Callable[[], None],  # НОВЫЙ параметр
    ):
        ...
```

**Новый UI элемент:**
```python
self.add_payment_button = ft.IconButton(
    icon=ft.Icons.ADD,
    tooltip="Добавить отложенный платёж",
    icon_color=ft.Colors.PRIMARY,
    on_click=lambda _: self.on_add_payment()
)
```


**Обновлённый layout заголовка:**
```python
ft.Row(
    controls=[
        ft.Column(
            controls=[
                self.title_text,
                self.stats_text,
            ],
            spacing=2,
        ),
        ft.Row(
            controls=[
                self.add_payment_button,  # НОВАЯ кнопка
                self.show_all_button,
            ],
            spacing=5,
        ),
    ],
    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
)
```

### 2. HomeView

**Изменения:**
- Обновить инициализацию `PendingPaymentsWidget` с новым callback
- Обновить инициализацию `PendingPaymentModal` с правильным callback
- Добавить метод `on_add_pending_payment` для открытия модального окна
- Добавить метод `on_pending_payment_saved` для обработки сохранения
- Реализовать метод `on_show_all_payments` для навигации

**Новые методы:**
```python
def on_add_pending_payment(self):
    """Открытие модального окна добавления отложенного платежа."""
    try:
        logger.debug("Открытие модального окна добавления отложенного платежа")
        
        if not self.page:
            logger.error("Page не инициализирована")
            return
            
        if not self.payment_modal:
            logger.error("PendingPaymentModal не инициализирован")
            return
            
        self.payment_modal.open(self.page)
        logger.info("Модальное окно добавления отложенного платежа открыто")
        
    except Exception as e:
        logger.error(f"Ошибка при открытии модального окна: {e}", exc_info=True)
        if self.page:
            self.page.open(ft.SnackBar(
                content=ft.Text("Не удалось открыть форму добавления платежа"),
                bgcolor=ft.Colors.ERROR
            ))

def on_pending_payment_saved(self, data: PendingPaymentCreate):
    """Обработка сохранения нового отложенного платежа."""
    self.presenter.create_pending_payment(data)

def on_show_all_payments(self):
    """Переход к разделу всех отложенных платежей."""
    try:
        logger.info("Переход к разделу отложенных платежей")
        # Вызываем метод главного окна для переключения раздела
        if hasattr(self.page, 'window') and hasattr(self.page.window, 'navigate_to_pending_payments'):
            self.page.window.navigate_to_pending_payments()
        else:
            logger.warning("Навигация к разделу отложенных платежей не реализована")
            self.page.open(ft.SnackBar(
                content=ft.Text("Раздел 'Отложенные платежи' в разработке")
            ))
    except Exception as e:
        logger.error(f"Ошибка при переходе к разделу отложенных платежей: {e}")
```

**Обновлённая инициализация компонентов:**
```python
# В __init__ HomeView
self.pending_payments_widget = PendingPaymentsWidget(
    session=self.session,
    on_execute=self.on_execute_payment,
    on_cancel=self.on_cancel_payment,
    on_delete=self.on_delete_payment,
    on_show_all=self.on_show_all_payments,
    on_add_payment=self.on_add_pending_payment,  # НОВЫЙ callback
)

self.payment_modal = PendingPaymentModal(
    session=self.session,
    on_save=self.on_pending_payment_saved,  # ОБНОВЛЁННЫЙ callback
    on_update=lambda _, __: None  # Не используется на главном экране
)
```

### 3. HomePresenter

**Новый метод:**
```python
def create_pending_payment(self, payment_data: PendingPaymentCreate) -> None:
    """
    Создать новый отложенный платёж.
    
    Args:
        payment_data: Данные для создания платежа
    """
    try:
        logger.debug(f"Создание отложенного платежа: {payment_data}")
        
        pending_payment_service.create_pending_payment(self.session, payment_data)
        self.session.commit()
        
        logger.info("Отложенный платёж успешно создан")
        self._refresh_data()
        self.callbacks.show_message("Отложенный платёж успешно создан")
        
    except ValueError as ve:
        self.session.rollback()
        logger.error(f"Ошибка валидации при создании платежа: {ve}")
        self.callbacks.show_error(f"Ошибка валидации: {str(ve)}")
    except Exception as e:
        self.session.rollback()
        logger.error(f"Ошибка создания отложенного платежа: {e}", exc_info=True)
        self._handle_error("Ошибка создания отложенного платежа", e)
```

### 4. MainWindow (опционально)

**Новый метод для навигации:**
```python
def navigate_to_pending_payments(self):
    """Переключение на раздел отложенных платежей."""
    try:
        # Устанавливаем активный раздел
        self.current_view = "pending_payments"
        
        # Обновляем навигационную панель
        self._update_navigation_highlight()
        
        # Переключаем отображаемый контент
        self._switch_to_pending_payments_view()
        
        logger.info("Переключено на раздел отложенных платежей")
    except Exception as e:
        logger.error(f"Ошибка при переключении на раздел: {e}")
```

## Модели данных

### PendingPaymentCreate (уже существует)

```python
class PendingPaymentCreate(BaseModel):
    amount: Decimal
    category_id: str
    description: str
    priority: PendingPaymentPriority = PendingPaymentPriority.MEDIUM
    planned_date: Optional[date] = None
```

## Correctness Properties

*Свойство (property) - это характеристика или поведение, которое должно выполняться для всех валидных выполнений системы - по сути, формальное утверждение о том, что система должна делать. Свойства служат мостом между человекочитаемыми спецификациями и машинно-проверяемыми гарантиями корректности.*


### Property 1: Создание платежа сохраняет в БД

*For any* валидные данные отложенного платежа (сумма > 0, существующая категория EXPENSE, непустое описание), создание платежа через Presenter должно привести к появлению записи в базе данных с соответствующими данными.

**Validates: Requirements 1.3**

### Property 2: Создание платежа обновляет виджет

*For any* созданный отложенный платёж, виджет отложенных платежей должен обновить свой список и включить новый платёж в отображение.

**Validates: Requirements 1.4, 5.1**

### Property 3: Создание платежа обновляет статистику

*For any* созданный отложенный платёж, статистика виджета (total_active, total_amount) должна увеличиться на 1 и на сумму платежа соответственно.

**Validates: Requirements 5.2**

### Property 4: Платёж с датой отображается в календаре

*For any* отложенный платёж с установленной плановой датой, календарь должен отобразить индикатор платежа на соответствующей дате после создания.

**Validates: Requirements 5.3**

### Property 5: Каскадное обновление компонентов

*For any* операция создания платежа через Presenter, должны обновиться все зависимые компоненты: виджет отложенных платежей, календарь, статистика.

**Validates: Requirements 3.3**

### Property 6: Валидация пустых полей

*For any* попытка создания платежа с пустыми обязательными полями (amount = 0, description = "", category_id = None), система должна показать сообщения об ошибках валидации и не создавать запись в БД.

**Validates: Requirements 6.1**

### Property 7: Раздел отложенных платежей показывает все платежи

*For any* набор отложенных платежей в БД (активные, отменённые, исполненные), раздел "Отложенные платежи" должен отображать все платежи с возможностью фильтрации по статусу.

**Validates: Requirements 2.2, 7.3**

## Обработка ошибок

### Ошибки валидации

**Сценарий:** Пользователь пытается создать платёж с невалидными данными

**Обработка:**
1. Модальное окно выполняет валидацию на клиенте
2. При ошибках показываются сообщения в полях формы
3. Кнопка "Сохранить" остаётся активной для исправления
4. Модальное окно остаётся открытым

**Примеры ошибок:**
- Сумма <= 0: "Сумма должна быть больше 0"
- Пустое описание: "Введите описание"
- Не выбрана категория: "Выберите категорию"

### Ошибки базы данных

**Сценарий:** Ошибка при сохранении в БД (например, категория удалена)

**Обработка:**
1. Presenter ловит исключение от сервиса
2. Выполняется rollback транзакции
3. Вызывается `callbacks.show_error()` с описанием ошибки
4. Модальное окно остаётся открытым
5. Логируется полная информация об ошибке

**Пример:**
```python
try:
    pending_payment_service.create_pending_payment(self.session, payment_data)
    self.session.commit()
except ValueError as ve:
    self.session.rollback()
    self.callbacks.show_error(f"Ошибка валидации: {str(ve)}")
except SQLAlchemyError as e:
    self.session.rollback()
    self.callbacks.show_error("Ошибка при сохранении платежа")
    logger.error(f"DB error: {e}", exc_info=True)
```

### Ошибки навигации

**Сценарий:** Раздел "Отложенные платежи" ещё не реализован

**Обработка:**
1. Проверка наличия метода навигации
2. Если метод отсутствует - показать SnackBar с сообщением
3. Логировать предупреждение

**Пример:**
```python
if hasattr(self.page, 'window') and hasattr(self.page.window, 'navigate_to_pending_payments'):
    self.page.window.navigate_to_pending_payments()
else:
    logger.warning("Навигация не реализована")
    self.page.open(ft.SnackBar(
        content=ft.Text("Раздел 'Отложенные платежи' в разработке")
    ))
```

## Стратегия тестирования

### Unit Tests

**Тесты для PendingPaymentsWidget:**
1. `test_add_payment_button_exists` - проверка наличия кнопки
2. `test_add_payment_button_attributes` - проверка атрибутов кнопки (иконка, tooltip, цвет)
3. `test_add_payment_button_callback` - проверка вызова callback при нажатии
4. `test_show_all_button_callback` - проверка вызова callback "Показать всё"

**Тесты для HomeView:**
1. `test_pending_payment_modal_initialization` - проверка инициализации модального окна
2. `test_open_add_payment_modal` - проверка открытия модального окна
3. `test_pending_payment_saved_callback` - проверка обработки сохранения
4. `test_show_all_payments_navigation` - проверка навигации

**Тесты для HomePresenter:**
1. `test_create_pending_payment_success` - успешное создание платежа
2. `test_create_pending_payment_validation_error` - ошибка валидации
3. `test_create_pending_payment_db_error` - ошибка БД
4. `test_create_pending_payment_updates_components` - обновление компонентов

### Property-Based Tests

**Property 1: Создание платежа с валидными данными**
```python
@given(
    amount=st.decimals(min_value=Decimal('0.01'), max_value=Decimal('999999.99')),
    description=st.text(min_size=1, max_size=500),
    priority=st.sampled_from(list(PendingPaymentPriority))
)
def test_create_payment_saves_to_db(amount, description, priority):
    """
    **Feature: pending-payment-add-button, Property 1: Создание платежа сохраняет в БД**
    **Validates: Requirements 1.3**
    
    Property: Для любых валидных данных создание платежа должно сохранить запись в БД.
    """
    # Arrange
    with get_db_session() as session:
        category = create_test_category(session, type=TransactionType.EXPENSE)
        payment_data = PendingPaymentCreate(
            amount=amount,
            category_id=category.id,
            description=description,
            priority=priority
        )
        
        # Act
        payment = pending_payment_service.create_pending_payment(session, payment_data)
        session.commit()
        
        # Assert
        saved_payment = session.query(PendingPaymentDB).filter_by(id=payment.id).first()
        assert saved_payment is not None
        assert saved_payment.amount == amount
        assert saved_payment.description == description.strip()
        assert saved_payment.priority == priority
```

**Property 2: Обновление виджета после создания**
```python
@given(
    amount=st.decimals(min_value=Decimal('0.01'), max_value=Decimal('999999.99')),
    description=st.text(min_size=1, max_size=500)
)
def test_create_payment_updates_widget(amount, description):
    """
    **Feature: pending-payment-add-button, Property 2: Создание платежа обновляет виджет**
    **Validates: Requirements 1.4, 5.1**
    
    Property: Для любого созданного платежа виджет должен обновиться.
    """
    # Arrange
    mock_callbacks = Mock()
    with get_db_session() as session:
        presenter = HomePresenter(session, mock_callbacks)
        category = create_test_category(session, type=TransactionType.EXPENSE)
        
        payment_data = PendingPaymentCreate(
            amount=amount,
            category_id=category.id,
            description=description,
            priority=PendingPaymentPriority.MEDIUM
        )
        
        # Act
        presenter.create_pending_payment(payment_data)
        
        # Assert
        mock_callbacks.update_pending_payments.assert_called()
```

**Property 3: Валидация пустых полей**
```python
@given(
    invalid_amount=st.one_of(st.just(Decimal('0')), st.just(Decimal('-1'))),
    invalid_description=st.one_of(st.just(""), st.just("   "))
)
def test_validation_rejects_invalid_data(invalid_amount, invalid_description):
    """
    **Feature: pending-payment-add-button, Property 6: Валидация пустых полей**
    **Validates: Requirements 6.1**
    
    Property: Для любых невалидных данных система должна показать ошибки.
    """
    # Arrange
    with get_db_session() as session:
        category = create_test_category(session, type=TransactionType.EXPENSE)
        
        # Act & Assert - проверяем, что Pydantic валидация отклоняет данные
        with pytest.raises(ValidationError):
            PendingPaymentCreate(
                amount=invalid_amount,
                category_id=category.id,
                description=invalid_description,
                priority=PendingPaymentPriority.MEDIUM
            )
```

### Integration Tests

**Тест полного цикла создания платежа:**
```python
def test_complete_payment_creation_flow():
    """Интеграционный тест: полный цикл создания отложенного платежа."""
    # Arrange
    with get_db_session() as session:
        category = create_test_category(session, type=TransactionType.EXPENSE)
        mock_page = create_mock_page()
        home_view = HomeView(mock_page, session)
        
        # Act - полный сценарий
        # 1. Нажатие кнопки добавления
        home_view.on_add_pending_payment()
        
        # 2. Заполнение формы
        modal = home_view.payment_modal
        modal.amount_field.value = "1000.50"
        modal.category_dropdown.value = str(category.id)
        modal.description_field.value = "Тестовый платёж"
        modal.priority_dropdown.value = PendingPaymentPriority.HIGH.value
        
        # 3. Сохранение
        modal._save(None)
        
        # Assert
        payments = session.query(PendingPaymentDB).all()
        assert len(payments) == 1
        assert payments[0].amount == Decimal('1000.50')
        assert payments[0].description == "Тестовый платёж"
        
        # Проверяем обновление UI
        mock_page.update.assert_called()
```

## Примечания по реализации

### Современный Flet API

**КРИТИЧЕСКИ ВАЖНО:** Использовать только современный Flet API для работы с диалогами:

```python
# ✅ ПРАВИЛЬНО
page.open(dialog)
page.close(dialog)
```

### Логирование

Все операции должны логироваться:
- DEBUG: Начало операции с параметрами
- INFO: Успешное завершение операции
- ERROR: Ошибки с полным контекстом и stack trace

### Типизация

Все callback функции должны быть правильно типизированы:
```python
on_add_payment: Callable[[], None]
on_save: Callable[[PendingPaymentCreate], None]
```

### Обработка None

Всегда проверять наличие page и других зависимостей перед использованием:
```python
if not self.page:
    logger.error("Page не инициализирована")
    return
```

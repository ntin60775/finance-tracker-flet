# Design Document: Передача долга между кредиторами

## Overview

Функциональность позволяет отслеживать историю смены держателей долга по кредиту. Реализуется через новую сущность `DebtTransferDB` для хранения полной истории передач, расширение `LoanDB` полями `original_lender_id` и `current_holder_id`, а также добавление типа кредитора `COLLECTOR` в `LenderType`.

### Архитектурное решение

**Выбран Вариант А: Новая сущность DebtTransfer**

Обоснование:
- Полная история передач (МФО → Коллектор1 → Коллектор2)
- Возможность хранить дополнительные данные о каждой передаче (причина, документы)
- Гибкость для будущих расширений
- Соответствует принципу нормализации данных

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         UI Layer                                │
├─────────────────────────────────────────────────────────────────┤
│  LoanDetailsView    │  DebtTransferModal  │  LoansView          │
│  (история передач)  │  (создание передачи)│  (индикаторы)       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Service Layer                             │
├─────────────────────────────────────────────────────────────────┤
│  debt_transfer_service.py                                       │
│  - create_debt_transfer()                                       │
│  - get_transfer_history()                                       │
│  - get_current_holder()                                         │
│  - validate_transfer()                                          │
├─────────────────────────────────────────────────────────────────┤
│  loan_service.py (расширение)                                   │
│  - get_loans_by_current_holder()                                │
│  - get_debt_by_holder_statistics()                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Data Layer                                │
├─────────────────────────────────────────────────────────────────┤
│  LenderDB          │  LoanDB              │  DebtTransferDB     │
│  + COLLECTOR type  │  + original_lender_id│  (новая сущность)   │
│                    │  + current_holder_id │                     │
└─────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Расширение LenderType (enums.py)

```python
class LenderType(str, Enum):
    """Тип займодателя."""
    BANK = "bank"
    MFO = "mfo"
    INDIVIDUAL = "individual"
    COLLECTOR = "collector"  # НОВОЕ: Коллекторское агентство
    OTHER = "other"
```

### 2. Новая модель DebtTransferDB (models.py)

```python
class DebtTransferDB(Base):
    """
    Запись о передаче долга между кредиторами.
    
    Attributes:
        id: Уникальный идентификатор передачи (UUID)
        loan_id: ID кредита, по которому передаётся долг (UUID)
        from_lender_id: ID кредитора, от которого передаётся долг (UUID)
        to_lender_id: ID кредитора, которому передаётся долг (UUID)
        transfer_date: Дата передачи долга
        transfer_amount: Сумма долга на момент передачи
        previous_amount: Сумма долга до передачи (для расчёта разницы)
        amount_difference: Разница в сумме (пени, штрафы)
        reason: Причина передачи (опционально)
        notes: Примечания (опционально)
        created_at: Дата создания записи
        updated_at: Дата последнего обновления
    """
    __tablename__ = "debt_transfers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    loan_id = Column(String(36), ForeignKey("loans.id"), nullable=False)
    from_lender_id = Column(String(36), ForeignKey("lenders.id"), nullable=False)
    to_lender_id = Column(String(36), ForeignKey("lenders.id"), nullable=False)
    transfer_date = Column(Date, nullable=False, index=True)
    transfer_amount = Column(Numeric(10, 2), nullable=False)
    previous_amount = Column(Numeric(10, 2), nullable=False)
    amount_difference = Column(Numeric(10, 2), nullable=False, default=Decimal('0'))
    reason = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Связи
    loan = relationship("LoanDB", back_populates="debt_transfers")
    from_lender = relationship("LenderDB", foreign_keys=[from_lender_id])
    to_lender = relationship("LenderDB", foreign_keys=[to_lender_id])

    # Индексы
    __table_args__ = (
        Index('ix_debt_transfers_loan_id', 'loan_id'),
        Index('ix_debt_transfers_transfer_date', 'transfer_date'),
        Index('ix_debt_transfers_loan_id_transfer_date', 'loan_id', 'transfer_date'),
    )
```

### 3. Расширение LoanDB (models.py)

```python
class LoanDB(Base):
    # ... существующие поля ...
    
    # НОВЫЕ поля для отслеживания передачи долга
    original_lender_id = Column(String(36), ForeignKey("lenders.id"), nullable=True)
    current_holder_id = Column(String(36), ForeignKey("lenders.id"), nullable=True)
    
    # НОВЫЕ связи
    original_lender = relationship("LenderDB", foreign_keys=[original_lender_id])
    current_holder = relationship("LenderDB", foreign_keys=[current_holder_id])
    debt_transfers = relationship("DebtTransferDB", back_populates="loan", order_by="DebtTransferDB.transfer_date")
    
    @property
    def is_transferred(self) -> bool:
        """Проверяет, был ли долг передан другому кредитору."""
        return self.current_holder_id is not None and self.current_holder_id != self.lender_id
    
    @property
    def effective_holder_id(self) -> str:
        """Возвращает ID текущего держателя долга (current_holder_id или lender_id)."""
        return self.current_holder_id if self.current_holder_id else self.lender_id
```

### 4. Сервис передачи долга (debt_transfer_service.py)

```python
def create_debt_transfer(
    session: Session,
    loan_id: str,
    to_lender_id: str,
    transfer_date: date,
    transfer_amount: Decimal,
    reason: Optional[str] = None,
    notes: Optional[str] = None
) -> DebtTransferDB:
    """
    Создаёт запись о передаче долга.
    
    Args:
        session: Сессия БД
        loan_id: ID кредита
        to_lender_id: ID нового держателя долга
        transfer_date: Дата передачи
        transfer_amount: Сумма долга при передаче
        reason: Причина передачи (опционально)
        notes: Примечания (опционально)
        
    Returns:
        Созданная запись DebtTransferDB
        
    Raises:
        ValueError: При невалидных данных
        LoanNotFoundError: Если кредит не найден
        LenderNotFoundError: Если кредитор не найден
    """
    pass

def get_transfer_history(session: Session, loan_id: str) -> List[DebtTransferDB]:
    """
    Возвращает историю передач долга по кредиту в хронологическом порядке.
    """
    pass

def validate_transfer(
    session: Session,
    loan_id: str,
    to_lender_id: str,
    transfer_amount: Decimal
) -> Tuple[bool, Optional[str]]:
    """
    Валидирует возможность передачи долга.
    
    Returns:
        Tuple[is_valid, error_message]
    """
    pass

def get_remaining_debt(session: Session, loan_id: str) -> Decimal:
    """
    Вычисляет текущий остаток долга по кредиту.
    """
    pass
```

### 5. Модальное окно передачи долга (debt_transfer_modal.py)

```python
class DebtTransferModal(ft.UserControl):
    """
    Модальное окно для создания передачи долга.
    
    Отображает:
    - Информацию о текущем держателе
    - Текущий остаток долга
    - Выбор нового держателя (с возможностью создания)
    - Дату передачи
    - Сумму долга при передаче
    - Разницу с текущим остатком
    - Причину передачи (опционально)
    """
    
    def __init__(self, session: Session, loan: LoanDB, on_transfer_callback: Callable):
        pass
    
    def open(self, page: ft.Page) -> None:
        """Открывает модальное окно."""
        pass
    
    def _build_content(self) -> ft.Column:
        """Строит содержимое модального окна."""
        pass
    
    def _on_amount_change(self, e) -> None:
        """Обработчик изменения суммы — показывает разницу."""
        pass
    
    def _on_create_lender(self, e) -> None:
        """Открывает модальное окно создания кредитора."""
        pass
    
    def _on_confirm(self, e) -> None:
        """Подтверждение передачи с диалогом подтверждения."""
        pass
```

### 6. Расширение LoanDetailsView

```python
class LoanDetailsView:
    # ... существующий код ...
    
    def _build_transfer_history_section(self) -> ft.Container:
        """
        Строит секцию истории передач долга.
        
        Отображает:
        - Заголовок "История передач"
        - Список передач в хронологическом порядке
        - Для каждой передачи: дата, от кого, кому, сумма, разница
        - Кнопку "Передать долг" (если кредит активен)
        """
        pass
    
    def _build_transfer_indicator(self) -> Optional[ft.Container]:
        """
        Строит индикатор передачи для заголовка.
        
        Возвращает бейдж "Долг передан от X к Y" если есть передачи.
        """
        pass
```

## Data Models

### Pydantic модели

```python
class DebtTransferCreate(BaseModel):
    """Модель для создания передачи долга."""
    loan_id: str
    to_lender_id: str
    transfer_date: date
    transfer_amount: Decimal = Field(gt=Decimal('0'))
    reason: Optional[str] = None
    notes: Optional[str] = None

class DebtTransfer(DebtTransferCreate):
    """Модель для чтения передачи долга."""
    id: str
    from_lender_id: str
    previous_amount: Decimal
    amount_difference: Decimal
    created_at: datetime
    updated_at: datetime
    
    # Вложенные объекты для отображения
    from_lender_name: Optional[str] = None
    to_lender_name: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class LoanWithTransferInfo(BaseModel):
    """Расширенная модель кредита с информацией о передаче."""
    # ... базовые поля Loan ...
    is_transferred: bool
    original_lender_name: Optional[str] = None
    current_holder_name: Optional[str] = None
    transfer_count: int = 0
```

### Миграция базы данных

```sql
-- Добавление полей в таблицу loans
ALTER TABLE loans ADD COLUMN original_lender_id VARCHAR(36) REFERENCES lenders(id);
ALTER TABLE loans ADD COLUMN current_holder_id VARCHAR(36) REFERENCES lenders(id);

-- Создание таблицы debt_transfers
CREATE TABLE debt_transfers (
    id VARCHAR(36) PRIMARY KEY,
    loan_id VARCHAR(36) NOT NULL REFERENCES loans(id),
    from_lender_id VARCHAR(36) NOT NULL REFERENCES lenders(id),
    to_lender_id VARCHAR(36) NOT NULL REFERENCES lenders(id),
    transfer_date DATE NOT NULL,
    transfer_amount NUMERIC(10, 2) NOT NULL,
    previous_amount NUMERIC(10, 2) NOT NULL,
    amount_difference NUMERIC(10, 2) NOT NULL DEFAULT 0,
    reason VARCHAR,
    notes VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы
CREATE INDEX ix_debt_transfers_loan_id ON debt_transfers(loan_id);
CREATE INDEX ix_debt_transfers_transfer_date ON debt_transfers(transfer_date);
CREATE INDEX ix_debt_transfers_loan_id_transfer_date ON debt_transfers(loan_id, transfer_date);
CREATE INDEX ix_loans_original_lender_id ON loans(original_lender_id);
CREATE INDEX ix_loans_current_holder_id ON loans(current_holder_id);
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Консистентность текущего держателя после передачи

*For any* кредит и валидную передачу долга, после создания передачи `loan.current_holder_id` должен равняться `transfer.to_lender_id`, и все новые платежи должны быть привязаны к этому держателю.

**Validates: Requirements 2.2, 4.3**

### Property 2: Неизменность исходного кредитора

*For any* кредит с историей передач, `loan.original_lender_id` должен равняться `loan.lender_id` (исходному кредитору) и не должен меняться при последующих передачах.

**Validates: Requirements 2.3**

### Property 3: Корректность вычисления разницы сумм

*For any* передачу долга, `transfer.amount_difference` должен равняться `transfer.transfer_amount - transfer.previous_amount`.

**Validates: Requirements 2.4, 8.5**

### Property 4: Валидация источника передачи

*For any* попытку создания передачи, если `from_lender_id` не равен `loan.effective_holder_id`, передача должна быть отклонена с ошибкой.

**Validates: Requirements 2.5**

### Property 5: Хронологический порядок истории передач

*For any* кредит с историей передач, список передач должен быть отсортирован по `transfer_date` в порядке возрастания.

**Validates: Requirements 3.3**

### Property 6: Неизменность исполненных платежей при передаче

*For any* передачу долга, платежи со статусом EXECUTED или EXECUTED_LATE не должны изменяться (их привязка к кредитору сохраняется).

**Validates: Requirements 4.2**

### Property 7: Обновление ожидающих платежей при передаче

*For any* передачу долга, все платежи со статусом PENDING должны быть обновлены для привязки к новому держателю.

**Validates: Requirements 4.1**

### Property 8: Запрет передачи погашенного кредита

*For any* кредит со статусом PAID_OFF, попытка создания передачи должна быть отклонена с соответствующей ошибкой.

**Validates: Requirements 6.1**

### Property 9: Запрет передачи самому себе

*For any* попытку передачи, где `to_lender_id` равен текущему держателю (`loan.effective_holder_id`), передача должна быть отклонена.

**Validates: Requirements 6.2**

### Property 10: Запрет отрицательной или нулевой суммы передачи

*For any* попытку передачи с `transfer_amount <= 0`, передача должна быть отклонена с ошибкой валидации.

**Validates: Requirements 6.3**

### Property 11: Корректность группировки задолженностей по держателям

*For any* запрос статистики по кредитору, сумма задолженности должна включать только кредиты, где `loan.effective_holder_id` равен ID этого кредитора.

**Validates: Requirements 7.2, 7.3**

### Property 12: Предзаполнение суммы текущим остатком

*For any* открытие модального окна передачи, поле суммы должно быть предзаполнено значением `get_remaining_debt(loan_id)`.

**Validates: Requirements 8.3**

## Error Handling

### Ошибки валидации

|           Ошибка       |        Условие       |                   Сообщение                            |
|------------------------|----------------------|--------------------------------------------------------|
| `LoanNotFoundError`    | Кредит не найден     | "Кредит с ID {loan_id} не найден"                      |
| `LenderNotFoundError`  | Кредитор не найден   | "Кредитор с ID {lender_id} не найден"                  |
| `InvalidTransferError` | Передача самому себе | "Нельзя передать долг тому же кредитору"               |
| `InvalidTransferError` | Погашенный кредит    | "Нельзя передать погашенный кредит"                    |
| `InvalidTransferError` | Неверный источник    | "Передача возможна только от текущего держателя долга" |
| `ValidationError`      | Сумма <= 0           | "Сумма передачи должна быть положительной"             |

### Обработка в UI

```python
def _on_confirm(self, e):
    """Обработчик подтверждения передачи."""
    try:
        is_valid, error = validate_transfer(
            self.session, 
            self.loan.id, 
            self.to_lender_dropdown.value,
            Decimal(self.amount_field.value)
        )
        if not is_valid:
            self._show_error(error)
            return
            
        # Показываем диалог подтверждения
        self._show_confirmation_dialog()
    except Exception as e:
        logger.error(f"Ошибка при валидации передачи: {e}")
        self._show_error("Произошла ошибка при проверке данных")
```

## Testing Strategy

### Unit Tests

1. **Тесты сервиса передачи долга:**
   - Создание передачи с валидными данными
   - Валидация всех ограничений (погашенный кредит, передача себе, отрицательная сумма)
   - Получение истории передач
   - Вычисление остатка долга

2. **Тесты модели DebtTransferDB:**
   - Создание записи с обязательными полями
   - Вычисление amount_difference
   - Связи с Loan и Lender

3. **Тесты расширения LoanDB:**
   - Свойство is_transferred
   - Свойство effective_holder_id
   - Связь с debt_transfers

### Property-Based Tests (Hypothesis)

Каждый property-based тест должен:
- Запускаться минимум 100 итераций
- Быть аннотирован ссылкой на свойство из дизайна
- Использовать генераторы для создания случайных валидных данных

```python
@given(
    loan=loan_strategy(),
    to_lender=lender_strategy(),
    transfer_amount=st.decimals(min_value=Decimal('0.01'), max_value=Decimal('999999.99'))
)
@settings(max_examples=100)
def test_property_1_current_holder_consistency(loan, to_lender, transfer_amount):
    """
    **Feature: debt-transfer, Property 1: Консистентность текущего держателя**
    **Validates: Requirements 2.2, 4.3**
    """
    # ... тест ...
```

### Integration Tests

1. **Полный цикл передачи:**
   - Создание кредита → Передача коллектору → Проверка истории → Создание платежа

2. **Множественные передачи:**
   - МФО → Коллектор1 → Коллектор2 → Проверка цепочки

3. **Интеграция с отчётами:**
   - Проверка группировки по текущим держателям

### UI Tests

1. **Тесты модального окна:**
   - Открытие с предзаполненными данными
   - Валидация формы
   - Отображение разницы сумм
   - Создание нового кредитора

2. **Тесты LoanDetailsView:**
   - Отображение секции истории передач
   - Индикатор передачи в заголовке

3. **Тесты LoansView:**
   - Индикатор "Долг передан" в списке
   - Tooltip с информацией о передаче

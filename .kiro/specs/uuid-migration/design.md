# Design Document

## Overview

Переход Finance Tracker на использование UUID вместо Integer ID во всех таблицах базы данных и добавление колонки `updated_at` для полного отслеживания изменений. Это обеспечит глобальную уникальность идентификаторов для будущей синхронизации между устройствами.

**Ключевые решения:**
- UUID версии 4 (случайный) для максимальной уникальности
- Генерация UUID на стороне приложения (Python)
- Хранение UUID как строка (VARCHAR(36)) в SQLite
- Автоматическое обновление `updated_at` через SQLAlchemy
- Пересоздание базы данных (миграция данных не требуется)

## Architecture

### Слои системы

```
┌─────────────────────────────────────────┐
│           UI Layer (Flet)               │
│  - Компоненты работают со строковыми ID │
│  - Не отображают UUID пользователю      │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         Service Layer                   │
│  - Функции принимают str (UUID)         │
│  - Валидация формата UUID               │
│  - Бизнес-логика                        │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      Data Layer (SQLAlchemy)            │
│  - Модели с UUID первичными ключами     │
│  - Автогенерация UUID                   │
│  - Автообновление updated_at            │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         Database (SQLite)               │
│  - UUID хранятся как VARCHAR(36)        │
│  - Индексы на UUID колонках             │
└─────────────────────────────────────────┘
```

### Генерация UUID

UUID генерируется на стороне приложения с использованием стандартной библиотеки Python:

```python
import uuid

# UUID версии 4 (случайный)
new_id = str(uuid.uuid4())  # Пример: "550e8400-e29b-41d4-a716-446655440000"
```

**Преимущества генерации на стороне приложения:**
- Не зависит от возможностей БД
- Можно использовать ID до сохранения в БД
- Упрощает тестирование
- Единообразие между разными БД


## Components and Interfaces

### 1. Database Models (SQLAlchemy)

Все модели обновляются для использования UUID и `updated_at`:

```python
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime
import uuid

class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""
    pass

# Пример: CategoryDB
class CategoryDB(Base):
    __tablename__ = "categories"
    
    # UUID как первичный ключ
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String, nullable=False, unique=True)
    type = Column(SQLEnum(TransactionType), nullable=False)
    is_system = Column(Boolean, default=False)
    
    # Временные метки
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)  # НОВОЕ
    
    # Связи (обратные ссылки остаются без изменений)
    transactions = relationship("TransactionDB", back_populates="category")

# Пример: TransactionDB с внешним ключом
class TransactionDB(Base):
    __tablename__ = "transactions"
    
    # UUID как первичный ключ
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    type = Column(SQLEnum(TransactionType), nullable=False)
    
    # UUID как внешний ключ
    category_id = Column(String(36), ForeignKey("categories.id"), nullable=False)
    
    description = Column(String)
    transaction_date = Column(Date, nullable=False, index=True)
    
    # Временные метки
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Связи
    category = relationship("CategoryDB", back_populates="transactions")
```

**Изменения в каждой модели:**
1. `id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)`
2. Все внешние ключи: `Column(String(36), ForeignKey(...))`
3. Добавление `updated_at` (где отсутствует)


### 2. Pydantic Models

Обновление моделей для валидации UUID:

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime, date
from decimal import Decimal
import uuid

class TransactionCreate(BaseModel):
    """Модель для создания транзакции."""
    amount: Decimal = Field(gt=Decimal('0'))
    type: TransactionType
    category_id: str  # UUID как строка
    description: Optional[str] = None
    transaction_date: date = Field(default_factory=date.today)
    
    @field_validator('category_id')
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        """Валидация формата UUID."""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError(f'Невалидный UUID: {v}')

class Transaction(TransactionCreate):
    """Модель для чтения транзакции."""
    id: str  # UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class Category(BaseModel):
    """Модель для категории."""
    id: str  # UUID
    name: str
    type: TransactionType
    is_system: bool
    created_at: datetime
    updated_at: datetime  # НОВОЕ
    
    model_config = ConfigDict(from_attributes=True)
```

**Паттерн валидации UUID:**
- Все ID поля имеют тип `str`
- Валидатор проверяет формат UUID
- Понятное сообщение об ошибке


### 3. Service Layer

Обновление сигнатур функций для работы с UUID:

```python
from typing import Optional, List
from sqlalchemy.orm import Session
import uuid

def validate_uuid_format(id_value: str, field_name: str = "ID") -> None:
    """
    Валидация формата UUID.
    
    Args:
        id_value: Значение для проверки
        field_name: Название поля для сообщения об ошибке
        
    Raises:
        ValueError: Если формат невалидный
    """
    try:
        uuid.UUID(id_value)
    except ValueError:
        raise ValueError(f'Невалидный формат {field_name}: {id_value}')

# Пример: transaction_service.py
def delete_transaction(session: Session, transaction_id: str) -> bool:
    """
    Удаляет транзакцию по UUID.
    
    Args:
        session: Сессия БД
        transaction_id: UUID транзакции (строка)
        
    Returns:
        True если удалена, False если не найдена
        
    Raises:
        ValueError: Если UUID невалидный
    """
    # Валидация формата UUID
    validate_uuid_format(transaction_id, "transaction_id")
    
    transaction = session.query(TransactionDB).filter(
        TransactionDB.id == transaction_id
    ).first()
    
    if not transaction:
        logger.warning(f"Транзакция {transaction_id} не найдена")
        return False
    
    session.delete(transaction)
    session.commit()
    logger.info(f"Транзакция {transaction_id} удалена")
    return True

# Пример: loan_service.py
def get_loan_by_id(session: Session, loan_id: str) -> Optional[LoanDB]:
    """
    Получает кредит по UUID.
    
    Args:
        session: Сессия БД
        loan_id: UUID кредита (строка)
        
    Returns:
        Объект LoanDB или None
        
    Raises:
        ValueError: Если UUID невалидный
    """
    validate_uuid_format(loan_id, "loan_id")
    
    return session.query(LoanDB).filter(LoanDB.id == loan_id).first()
```

**Изменения в сервисах:**
1. Все параметры `*_id: int` → `*_id: str`
2. Добавление валидации UUID в начале функции
3. Использование строкового сравнения в фильтрах
4. Логирование с UUID для трассировки


### 4. UI Components (Flet)

Обновление компонентов для работы с UUID:

```python
import flet as ft

class TransactionModal:
    def __init__(self, page: ft.Page, on_save_callback):
        self.page = page
        self.on_save_callback = on_save_callback
        
        # Хранение UUID как строка
        self.selected_category_id: str = None
        self.transaction_id: str = None  # Для редактирования
    
    def show_create(self):
        """Показать модальное окно для создания."""
        self.transaction_id = None
        # ... остальная логика
    
    def show_edit(self, transaction_id: str):
        """
        Показать модальное окно для редактирования.
        
        Args:
            transaction_id: UUID транзакции (строка)
        """
        self.transaction_id = transaction_id
        # Загрузка данных транзакции по UUID
        # ... остальная логика
    
    def on_save_clicked(self, e):
        """Обработчик сохранения."""
        try:
            if self.transaction_id:
                # Редактирование - передаём UUID
                update_transaction(
                    transaction_id=self.transaction_id,
                    category_id=self.selected_category_id,  # UUID
                    # ... остальные поля
                )
            else:
                # Создание - UUID генерируется в сервисе
                create_transaction(
                    category_id=self.selected_category_id,  # UUID
                    # ... остальные поля
                )
            
            self.on_save_callback()
        except ValueError as e:
            # Обработка ошибок валидации UUID
            self.show_error(str(e))
```

**Изменения в UI:**
1. Все переменные с ID используют тип `str`
2. UUID не отображаются пользователю (только внутреннее использование)
3. Передача UUID в сервисы как строки
4. Обработка ошибок валидации UUID


## Data Models

### Таблицы базы данных с UUID

Все 9 таблиц обновляются по единому паттерну:

#### 1. categories
```sql
CREATE TABLE categories (
    id VARCHAR(36) PRIMARY KEY,  -- UUID
    name VARCHAR NOT NULL UNIQUE,
    type VARCHAR NOT NULL,  -- INCOME или EXPENSE
    is_system BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP  -- НОВОЕ
);
CREATE INDEX ix_categories_id ON categories(id);
```

#### 2. planned_transactions
```sql
CREATE TABLE planned_transactions (
    id VARCHAR(36) PRIMARY KEY,  -- UUID
    amount NUMERIC(10, 2) NOT NULL,
    category_id VARCHAR(36) NOT NULL,  -- FK → categories.id (UUID)
    description VARCHAR,
    type VARCHAR NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);
CREATE INDEX ix_planned_transactions_id ON planned_transactions(id);
CREATE INDEX ix_planned_transactions_category_id ON planned_transactions(category_id);
```

#### 3. recurrence_rules
```sql
CREATE TABLE recurrence_rules (
    id VARCHAR(36) PRIMARY KEY,  -- UUID
    planned_transaction_id VARCHAR(36) NOT NULL UNIQUE,  -- FK → planned_transactions.id (UUID)
    recurrence_type VARCHAR NOT NULL,
    interval INTEGER,
    interval_unit VARCHAR,
    weekdays VARCHAR,
    only_workdays BOOLEAN DEFAULT FALSE,
    end_condition_type VARCHAR NOT NULL,
    end_date DATE,
    occurrences_count INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,  -- НОВОЕ
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,  -- НОВОЕ
    FOREIGN KEY (planned_transaction_id) REFERENCES planned_transactions(id)
);
CREATE INDEX ix_recurrence_rules_id ON recurrence_rules(id);
```

#### 4. planned_occurrences
```sql
CREATE TABLE planned_occurrences (
    id VARCHAR(36) PRIMARY KEY,  -- UUID
    planned_transaction_id VARCHAR(36) NOT NULL,  -- FK → planned_transactions.id (UUID)
    occurrence_date DATE NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    status VARCHAR DEFAULT 'PENDING',
    actual_transaction_id VARCHAR(36),  -- FK → transactions.id (UUID)
    executed_date DATE,
    executed_amount NUMERIC(10, 2),
    skipped_date DATE,
    skip_reason VARCHAR,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,  -- НОВОЕ
    FOREIGN KEY (planned_transaction_id) REFERENCES planned_transactions(id),
    FOREIGN KEY (actual_transaction_id) REFERENCES transactions(id)
);
CREATE INDEX ix_planned_occurrences_id ON planned_occurrences(id);
CREATE INDEX ix_planned_occurrences_planned_transaction_id ON planned_occurrences(planned_transaction_id);
CREATE INDEX ix_planned_occurrences_status_occurrence_date ON planned_occurrences(status, occurrence_date);
```

#### 5. transactions
```sql
CREATE TABLE transactions (
    id VARCHAR(36) PRIMARY KEY,  -- UUID
    amount NUMERIC(10, 2) NOT NULL,
    type VARCHAR NOT NULL,
    category_id VARCHAR(36) NOT NULL,  -- FK → categories.id (UUID)
    description VARCHAR,
    transaction_date DATE NOT NULL,
    planned_occurrence_id VARCHAR(36),  -- FK → planned_occurrences.id (UUID)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (planned_occurrence_id) REFERENCES planned_occurrences(id) ON DELETE SET NULL
);
CREATE INDEX ix_transactions_id ON transactions(id);
CREATE INDEX ix_transactions_date_type ON transactions(transaction_date, type);
CREATE INDEX ix_transactions_category_id_date ON transactions(category_id, transaction_date);
```


#### 6. lenders
```sql
CREATE TABLE lenders (
    id VARCHAR(36) PRIMARY KEY,  -- UUID
    name VARCHAR NOT NULL UNIQUE,
    lender_type VARCHAR DEFAULT 'OTHER',
    description VARCHAR,
    contact_info VARCHAR,
    notes VARCHAR,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_lenders_id ON lenders(id);
```

#### 7. loans
```sql
CREATE TABLE loans (
    id VARCHAR(36) PRIMARY KEY,  -- UUID
    lender_id VARCHAR(36) NOT NULL,  -- FK → lenders.id (UUID)
    name VARCHAR NOT NULL,
    loan_type VARCHAR DEFAULT 'OTHER',
    amount NUMERIC(10, 2) NOT NULL,
    interest_rate NUMERIC(5, 2),
    term_months INTEGER,
    issue_date DATE NOT NULL,
    end_date DATE,
    disbursement_transaction_id VARCHAR(36),  -- FK → transactions.id (UUID)
    contract_number VARCHAR,
    description VARCHAR,
    status VARCHAR DEFAULT 'ACTIVE',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lender_id) REFERENCES lenders(id),
    FOREIGN KEY (disbursement_transaction_id) REFERENCES transactions(id)
);
CREATE INDEX ix_loans_id ON loans(id);
CREATE INDEX ix_loans_lender_id ON loans(lender_id);
CREATE INDEX ix_loans_status ON loans(status);
```

#### 8. loan_payments
```sql
CREATE TABLE loan_payments (
    id VARCHAR(36) PRIMARY KEY,  -- UUID
    loan_id VARCHAR(36) NOT NULL,  -- FK → loans.id (UUID)
    scheduled_date DATE NOT NULL,
    principal_amount NUMERIC(10, 2) NOT NULL,
    interest_amount NUMERIC(10, 2) NOT NULL,
    total_amount NUMERIC(10, 2) NOT NULL,
    status VARCHAR DEFAULT 'PENDING',
    planned_transaction_id VARCHAR(36),  -- FK → planned_transactions.id (UUID)
    actual_transaction_id VARCHAR(36),  -- FK → transactions.id (UUID)
    executed_date DATE,
    executed_amount NUMERIC(10, 2),
    overdue_days INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (loan_id) REFERENCES loans(id),
    FOREIGN KEY (planned_transaction_id) REFERENCES planned_transactions(id),
    FOREIGN KEY (actual_transaction_id) REFERENCES transactions(id)
);
CREATE INDEX ix_loan_payments_id ON loan_payments(id);
CREATE INDEX ix_loan_payments_loan_id ON loan_payments(loan_id);
CREATE INDEX ix_loan_payments_status ON loan_payments(status);
```

#### 9. pending_payments
```sql
CREATE TABLE pending_payments (
    id VARCHAR(36) PRIMARY KEY,  -- UUID
    amount NUMERIC(10, 2) NOT NULL,
    category_id VARCHAR(36) NOT NULL,  -- FK → categories.id (UUID)
    description VARCHAR NOT NULL,
    priority VARCHAR DEFAULT 'MEDIUM',
    planned_date DATE,
    status VARCHAR DEFAULT 'ACTIVE',
    actual_transaction_id VARCHAR(36),  -- FK → transactions.id (UUID)
    executed_date DATE,
    executed_amount NUMERIC(10, 2),
    cancelled_date DATE,
    cancel_reason VARCHAR,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (actual_transaction_id) REFERENCES transactions(id)
);
CREATE INDEX ix_pending_payments_id ON pending_payments(id);
CREATE INDEX ix_pending_payments_category_id ON pending_payments(category_id);
CREATE INDEX ix_pending_payments_status ON pending_payments(status);
```

### Сводка изменений

**Все таблицы:**
- `id`: `INTEGER` → `VARCHAR(36)` (UUID)
- Все внешние ключи: `INTEGER` → `VARCHAR(36)` (UUID)
- Добавлена `updated_at` (где отсутствовала): categories, recurrence_rules, planned_occurrences

**Индексы:**
- Все первичные ключи индексируются
- Все внешние ключи индексируются
- Составные индексы сохраняются


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: UUID автогенерация
*For any* новой записи в любой таблице, система должна автоматически генерировать валидный UUID версии 4 в качестве первичного ключа
**Validates: Requirements 1.1, 1.2**

### Property 2: Уникальность UUID
*For any* попытки создать запись с существующим UUID, база данных должна отклонять операцию с ошибкой уникальности
**Validates: Requirements 1.6**

### Property 3: UUID в внешних ключах
*For any* таблицы с внешними ключами, все внешние ключи должны иметь тип VARCHAR(36) и ссылаться на UUID первичные ключи
**Validates: Requirements 2.1**

### Property 4: Каскадное удаление
*For any* записи с каскадным правилом удаления, при удалении родительской записи связанные записи должны быть удалены или обнулены согласно правилу
**Validates: Requirements 2.3**

### Property 5: Валидация существования FK
*For any* попытки создать запись с несуществующим UUID в качестве внешнего ключа, система должна отклонять операцию с ошибкой
**Validates: Requirements 2.5**

### Property 6: Установка updated_at при создании
*For any* новой записи в любой таблице, колонка updated_at должна быть установлена в текущее время (UTC)
**Validates: Requirements 3.1, 3.4**

### Property 7: Автообновление updated_at
*For any* обновления существующей записи, колонка updated_at должна автоматически обновиться на текущее время (UTC), и новое значение должно быть больше предыдущего
**Validates: Requirements 3.2, 3.4**

### Property 8: Валидация UUID в сервисах
*For any* вызова сервисной функции с невалидным UUID, система должна возвращать ValueError с понятным сообщением об ошибке
**Validates: Requirements 5.4, 5.5**

### Property 9: Валидация UUID в Pydantic
*For any* попытки создать Pydantic модель с невалидным UUID, система должна возвращать ValidationError
**Validates: Requirements 6.3**

### Property 10: UUID в строковом формате
*For any* API ответа, содержащего ID, ID должен быть представлен в виде строки формата UUID
**Validates: Requirements 6.4**

### Property 11: Кэширование UUID
*For any* повторного запроса часто используемых данных (категории, займодатели), второй запрос должен выполняться быстрее первого за счёт кэширования
**Validates: Requirements 10.4**


## Error Handling

### Типы ошибок и обработка

#### 1. Невалидный формат UUID

**Ситуация:** Пользователь или система передаёт строку, не являющуюся валидным UUID

**Обработка:**
```python
def validate_uuid_format(id_value: str, field_name: str = "ID") -> None:
    """Валидация формата UUID с понятным сообщением."""
    try:
        uuid.UUID(id_value)
    except ValueError:
        error_msg = f'Невалидный формат {field_name}: {id_value}. Ожидается UUID формата: 550e8400-e29b-41d4-a716-446655440000'
        logger.error(error_msg)
        raise ValueError(error_msg)
```

**Логирование:**
```
ERROR: Невалидный формат transaction_id: abc123. Ожидается UUID формата: 550e8400-e29b-41d4-a716-446655440000
```

#### 2. Несуществующий UUID (запись не найдена)

**Ситуация:** Запрос записи по UUID, которого нет в БД

**Обработка:**
```python
def get_transaction_by_id(session: Session, transaction_id: str) -> Optional[TransactionDB]:
    """Получение транзакции по UUID."""
    validate_uuid_format(transaction_id, "transaction_id")
    
    transaction = session.query(TransactionDB).filter(
        TransactionDB.id == transaction_id
    ).first()
    
    if not transaction:
        logger.warning(f"Транзакция {transaction_id} не найдена")
        return None
    
    return transaction
```

**Логирование:**
```
WARNING: Транзакция 550e8400-e29b-41d4-a716-446655440000 не найдена
```

#### 3. Нарушение уникальности UUID

**Ситуация:** Попытка создать запись с существующим UUID (крайне редко при автогенерации)

**Обработка:**
```python
try:
    session.add(new_record)
    session.commit()
except IntegrityError as e:
    logger.error(f"Ошибка уникальности UUID: {e}")
    session.rollback()
    raise ValueError("UUID уже существует в базе данных")
```

**Логирование:**
```
ERROR: Ошибка уникальности UUID: UNIQUE constraint failed: transactions.id
```

#### 4. Нарушение внешнего ключа

**Ситуация:** Попытка создать запись с несуществующим UUID в качестве FK

**Обработка:**
```python
def create_transaction(session: Session, data: TransactionCreate) -> TransactionDB:
    """Создание транзакции с валидацией FK."""
    # Проверка существования категории
    category = session.query(CategoryDB).filter(
        CategoryDB.id == data.category_id
    ).first()
    
    if not category:
        error_msg = f"Категория {data.category_id} не найдена"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Создание транзакции
    transaction = TransactionDB(**data.model_dump())
    session.add(transaction)
    session.commit()
    
    return transaction
```

**Логирование:**
```
ERROR: Категория 550e8400-e29b-41d4-a716-446655440000 не найдена
```

### Стратегия логирования

**Уровни логирования:**
- **ERROR**: Невалидный UUID, нарушение целостности БД
- **WARNING**: Запись не найдена, попытка удаления несуществующей записи
- **INFO**: Успешное создание/обновление/удаление с UUID
- **DEBUG**: Генерация UUID, валидация UUID

**Формат логов:**
```python
logger.info(f"Создана транзакция {transaction.id} на сумму {transaction.amount}")
logger.debug(f"Сгенерирован UUID: {new_id}")
logger.error(f"Невалидный UUID category_id: {invalid_id}")
```


## Testing Strategy

### Dual Testing Approach

Используем комбинацию unit-тестов и property-based тестов для полного покрытия:

**Unit тесты** проверяют конкретные примеры и edge cases:
- Создание записи с автогенерацией UUID
- Валидация формата UUID
- Обработка ошибок

**Property-based тесты** проверяют универсальные свойства:
- UUID генерируется для всех типов записей
- updated_at обновляется при любом изменении
- Валидация работает для любых невалидных строк

### Property-Based Testing

**Библиотека:** Hypothesis (для Python)

**Конфигурация:** Минимум 100 итераций для каждого теста

**Формат тегов:** `**Feature: uuid-migration, Property {number}: {property_text}**`

#### Пример property-based теста

```python
from hypothesis import given, strategies as st
import uuid

@given(st.text())
def test_uuid_validation_rejects_invalid_strings(invalid_string):
    """
    **Feature: uuid-migration, Property 8: Валидация UUID в сервисах**
    
    Проверяет, что любая невалидная строка отклоняется валидатором UUID.
    """
    # Исключаем случайно валидные UUID
    try:
        uuid.UUID(invalid_string)
        return  # Это валидный UUID, пропускаем
    except ValueError:
        pass
    
    # Проверяем, что валидатор отклоняет невалидную строку
    with pytest.raises(ValueError, match="Невалидный формат"):
        validate_uuid_format(invalid_string, "test_id")

@given(st.sampled_from(['CategoryDB', 'TransactionDB', 'LoanDB']))
def test_uuid_autogeneration_for_all_models(model_class_name):
    """
    **Feature: uuid-migration, Property 1: UUID автогенерация**
    
    Проверяет, что UUID автоматически генерируется для всех моделей.
    """
    model_class = globals()[model_class_name]
    
    # Создаём экземпляр модели
    instance = model_class(**get_valid_data_for_model(model_class))
    
    # Проверяем, что ID является валидным UUID
    assert instance.id is not None
    uuid.UUID(instance.id)  # Должно пройти без ошибок
```

### Unit Testing

#### Тесты для моделей

```python
def test_category_uuid_generation():
    """Проверка автогенерации UUID для категории."""
    category = CategoryDB(name="Тест", type=TransactionType.INCOME)
    
    assert category.id is not None
    assert len(category.id) == 36
    uuid.UUID(category.id)  # Валидация формата

def test_category_updated_at_on_create():
    """Проверка установки updated_at при создании."""
    category = CategoryDB(name="Тест", type=TransactionType.INCOME)
    
    assert category.updated_at is not None
    assert category.created_at == category.updated_at

def test_transaction_foreign_key_uuid():
    """Проверка UUID в внешнем ключе."""
    category = CategoryDB(name="Тест", type=TransactionType.INCOME)
    session.add(category)
    session.commit()
    
    transaction = TransactionDB(
        amount=Decimal('100.00'),
        type=TransactionType.INCOME,
        category_id=category.id,  # UUID
        transaction_date=date.today()
    )
    
    assert transaction.category_id == category.id
    assert len(transaction.category_id) == 36
```

#### Тесты для сервисов

```python
def test_validate_uuid_format_valid():
    """Проверка валидации валидного UUID."""
    valid_uuid = str(uuid.uuid4())
    validate_uuid_format(valid_uuid, "test_id")  # Не должно выбросить ошибку

def test_validate_uuid_format_invalid():
    """Проверка валидации невалидного UUID."""
    with pytest.raises(ValueError, match="Невалидный формат"):
        validate_uuid_format("not-a-uuid", "test_id")

def test_delete_transaction_with_uuid():
    """Проверка удаления транзакции по UUID."""
    # Создаём транзакцию
    transaction = create_test_transaction(session)
    transaction_id = transaction.id
    
    # Удаляем
    result = delete_transaction(session, transaction_id)
    
    assert result is True
    assert session.query(TransactionDB).filter(
        TransactionDB.id == transaction_id
    ).first() is None
```

#### Тесты для Pydantic моделей

```python
def test_transaction_create_valid_uuid():
    """Проверка валидации валидного UUID в Pydantic."""
    category_id = str(uuid.uuid4())
    
    data = TransactionCreate(
        amount=Decimal('100.00'),
        type=TransactionType.INCOME,
        category_id=category_id,
        transaction_date=date.today()
    )
    
    assert data.category_id == category_id

def test_transaction_create_invalid_uuid():
    """Проверка валидации невалидного UUID в Pydantic."""
    with pytest.raises(ValidationError, match="Невалидный UUID"):
        TransactionCreate(
            amount=Decimal('100.00'),
            type=TransactionType.INCOME,
            category_id="not-a-uuid",
            transaction_date=date.today()
        )
```

### Integration Testing

```python
def test_full_transaction_flow_with_uuid():
    """Интеграционный тест: создание категории и транзакции с UUID."""
    # Создаём категорию
    category = create_category(session, "Тест", TransactionType.INCOME)
    assert uuid.UUID(category.id)
    
    # Создаём транзакцию
    transaction_data = TransactionCreate(
        amount=Decimal('100.00'),
        type=TransactionType.INCOME,
        category_id=category.id,
        transaction_date=date.today()
    )
    transaction = create_transaction(session, transaction_data)
    assert uuid.UUID(transaction.id)
    
    # Проверяем связь
    assert transaction.category_id == category.id
    assert transaction.category.name == "Тест"
```

### Test Coverage Goals

- **Модели:** 100% покрытие (все поля, все связи)
- **Сервисы:** 90%+ покрытие (все функции с UUID)
- **Валидация:** 100% покрытие (все edge cases)
- **Property-based тесты:** Минимум 1 тест на каждое свойство


"""
Модуль моделей данных для Finance Tracker Flet.

Содержит определения моделей для работы с транзакциями:
- TransactionType: enum для типов транзакций (доход/расход)
- TransactionDB: SQLAlchemy модель для хранения в базе данных
- TransactionCreate: Pydantic модель для создания транзакции с валидацией
- Transaction: Pydantic модель для чтения транзакции из БД
"""

from datetime import datetime
from datetime import date as date_type
from typing import Optional
from decimal import Decimal
import uuid

from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, Enum as SQLEnum, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship, DeclarativeBase
from pydantic import BaseModel, field_validator, Field, ConfigDict, computed_field

from .enums import (
    TransactionType, RecurrenceType, OccurrenceStatus, IntervalUnit,
    EndConditionType, LenderType, LoanType, LoanStatus, PaymentStatus,
    PendingPaymentPriority, PendingPaymentStatus
)

# Декларативная база для SQLAlchemy моделей
class Base(DeclarativeBase):
    """Базовый класс для всех SQLAlchemy моделей."""
    pass


class CategoryDB(Base):
    """
    Справочник категорий для классификации транзакций.

    Attributes:
        id: Уникальный идентификатор категории (UUID)
        name: Название категории (уникальное)
        type: Тип категории (доход или расход)
        is_system: Признак системной категории (нельзя удалить)
        created_at: Дата создания категории
        updated_at: Дата последнего обновления
    """
    __tablename__ = "categories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String, nullable=False, unique=True)
    type = Column(SQLEnum(TransactionType), nullable=False)
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Связи
    transactions = relationship("TransactionDB", back_populates="category")
    planned_transactions = relationship("PlannedTransactionDB", back_populates="category")
    pending_payments = relationship("PendingPaymentDB", back_populates="category")


class PlannedTransactionDB(Base):
    """
    Шаблон плановой транзакции.

    Представляет план будущей транзакции (однократной или периодической).
    Для периодических транзакций генерирует вхождения (PlannedOccurrenceDB).

    Attributes:
        id: Уникальный идентификатор плановой транзакции (UUID)
        amount: Плановая сумма транзакции
        category_id: Ссылка на категорию из справочника (UUID)
        description: Описание плановой транзакции
        type: Тип транзакции (доход или расход)
        start_date: Дата начала действия плана
        end_date: Дата окончания (None = бессрочно)
        is_active: Признак активности (неактивные не генерируют вхождения)
        created_at: Дата создания записи
        updated_at: Дата последнего обновления
    """
    __tablename__ = "planned_transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    category_id = Column(String(36), ForeignKey("categories.id"), nullable=False)
    description = Column(String)
    type = Column(SQLEnum(TransactionType), nullable=False, index=True)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Связи
    category = relationship("CategoryDB", back_populates="planned_transactions")
    recurrence_rule = relationship("RecurrenceRuleDB", back_populates="planned_transaction", uselist=False)
    occurrences = relationship("PlannedOccurrenceDB", back_populates="planned_transaction")


class RecurrenceRuleDB(Base):
    """
    Правило повторения для периодической плановой транзакции.

    Определяет, как часто и по каким правилам должны генерироваться
    вхождения плановой транзакции.

    Attributes:
        id: Уникальный идентификатор правила (UUID)
        planned_transaction_id: Ссылка на плановую транзакцию (1:1) (UUID)
        recurrence_type: Тип повторения (ежедневно, еженедельно и т.д.)
        interval: Интервал повторения (каждые N единиц)
        interval_unit: Единица интервала (дни, недели, месяцы, годы)
        weekdays: Дни недели для повторения (JSON массив: [0,1,2,3,4] для пн-пт)
        only_workdays: Признак "только рабочие дни" (пропускать выходные)
        end_condition_type: Тип условия окончания
        end_date: Дата окончания (для UNTIL_DATE)
        occurrences_count: Количество повторений (для AFTER_COUNT)
        created_at: Дата создания записи
        updated_at: Дата последнего обновления
    """
    __tablename__ = "recurrence_rules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    planned_transaction_id = Column(String(36), ForeignKey("planned_transactions.id"), nullable=False, unique=True)
    recurrence_type = Column(SQLEnum(RecurrenceType), nullable=False, default=RecurrenceType.NONE)
    interval = Column(Integer, nullable=True)
    interval_unit = Column(SQLEnum(IntervalUnit), nullable=True)
    weekdays = Column(String, nullable=True)  # JSON массив дней недели (0=пн, 6=вс)
    only_workdays = Column(Boolean, default=False)
    end_condition_type = Column(SQLEnum(EndConditionType), nullable=False, default=EndConditionType.NEVER)
    end_date = Column(Date, nullable=True)
    occurrences_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Связи
    planned_transaction = relationship("PlannedTransactionDB", back_populates="recurrence_rule")


class PlannedOccurrenceDB(Base):
    """
    Конкретное вхождение (экземпляр) плановой транзакции.

    Генерируется автоматически для периодических транзакций на основе правила повторения.
    Каждое вхождение соответствует одной дате исполнения плановой транзакции.

    Attributes:
        id: Уникальный идентификатор вхождения (UUID)
        planned_transaction_id: Ссылка на шаблон плановой транзакции (UUID)
        occurrence_date: Дата вхождения (когда должна быть выполнена)
        amount: Сумма для этого вхождения (по умолчанию = плановая)
        status: Статус вхождения (pending, executed, skipped)
        actual_transaction_id: Ссылка на фактическую транзакцию (после исполнения) (UUID)
        executed_date: Фактическая дата исполнения
        executed_amount: Фактическая сумма исполнения
        skipped_date: Дата пропуска
        skip_reason: Причина пропуска
        created_at: Дата создания записи
        updated_at: Дата последнего обновления
        
    Properties (aliases и вычисляемые поля):
        scheduled_date: Alias для occurrence_date (обратная совместимость)
        amount_deviation: Вычисляемое отклонение по сумме (executed_amount - amount)
        date_deviation: Вычисляемое отклонение по дате в днях (executed_date - occurrence_date).days
    """
    __tablename__ = "planned_occurrences"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    planned_transaction_id = Column(String(36), ForeignKey("planned_transactions.id"), nullable=False)
    occurrence_date = Column(Date, nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(SQLEnum(OccurrenceStatus), default=OccurrenceStatus.PENDING, index=True)
    actual_transaction_id = Column(String(36), ForeignKey("transactions.id"), nullable=True)
    executed_date = Column(Date, nullable=True)
    executed_amount = Column(Numeric(10, 2), nullable=True)
    skipped_date = Column(Date, nullable=True)
    skip_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Связи
    planned_transaction = relationship("PlannedTransactionDB", back_populates="occurrences")
    actual_transaction = relationship("TransactionDB", foreign_keys=[actual_transaction_id])

    # Индексы для производительности
    __table_args__ = (
        Index('ix_planned_occurrences_planned_transaction_id', 'planned_transaction_id'),
        Index('ix_planned_occurrences_planned_transaction_id_occurrence_date', 'planned_transaction_id', 'occurrence_date'),
        Index('ix_planned_occurrences_status_occurrence_date', 'status', 'occurrence_date'),
    )
    
    @property
    def scheduled_date(self) -> date_type:
        """
        Alias для occurrence_date (обратная совместимость).
        
        Возвращает дату вхождения. Используется для обеспечения обратной
        совместимости с кодом, который использовал старое название поля.
        
        Returns:
            Дата вхождения (occurrence_date)
        """
        return self.occurrence_date
    
    @scheduled_date.setter
    def scheduled_date(self, value: date_type) -> None:
        """
        Setter для alias scheduled_date (обратная совместимость).
        
        Устанавливает значение occurrence_date через alias scheduled_date.
        
        Args:
            value: Новое значение даты вхождения
        """
        self.occurrence_date = value
    
    @property
    def amount_deviation(self) -> Optional[Decimal]:
        """
        Вычисляемое отклонение факта от плана по сумме.
        
        Рассчитывается как разница между фактической суммой исполнения
        и плановой суммой. Доступно только для исполненных вхождений.
        
        Returns:
            Отклонение по сумме (executed_amount - amount) для исполненных вхождений,
            None для вхождений со статусом PENDING или SKIPPED
        
        Example:
            >>> occurrence.amount = Decimal('1000.00')
            >>> occurrence.executed_amount = Decimal('1050.50')
            >>> occurrence.status = OccurrenceStatus.EXECUTED
            >>> occurrence.amount_deviation
            Decimal('50.50')
        """
        if self.status == OccurrenceStatus.EXECUTED and self.executed_amount is not None:
            return self.executed_amount - self.amount
        return None
    
    @property
    def date_deviation(self) -> Optional[int]:
        """
        Вычисляемое отклонение факта от плана по дате (в днях).
        
        Рассчитывается как разница в днях между фактической датой исполнения
        и плановой датой вхождения. Доступно только для исполненных вхождений.
        
        Returns:
            Отклонение по дате в днях (executed_date - occurrence_date).days
            для исполненных вхождений, None для вхождений со статусом PENDING или SKIPPED
        
        Example:
            >>> occurrence.occurrence_date = date(2025, 1, 15)
            >>> occurrence.executed_date = date(2025, 1, 17)
            >>> occurrence.status = OccurrenceStatus.EXECUTED
            >>> occurrence.date_deviation
            2
        """
        if self.status == OccurrenceStatus.EXECUTED and self.executed_date is not None:
            return (self.executed_date - self.occurrence_date).days
        return None


class TransactionDB(Base):
    """
    Фактическая финансовая транзакция (доход или расход).

    Это основная модель для хранения всех реальных финансовых операций.

    Attributes:
        id: Уникальный идентификатор транзакции (UUID)
        amount: Сумма транзакции (положительное число)
        type: Тип транзакции (доход или расход)
        category_id: Ссылка на категорию из справочника (UUID)
        description: Описание транзакции (необязательное)
        transaction_date: Дата совершения транзакции
        planned_occurrence_id: Ссылка на плановое вхождение (если создана из плана) (UUID)
        created_at: Дата создания записи
        updated_at: Дата последнего обновления
        
    Properties (aliases):
        date: Alias для transaction_date (обратная совместимость)
    """
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    type = Column(SQLEnum(TransactionType), nullable=False)
    category_id = Column(String(36), ForeignKey("categories.id"), nullable=False)
    description = Column(String)
    transaction_date = Column(Date, nullable=False, index=True)
    planned_occurrence_id = Column(String(36), ForeignKey("planned_occurrences.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Связи
    category = relationship("CategoryDB", back_populates="transactions")
    planned_occurrence = relationship("PlannedOccurrenceDB", foreign_keys=[planned_occurrence_id])

    # Индексы для быстрого поиска
    __table_args__ = (
        Index('ix_transactions_date_type', 'transaction_date', 'type'),
        Index('ix_transactions_category_id_date', 'category_id', 'transaction_date'),
    )
    
    @property
    def date(self) -> date_type:
        """
        Alias для transaction_date (обратная совместимость).

        Возвращает дату транзакции. Используется для обеспечения обратной
        совместимости с кодом, который использовал старое название поля.

        Returns:
            Дата транзакции (transaction_date)
        """
        return self.transaction_date

    @date.setter
    def date(self, value: date_type):
        """
        Setter для date (устанавливает transaction_date).

        Args:
            value: Новая дата транзакции
        """
        self.transaction_date = value


class LenderDB(Base):
    """
    Займодатель (банк, микрофинансовая организация или физическое лицо).

    Attributes:
        id: Уникальный идентификатор (UUID)
        name: Название займодателя
        lender_type: Тип займодателя (основное поле)
        type: Alias для lender_type (обратная совместимость)
        description: Описание (опционально)
        contact_info: Контактная информация (опционально)
        notes: Примечания (опционально)
        created_at: Дата создания записи
        updated_at: Дата последнего обновления
        loans: Список кредитов от этого займодателя
    """
    __tablename__ = "lenders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String, nullable=False, unique=True)
    lender_type = Column(SQLEnum(LenderType), default=LenderType.OTHER)
    description = Column(String, nullable=True)
    contact_info = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Связи
    loans = relationship("LoanDB", back_populates="lender")

    @property
    def type(self) -> LenderType:
        """
        Alias для lender_type (обратная совместимость).
        
        Returns:
            Тип займодателя
        """
        return self.lender_type
    
    @type.setter
    def type(self, value: LenderType) -> None:
        """
        Setter для alias type (обратная совместимость).
        
        Args:
            value: Новое значение типа займодателя
        """
        self.lender_type = value


class LoanDB(Base):
    """
    Кредит или займ.

    Attributes:
        id: Уникальный идентификатор (UUID)
        lender_id: ID займодателя (UUID)
        name: Название кредита
        loan_type: Тип кредита
        amount: Сумма кредита
        interest_rate: Годовая процентная ставка (%)
        term_months: Срок кредита в месяцах
        issue_date: Дата выдачи кредита
        end_date: Дата окончания кредита (опционально, вычисляется автоматически если не указана)
        disbursement_transaction_id: ID транзакции выдачи кредита (опционально) (UUID)
        contract_number: Номер договора (опционально)
        description: Описание (опционально)
        status: Статус кредита
        created_at: Дата создания записи
        updated_at: Дата последнего обновления
        lender: Займодатель
        payments: Список платежей по кредиту
        disbursement_transaction: Транзакция выдачи кредита

    Properties (вычисляемые поля):
        calculated_end_date: Вычисляемая дата окончания кредита
            - Если end_date указана явно, возвращает её
            - Если end_date = None, вычисляет как issue_date + term_months
            - Если term_months = None и end_date = None, возвращает None
    """
    __tablename__ = "loans"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    lender_id = Column(String(36), ForeignKey("lenders.id"), nullable=False)
    name = Column(String, nullable=False)
    loan_type = Column(SQLEnum(LoanType), default=LoanType.OTHER)
    amount = Column(Numeric(10, 2), nullable=False)
    interest_rate = Column(Numeric(5, 2), nullable=True)
    term_months = Column(Integer, nullable=True)
    issue_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)  # НОВОЕ: явная дата окончания кредита
    disbursement_transaction_id = Column(String(36), ForeignKey("transactions.id"), nullable=True)  # Транзакция выдачи
    contract_number = Column(String, nullable=True)
    description = Column(String, nullable=True)
    status = Column(SQLEnum(LoanStatus), default=LoanStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Связи
    lender = relationship("LenderDB", back_populates="loans")
    payments = relationship("LoanPaymentDB", back_populates="loan", cascade="all, delete-orphan")
    disbursement_transaction = relationship("TransactionDB", foreign_keys=[disbursement_transaction_id])

    # Индексы
    __table_args__ = (
        Index('ix_loans_lender_id', 'lender_id'),
        Index('ix_loans_status', 'status'),
        Index('ix_loans_issue_date', 'issue_date'),
    )
    
    @property
    def calculated_end_date(self) -> Optional[date_type]:
        """
        Вычисляемая дата окончания кредита.
        
        Логика вычисления:
        1. Если end_date указана явно, возвращает её (приоритет явной даты)
        2. Если end_date = None, но term_months указан, вычисляет как issue_date + term_months
        3. Если оба поля None, возвращает None
        
        Returns:
            Дата окончания кредита или None, если невозможно вычислить
        
        Example:
            >>> loan.end_date = date(2026, 12, 31)
            >>> loan.calculated_end_date
            date(2026, 12, 31)  # Явная дата имеет приоритет
            
            >>> loan.end_date = None
            >>> loan.issue_date = date(2025, 1, 1)
            >>> loan.term_months = 12
            >>> loan.calculated_end_date
            date(2026, 1, 1)  # Вычислено автоматически
            
            >>> loan.end_date = None
            >>> loan.term_months = None
            >>> loan.calculated_end_date
            None  # Невозможно вычислить
        """
        # Приоритет 1: Явная дата окончания
        if self.end_date is not None:
            return self.end_date
        
        # Приоритет 2: Вычисление через term_months
        if self.term_months is not None:
            from dateutil.relativedelta import relativedelta
            return self.issue_date + relativedelta(months=self.term_months)
        
        # Если ничего не указано, возвращаем None
        return None


class LoanPaymentDB(Base):
    """
    Платёж по кредиту.

    Attributes:
        id: Уникальный идентификатор (UUID)
        loan_id: ID кредита (UUID)
        scheduled_date: Запланированная дата платежа
        principal_amount: Сумма основного долга
        interest_amount: Сумма процентов
        total_amount: Общая сумма платежа
        status: Статус платежа
        planned_transaction_id: ID плановой транзакции (UUID)
        actual_transaction_id: ID фактической транзакции (после исполнения) (UUID)
        executed_date: Фактическая дата выплаты
        executed_amount: Фактическая сумма выплаты
        overdue_days: Количество дней просрочки
        created_at: Дата создания записи
        updated_at: Дата последнего обновления
        loan: Кредит, к которому относится платеж
        planned_transaction: Плановая транзакция
        actual_transaction: Фактическая транзакция
    """
    __tablename__ = "loan_payments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    loan_id = Column(String(36), ForeignKey("loans.id"), nullable=False)
    scheduled_date = Column(Date, nullable=False)
    principal_amount = Column(Numeric(10, 2), nullable=False)
    interest_amount = Column(Numeric(10, 2), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING)
    planned_transaction_id = Column(String(36), ForeignKey("planned_transactions.id"), nullable=True)
    actual_transaction_id = Column(String(36), ForeignKey("transactions.id"), nullable=True)
    executed_date = Column(Date, nullable=True)
    executed_amount = Column(Numeric(10, 2), nullable=True)
    overdue_days = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Связи
    loan = relationship("LoanDB", back_populates="payments")
    planned_transaction = relationship("PlannedTransactionDB")
    actual_transaction = relationship("TransactionDB", foreign_keys=[actual_transaction_id])

    # Индексы для производительности
    __table_args__ = (
        Index('ix_loan_payments_loan_id', 'loan_id'),
        Index('ix_loan_payments_scheduled_date', 'scheduled_date'),
        Index('ix_loan_payments_status', 'status'),
        Index('ix_loan_payments_loan_id_scheduled_date', 'loan_id', 'scheduled_date'),
    )


class PendingPaymentDB(Base):
    """
    Отложенный платёж — расход без конкретной даты или с плановой датой.

    Отложенные платежи позволяют пользователю отслеживать расходы, которые
    нужно совершить, но нельзя привязать к конкретной дате. Опционально
    можно установить плановую дату для интеграции с календарём и прогнозом баланса.

    Attributes:
        id: Уникальный идентификатор платежа (UUID)
        amount: Сумма платежа
        category_id: Ссылка на категорию расходов (ОБЯЗАТЕЛЬНО тип EXPENSE) (UUID)
        description: Описание платежа (НЕ может быть пустым)
        priority: Приоритет (low, medium, high, critical)
        planned_date: Опциональная плановая дата исполнения (NULL = без даты)
        status: Статус (active, executed, cancelled)
        actual_transaction_id: Ссылка на фактическую транзакцию (после исполнения) (UUID)
        executed_date: Фактическая дата исполнения
        executed_amount: Фактическая сумма исполнения
        cancelled_date: Дата отмены
        cancel_reason: Причина отмены
        created_at: Дата создания записи
        updated_at: Дата последнего обновления
    """
    __tablename__ = "pending_payments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    category_id = Column(String(36), ForeignKey("categories.id"), nullable=False)
    description = Column(String, nullable=False)
    priority = Column(SQLEnum(PendingPaymentPriority), default=PendingPaymentPriority.MEDIUM)
    planned_date = Column(Date, nullable=True)
    status = Column(SQLEnum(PendingPaymentStatus), default=PendingPaymentStatus.ACTIVE)

    # Факт исполнения
    actual_transaction_id = Column(String(36), ForeignKey("transactions.id"), nullable=True)
    executed_date = Column(Date, nullable=True, index=True)
    executed_amount = Column(Numeric(10, 2), nullable=True)

    # Отмена
    cancelled_date = Column(Date, nullable=True, index=True)
    cancel_reason = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Связи
    category = relationship("CategoryDB", back_populates="pending_payments")
    actual_transaction = relationship("TransactionDB", foreign_keys=[actual_transaction_id])

    # Индексы для производительности
    __table_args__ = (
        Index('ix_pending_payments_status', 'status'),
        Index('ix_pending_payments_priority', 'priority'),
        Index('ix_pending_payments_planned_date', 'planned_date'),
        Index('ix_pending_payments_category_id', 'category_id'),
        Index('ix_pending_payments_status_planned_date', 'status', 'planned_date'),
    )


# =============================================================================
# Pydantic модели для валидации и API responses
# =============================================================================

class TransactionCreate(BaseModel):
    """
    Pydantic модель для создания транзакции с валидацией.

    Обеспечивает валидацию данных при создании новой транзакции:
    - Проверяет, что сумма положительная
    - Проверяет, что дата не в будущем
    - Проверяет валидность типа транзакции

    Attributes:
        amount: Сумма транзакции (должна быть больше 0)
        type: Тип транзакции (доход или расход)
        category_id: ID категории из справочника (UUID)
        description: Необязательное описание транзакции
        transaction_date: Дата транзакции (по умолчанию текущая дата)
    """
    amount: Decimal = Field(gt=Decimal('0'), description="Сумма транзакции должна быть положительной")
    type: TransactionType
    category_id: str
    description: Optional[str] = None
    transaction_date: date_type = Field(default_factory=date_type.today)

    @field_validator('category_id')
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        """Валидация формата UUID."""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError(f'Невалидный UUID: {v}')


class TransactionUpdate(BaseModel):
    """
    Pydantic модель для обновления транзакции.

    Все поля опциональные - обновляются только указанные.
    """
    amount: Optional[Decimal] = Field(None, gt=Decimal('0'))
    type: Optional[TransactionType] = None
    category_id: Optional[str] = None
    description: Optional[str] = None
    transaction_date: Optional[date_type] = None

    @field_validator('category_id')
    @classmethod
    def validate_uuid(cls, v: Optional[str]) -> Optional[str]:
        """Валидация формата UUID."""
        if v is not None:
            try:
                uuid.UUID(v)
            except ValueError:
                raise ValueError(f'Невалидный UUID: {v}')
        return v


class Transaction(TransactionCreate):
    """
    Pydantic модель для чтения транзакции из базы данных.

    Добавляет поля, которые генерируются автоматически:
    - id
    - created_at
    - updated_at
    """
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Category(BaseModel):
    """
    Pydantic модель для категории.

    Используется для чтения категорий из БД и возврата через API.
    """
    id: str
    name: str
    type: TransactionType
    is_system: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CategoryCreate(BaseModel):
    """
    Pydantic модель для создания категории с валидацией.
    
    Обеспечивает валидацию данных при создании новой категории:
    - Проверяет, что название не пустое и не состоит только из пробелов
    - Автоматически обрезает пробелы по краям названия
    
    Attributes:
        name: Название категории (не может быть пустым)
        type: Тип категории (доход или расход)
        is_system: Признак системной категории (по умолчанию False)
    """
    name: str = Field(description="Название категории")
    type: TransactionType
    is_system: bool = False
    
    @field_validator('name')
    @classmethod
    def name_not_empty_and_trim(cls, v: str) -> str:
        """
        Валидатор для проверки и обрезки названия категории.
        
        Проверяет, что название не пустое и не состоит только из пробелов.
        Автоматически обрезает пробелы по краям.
        
        Args:
            v: Значение поля name для валидации
            
        Returns:
            Обрезанное название категории
            
        Raises:
            ValueError: Если название пустое или состоит только из пробелов
            
        Example:
            >>> CategoryCreate(name="  Продукты  ", type=TransactionType.EXPENSE)
            CategoryCreate(name="Продукты", type=TransactionType.EXPENSE, is_system=False)
        """
        if not v or not v.strip():
            raise ValueError('Название категории не может быть пустым или состоять только из пробелов')
        return v.strip()


class PlannedTransactionCreate(BaseModel):
    """
    Pydantic модель для создания плановой транзакции.

    Attributes:
        amount: Сумма транзакции (должна быть > 0)
        category_id: ID категории (UUID)
        description: Описание (опционально)
        type: Тип транзакции (INCOME или EXPENSE)
        start_date: Дата начала
        end_date: Дата окончания (опционально, должна быть > start_date)
        recurrence_rule: Правило повторения (опционально)
        is_active: Флаг активности (по умолчанию True)
    """
    amount: Decimal = Field(gt=Decimal('0'), description="Сумма транзакции")
    category_id: str = Field(description="ID категории (UUID)")
    description: Optional[str] = None
    type: TransactionType
    start_date: date_type
    end_date: Optional[date_type] = None
    recurrence_rule: Optional["RecurrenceRuleCreate"] = None
    is_active: bool = True

    @field_validator('category_id')
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        """Валидация формата UUID."""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError(f'Невалидный UUID: {v}')

    @field_validator('end_date')
    @classmethod
    def end_date_after_start(cls, v: Optional[date_type], values) -> Optional[date_type]:
        """Проверка, что end_date больше start_date (если указан)."""
        if v is not None and 'start_date' in values.data:
            start_date = values.data['start_date']
            if v <= start_date:
                raise ValueError('Дата окончания должна быть позже даты начала')
        return v


class PlannedTransaction(PlannedTransactionCreate):
    """
    Pydantic модель для чтения плановой транзакции из БД.
    """
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecurrenceRuleCreate(BaseModel):
    """
    Pydantic модель для создания правила повторения с валидацией.
    
    Обеспечивает валидацию данных при создании правила повторения:
    - Интервал должен быть больше 0 (если указан)
    - Количество повторений должно быть больше 0 (если указано)
    
    Attributes:
        recurrence_type: Тип повторения (по умолчанию NONE)
        interval: Интервал повторения (должен быть > 0, если указан)
        interval_unit: Единица интервала (дни, недели, месяцы, годы)
        weekdays: Дни недели для повторения (JSON массив)
        only_workdays: Признак "только рабочие дни"
        end_condition_type: Тип условия окончания (по умолчанию NEVER)
        end_date: Дата окончания (для UNTIL_DATE)
        occurrences_count: Количество повторений (должно быть > 0, если указано)
    """
    recurrence_type: RecurrenceType = RecurrenceType.NONE
    interval: Optional[int] = Field(None, gt=0, description="Интервал должен быть больше нуля")
    interval_unit: Optional[IntervalUnit] = None
    weekdays: Optional[str] = None
    only_workdays: bool = False
    end_condition_type: EndConditionType = EndConditionType.NEVER
    end_date: Optional[date_type] = None
    occurrences_count: Optional[int] = Field(None, gt=0, description="Количество повторений должно быть больше нуля")


class RecurrenceRule(RecurrenceRuleCreate):
    """
    Pydantic модель для чтения правила повторения из БД.
    """
    id: str
    planned_transaction_id: str

    model_config = ConfigDict(from_attributes=True)


class PlannedOccurrenceCreate(BaseModel):
    """
    Pydantic модель для создания вхождения плановой транзакции.
    """
    planned_transaction_id: str
    occurrence_date: date_type
    amount: Decimal = Field(gt=Decimal('0'))
    status: OccurrenceStatus = OccurrenceStatus.PENDING

    @field_validator('planned_transaction_id')
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        """Валидация формата UUID."""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError(f'Невалидный UUID: {v}')


class PlannedOccurrence(PlannedOccurrenceCreate):
    """
    Pydantic модель для чтения вхождения из БД.
    """
    id: str
    actual_transaction_id: Optional[str] = None
    executed_date: Optional[date_type] = None
    executed_amount: Optional[Decimal] = None
    skipped_date: Optional[date_type] = None
    skip_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Lender(BaseModel):
    """
    Pydantic модель для чтения займодателя из базы данных.

    Attributes:
        id: Уникальный идентификатор
        name: Название займодателя
        lender_type: Тип займодателя
        type: Alias для lender_type
        description: Описание
        contact_info: Контактная информация
        notes: Примечания
        created_at: Дата создания
        updated_at: Дата обновления
    """
    id: str
    name: str
    lender_type: LenderType
    description: Optional[str] = None
    contact_info: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def type(self) -> LenderType:
        """Alias для lender_type."""
        return self.lender_type


class LenderCreate(BaseModel):
    """
    Pydantic модель для создания займодателя.

    Attributes:
        name: Название займодателя (должно быть уникальным)
        lender_type: Тип займодателя (поддерживает оба имени: type и lender_type)
        description: Описание (опционально)
        contact_info: Контактная информация (опционально)
        notes: Примечания (опционально)
    """
    name: str = Field(min_length=1, max_length=200, description="Название займодателя")
    lender_type: LenderType = Field(default=LenderType.OTHER, description="Тип займодателя", alias="type")
    description: Optional[str] = Field(None, max_length=500, description="Описание")
    contact_info: Optional[str] = Field(None, max_length=500, description="Контактная информация")
    notes: Optional[str] = Field(None, max_length=1000, description="Примечания")

    model_config = ConfigDict(populate_by_name=True)

    @property
    def type(self) -> LenderType:
        """Alias для lender_type."""
        return self.lender_type

    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        """Проверка, что название не пустое."""
        if not v or not v.strip():
            raise ValueError('Название не может быть пустым')
        return v.strip()


class LenderUpdate(BaseModel):
    """
    Pydantic модель для обновления займодателя.

    Все поля опциональные — обновляются только указанные.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    lender_type: Optional[LenderType] = None
    description: Optional[str] = Field(None, max_length=500)


class Loan(BaseModel):
    """
    Pydantic модель для чтения кредита из базы данных.

    Attributes:
        id: Уникальный идентификатор
        lender_id: ID займодателя
        name: Название кредита
        loan_type: Тип кредита
        amount: Сумма кредита
        interest_rate: Процентная ставка
        term_months: Срок в месяцах
        issue_date: Дата выдачи
        end_date: Дата окончания
        contract_number: Номер договора
        description: Описание
        status: Статус кредита
        created_at: Дата создания
        updated_at: Дата обновления
    """
    id: str
    lender_id: str
    name: str
    loan_type: LoanType
    amount: Decimal
    interest_rate: Optional[Decimal] = None
    term_months: Optional[int] = None
    issue_date: date_type
    end_date: Optional[date_type] = None
    contract_number: Optional[str] = None
    description: Optional[str] = None
    status: LoanStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoanCreate(BaseModel):
    """
    Pydantic модель для создания кредита.

    Attributes:
        lender_id: ID займодателя
        name: Название кредита
        loan_type: Тип кредита
        amount: Сумма кредита (должна быть > 0)
        interest_rate: Годовая процентная ставка (%)
        term_months: Срок кредита в месяцах
        issue_date: Дата выдачи кредита
        end_date: Планируемая дата окончания (опционально)
        contract_number: Номер договора (опционально)
        description: Описание (опционально)
    """
    lender_id: str
    name: str = Field(min_length=1, max_length=200, description="Название кредита")
    loan_type: LoanType = LoanType.OTHER
    amount: Decimal = Field(gt=Decimal('0'), description="Сумма кредита")
    interest_rate: Optional[Decimal] = Field(None, ge=Decimal('0'), le=Decimal('100'), description="Процентная ставка (%)")
    term_months: Optional[int] = Field(None, gt=0, description="Срок в месяцах")
    issue_date: date_type = Field(description="Дата выдачи кредита")
    end_date: Optional[date_type] = Field(None, description="Планируемая дата окончания")
    contract_number: Optional[str] = Field(None, max_length=100, description="Номер договора")
    description: Optional[str] = Field(None, max_length=500, description="Описание")

    @field_validator('lender_id')
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        """Валидация формата UUID."""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError(f'Невалидный UUID: {v}')

    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        """Проверка, что название не пустое."""
        if not v or not v.strip():
            raise ValueError('Название не может быть пустым')
        return v.strip()


class LoanUpdate(BaseModel):
    """
    Pydantic модель для обновления кредита.

    Все поля опциональные — обновляются только указанные.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    loan_type: Optional[LoanType] = None
    interest_rate: Optional[Decimal] = Field(None, ge=Decimal('0'), le=Decimal('100'))
    term_months: Optional[int] = Field(None, gt=0)
    end_date: Optional[date_type] = None
    contract_number: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    status: Optional[LoanStatus] = None


class LoanPaymentCreate(BaseModel):
    """
    Pydantic модель для создания платежа по кредиту.

    Attributes:
        loan_id: ID кредита
        scheduled_date: Запланированная дата платежа
        principal_amount: Сумма основного долга (должна быть >= 0)
        interest_amount: Сумма процентов (должна быть >= 0)
        total_amount: Общая сумма платежа (должна быть > 0)
    """
    loan_id: str
    scheduled_date: date_type
    principal_amount: Decimal = Field(ge=Decimal('0'), description="Сумма основного долга")
    interest_amount: Decimal = Field(ge=Decimal('0'), description="Сумма процентов")
    total_amount: Decimal = Field(gt=Decimal('0'), description="Общая сумма платежа")

    @field_validator('loan_id')
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        """Валидация формата UUID."""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError(f'Невалидный UUID: {v}')

    @field_validator('total_amount')
    @classmethod
    def validate_total_amount(cls, v: Decimal, info) -> Decimal:
        """Проверка, что total_amount = principal_amount + interest_amount."""
        if 'principal_amount' in info.data and 'interest_amount' in info.data:
            expected = info.data['principal_amount'] + info.data['interest_amount']
            if abs(v - expected) > Decimal('0.01'):  # Допуск на округление
                raise ValueError(f'Общая сумма должна равняться сумме основного долга и процентов ({expected:.2f})')
        return v


class LoanPayment(LoanPaymentCreate):
    """
    Pydantic модель для чтения платежа из базы данных.

    Attributes:
        id: Уникальный идентификатор
        status: Статус платежа
        planned_transaction_id: ID плановой транзакции
        actual_transaction_id: ID фактической транзакции
        executed_date: Фактическая дата выплаты
        executed_amount: Фактическая сумма выплаты
        overdue_days: Количество дней просрочки
        created_at: Дата создания
        updated_at: Дата обновления
    """
    id: str
    status: PaymentStatus
    planned_transaction_id: Optional[str] = None
    actual_transaction_id: Optional[str] = None
    executed_date: Optional[date_type] = None
    executed_amount: Optional[Decimal] = None
    overdue_days: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PendingPaymentCreate(BaseModel):
    """
    Pydantic модель для создания отложенного платежа.

    Attributes:
        amount: Сумма платежа (должна быть > 0)
        category_id: ID категории расходов
        description: Описание платежа (не может быть пустым)
        priority: Приоритет (по умолчанию MEDIUM)
        planned_date: Опциональная плановая дата
    """
    amount: Decimal = Field(gt=Decimal('0'), description="Сумма платежа")
    category_id: str = Field(description="ID категории")
    description: str = Field(min_length=1, description="Описание платежа")
    priority: PendingPaymentPriority = PendingPaymentPriority.MEDIUM
    planned_date: Optional[date_type] = None

    @field_validator('category_id')
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        """Валидация формата UUID."""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError(f'Невалидный UUID: {v}')

    @field_validator('description')
    @classmethod
    def description_not_empty(cls, v: str) -> str:
        """Проверка, что описание не пустое."""
        if not v or not v.strip():
            raise ValueError('Описание не может быть пустым')
        return v.strip()


class PendingPaymentUpdate(BaseModel):
    """
    Pydantic модель для обновления отложенного платежа.

    Все поля опциональные — обновляются только указанные.
    """
    amount: Optional[Decimal] = Field(None, gt=Decimal('0'))
    category_id: Optional[str] = Field(None)
    description: Optional[str] = Field(None, min_length=1)
    priority: Optional[PendingPaymentPriority] = None
    planned_date: Optional[date_type] = None

    @field_validator('category_id')
    @classmethod
    def validate_uuid(cls, v: Optional[str]) -> Optional[str]:
        """Валидация формата UUID."""
        if v is not None:
            try:
                uuid.UUID(v)
            except ValueError:
                raise ValueError(f'Невалидный UUID: {v}')
        return v

    @field_validator('description')
    @classmethod
    def description_not_empty(cls, v: Optional[str]) -> Optional[str]:
        """Проверка, что описание не пустое."""
        if v is not None:
            if not v.strip():
                raise ValueError('Описание не может быть пустым')
            return v.strip()
        return v


class PendingPaymentExecute(BaseModel):
    """
    Pydantic модель для исполнения отложенного платежа.

    Attributes:
        executed_date: Дата исполнения (по умолчанию сегодня)
        executed_amount: Фактическая сумма (по умолчанию = amount)
    """
    executed_date: date_type = Field(default_factory=date_type.today)
    executed_amount: Optional[Decimal] = Field(None, gt=Decimal('0'))


class PendingPaymentCancel(BaseModel):
    """
    Pydantic модель для отмены отложенного платежа.

    Attributes:
        cancel_reason: Причина отмены (опционально)
    """
    cancel_reason: Optional[str] = None


class PendingPayment(PendingPaymentCreate):
    """
    Pydantic модель для чтения отложенного платежа из БД.
    """
    id: str
    status: PendingPaymentStatus
    actual_transaction_id: Optional[str] = None
    executed_date: Optional[date_type] = None
    executed_amount: Optional[Decimal] = None
    cancelled_date: Optional[date_type] = None
    cancel_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
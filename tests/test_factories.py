"""
Фабрики для создания тестовых данных.

Этот модуль предоставляет функции-фабрики для создания тестовых объектов
всех моделей приложения. Фабрики упрощают создание тестовых данных и
обеспечивают консистентность между тестами.

Каждая фабрика:
- Принимает опциональные параметры для переопределения значений по умолчанию
- Возвращает объект модели SQLAlchemy (не сохраняет в БД автоматически)
- Предоставляет разумные значения по умолчанию для всех полей
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional

from finance_tracker.models import (
    CategoryDB,
    TransactionDB,
    PlannedTransactionDB,
    RecurrenceRuleDB,
    PlannedOccurrenceDB,
    LenderDB,
    LoanDB,
    LoanPaymentDB,
    PendingPaymentDB,
)
from finance_tracker.models.enums import (
    TransactionType,
    RecurrenceType,
    OccurrenceStatus,
    IntervalUnit,
    EndConditionType,
    LenderType,
    LoanType,
    LoanStatus,
    PaymentStatus,
    PendingPaymentPriority,
    PendingPaymentStatus,
)


# =============================================================================
# Фабрики для основных моделей
# =============================================================================

def create_test_category(
    id: Optional[int] = None,
    name: str = "Тестовая категория",
    type: TransactionType = TransactionType.EXPENSE,
    is_system: bool = False,
    created_at: Optional[datetime] = None,
) -> CategoryDB:
    """
    Создаёт тестовую категорию.

    Args:
        id: Уникальный идентификатор (None = автогенерация)
        name: Название категории
        type: Тип категории (доход или расход)
        is_system: Признак системной категории
        created_at: Дата создания (None = текущее время)

    Returns:
        Объект CategoryDB (не сохранён в БД)

    Example:
        >>> category = create_test_category(name="Продукты", type=TransactionType.EXPENSE)
        >>> session.add(category)
        >>> session.commit()
    """
    return CategoryDB(
        id=id,
        name=name,
        type=type,
        is_system=is_system,
        created_at=created_at or datetime.now(),
    )


def create_test_transaction(
    id: Optional[int] = None,
    amount: Decimal = Decimal("100.00"),
    type: TransactionType = TransactionType.EXPENSE,
    category_id: int = 1,
    description: Optional[str] = "Тестовая транзакция",
    transaction_date: Optional[date] = None,
    planned_occurrence_id: Optional[int] = None,
    created_at: Optional[datetime] = None,
    updated_at: Optional[datetime] = None,
) -> TransactionDB:
    """
    Создаёт тестовую транзакцию.

    Args:
        id: Уникальный идентификатор (None = автогенерация)
        amount: Сумма транзакции
        type: Тип транзакции (доход или расход)
        category_id: ID категории
        description: Описание транзакции
        transaction_date: Дата транзакции (None = сегодня)
        planned_occurrence_id: ID планового вхождения (если создана из плана)
        created_at: Дата создания (None = текущее время)
        updated_at: Дата обновления (None = текущее время)

    Returns:
        Объект TransactionDB (не сохранён в БД)

    Example:
        >>> transaction = create_test_transaction(
        ...     amount=Decimal("500.00"),
        ...     type=TransactionType.INCOME,
        ...     category_id=2
        ... )
    """
    return TransactionDB(
        id=id,
        amount=amount,
        type=type,
        category_id=category_id,
        description=description,
        transaction_date=transaction_date or date.today(),
        planned_occurrence_id=planned_occurrence_id,
        created_at=created_at or datetime.now(),
        updated_at=updated_at or datetime.now(),
    )


def create_test_planned_transaction(
    id: Optional[int] = None,
    amount: Decimal = Decimal("100.00"),
    category_id: int = 1,
    description: Optional[str] = "Тестовая плановая транзакция",
    type: TransactionType = TransactionType.EXPENSE,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    is_active: bool = True,
    created_at: Optional[datetime] = None,
    updated_at: Optional[datetime] = None,
) -> PlannedTransactionDB:
    """
    Создаёт тестовую плановую транзакцию.

    Args:
        id: Уникальный идентификатор (None = автогенерация)
        amount: Плановая сумма
        category_id: ID категории
        description: Описание
        type: Тип транзакции
        start_date: Дата начала (None = сегодня)
        end_date: Дата окончания (None = бессрочно)
        is_active: Признак активности
        created_at: Дата создания (None = текущее время)
        updated_at: Дата обновления (None = текущее время)

    Returns:
        Объект PlannedTransactionDB (не сохранён в БД)

    Example:
        >>> planned = create_test_planned_transaction(
        ...     amount=Decimal("1000.00"),
        ...     start_date=date(2025, 1, 1),
        ...     end_date=date(2025, 12, 31)
        ... )
    """
    return PlannedTransactionDB(
        id=id,
        amount=amount,
        category_id=category_id,
        description=description,
        type=type,
        start_date=start_date or date.today(),
        end_date=end_date,
        is_active=is_active,
        created_at=created_at or datetime.now(),
        updated_at=updated_at or datetime.now(),
    )


def create_test_lender(
    id: Optional[int] = None,
    name: str = "Тестовый займодатель",
    lender_type: LenderType = LenderType.BANK,
    description: Optional[str] = None,
    contact_info: Optional[str] = None,
    notes: Optional[str] = None,
    created_at: Optional[datetime] = None,
    updated_at: Optional[datetime] = None,
) -> LenderDB:
    """
    Создаёт тестового займодателя.

    Args:
        id: Уникальный идентификатор (None = автогенерация)
        name: Название займодателя
        lender_type: Тип займодателя
        description: Описание
        contact_info: Контактная информация
        notes: Примечания
        created_at: Дата создания (None = текущее время)
        updated_at: Дата обновления (None = текущее время)

    Returns:
        Объект LenderDB (не сохранён в БД)

    Example:
        >>> lender = create_test_lender(
        ...     name="Сбербанк",
        ...     lender_type=LenderType.BANK,
        ...     contact_info="8-800-555-55-55"
        ... )
    """
    return LenderDB(
        id=id,
        name=name,
        lender_type=lender_type,
        description=description,
        contact_info=contact_info,
        notes=notes,
        created_at=created_at or datetime.now(),
        updated_at=updated_at or datetime.now(),
    )


def create_test_loan(
    id: Optional[int] = None,
    lender_id: int = 1,
    name: str = "Тестовый кредит",
    loan_type: LoanType = LoanType.CONSUMER,
    amount: Decimal = Decimal("100000.00"),
    interest_rate: Optional[Decimal] = Decimal("10.5"),
    term_months: Optional[int] = 12,
    issue_date: Optional[date] = None,
    end_date: Optional[date] = None,
    disbursement_transaction_id: Optional[int] = None,
    contract_number: Optional[str] = None,
    description: Optional[str] = None,
    status: LoanStatus = LoanStatus.ACTIVE,
    created_at: Optional[datetime] = None,
    updated_at: Optional[datetime] = None,
) -> LoanDB:
    """
    Создаёт тестовый кредит.

    Args:
        id: Уникальный идентификатор (None = автогенерация)
        lender_id: ID займодателя
        name: Название кредита
        loan_type: Тип кредита
        amount: Сумма кредита
        interest_rate: Годовая процентная ставка (%)
        term_months: Срок кредита в месяцах
        issue_date: Дата выдачи (None = сегодня)
        end_date: Дата окончания (None = вычисляется автоматически)
        disbursement_transaction_id: ID транзакции выдачи
        contract_number: Номер договора
        description: Описание
        status: Статус кредита
        created_at: Дата создания (None = текущее время)
        updated_at: Дата обновления (None = текущее время)

    Returns:
        Объект LoanDB (не сохранён в БД)

    Example:
        >>> loan = create_test_loan(
        ...     name="Ипотека",
        ...     loan_type=LoanType.MORTGAGE,
        ...     amount=Decimal("5000000.00"),
        ...     interest_rate=Decimal("8.5"),
        ...     term_months=240
        ... )
    """
    return LoanDB(
        id=id,
        lender_id=lender_id,
        name=name,
        loan_type=loan_type,
        amount=amount,
        interest_rate=interest_rate,
        term_months=term_months,
        issue_date=issue_date or date.today(),
        end_date=end_date,
        disbursement_transaction_id=disbursement_transaction_id,
        contract_number=contract_number,
        description=description,
        status=status,
        created_at=created_at or datetime.now(),
        updated_at=updated_at or datetime.now(),
    )


def create_test_pending_payment(
    id: Optional[int] = None,
    amount: Decimal = Decimal("100.00"),
    category_id: int = 1,
    description: str = "Тестовый отложенный платёж",
    priority: PendingPaymentPriority = PendingPaymentPriority.MEDIUM,
    planned_date: Optional[date] = None,
    status: PendingPaymentStatus = PendingPaymentStatus.ACTIVE,
    actual_transaction_id: Optional[int] = None,
    executed_date: Optional[date] = None,
    executed_amount: Optional[Decimal] = None,
    cancelled_date: Optional[date] = None,
    cancel_reason: Optional[str] = None,
    created_at: Optional[datetime] = None,
    updated_at: Optional[datetime] = None,
) -> PendingPaymentDB:
    """
    Создаёт тестовый отложенный платёж.

    Args:
        id: Уникальный идентификатор (None = автогенерация)
        amount: Сумма платежа
        category_id: ID категории расходов
        description: Описание платежа
        priority: Приоритет
        planned_date: Плановая дата (None = без даты)
        status: Статус платежа
        actual_transaction_id: ID фактической транзакции
        executed_date: Фактическая дата исполнения
        executed_amount: Фактическая сумма исполнения
        cancelled_date: Дата отмены
        cancel_reason: Причина отмены
        created_at: Дата создания (None = текущее время)
        updated_at: Дата обновления (None = текущее время)

    Returns:
        Объект PendingPaymentDB (не сохранён в БД)

    Example:
        >>> payment = create_test_pending_payment(
        ...     amount=Decimal("5000.00"),
        ...     description="Оплата за интернет",
        ...     priority=PendingPaymentPriority.HIGH,
        ...     planned_date=date(2025, 1, 15)
        ... )
    """
    return PendingPaymentDB(
        id=id,
        amount=amount,
        category_id=category_id,
        description=description,
        priority=priority,
        planned_date=planned_date,
        status=status,
        actual_transaction_id=actual_transaction_id,
        executed_date=executed_date,
        executed_amount=executed_amount,
        cancelled_date=cancelled_date,
        cancel_reason=cancel_reason,
        created_at=created_at or datetime.now(),
        updated_at=updated_at or datetime.now(),
    )


# =============================================================================
# Фабрики для дополнительных моделей
# =============================================================================

def create_test_recurrence_rule(
    id: Optional[int] = None,
    planned_transaction_id: int = 1,
    recurrence_type: RecurrenceType = RecurrenceType.DAILY,
    interval: Optional[int] = 1,
    interval_unit: Optional[IntervalUnit] = IntervalUnit.DAYS,
    weekdays: Optional[str] = None,
    only_workdays: bool = False,
    end_condition_type: EndConditionType = EndConditionType.NEVER,
    end_date: Optional[date] = None,
    occurrences_count: Optional[int] = None,
) -> RecurrenceRuleDB:
    """
    Создаёт тестовое правило повторения.

    Args:
        id: Уникальный идентификатор (None = автогенерация)
        planned_transaction_id: ID плановой транзакции
        recurrence_type: Тип повторения
        interval: Интервал повторения
        interval_unit: Единица интервала
        weekdays: Дни недели (JSON массив)
        only_workdays: Признак "только рабочие дни"
        end_condition_type: Тип условия окончания
        end_date: Дата окончания
        occurrences_count: Количество повторений

    Returns:
        Объект RecurrenceRuleDB (не сохранён в БД)

    Example:
        >>> rule = create_test_recurrence_rule(
        ...     recurrence_type=RecurrenceType.WEEKLY,
        ...     interval=1,
        ...     weekdays="[0,2,4]",  # Пн, Ср, Пт
        ...     end_condition_type=EndConditionType.AFTER_COUNT,
        ...     occurrences_count=10
        ... )
    """
    return RecurrenceRuleDB(
        id=id,
        planned_transaction_id=planned_transaction_id,
        recurrence_type=recurrence_type,
        interval=interval,
        interval_unit=interval_unit,
        weekdays=weekdays,
        only_workdays=only_workdays,
        end_condition_type=end_condition_type,
        end_date=end_date,
        occurrences_count=occurrences_count,
    )


def create_test_planned_occurrence(
    id: Optional[int] = None,
    planned_transaction_id: int = 1,
    occurrence_date: Optional[date] = None,
    amount: Decimal = Decimal("100.00"),
    status: OccurrenceStatus = OccurrenceStatus.PENDING,
    actual_transaction_id: Optional[int] = None,
    executed_date: Optional[date] = None,
    executed_amount: Optional[Decimal] = None,
    skipped_date: Optional[date] = None,
    skip_reason: Optional[str] = None,
    created_at: Optional[datetime] = None,
) -> PlannedOccurrenceDB:
    """
    Создаёт тестовое вхождение плановой транзакции.

    Args:
        id: Уникальный идентификатор (None = автогенерация)
        planned_transaction_id: ID плановой транзакции
        occurrence_date: Дата вхождения (None = сегодня)
        amount: Сумма вхождения
        status: Статус вхождения
        actual_transaction_id: ID фактической транзакции
        executed_date: Фактическая дата исполнения
        executed_amount: Фактическая сумма исполнения
        skipped_date: Дата пропуска
        skip_reason: Причина пропуска
        created_at: Дата создания (None = текущее время)

    Returns:
        Объект PlannedOccurrenceDB (не сохранён в БД)

    Example:
        >>> occurrence = create_test_planned_occurrence(
        ...     occurrence_date=date(2025, 1, 15),
        ...     amount=Decimal("1000.00"),
        ...     status=OccurrenceStatus.PENDING
        ... )
    """
    return PlannedOccurrenceDB(
        id=id,
        planned_transaction_id=planned_transaction_id,
        occurrence_date=occurrence_date or date.today(),
        amount=amount,
        status=status,
        actual_transaction_id=actual_transaction_id,
        executed_date=executed_date,
        executed_amount=executed_amount,
        skipped_date=skipped_date,
        skip_reason=skip_reason,
        created_at=created_at or datetime.now(),
    )


def create_test_loan_payment(
    id: Optional[int] = None,
    loan_id: int = 1,
    scheduled_date: Optional[date] = None,
    principal_amount: Decimal = Decimal("8000.00"),
    interest_amount: Decimal = Decimal("875.00"),
    total_amount: Optional[Decimal] = None,
    status: PaymentStatus = PaymentStatus.PENDING,
    planned_transaction_id: Optional[int] = None,
    actual_transaction_id: Optional[int] = None,
    executed_date: Optional[date] = None,
    executed_amount: Optional[Decimal] = None,
    overdue_days: Optional[int] = None,
    created_at: Optional[datetime] = None,
    updated_at: Optional[datetime] = None,
) -> LoanPaymentDB:
    """
    Создаёт тестовый платёж по кредиту.

    Args:
        id: Уникальный идентификатор (None = автогенерация)
        loan_id: ID кредита
        scheduled_date: Запланированная дата (None = сегодня)
        principal_amount: Сумма основного долга
        interest_amount: Сумма процентов
        total_amount: Общая сумма (None = principal + interest)
        status: Статус платежа
        planned_transaction_id: ID плановой транзакции
        actual_transaction_id: ID фактической транзакции
        executed_date: Фактическая дата выплаты
        executed_amount: Фактическая сумма выплаты
        overdue_days: Количество дней просрочки
        created_at: Дата создания (None = текущее время)
        updated_at: Дата обновления (None = текущее время)

    Returns:
        Объект LoanPaymentDB (не сохранён в БД)

    Example:
        >>> payment = create_test_loan_payment(
        ...     scheduled_date=date(2025, 2, 1),
        ...     principal_amount=Decimal("10000.00"),
        ...     interest_amount=Decimal("1000.00")
        ... )
    """
    if total_amount is None:
        total_amount = principal_amount + interest_amount

    return LoanPaymentDB(
        id=id,
        loan_id=loan_id,
        scheduled_date=scheduled_date or date.today(),
        principal_amount=principal_amount,
        interest_amount=interest_amount,
        total_amount=total_amount,
        status=status,
        planned_transaction_id=planned_transaction_id,
        actual_transaction_id=actual_transaction_id,
        executed_date=executed_date,
        executed_amount=executed_amount,
        overdue_days=overdue_days,
        created_at=created_at or datetime.now(),
        updated_at=updated_at or datetime.now(),
    )


# =============================================================================
# Генераторы граничных значений и edge cases
# =============================================================================

def create_minimal_category() -> CategoryDB:
    """
    Создаёт категорию с минимальным набором полей.

    Returns:
        Категория с минимальными обязательными полями
    """
    return CategoryDB(
        name="Минимальная",
        type=TransactionType.EXPENSE,
    )


def create_minimal_transaction(category_id: int) -> TransactionDB:
    """
    Создаёт транзакцию с минимальным набором полей.

    Args:
        category_id: ID существующей категории

    Returns:
        Транзакция с минимальными обязательными полями
    """
    return TransactionDB(
        amount=Decimal("0.01"),  # Минимальная сумма
        type=TransactionType.EXPENSE,
        category_id=category_id,
        transaction_date=date.today(),
    )


def create_large_amount_transaction(category_id: int) -> TransactionDB:
    """
    Создаёт транзакцию с очень большой суммой (граничное значение).

    Args:
        category_id: ID существующей категории

    Returns:
        Транзакция с большой суммой
    """
    return TransactionDB(
        amount=Decimal("99999999.99"),  # Максимальная сумма для Numeric(10, 2)
        type=TransactionType.INCOME,
        category_id=category_id,
        transaction_date=date.today(),
    )


def create_old_date_transaction(category_id: int) -> TransactionDB:
    """
    Создаёт транзакцию с очень старой датой (edge case).

    Args:
        category_id: ID существующей категории

    Returns:
        Транзакция с датой в прошлом
    """
    return TransactionDB(
        amount=Decimal("100.00"),
        type=TransactionType.EXPENSE,
        category_id=category_id,
        transaction_date=date(2000, 1, 1),
    )


def create_future_date_transaction(category_id: int) -> TransactionDB:
    """
    Создаёт транзакцию с будущей датой (edge case для валидации).

    Args:
        category_id: ID существующей категории

    Returns:
        Транзакция с будущей датой
    """
    return TransactionDB(
        amount=Decimal("100.00"),
        type=TransactionType.EXPENSE,
        category_id=category_id,
        transaction_date=date.today() + timedelta(days=365),
    )


def create_zero_interest_loan(lender_id: int) -> LoanDB:
    """
    Создаёт кредит с нулевой процентной ставкой (edge case).

    Args:
        lender_id: ID существующего займодателя

    Returns:
        Кредит с нулевой ставкой
    """
    return LoanDB(
        lender_id=lender_id,
        name="Беспроцентный займ",
        loan_type=LoanType.OTHER,
        amount=Decimal("50000.00"),
        interest_rate=Decimal("0.00"),
        term_months=12,
        issue_date=date.today(),
        status=LoanStatus.ACTIVE,
    )


def create_short_term_loan(lender_id: int) -> LoanDB:
    """
    Создаёт краткосрочный кредит (edge case).

    Args:
        lender_id: ID существующего займодателя

    Returns:
        Кредит на 1 месяц
    """
    return LoanDB(
        lender_id=lender_id,
        name="Краткосрочный займ",
        loan_type=LoanType.CONSUMER,
        amount=Decimal("10000.00"),
        interest_rate=Decimal("15.0"),
        term_months=1,
        issue_date=date.today(),
        status=LoanStatus.ACTIVE,
    )


def create_long_term_loan(lender_id: int) -> LoanDB:
    """
    Создаёт долгосрочный кредит (edge case).

    Args:
        lender_id: ID существующего займодателя

    Returns:
        Кредит на 30 лет (360 месяцев)
    """
    return LoanDB(
        lender_id=lender_id,
        name="Ипотека на 30 лет",
        loan_type=LoanType.MORTGAGE,
        amount=Decimal("10000000.00"),
        interest_rate=Decimal("8.5"),
        term_months=360,
        issue_date=date.today(),
        status=LoanStatus.ACTIVE,
    )


def create_high_priority_pending_payment(category_id: int) -> PendingPaymentDB:
    """
    Создаёт отложенный платёж с критическим приоритетом.

    Args:
        category_id: ID существующей категории расходов

    Returns:
        Отложенный платёж с приоритетом CRITICAL
    """
    return PendingPaymentDB(
        amount=Decimal("50000.00"),
        category_id=category_id,
        description="Срочный платёж",
        priority=PendingPaymentPriority.CRITICAL,
        planned_date=date.today(),
        status=PendingPaymentStatus.ACTIVE,
    )


def create_no_date_pending_payment(category_id: int) -> PendingPaymentDB:
    """
    Создаёт отложенный платёж без плановой даты (edge case).

    Args:
        category_id: ID существующей категории расходов

    Returns:
        Отложенный платёж без даты
    """
    return PendingPaymentDB(
        amount=Decimal("1000.00"),
        category_id=category_id,
        description="Платёж без даты",
        priority=PendingPaymentPriority.LOW,
        planned_date=None,  # Без даты
        status=PendingPaymentStatus.ACTIVE,
    )

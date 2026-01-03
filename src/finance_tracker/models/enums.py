"""
Модуль перечислений (enums) для Finance Tracker Flet.

Содержит все Enum классы, используемые в моделях данных.
"""

from enum import Enum


class TransactionType(str, Enum):
    """
    Тип финансовой транзакции.

    Attributes:
        INCOME: Доход (поступление средств)
        EXPENSE: Расход (трата средств)
    """
    INCOME = "income"
    EXPENSE = "expense"


class RecurrenceType(str, Enum):
    """
    Тип правила повторения для периодических транзакций.

    Attributes:
        NONE: Однократная транзакция (без повторения)
        DAILY: Ежедневное повторение
        WEEKLY: Еженедельное повторение
        MONTHLY: Ежемесячное повторение
        YEARLY: Ежегодное повторение
        CUSTOM: Кастомное правило повторения
    """
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class OccurrenceStatus(str, Enum):
    """
    Статус вхождения плановой транзакции.

    Attributes:
        PENDING: Ожидается исполнение
        EXECUTED: Исполнено (создана фактическая транзакция)
        SKIPPED: Пропущено пользователем
    """
    PENDING = "pending"
    EXECUTED = "executed"
    SKIPPED = "skipped"


class IntervalUnit(str, Enum):
    """
    Единица измерения интервала для кастомных правил повторения.

    Attributes:
        DAYS: Дни
        WEEKS: Недели
        MONTHS: Месяцы
        YEARS: Годы
    """
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"
    YEARS = "years"


class EndConditionType(str, Enum):
    """
    Тип условия окончания для периодических транзакций.

    Attributes:
        NEVER: Бессрочно (без даты окончания)
        UNTIL_DATE: До указанной даты
        AFTER_COUNT: После N повторений
    """
    NEVER = "never"
    UNTIL_DATE = "until_date"
    AFTER_COUNT = "after_count"


class LenderType(str, Enum):
    """
    Тип займодателя.

    Attributes:
        BANK: Банк
        MFO: Микрофинансовая организация
        INDIVIDUAL: Физическое лицо
        COLLECTOR: Коллекторское агентство
        OTHER: Другое
    """
    BANK = "bank"
    MFO = "mfo"
    INDIVIDUAL = "individual"
    COLLECTOR = "collector"
    OTHER = "other"


class LoanType(str, Enum):
    """
    Тип кредита.

    Attributes:
        MICROLOAN: Микрокредит
        CONSUMER: Потребительский кредит
        MORTGAGE: Ипотека
        PERSONAL: Личный займ
        OTHER: Другое
    """
    MICROLOAN = "microloan"
    CONSUMER = "consumer"
    MORTGAGE = "mortgage"
    PERSONAL = "personal"
    OTHER = "other"


class LoanStatus(str, Enum):
    """
    Статус кредита.

    Attributes:
        ACTIVE: Активный
        PAID_OFF: Погашен
        OVERDUE: Просрочен
    """
    ACTIVE = "active"
    PAID_OFF = "paid_off"
    OVERDUE = "overdue"


class PaymentStatus(str, Enum):
    """
    Статус платежа по кредиту.

    Attributes:
        PENDING: Ожидается
        EXECUTED: Выполнен
        EXECUTED_LATE: Выполнен с просрочкой
        OVERDUE: Просрочен
        CANCELLED: Отменен
    """
    PENDING = "pending"
    EXECUTED = "executed"
    EXECUTED_LATE = "executed_late"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class PendingPaymentPriority(str, Enum):
    """
    Приоритет отложенного платежа.

    Attributes:
        LOW: Низкий приоритет
        MEDIUM: Средний приоритет
        HIGH: Высокий приоритет
        CRITICAL: Критический приоритет
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PendingPaymentStatus(str, Enum):
    """
    Статус отложенного платежа.

    Attributes:
        ACTIVE: Активный (ожидает исполнения)
        EXECUTED: Выполнен (создана фактическая транзакция)
        CANCELLED: Отменён пользователем
    """
    ACTIVE = "active"
    EXECUTED = "executed"
    CANCELLED = "cancelled"

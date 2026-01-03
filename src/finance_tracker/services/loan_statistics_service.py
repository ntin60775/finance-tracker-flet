"""
Сервис для расчета статистики по кредитам.

Предоставляет функции для расчета различных метрик:
- Общая статистика по активным кредитам
- Расчет кредитной нагрузки на доход
- Статистика просроченной задолженности
- Статистика платежей за период
"""

import logging
from typing import Dict, Any
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from finance_tracker.models import (
    LoanDB, LoanPaymentDB, TransactionDB,
    LoanStatus, PaymentStatus, TransactionType
)
from finance_tracker.services.loan_service import get_debt_by_holder_statistics

# Настройка логирования
logger = logging.getLogger(__name__)


def get_summary_statistics(session: Session) -> Dict[str, Any]:
    """
    Получает общую статистику по кредитам.

    Рассчитывает:
    - Общую сумму активных кредитов
    - Ежемесячную сумму запланированных платежей
    - Общее количество активных кредитов
    - Общее количество закрытых кредитов
    - Информацию о текущих держателях долга

    Args:
        session: Активная сессия БД

    Returns:
        Словарь со статистикой:
        {
            "total_active_loans": количество активных,
            "total_active_amount": сумма активных,
            "total_closed_loans": количество закрытых,
            "monthly_payments_sum": сумма ежемесячных платежей,
            "total_interest_expected": ожидаемые проценты,
            "total_overpayment": переплата,
            "by_holder": статистика по текущим держателям {
                holder_id: {
                    "holder_name": имя держателя,
                    "loan_count": количество кредитов,
                    "total_debt": общая задолженность
                }
            }
        }

    Raises:
        SQLAlchemyError: При ошибках работы с БД

    Example:
        >>> with get_db_session() as session:
        ...     stats = get_summary_statistics(session)
        ...     print(f"Активных кредитов: {stats['total_active_loans']}")
        ...     for holder_id, holder_info in stats['by_holder'].items():
        ...         print(f"Держатель {holder_info['holder_name']}: {holder_info['total_debt']}")
    """
    try:
        # <ai:block name="active_loans_stats">
        #     <ai:purpose>Получение статистики по активным кредитам</ai:purpose>

        # Получаем активные кредиты
        active_loans = session.query(LoanDB).filter(
            LoanDB.status == LoanStatus.ACTIVE
        ).all()

        # <ai:step type="calculation">
        total_active_loans = len(active_loans)
        total_active_amount = sum(loan.amount for loan in active_loans)
        # </ai:step>

        # Получаем закрытые кредиты
        closed_loans = session.query(LoanDB).filter(
            LoanDB.status == LoanStatus.PAID_OFF
        ).all()

        # <ai:step type="calculation">
        total_closed_loans = len(closed_loans)
        # </ai:step>
        # </ai:block>

        # <ai:block name="monthly_payments_calculation">
        #     <ai:purpose>Расчет ежемесячных платежей</ai:purpose>

        # Для каждого активного кредита получаем платежи
        monthly_payments_sum = Decimal('0')
        total_interest_expected = Decimal('0')
        total_overpayment = Decimal('0')

        for loan in active_loans:
            # Получаем все платежи по этому кредиту
            payments = session.query(LoanPaymentDB).filter_by(
                loan_id=loan.id,
                status=PaymentStatus.PENDING
            ).all()

            # <ai:step type="calculation">
            # Суммируем платежи (приблизительно ежемесячные платежи)
            for payment in payments:
                monthly_payments_sum += payment.total_amount
                total_interest_expected += payment.interest_amount
            # </ai:step>

        # Рассчитываем переплату
        total_overpayment = sum(loan.amount * (loan.interest_rate / Decimal('100')) / Decimal('12')
                               for loan in active_loans
                               if loan.interest_rate > 0)

        # </ai:block>

        # <ai:block name="holder_statistics">
        #     <ai:purpose>Получение статистики по текущим держателям долга</ai:purpose>

        # Получаем статистику по держателям для активных кредитов
        holder_stats = get_debt_by_holder_statistics(session, status=LoanStatus.ACTIVE)

        # Форматируем статистику по держателям для возврата
        by_holder = {}
        for holder_id, holder_info in holder_stats.items():
            by_holder[holder_id] = {
                "holder_name": holder_info["holder_name"],
                "loan_count": holder_info["loan_count"],
                "total_debt": round(holder_info["total_debt"], 2)
            }

        # </ai:block>

        logger.info(
            f"Получена общая статистика: активных кредитов={total_active_loans}, "
            f"сумма={total_active_amount}, ежемесячные платежи={monthly_payments_sum}, "
            f"держателей={len(by_holder)}"
        )

        return {
            "total_active_loans": total_active_loans,
            "total_active_amount": round(total_active_amount, 2),
            "total_closed_loans": total_closed_loans,
            "monthly_payments_sum": round(monthly_payments_sum, 2),
            "total_interest_expected": round(total_interest_expected, 2),
            "total_overpayment": round(total_overpayment, 2),
            "by_holder": by_holder
        }

    except SQLAlchemyError as e:
        error_msg = f"Ошибка при получении статистики кредитов: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    except Exception as e:
        error_msg = f"Неожиданная ошибка при расчете статистики: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg)


def get_monthly_burden_statistics(session: Session) -> Dict[str, Any]:
    """
    Рассчитывает кредитную нагрузку на доход.

    Кредитная нагрузка = ежемесячные платежи / средний месячный доход * 100%

    Args:
        session: Активная сессия БД

    Returns:
        Словарь со статистикой:
        {
            "monthly_income": средний месячный доход,
            "monthly_payments": ежемесячные платежи,
            "burden_percent": процент нагрузки,
            "is_healthy": True если < 30%, False если > 30%
        }

    Raises:
        ValueError: При ошибках расчета

    Example:
        >>> with get_db_session() as session:
        ...     burden = get_monthly_burden_statistics(session)
        ...     if burden["is_healthy"]:
        ...         print("Кредитная нагрузка в норме")
    """
    try:
        # <ai:block name="income_calculation">
        #     <ai:purpose>Расчет среднего месячного дохода</ai:purpose>

        # Получаем все доходные транзакции за последние 6 месяцев
        six_months_ago = date.today() - timedelta(days=180)

        income_transactions = session.query(TransactionDB).filter(
            TransactionDB.type == TransactionType.INCOME,
            TransactionDB.transaction_date >= six_months_ago
        ).all()

        # <ai:step type="calculation">
        total_income = sum(t.amount for t in income_transactions)
        # Предполагаем 180 дней = 6 месяцев
        monthly_income = total_income / Decimal('6') if total_income > 0 else Decimal('0')
        # </ai:step>

        # </ai:block>

        # <ai:block name="burden_calculation">
        #     <ai:purpose>Расчет кредитной нагрузки</ai:purpose>

        # Получаем ежемесячные платежи (из предыдущей функции)
        summary = get_summary_statistics(session)
        monthly_payments = Decimal(str(summary["monthly_payments_sum"]))

        # <ai:step type="calculation">
        # Рассчитываем процент нагрузки
        if monthly_income > 0:
            burden_percent = (monthly_payments / monthly_income) * Decimal('100')
        else:
            burden_percent = Decimal('0') if monthly_payments == 0 else Decimal('100')
        # </ai:step>

        # <ai:condition test="burden_level">
        # Здоровая нагрузка считается < 30%
        is_healthy = burden_percent < 30
        # </ai:condition>

        # </ai:block>

        logger.info(
            f"Расчет кредитной нагрузки: доход={monthly_income}, "
            f"платежи={monthly_payments}, нагрузка={burden_percent}%"
        )

        return {
            "monthly_income": round(monthly_income, 2),
            "monthly_payments": round(monthly_payments, 2),
            "burden_percent": round(burden_percent, 2),
            "is_healthy": is_healthy
        }

    except ValueError:
        raise
    except Exception as e:
        error_msg = f"Ошибка при расчете кредитной нагрузки: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg)


def get_overdue_statistics(session: Session) -> Dict[str, Any]:
    """
    Получает статистику по просроченной задолженности.

    Args:
        session: Активная сессия БД

    Returns:
        Словарь со статистикой:
        {
            "total_overdue_payments": количество просроченных платежей,
            "total_overdue_amount": сумма просрочки,
            "overdue_by_loan": {
                loan_id: {
                    "loan_name": название,
                    "count": количество,
                    "total_amount": сумма
                }
            },
            "most_overdue_loan": информация о кредите с максимальной просрочкой
        }

    Raises:
        SQLAlchemyError: При ошибках работы с БД

    Example:
        >>> with get_db_session() as session:
        ...     overdue = get_overdue_statistics(session)
        ...     if overdue["total_overdue_payments"] > 0:
        ...         print(f"Просроченные платежи: {overdue['total_overdue_amount']}")
    """
    try:
        # <ai:block name="overdue_payments">
        #     <ai:purpose>Получение просроченных платежей</ai:purpose>

        # Получаем все просроченные платежи
        overdue_payments = session.query(LoanPaymentDB).filter(
            LoanPaymentDB.status == PaymentStatus.OVERDUE
        ).all()

        # <ai:step type="calculation">
        total_overdue_count = len(overdue_payments)
        total_overdue_amount = sum(p.total_amount for p in overdue_payments)
        # </ai:step>

        # </ai:block>

        # <ai:block name="overdue_by_loan">
        #     <ai:purpose>Группировка просроченных платежей по кредитам</ai:purpose>

        overdue_by_loan: Dict[int, Dict[str, Any]] = {}

        for payment in overdue_payments:
            loan = payment.loan
            loan_id = loan.id

            if loan_id not in overdue_by_loan:
                overdue_by_loan[loan_id] = {
                    "loan_name": loan.name,
                    "count": 0,
                    "total_amount": Decimal('0'),
                    "oldest_payment_date": None,
                    "overdue_days": 0
                }

            overdue_by_loan[loan_id]["count"] += 1
            overdue_by_loan[loan_id]["total_amount"] += payment.total_amount

            # <ai:condition test="oldest_payment">
            # Отслеживаем самый старый просроченный платеж
            if overdue_by_loan[loan_id]["oldest_payment_date"] is None:
                overdue_by_loan[loan_id]["oldest_payment_date"] = payment.scheduled_date
            else:
                if payment.scheduled_date < overdue_by_loan[loan_id]["oldest_payment_date"]:
                    overdue_by_loan[loan_id]["oldest_payment_date"] = payment.scheduled_date
            # </ai:condition>

        # Рассчитываем количество дней просрочки
        today = date.today()
        for loan_id, loan_info in overdue_by_loan.items():
            if loan_info["oldest_payment_date"]:
                overdue_days = (today - loan_info["oldest_payment_date"]).days
                loan_info["overdue_days"] = max(0, overdue_days)

        # </ai:block>

        # <ai:block name="most_overdue">
        #     <ai:purpose>Поиск кредита с максимальной просрочкой</ai:purpose>

        most_overdue_loan = None
        if overdue_by_loan:
            most_overdue_loan = max(
                overdue_by_loan.items(),
                key=lambda x: x[1]["total_amount"]
            )
            most_overdue_loan = {
                "loan_id": most_overdue_loan[0],
                "loan_name": most_overdue_loan[1]["loan_name"],
                "total_amount": most_overdue_loan[1]["total_amount"],
                "overdue_days": most_overdue_loan[1]["overdue_days"]
            }

        # </ai:block>

        logger.info(
            f"Статистика просрочки: всего просроченных={total_overdue_count}, "
            f"сумма={total_overdue_amount}, по кредитам={len(overdue_by_loan)}"
        )

        return {
            "total_overdue_payments": total_overdue_count,
            "total_overdue_amount": round(total_overdue_amount, 2),
            "overdue_by_loan": {
                str(k): {**v, "total_amount": round(v["total_amount"], 2)}
                for k, v in overdue_by_loan.items()
            },
            "most_overdue_loan": most_overdue_loan
        }

    except SQLAlchemyError as e:
        error_msg = f"Ошибка при получении статистики просрочки: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    except Exception as e:
        error_msg = f"Неожиданная ошибка при расчете статистики просрочки: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg)


def get_period_statistics(
    session: Session,
    start_date: date,
    end_date: date
) -> Dict[str, Any]:
    """
    Получает статистику платежей за период.

    Args:
        session: Активная сессия БД
        start_date: Начало периода (включительно)
        end_date: Конец периода (включительно)

    Returns:
        Словарь со статистикой:
        {
            "period_start": дата начала,
            "period_end": дата конца,
            "total_payments_count": количество платежей,
            "total_principal_paid": выплачено основного долга,
            "total_interest_paid": выплачено процентов,
            "total_paid": выплачено всего,
            "average_payment": средний платеж,
            "by_loan": статистика по каждому кредиту
        }

    Raises:
        ValueError: Если start_date > end_date

    Example:
        >>> with get_db_session() as session:
        ...     stats = get_period_statistics(session, date(2025, 1, 1), date(2025, 12, 31))
        ...     print(f"Выплачено за год: {stats['total_paid']}")
    """
    try:
        # <ai:condition test="date_validation">
        if start_date > end_date:
            raise ValueError("Start date must be before or equal to end date")
        # </ai:condition>

        # <ai:block name="period_payments">
        #     <ai:purpose>Получение платежей в периоде</ai:purpose>

        # Получаем исполненные платежи в периоде
        payments = session.query(LoanPaymentDB).filter(
            LoanPaymentDB.scheduled_date >= start_date,
            LoanPaymentDB.scheduled_date <= end_date,
            LoanPaymentDB.actual_transaction_id.isnot(None)
        ).all()

        # <ai:step type="calculation">
        total_payments = len(payments)
        total_principal = sum(p.principal_amount for p in payments)
        total_interest = sum(p.interest_amount for p in payments)
        total_paid = sum(p.executed_amount or Decimal('0') for p in payments)
        # </ai:step>

        # <ai:step type="calculation">
        average_payment = total_paid / Decimal(str(total_payments)) if total_payments > 0 else Decimal('0')
        # </ai:step>

        # </ai:block>

        # <ai:block name="by_loan_statistics">
        #     <ai:purpose>Статистика по каждому кредиту</ai:purpose>

        by_loan: Dict[int, Dict[str, Any]] = {}

        for payment in payments:
            loan = payment.loan
            loan_id = loan.id

            if loan_id not in by_loan:
                by_loan[loan_id] = {
                    "loan_name": loan.name,
                    "loan_type": loan.loan_type.value,
                    "count": 0,
                    "principal_paid": Decimal('0'),
                    "interest_paid": Decimal('0'),
                    "total_paid": Decimal('0')
                }

            by_loan[loan_id]["count"] += 1
            by_loan[loan_id]["principal_paid"] += payment.principal_amount
            by_loan[loan_id]["interest_paid"] += payment.interest_amount
            by_loan[loan_id]["total_paid"] += payment.executed_amount or Decimal('0')

        # </ai:block>

        logger.info(
            f"Получена статистика за период {start_date} - {end_date}: "
            f"платежей={total_payments}, выплачено={total_paid}"
        )

        return {
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "total_payments_count": total_payments,
            "total_principal_paid": round(total_principal, 2),
            "total_interest_paid": round(total_interest, 2),
            "total_paid": round(total_paid, 2),
            "average_payment": round(average_payment, 2),
            "by_loan": {
                str(k): {**v,
                         "principal_paid": round(v["principal_paid"], 2),
                         "interest_paid": round(v["interest_paid"], 2),
                         "total_paid": round(v["total_paid"], 2)}
                for k, v in by_loan.items()
            }
        }

    except ValueError:
        raise
    except SQLAlchemyError as e:
        error_msg = f"Ошибка при получении статистики за период: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    except Exception as e:
        error_msg = f"Неожиданная ошибка при расчете статистики периода: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg)

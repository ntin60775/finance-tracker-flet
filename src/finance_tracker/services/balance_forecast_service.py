"""
Сервис прогнозирования баланса с учётом плановых транзакций и платежей по кредитам.

Предоставляет функции для:
- Расчёта фактического баланса на основе фактических транзакций
- Расчёта прогнозируемого баланса с учётом плановых транзакций и платежей по кредитам
- Получения прогноза баланса на период
- Определения кассовых разрывов (когда прогнозируемый баланс становится отрицательным)
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from finance_tracker.models.models import (
    TransactionDB,
    PlannedTransactionDB,
    LoanPaymentDB,
    PendingPaymentDB,
)
from finance_tracker.models.enums import (
    TransactionType,
    PaymentStatus,
    PendingPaymentStatus
)
from finance_tracker.services.recurrence_service import generate_occurrences_for_period

# Настройка логирования
logger = logging.getLogger(__name__)


def _get_pending_payments_for_period(
    session: Session,
    start_date: date,
    end_date: date
) -> List[PendingPaymentDB]:
    """
    Получает активные отложенные платежи с плановой датой для указанного периода.
    
    Функция возвращает только активные отложенные платежи (status=ACTIVE),
    у которых установлена плановая дата (planned_date IS NOT NULL) в указанном периоде.
    
    Согласно правилу календаря: если платёж отображается в календаре (имеет planned_date),
    он ДОЛЖЕН учитываться в прогнозе баланса и кассовых разрывах.
    
    Args:
        session: Активная сессия БД для выполнения запросов
        start_date: Начало периода для поиска
        end_date: Конец периода для поиска (включительно)
        
    Returns:
        Список активных отложенных платежей с плановой датой в указанном периоде.
        Список может быть пустым, если таких платежей нет.
        
    Raises:
        SQLAlchemyError: При ошибках работы с БД
        
    Example:
        >>> with get_db_session() as session:
        ...     # Получить отложенные платежи на неделю
        ...     payments = _get_pending_payments_for_period(
        ...         session,
        ...         date.today(),
        ...         date.today() + timedelta(days=7)
        ...     )
        ...     print(f"Найдено {len(payments)} отложенных платежей")
    """
    try:
        # <ai:step type="query">Получаем активные отложенные платежи с плановой датой</ai:step>
        pending_payments = session.query(PendingPaymentDB).filter(
            PendingPaymentDB.status == PendingPaymentStatus.ACTIVE,
            PendingPaymentDB.planned_date.isnot(None),
            PendingPaymentDB.planned_date >= start_date,
            PendingPaymentDB.planned_date <= end_date
        ).all()
        
        logger.debug(
            f"Найдено {len(pending_payments)} активных отложенных платежей "
            f"с плановой датой в периоде {start_date} - {end_date}"
        )
        
        return pending_payments
        
    except SQLAlchemyError as e:
        error_msg = (
            f"Ошибка при получении отложенных платежей для периода "
            f"{start_date} - {end_date}: {e}"
        )
        logger.error(error_msg)
        raise


def calculate_actual_balance(
    session: Session,
    up_to_date: date
) -> Decimal:
    """
    Вычисляет фактический баланс на основе фактических транзакций до указанной даты.
    
    Функция суммирует все доходы и вычитает все расходы из фактических транзакций,
    которые произошли до указанной даты (включительно). Плановые транзакции
    НЕ учитываются в фактическом балансе.
    
    Args:
        session: Активная сессия БД для выполнения запросов
        up_to_date: Дата, до которой (включительно) рассчитывается баланс
        
    Returns:
        Фактический баланс (доходы - расходы). Может быть отрицательным.
        
    Raises:
        SQLAlchemyError: При ошибках работы с БД
        
    Example:
        >>> with get_db_session() as session:
        ...     # Получить фактический баланс на сегодня
        ...     balance = calculate_actual_balance(session, date.today())
        ...     print(f"Текущий баланс: {balance}")
        ...     
        ...     # Получить фактический баланс на конкретную дату
        ...     balance = calculate_actual_balance(session, date(2025, 1, 15))
    """
    try:
        # Получаем все фактические транзакции до указанной даты
        transactions = session.query(TransactionDB).filter(
            TransactionDB.transaction_date <= up_to_date
        ).all()
        
        # Вычисляем баланс
        balance = Decimal('0.0')
        
        for transaction in transactions:
            if transaction.type == TransactionType.INCOME:
                balance += transaction.amount
            elif transaction.type == TransactionType.EXPENSE:
                balance -= transaction.amount
        
        logger.info(
            f"Рассчитан фактический баланс на {up_to_date}: {balance:.2f} "
            f"(транзакций: {len(transactions)})"
        )
        
        return balance
        
    except SQLAlchemyError as e:
        error_msg = f"Ошибка при расчёте фактического баланса на {up_to_date}: {e}"
        logger.error(error_msg)
        raise


def calculate_forecast_balance(
    session: Session,
    target_date: date
) -> Decimal:
    """
    Вычисляет прогнозируемый баланс на указанную дату.

    Функция рассчитывает прогнозируемый баланс как сумму:
    - Фактического баланса на текущую дату
    - Всех неисполненных плановых транзакций до target_date
    - Всех неисполненных платежей по кредитам до target_date

    Учитываются только активные плановые транзакции (is_active=True) и платежи со статусом PENDING/OVERDUE.
    Для периодических транзакций генерируются все вхождения до target_date.

    Args:
        session: Активная сессия БД для выполнения запросов
        target_date: Дата, на которую рассчитывается прогноз

    Returns:
        Прогнозируемый баланс на указанную дату. Может быть отрицательным.

    Raises:
        SQLAlchemyError: При ошибках работы с БД

    Example:
        >>> with get_db_session() as session:
        ...     # Получить прогноз на следующий месяц
        ...     forecast = calculate_forecast_balance(
        ...         session,
        ...         date.today() + timedelta(days=30)
        ...     )
        ...     print(f"Прогнозируемый баланс через месяц: {forecast}")
    """
    try:
        # Получаем фактический баланс на сегодня
        today = date.today()
        actual_balance = calculate_actual_balance(session, today)

        # Если target_date в прошлом или сегодня, возвращаем фактический баланс
        if target_date <= today:
            return actual_balance

        # Получаем все активные плановые транзакции
        planned_transactions = session.query(PlannedTransactionDB).filter(
            PlannedTransactionDB.is_active
        ).all()

        # Вычисляем прогнозируемый баланс
        forecast_balance = actual_balance

        for planned_tx in planned_transactions:
            # <ai:step type="calculation">Генерируем вхождения для периода</ai:step>
            occurrences = generate_occurrences_for_period(
                session,
                planned_tx,
                today + timedelta(days=1),  # Начинаем с завтрашнего дня
                target_date
            )

            # Добавляем/вычитаем суммы плановых транзакций
            for occurrence_date in occurrences:
                if planned_tx.type == TransactionType.INCOME:
                    forecast_balance += planned_tx.amount
                elif planned_tx.type == TransactionType.EXPENSE:
                    forecast_balance -= planned_tx.amount

        # <ai:step type="calculation">Учитываем платежи по кредитам</ai:step>
        # Получаем все неисполненные платежи до target_date
        loan_payments = session.query(LoanPaymentDB).filter(
            LoanPaymentDB.scheduled_date > today,
            LoanPaymentDB.scheduled_date <= target_date,
            LoanPaymentDB.status.in_([PaymentStatus.PENDING, PaymentStatus.OVERDUE])
        ).all()

        for payment in loan_payments:
            # Платежи - это расходы, поэтому вычитаем их из прогноза
            forecast_balance -= payment.total_amount

        # <ai:step type="calculation">Учитываем отложенные платежи с плановой датой</ai:step>
        # Получаем активные отложенные платежи с плановой датой до target_date
        # Согласно правилу календаря: если платёж имеет planned_date, он учитывается в прогнозе
        pending_payments = _get_pending_payments_for_period(
            session,
            today + timedelta(days=1),  # Начинаем с завтрашнего дня
            target_date
        )

        for pending_payment in pending_payments:
            # Отложенные платежи - это всегда расходы, поэтому вычитаем их из прогноза
            forecast_balance -= pending_payment.amount

        logger.info(
            f"Рассчитан прогнозируемый баланс на {target_date}: {forecast_balance:.2f} "
            f"(фактический: {actual_balance:.2f}, плановых транзакций: {len(planned_transactions)}, "
            f"платежей по кредитам: {len(loan_payments)}, "
            f"отложенных платежей: {len(pending_payments)})"
        )

        return forecast_balance

    except SQLAlchemyError as e:
        error_msg = f"Ошибка при расчёте прогнозируемого баланса на {target_date}: {e}"
        logger.error(error_msg)
        raise


def get_forecast_for_period(
    session: Session,
    start_date: date,
    end_date: date
) -> Dict[date, Tuple[Decimal, Decimal]]:
    """
    Возвращает прогноз баланса для каждой даты в периоде.

    Функция рассчитывает фактический и прогнозируемый баланс для каждой даты
    в указанном периоде. Используется для отображения прогноза в календаре
    и для анализа финансового состояния на период.

    Учитывает плановые транзакции и платежи по кредитам.

    Args:
        session: Активная сессия БД для выполнения запросов
        start_date: Начало периода для прогноза
        end_date: Конец периода для прогноза (включительно)

    Returns:
        Словарь {дата: (фактический_баланс, прогнозируемый_баланс)}.
        Для дат в прошлом фактический и прогнозируемый балансы совпадают.
        Для будущих дат прогнозируемый баланс учитывает плановые транзакции и платежи по кредитам.

    Raises:
        ValueError: Если start_date > end_date
        SQLAlchemyError: При ошибках работы с БД

    Example:
        >>> with get_db_session() as session:
        ...     # Получить прогноз на неделю
        ...     forecast = get_forecast_for_period(
        ...         session,
        ...         date.today(),
        ...         date.today() + timedelta(days=7)
        ...     )
        ...
        ...     for forecast_date, (actual, predicted) in forecast.items():
        ...         print(f"{forecast_date}: факт={actual}, прогноз={predicted}")
    """
    # Валидация входных данных (Fail Fast)
    if start_date > end_date:
        error_msg = f"Дата начала ({start_date}) не может быть позже даты окончания ({end_date})"
        logger.error(error_msg)
        raise ValueError(error_msg)

    try:
        forecast: Dict[date, Tuple[Decimal, Decimal]] = {}
        today = date.today()

        # Получаем фактический баланс на сегодня
        actual_balance_today = calculate_actual_balance(session, today)

        # Получаем все активные плановые транзакции
        planned_transactions = session.query(PlannedTransactionDB).filter(
            PlannedTransactionDB.is_active
        ).all()

        # Создаём словарь плановых транзакций по датам
        planned_by_date: Dict[date, List[PlannedTransactionDB]] = {}

        for planned_tx in planned_transactions:
            # Генерируем вхождения для всего периода
            occurrences = generate_occurrences_for_period(
                session,
                planned_tx,
                start_date,
                end_date
            )

            for occurrence_date in occurrences:
                if occurrence_date not in planned_by_date:
                    planned_by_date[occurrence_date] = []
                planned_by_date[occurrence_date].append(planned_tx)

        # <ai:step type="calculation">Получаем платежи по кредитам для периода</ai:step>
        # Получаем все неисполненные платежи по кредитам в периоде
        loan_payments = session.query(LoanPaymentDB).filter(
            LoanPaymentDB.scheduled_date >= start_date,
            LoanPaymentDB.scheduled_date <= end_date,
            LoanPaymentDB.status.in_([PaymentStatus.PENDING, PaymentStatus.OVERDUE])
        ).all()

        # Создаём словарь платежей по датам
        payments_by_date: Dict[date, List[LoanPaymentDB]] = {}
        for payment in loan_payments:
            if payment.scheduled_date not in payments_by_date:
                payments_by_date[payment.scheduled_date] = []
            payments_by_date[payment.scheduled_date].append(payment)

        # <ai:step type="calculation">Получаем отложенные платежи с плановой датой для периода</ai:step>
        # Согласно правилу календаря: если платёж имеет planned_date, он учитывается в прогнозе
        pending_payments = _get_pending_payments_for_period(session, start_date, end_date)

        # Создаём словарь отложенных платежей по датам
        pending_by_date: Dict[date, List[PendingPaymentDB]] = {}
        for pending_payment in pending_payments:
            if pending_payment.planned_date not in pending_by_date:
                pending_by_date[pending_payment.planned_date] = []
            pending_by_date[pending_payment.planned_date].append(pending_payment)

        # Рассчитываем баланс для каждой даты в периоде
        current_date = start_date
        running_balance = actual_balance_today

        while current_date <= end_date:
            # Для дат в прошлом или сегодня используем фактический баланс
            if current_date <= today:
                actual_balance = calculate_actual_balance(session, current_date)
                forecast[current_date] = (actual_balance, actual_balance)
                running_balance = actual_balance
            else:
                # Для будущих дат рассчитываем прогноз
                # Применяем плановые транзакции на текущую дату
                if current_date in planned_by_date:
                    for planned_tx in planned_by_date[current_date]:
                        if planned_tx.type == TransactionType.INCOME:
                            running_balance += planned_tx.amount
                        elif planned_tx.type == TransactionType.EXPENSE:
                            running_balance -= planned_tx.amount

                # Применяем платежи по кредитам на текущую дату
                if current_date in payments_by_date:
                    for payment in payments_by_date[current_date]:
                        running_balance -= payment.amount

                # Применяем отложенные платежи на текущую дату
                if current_date in pending_by_date:
                    for pending_payment in pending_by_date[current_date]:
                        # Отложенные платежи - это всегда расходы
                        running_balance -= pending_payment.amount

                # Фактический баланс для будущих дат = баланс на сегодня
                forecast[current_date] = (actual_balance_today, running_balance)

            current_date += timedelta(days=1)
        
        logger.info(
            f"Рассчитан прогноз для периода {start_date} - {end_date} "
            f"({len(forecast)} дат, плановых транзакций: {len(planned_transactions)})"
        )
        
        return forecast
        
    except SQLAlchemyError as e:
        error_msg = f"Ошибка при расчёте прогноза для периода {start_date} - {end_date}: {e}"
        logger.error(error_msg)
        raise


def detect_cash_gaps(
    session: Session,
    start_date: date,
    end_date: date
) -> List[date]:
    """
    Определяет даты с кассовыми разрывами (прогнозируемый баланс < 0).

    Функция анализирует прогноз баланса на период и возвращает список дат,
    когда прогнозируемый баланс становится отрицательным. Используется для
    визуального выделения проблемных дат в календаре и для предупреждения
    пользователя о возможных финансовых проблемах.

    Учитывает плановые транзакции и платежи по кредитам при расчёте прогноза.

    Args:
        session: Активная сессия БД для выполнения запросов
        start_date: Начало периода для анализа
        end_date: Конец периода для анализа (включительно)

    Returns:
        Список дат, когда прогнозируемый баланс отрицательный.
        Список может быть пустым, если кассовых разрывов нет.

    Raises:
        ValueError: Если start_date > end_date
        SQLAlchemyError: При ошибках работы с БД

    Example:
        >>> with get_db_session() as session:
        ...     # Определить кассовые разрывы на месяц
        ...     gaps = detect_cash_gaps(
        ...         session,
        ...         date.today(),
        ...         date.today() + timedelta(days=30)
        ...     )
        ...
        ...     if gaps:
        ...         print(f"Внимание! Кассовые разрывы на даты: {gaps}")
        ...     else:
        ...         print("Кассовых разрывов не обнаружено")
    """
    # Валидация входных данных (Fail Fast)
    if start_date > end_date:
        error_msg = f"Дата начала ({start_date}) не может быть позже даты окончания ({end_date})"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        # Получаем прогноз для периода
        forecast = get_forecast_for_period(session, start_date, end_date)
        
        # Находим даты с отрицательным прогнозируемым балансом
        cash_gaps: List[date] = []
        
        for forecast_date, (actual_balance, predicted_balance) in forecast.items():
            if predicted_balance < Decimal('0'):
                cash_gaps.append(forecast_date)
        
        if cash_gaps:
            logger.warning(
                f"Обнаружено {len(cash_gaps)} кассовых разрывов в периоде {start_date} - {end_date}"
            )
        else:
            logger.info(
                f"Кассовых разрывов не обнаружено в периоде {start_date} - {end_date}"
            )
        
        return cash_gaps
        
    except SQLAlchemyError as e:
        error_msg = f"Ошибка при определении кассовых разрывов для периода {start_date} - {end_date}: {e}"
        logger.error(error_msg)
        raise

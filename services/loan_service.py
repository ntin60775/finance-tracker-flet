"""
Сервис управления кредитами и займами.

Предоставляет функции для работы с кредитами:
- Получение списка кредитов с фильтрацией
- Создание новых кредитов с валидацией
- Обновление информации о кредите
- Удаление кредита
- Расчёт статистики по кредиту
"""

import logging
from typing import List, Optional, Dict
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from models import (
    LoanDB, LoanPaymentDB, LenderDB, TransactionDB, CategoryDB,
    LoanType, LoanStatus, TransactionType, PaymentStatus
)

# Настройка логирования
logger = logging.getLogger(__name__)


def get_all_loans(
    session: Session,
    lender_id: Optional[int] = None,
    loan_type: Optional[LoanType] = None,
    status: Optional[LoanStatus] = None
) -> List[LoanDB]:
    """
    Получает список всех кредитов с опциональной фильтрацией.

    Функция возвращает все кредиты из справочника. Можно отфильтровать
    результаты по займодателю, типу кредита или статусу.

    Args:
        session: Активная сессия БД для выполнения запросов
        lender_id: ID займодателя для фильтрации (опциональное)
        loan_type: Тип кредита для фильтрации (опциональное)
        status: Статус кредита для фильтрации (опциональное)

    Returns:
        Список объектов LoanDB, отсортированных по названию.
        Список может быть пустым, если кредитов нет.

    Raises:
        SQLAlchemyError: При ошибках работы с БД

    Example:
        >>> with get_db_session() as session:
        ...     # Получить все кредиты
        ...     all_loans = get_all_loans(session)
        ...
        ...     # Получить активные кредиты банка с ID 1
        ...     active = get_all_loans(session, lender_id=1, status=LoanStatus.ACTIVE)
    """
    try:
        # Базовый запрос
        query = session.query(LoanDB)

        # Применяем фильтры
        if lender_id is not None:
            query = query.filter(LoanDB.lender_id == lender_id)
        if loan_type is not None:
            query = query.filter(LoanDB.loan_type == loan_type)
        if status is not None:
            query = query.filter(LoanDB.status == status)

        # Сортируем по названию
        query = query.order_by(LoanDB.name)

        # Выполняем запрос
        loans = query.all()

        logger.info(
            f"Получено {len(loans)} кредитов"
            f"{f' от займодателя ID {lender_id}' if lender_id else ''}"
            f"{f' типа {loan_type.value}' if loan_type else ''}"
            f"{f' статуса {status.value}' if status else ''}"
        )

        return loans

    except SQLAlchemyError as e:
        error_msg = f"Ошибка при получении кредитов: {e}"
        logger.error(error_msg)
        raise


def get_loan_by_id(session: Session, loan_id: int) -> Optional[LoanDB]:
    """
    Получает кредит по ID.

    Args:
        session: Активная сессия БД
        loan_id: ID кредита

    Returns:
        Объект LoanDB или None, если кредит не найден
    """
    try:
        return session.query(LoanDB).filter_by(id=loan_id).first()
    except SQLAlchemyError as e:
        error_msg = f"Ошибка при получении кредита ID {loan_id}: {e}"
        logger.error(error_msg)
        raise


def create_loan(
    session: Session,
    name: str,
    lender_id: int,
    loan_type: LoanType,
    amount: Decimal,
    issue_date: date,
    interest_rate: Optional[Decimal] = None,
    end_date: Optional[date] = None,
    contract_number: Optional[str] = None,
    description: Optional[str] = None
) -> LoanDB:
    """
    Создаёт новый кредит с валидацией.

    Функция создаёт новую запись о кредите. Выполняется валидация:
    - Займодатель должен существовать
    - Сумма должна быть больше 0
    - Процентная ставка должна быть 0-100%
    - end_date не может быть раньше issue_date

    Args:
        session: Активная сессия БД для выполнения операций
        name: Название кредита (обязательное)
        lender_id: ID займодателя (обязательное, должен существовать)
        loan_type: Тип кредита (обязательное)
        amount: Сумма кредита (обязательное, > 0)
        issue_date: Дата выдачи кредита (обязательное)
        interest_rate: Процентная ставка, % в год (опциональное, 0-100)
        end_date: Планируемая дата окончания (опциональное)
        contract_number: Номер договора (опциональное)
        description: Описание кредита (опциональное)

    Returns:
        Созданный объект LoanDB с заполненным id

    Raises:
        ValueError: Если валидация не прошла
        SQLAlchemyError: При ошибках работы с БД

    Example:
        >>> with get_db_session() as session:
        ...     loan = create_loan(
        ...         session,
        ...         name="Ипотека на квартиру",
        ...         lender_id=1,
        ...         loan_type=LoanType.MORTGAGE,
        ...         amount=Decimal('3000000.00'),
        ...         issue_date=date(2024, 1, 15),
        ...         interest_rate=Decimal('8.5'),
        ...         end_date=date(2054, 1, 15)
        ...     )
    """
    try:
        # Валидация суммы
        if amount <= Decimal('0'):
            raise ValueError("Сумма кредита должна быть больше 0")

        # Валидация процентной ставки
        if interest_rate is not None and (interest_rate < Decimal('0') or interest_rate > Decimal('100')):
            raise ValueError("Процентная ставка должна быть от 0 до 100%")

        # Валидация дат
        if end_date is not None and end_date < issue_date:
            raise ValueError("Дата окончания не может быть раньше даты выдачи")

        # Проверяем существование займодателя
        lender = session.query(LenderDB).filter_by(id=lender_id).first()
        if lender is None:
            raise ValueError(f"Займодатель ID {lender_id} не найден")

        # Создание кредита
        loan = LoanDB(
            name=name.strip(),
            lender_id=lender_id,
            loan_type=loan_type,
            amount=amount,
            interest_rate=interest_rate,
            issue_date=issue_date,
            end_date=end_date,
            contract_number=contract_number,
            description=description
        )
        session.add(loan)
        session.commit()
        session.refresh(loan)

        logger.info(f"Создан кредит '{name}' (ID {loan.id}) от '{lender.name}'")

        return loan

    except ValueError:
        session.rollback()
        raise
    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f"Ошибка при создании кредита: {e}"
        logger.error(error_msg)
        raise


def update_loan_status(session: Session, loan_id: int, new_status: LoanStatus) -> LoanDB:
    """
    Обновляет статус кредита.

    Args:
        session: Активная сессия БД
        loan_id: ID кредита
        new_status: Новый статус кредита

    Returns:
        Обновлённый объект LoanDB

    Raises:
        ValueError: Если кредит не найден
        SQLAlchemyError: При ошибках работы с БД
    """
    try:
        loan = session.query(LoanDB).filter_by(id=loan_id).first()
        if loan is None:
            raise ValueError(f"Кредит ID {loan_id} не найден")

        loan.status = new_status
        session.commit()
        session.refresh(loan)

        logger.info(f"Обновлён статус кредита '{loan.name}' (ID {loan_id}) на {new_status.value}")

        return loan

    except ValueError:
        session.rollback()
        raise
    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f"Ошибка при обновлении статуса кредита ID {loan_id}: {e}"
        logger.error(error_msg)
        raise


def calculate_loan_balance(session: Session, loan_id: int) -> Dict[str, Decimal]:
    """
    Рассчитывает остаток по кредиту на основе выполненных платежей.

    Функция рассчитывает:
    - Основной долг (сумма кредита минус выполненные платежи основного долга)
    - Итоговый остаток (основной долг + начисленные проценты)

    Args:
        session: Активная сессия БД
        loan_id: ID кредита

    Returns:
        Словарь с ключами:
        - principal_balance: остаток основного долга
        - total_balance: общий остаток с процентами

    Raises:
        ValueError: Если кредит не найден
        SQLAlchemyError: При ошибках работы с БД
    """
    try:
        loan = session.query(LoanDB).filter_by(id=loan_id).first()
        if loan is None:
            raise ValueError(f"Кредит ID {loan_id} не найден")

        # Получаем все выполненные платежи по кредиту
        payments = session.query(LoanPaymentDB).filter(
            LoanPaymentDB.loan_id == loan_id,
            LoanPaymentDB.actual_transaction_id.isnot(None)
        ).all()

        # Рассчитываем сумму выполненных платежей основного долга
        paid_principal = sum((p.principal_amount for p in payments), Decimal('0.0'))

        # Рассчитываем остаток основного долга
        principal_balance = loan.amount - paid_principal

        # Для простоты считаем, что процентная часть равна плану минус выплаты процентов
        scheduled_payments = session.query(LoanPaymentDB).filter_by(
            loan_id=loan_id
        ).all()
        scheduled_interest = sum((p.interest_amount for p in scheduled_payments), Decimal('0.0'))
        paid_interest = sum((p.interest_amount for p in payments), Decimal('0.0'))
        accrued_interest = scheduled_interest - paid_interest

        total_balance = principal_balance + accrued_interest

        logger.debug(f"Рассчитан остаток по кредиту ID {loan_id}: "
                    f"основной долг={principal_balance}, всего={total_balance}")

        return {
            "principal_balance": max(Decimal('0'), principal_balance),
            "total_balance": max(Decimal('0'), total_balance)
        }

    except ValueError:
        raise
    except SQLAlchemyError as e:
        error_msg = f"Ошибка при расчёте остатка кредита ID {loan_id}: {e}"
        logger.error(error_msg)
        raise


def calculate_loan_statistics(session: Session, loan_id: int) -> dict:
    """
    Рассчитывает статистику по кредиту.

    Функция рассчитывает:
    - Общая сумма процентов, которые должны быть выплачены
    - Общая сумма процентов, которые уже выплачены
    - Переплата (процент от суммы кредита)

    Args:
        session: Активная сессия БД
        loan_id: ID кредита

    Returns:
        Словарь со статистикой

    Raises:
        ValueError: Если кредит не найден
        SQLAlchemyError: При ошибках работы с БД
    """
    try:
        loan = session.query(LoanDB).filter_by(id=loan_id).first()
        if loan is None:
            raise ValueError(f"Кредит ID {loan_id} не найден")

        # Получаем все платежи
        payments = session.query(LoanPaymentDB).filter_by(loan_id=loan_id).all()

        # Рассчитываем статистику
        total_interest = sum((p.interest_amount for p in payments), Decimal('0.0'))
        paid_interest = sum(
            (p.interest_amount for p in payments if p.actual_transaction_id is not None),
            Decimal('0.0')
        )

        overpayment_percent = (total_interest / loan.amount * 100) if loan.amount > Decimal('0') else Decimal('0')

        logger.debug(f"Рассчитана статистика по кредиту ID {loan_id}: "
                    f"всего процентов={total_interest}, выплачено={paid_interest}")

        return {
            "total_interest": total_interest,
            "paid_interest": paid_interest,
            "overpayment_percent": round(overpayment_percent, 2)
        }

    except ValueError:
        raise
    except SQLAlchemyError as e:
        error_msg = f"Ошибка при расчёте статистики кредита ID {loan_id}: {e}"
        logger.error(error_msg)
        raise


def delete_loan(session: Session, loan_id: int, keep_transactions: bool = True) -> bool:
    """
    Удаляет кредит с опциональным сохранением фактических транзакций.

    Args:
        session: Активная сессия БД
        loan_id: ID кредита для удаления
        keep_transactions: Сохранять ли фактические транзакции (по умолчанию True)

    Returns:
        True, если кредит успешно удалён

    Raises:
        ValueError: Если кредит не найден
        SQLAlchemyError: При ошибках работы с БД
    """
    try:
        loan = session.query(LoanDB).filter_by(id=loan_id).first()
        if loan is None:
            raise ValueError(f"Кредит ID {loan_id} не найден")

        loan_name = loan.name
        session.delete(loan)
        session.commit()

        logger.info(f"Удалён кредит '{loan_name}' (ID {loan_id})")

        return True

    except ValueError:
        session.rollback()
        raise
    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f"Ошибка при удалении кредита ID {loan_id}: {e}"
        logger.error(error_msg)
        raise


def create_disbursement_transaction(
    session: Session,
    loan_id: int,
    transaction_date: Optional[date] = None
) -> TransactionDB:
    """
    Создаёт транзакцию получения кредита (INCOME).

    Функция создаёт запись в TransactionDB типа INCOME с категорией
    "Получение кредита" и устанавливает связь с кредитом.

    Args:
        session: Активная сессия БД
        loan_id: ID кредита
        transaction_date: Дата транзакции (по умолчанию дата выдачи кредита)

    Returns:
        Созданный объект TransactionDB

    Raises:
        ValueError: Если кредит не найден или транзакция уже существует
        SQLAlchemyError: При ошибках работы с БД

    Example:
        >>> with get_db_session() as session:
        ...     transaction = create_disbursement_transaction(session, loan_id=1)
    """
    try:
        # Получаем кредит
        loan = session.query(LoanDB).filter_by(id=loan_id).first()
        if loan is None:
            raise ValueError(f"Кредит ID {loan_id} не найден")

        # Проверяем, что транзакция ещё не создана
        if loan.disbursement_transaction_id is not None:
            raise ValueError(
                f"Транзакция получения кредита ID {loan_id} уже существует"
            )

        # Получаем категорию "Получение кредита"
        category = session.query(CategoryDB).filter_by(
            name="Получение кредита",
            is_system=True
        ).first()
        if category is None:
            raise ValueError(
                "Категория 'Получение кредита' не найдена. "
                "Убедитесь, что инициализированы системные категории."
            )

        # Используем дату выдачи кредита или переданную дату
        trans_date = transaction_date if transaction_date is not None else loan.issue_date

        # Создаём транзакцию
        transaction = TransactionDB(
            amount=loan.amount,
            category_id=category.id,
            type=TransactionType.INCOME,
            transaction_date=trans_date,
            description=f"Получение кредита: {loan.name}"
        )
        session.add(transaction)
        session.flush()  # Получаем ID транзакции
        session.refresh(transaction)

        # Обновляем кредит со ссылкой на транзакцию
        loan.disbursement_transaction_id = transaction.id
        session.commit()

        logger.info(
            f"Создана транзакция получения кредита ID {loan_id} "
            f"(транзакция ID {transaction.id}, сумма {loan.amount})"
        )

        return transaction

    except ValueError:
        session.rollback()
        raise
    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f"Ошибка при создании транзакции кредита ID {loan_id}: {e}"
        logger.error(error_msg)
        raise


def update_loan(
    session: Session,
    loan_id: int,
    name: Optional[str] = None,
    interest_rate: Optional[Decimal] = None,
    end_date: Optional[date] = None,
    contract_number: Optional[str] = None,
    description: Optional[str] = None
) -> LoanDB:
    """
    Обновляет информацию о кредите.

    Функция обновляет данные существующего кредита. Все параметры опциональны;
    обновляются только те поля, для которых переданы значения.

    Args:
        session: Активная сессия БД
        loan_id: ID кредита для обновления
        name: Новое название (опциональное)
        interest_rate: Новая процентная ставка (опциональное, 0-100)
        end_date: Новая дата окончания (опциональное)
        contract_number: Новый номер договора (опциональное)
        description: Новое описание (опциональное)

    Returns:
        Обновлённый объект LoanDB

    Raises:
        ValueError: Если кредит не найден или валидация не прошла
        SQLAlchemyError: При ошибках работы с БД

    Example:
        >>> with get_db_session() as session:
        ...     loan = update_loan(session, loan_id=1, interest_rate=Decimal('9.5'))
    """
    try:
        # Получаем кредит
        loan = session.query(LoanDB).filter_by(id=loan_id).first()
        if loan is None:
            raise ValueError(f"Кредит ID {loan_id} не найден")

        # Обновляем поля, если переданы
        if name is not None:
            loan.name = name.strip()

        if interest_rate is not None:
            if interest_rate < Decimal('0') or interest_rate > Decimal('100'):
                raise ValueError("Процентная ставка должна быть от 0 до 100%")
            loan.interest_rate = interest_rate

        if end_date is not None:
            if end_date < loan.issue_date:
                raise ValueError("Дата окончания не может быть раньше даты выдачи")
            loan.end_date = end_date

        if contract_number is not None:
            loan.contract_number = contract_number

        if description is not None:
            loan.description = description

        session.commit()
        session.refresh(loan)

        logger.info(f"Обновлён кредит '{loan.name}' (ID {loan_id})")

        return loan

    except ValueError:
        session.rollback()
        raise
    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f"Ошибка при обновлении кредита ID {loan_id}: {e}"
        logger.error(error_msg)
        raise


def execute_payment(
    session: Session,
    payment_id: int,
    transaction_amount: Decimal,
    transaction_date: Optional[date] = None
) -> tuple[LoanPaymentDB, TransactionDB]:
    """
    Исполняет платёж по кредиту через создание фактической транзакции.

    Функция создаёт транзакцию EXPENSE и устанавливает связь с графиком платежа.
    Автоматически рассчитывает количество дней просрочки и обновляет статус.

    Args:
        session: Активная сессия БД
        payment_id: ID платежа в графике
        transaction_amount: Сумма исполненного платежа
        transaction_date: Дата исполнения (по умолчанию сегодня)

    Returns:
        Кортеж (обновленный платёж, созданная транзакция)

    Raises:
        ValueError: Если платёж не найден, неверная сумма или статус
        SQLAlchemyError: При ошибках работы с БД

    Example:
        >>> with get_db_session() as session:
        ...     payment, transaction = execute_payment(
        ...         session, payment_id=1, transaction_amount=Decimal('10500.00')
        ...     )
    """
    try:
        # Получаем платёж
        payment = session.query(LoanPaymentDB).filter_by(id=payment_id).first()
        if payment is None:
            raise ValueError(f"Платёж ID {payment_id} не найден")

        # Проверяем статус
        if payment.status not in (PaymentStatus.PENDING, PaymentStatus.OVERDUE):
            raise ValueError(
                f"Платёж может быть исполнен только со статусом PENDING или OVERDUE, "
                f"текущий статус: {payment.status.value}"
            )

        # Валидация суммы
        if transaction_amount <= Decimal('0'):
            raise ValueError("Сумма платежа должна быть больше 0")

        # Получаем кредит и категорию
        loan = payment.loan
        category = session.query(CategoryDB).filter_by(
            name="Выплата кредита (основной долг)",
            is_system=True
        ).first()
        if category is None:
            raise ValueError(
                "Категория 'Выплата кредита (основной долг)' не найдена. "
                "Убедитесь, что инициализированы системные категории."
            )

        # Дата исполнения
        exec_date = transaction_date if transaction_date is not None else date.today()

        # Создаём транзакцию
        transaction = TransactionDB(
            amount=transaction_amount,
            category_id=category.id,
            type=TransactionType.EXPENSE,
            transaction_date=exec_date,
            description=f"Платёж по кредиту: {loan.name}"
        )
        session.add(transaction)
        session.flush()
        session.refresh(transaction)

        # Обновляем платёж
        payment.actual_transaction_id = transaction.id
        payment.executed_date = exec_date
        payment.executed_amount = transaction_amount

        # Рассчитываем количество дней просрочки
        if exec_date > payment.scheduled_date:
            payment.overdue_days = (exec_date - payment.scheduled_date).days
            payment.status = PaymentStatus.EXECUTED_LATE
        else:
            payment.overdue_days = 0
            payment.status = PaymentStatus.EXECUTED

        session.commit()
        session.refresh(payment)
        session.refresh(transaction)

        logger.info(
            f"Исполнен платёж ID {payment_id} по кредиту ID {loan.id} "
            f"(транзакция ID {transaction.id}, сумма {transaction_amount})"
        )

        return payment, transaction

    except ValueError:
        session.rollback()
        raise
    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f"Ошибка при исполнении платежа ID {payment_id}: {e}"
        logger.error(error_msg)
        raise

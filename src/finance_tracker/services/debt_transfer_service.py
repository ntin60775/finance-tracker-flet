"""
Сервис управления передачей долга между кредиторами.

Предоставляет функции для работы с передачей долга:
- Создание записи о передаче долга
- Получение истории передач по кредиту
- Валидация возможности передачи
- Расчёт текущего остатка долга
- Обновление платежей при передаче
"""

import logging
import uuid
from typing import List, Optional, Tuple
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from finance_tracker.models import (
    LoanDB, LenderDB, DebtTransferDB, LoanPaymentDB,
    LoanStatus, PaymentStatus
)
from finance_tracker.utils.validation import validate_uuid_format
from finance_tracker.utils.exceptions import LoanNotFoundError

# Настройка логирования
logger = logging.getLogger(__name__)


def update_payments_on_transfer(
    session: Session,
    loan_id: str,
    new_holder_id: str
) -> int:
    """
    Обновляет PENDING платежи при передаче долга.
    
    Обновляет holder_id для всех платежей со статусом PENDING,
    привязывая их к новому держателю долга. Платежи со статусами
    EXECUTED и EXECUTED_LATE остаются без изменений.
    
    Args:
        session: Активная сессия БД
        loan_id: ID кредита (UUID)
        new_holder_id: ID нового держателя долга (UUID)
        
    Returns:
        int: Количество обновлённых платежей
        
    Raises:
        SQLAlchemyError: При ошибках работы с БД
        
    Example:
        >>> with get_db_session() as session:
        ...     updated_count = update_payments_on_transfer(
        ...         session=session,
        ...         loan_id="loan-uuid",
        ...         new_holder_id="collector-uuid"
        ...     )
        ...     print(f"Обновлено платежей: {updated_count}")
        
    Validates:
        Requirements 4.1, 4.2
    """
    try:
        logger.debug(
            f"Обновление платежей при передаче долга: loan_id={loan_id}, "
            f"new_holder_id={new_holder_id}"
        )
        
        # Получаем все PENDING платежи по кредиту
        pending_payments = session.query(LoanPaymentDB).filter(
            LoanPaymentDB.loan_id == loan_id,
            LoanPaymentDB.status == PaymentStatus.PENDING
        ).all()
        
        updated_count = 0
        for payment in pending_payments:
            payment.holder_id = new_holder_id
            updated_count += 1
        
        logger.info(
            f"Обновлено {updated_count} PENDING платежей для кредита {loan_id}: "
            f"новый держатель {new_holder_id}"
        )
        
        return updated_count
        
    except SQLAlchemyError as e:
        error_msg = f"Ошибка БД при обновлении платежей для кредита {loan_id}: {e}"
        logger.error(error_msg)
        raise
    except Exception as e:
        error_msg = f"Неожиданная ошибка при обновлении платежей: {e}"
        logger.error(error_msg)
        raise


def validate_transfer(
    session: Session,
    loan_id: str,
    to_lender_id: str,
    transfer_amount: Decimal
) -> Tuple[bool, Optional[str]]:
    """
    Валидирует возможность передачи долга.
    
    Проверяет:
    - Существование кредита и кредитора
    - Статус кредита (не PAID_OFF)
    - Что to_lender_id != current_holder
    - Что transfer_amount > 0
    - Что from_lender_id соответствует текущему держателю
    
    Args:
        session: Активная сессия БД
        loan_id: ID кредита
        to_lender_id: ID нового держателя долга
        transfer_amount: Сумма долга при передаче
        
    Returns:
        Tuple[is_valid, error_message]: 
            - is_valid: True если передача возможна, False иначе
            - error_message: Описание ошибки или None если валидация прошла
        
    Validates:
        Requirements 6.1, 6.2, 6.3, 2.5
    """
    try:
        logger.debug(
            f"Валидация передачи долга: loan_id={loan_id}, "
            f"to_lender_id={to_lender_id}, transfer_amount={transfer_amount}"
        )
        
        # Проверка формата UUID
        try:
            validate_uuid_format(loan_id, "ID кредита")
        except ValueError as e:
            error_msg = str(e)
            logger.warning(error_msg)
            return False, error_msg
            
        try:
            validate_uuid_format(to_lender_id, "ID кредитора")
        except ValueError as e:
            error_msg = str(e)
            logger.warning(error_msg)
            return False, error_msg
        
        # Проверка существования кредита
        loan = session.query(LoanDB).filter_by(id=loan_id).first()
        if not loan:
            error_msg = f"Кредит с ID {loan_id} не найден"
            logger.warning(error_msg)
            return False, error_msg
        
        # Проверка существования кредитора
        to_lender = session.query(LenderDB).filter_by(id=to_lender_id).first()
        if not to_lender:
            error_msg = f"Кредитор с ID {to_lender_id} не найден"
            logger.warning(error_msg)
            return False, error_msg
        
        # Проверка статуса кредита (не PAID_OFF) - Requirement 6.1
        if loan.status == LoanStatus.PAID_OFF:
            error_msg = "Нельзя передать погашенный кредит"
            logger.warning(f"{error_msg}: loan_id={loan_id}")
            return False, error_msg
        
        # Получаем текущего держателя долга
        current_holder_id = loan.effective_holder_id
        
        # Проверка что to_lender_id != current_holder - Requirement 6.2
        if to_lender_id == current_holder_id:
            error_msg = "Нельзя передать долг тому же кредитору"
            logger.warning(
                f"{error_msg}: to_lender_id={to_lender_id}, "
                f"current_holder_id={current_holder_id}"
            )
            return False, error_msg
        
        # Проверка что transfer_amount > 0 - Requirement 6.3
        if transfer_amount <= Decimal('0'):
            error_msg = "Сумма передачи должна быть положительной"
            logger.warning(f"{error_msg}: transfer_amount={transfer_amount}")
            return False, error_msg
        
        logger.info(
            f"Валидация передачи долга успешна: loan_id={loan_id}, "
            f"to_lender_id={to_lender_id}"
        )
        return True, None
        
    except SQLAlchemyError as e:
        error_msg = f"Ошибка БД при валидации передачи: {e}"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Неожиданная ошибка при валидации передачи: {e}"
        logger.error(error_msg)
        return False, error_msg


def get_remaining_debt(session: Session, loan_id: str) -> Decimal:
    """
    Вычисляет текущий остаток долга по кредиту.
    
    Остаток долга рассчитывается как:
    - Сумма кредита минус сумма выполненных платежей (principal_amount)
    
    Учитываются только платежи со статусами:
    - EXECUTED (выполнен вовремя)
    - EXECUTED_LATE (выполнен с опозданием)
    
    Args:
        session: Активная сессия БД
        loan_id: ID кредита (UUID)
        
    Returns:
        Decimal: Текущий остаток долга по кредиту
        
    Raises:
        LoanNotFoundError: Если кредит не найден
        ValueError: Если формат loan_id некорректный
        SQLAlchemyError: При ошибках работы с БД
        
    Example:
        >>> with get_db_session() as session:
        ...     remaining = get_remaining_debt(session, loan_id="...")
        ...     print(f"Остаток долга: {remaining}")
        
    Validates:
        Requirements 8.3
    """
    try:
        logger.debug(f"Вычисление остатка долга по кредиту: loan_id={loan_id}")
        
        # Валидация формата UUID
        validate_uuid_format(loan_id, "ID кредита")
        
        # Получаем кредит
        loan = session.query(LoanDB).filter_by(id=loan_id).first()
        if not loan:
            error_msg = f"Кредит с ID {loan_id} не найден"
            logger.warning(error_msg)
            raise LoanNotFoundError(error_msg)
        
        # Получаем сумму выполненных платежей (только principal_amount)
        # Учитываем платежи со статусами EXECUTED и EXECUTED_LATE
        executed_statuses = [PaymentStatus.EXECUTED, PaymentStatus.EXECUTED_LATE]
        
        executed_payments = session.query(LoanPaymentDB).filter(
            LoanPaymentDB.loan_id == loan_id,
            LoanPaymentDB.status.in_(executed_statuses)
        ).all()
        
        # Суммируем principal_amount выполненных платежей
        total_paid_principal = sum(
            (payment.principal_amount for payment in executed_payments),
            Decimal('0')
        )
        
        # Вычисляем остаток долга
        remaining_debt = loan.amount - total_paid_principal
        
        # Остаток не может быть отрицательным
        remaining_debt = max(remaining_debt, Decimal('0'))
        
        logger.info(
            f"Остаток долга по кредиту ID {loan_id}: {remaining_debt} "
            f"(сумма кредита: {loan.amount}, выплачено: {total_paid_principal})"
        )
        
        return remaining_debt
        
    except (LoanNotFoundError, ValueError):
        raise
    except SQLAlchemyError as e:
        error_msg = f"Ошибка БД при вычислении остатка долга по кредиту ID {loan_id}: {e}"
        logger.error(error_msg)
        raise
    except Exception as e:
        error_msg = f"Неожиданная ошибка при вычислении остатка долга: {e}"
        logger.error(error_msg)
        raise


def get_transfer_history(session: Session, loan_id: str) -> List[DebtTransferDB]:
    """
    Возвращает историю передач долга по кредиту в хронологическом порядке.
    
    Получает список всех передач долга для указанного кредита,
    отсортированный по дате передачи в порядке возрастания (от старых к новым).
    
    Args:
        session: Активная сессия БД
        loan_id: ID кредита (UUID)
        
    Returns:
        List[DebtTransferDB]: Список передач долга в хронологическом порядке.
            Пустой список, если передач не было.
        
    Raises:
        ValueError: Если формат loan_id некорректный
        LoanNotFoundError: Если кредит не найден
        SQLAlchemyError: При ошибках работы с БД
        
    Example:
        >>> with get_db_session() as session:
        ...     history = get_transfer_history(session, loan_id="...")
        ...     for transfer in history:
        ...         print(f"{transfer.transfer_date}: {transfer.from_lender.name} -> {transfer.to_lender.name}")
        
    Validates:
        Requirements 3.2, 3.3
    """
    try:
        logger.debug(f"Получение истории передач долга по кредиту: loan_id={loan_id}")
        
        # Валидация формата UUID
        validate_uuid_format(loan_id, "ID кредита")
        
        # Проверяем существование кредита
        loan = session.query(LoanDB).filter_by(id=loan_id).first()
        if not loan:
            error_msg = f"Кредит с ID {loan_id} не найден"
            logger.warning(error_msg)
            raise LoanNotFoundError(error_msg)
        
        # Получаем историю передач, отсортированную по дате в хронологическом порядке
        transfers = session.query(DebtTransferDB).filter(
            DebtTransferDB.loan_id == loan_id
        ).order_by(
            DebtTransferDB.transfer_date.asc()
        ).all()
        
        logger.info(
            f"Получена история передач долга по кредиту ID {loan_id}: "
            f"{len(transfers)} записей"
        )
        
        return transfers
        
    except (ValueError, LoanNotFoundError):
        raise
    except SQLAlchemyError as e:
        error_msg = f"Ошибка БД при получении истории передач по кредиту ID {loan_id}: {e}"
        logger.error(error_msg)
        raise
    except Exception as e:
        error_msg = f"Неожиданная ошибка при получении истории передач: {e}"
        logger.error(error_msg)
        raise


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
    
    Выполняет следующие операции:
    1. Валидирует возможность передачи (через validate_transfer)
    2. Получает текущий остаток долга (через get_remaining_debt)
    3. Создаёт запись DebtTransferDB
    4. Обновляет loan.current_holder_id на нового держателя
    5. Устанавливает loan.original_lender_id при первой передаче
    6. Вычисляет amount_difference (transfer_amount - previous_amount)
    7. Обновляет PENDING платежи для привязки к новому держателю
    8. Сохраняет изменения в БД
    
    Args:
        session: Активная сессия БД
        loan_id: ID кредита (UUID)
        to_lender_id: ID нового держателя долга (UUID)
        transfer_date: Дата передачи
        transfer_amount: Сумма долга при передаче
        reason: Причина передачи (опционально)
        notes: Примечания (опционально)
        
    Returns:
        DebtTransferDB: Созданная запись о передаче долга
        
    Raises:
        ValueError: При невалидных данных (через validate_transfer)
        LoanNotFoundError: Если кредит не найден
        SQLAlchemyError: При ошибках работы с БД
        
    Example:
        >>> with get_db_session() as session:
        ...     transfer = create_debt_transfer(
        ...         session=session,
        ...         loan_id="loan-uuid",
        ...         to_lender_id="collector-uuid",
        ...         transfer_date=date(2025, 1, 15),
        ...         transfer_amount=Decimal('105000.00'),
        ...         reason="Продажа долга коллекторскому агентству"
        ...     )
        ...     print(f"Передача создана: {transfer.id}")
        
    Validates:
        Requirements 2.1, 2.2, 2.3, 2.4, 4.1, 4.2
    """
    try:
        logger.debug(
            f"Создание передачи долга: loan_id={loan_id}, "
            f"to_lender_id={to_lender_id}, transfer_date={transfer_date}, "
            f"transfer_amount={transfer_amount}"
        )
        
        # 1. Валидация возможности передачи
        is_valid, error_message = validate_transfer(
            session, loan_id, to_lender_id, transfer_amount
        )
        if not is_valid:
            logger.warning(f"Валидация передачи не прошла: {error_message}")
            raise ValueError(error_message)
        
        # 2. Получаем кредит
        loan = session.query(LoanDB).filter_by(id=loan_id).first()
        if not loan:
            error_msg = f"Кредит с ID {loan_id} не найден"
            logger.error(error_msg)
            raise LoanNotFoundError(error_msg)
        
        # 3. Получаем текущий остаток долга (previous_amount)
        previous_amount = get_remaining_debt(session, loan_id)
        
        # 4. Вычисляем разницу сумм (пени, штрафы)
        amount_difference = transfer_amount - previous_amount
        
        # 5. Получаем текущего держателя долга (from_lender_id)
        from_lender_id = loan.effective_holder_id
        
        # 6. Создаём запись о передаче
        debt_transfer = DebtTransferDB(
            id=str(uuid.uuid4()),
            loan_id=loan_id,
            from_lender_id=from_lender_id,
            to_lender_id=to_lender_id,
            transfer_date=transfer_date,
            transfer_amount=transfer_amount,
            previous_amount=previous_amount,
            amount_difference=amount_difference,
            reason=reason,
            notes=notes
        )
        
        session.add(debt_transfer)
        
        # 7. Обновляем loan.current_holder_id (Requirement 2.2)
        loan.current_holder_id = to_lender_id
        
        # 8. Устанавливаем loan.original_lender_id при первой передаче (Requirement 2.3)
        if loan.original_lender_id is None:
            loan.original_lender_id = loan.lender_id
            logger.info(
                f"Установлен original_lender_id={loan.lender_id} для кредита {loan_id} "
                f"(первая передача)"
            )
        
        # 9. Обновляем PENDING платежи для привязки к новому держателю (Requirements 4.1, 4.2)
        updated_payments_count = update_payments_on_transfer(
            session=session,
            loan_id=loan_id,
            new_holder_id=to_lender_id
        )
        
        # 10. Сохраняем изменения
        session.commit()
        
        logger.info(
            f"Передача долга создана успешно: ID={debt_transfer.id}, "
            f"loan_id={loan_id}, from={from_lender_id}, to={to_lender_id}, "
            f"amount={transfer_amount}, difference={amount_difference}, "
            f"updated_payments={updated_payments_count}"
        )
        
        return debt_transfer
        
    except (ValueError, LoanNotFoundError):
        session.rollback()
        raise
    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f"Ошибка БД при создании передачи долга: {e}"
        logger.error(error_msg)
        raise
    except Exception as e:
        session.rollback()
        error_msg = f"Неожиданная ошибка при создании передачи долга: {e}"
        logger.error(error_msg)
        raise

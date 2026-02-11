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
from typing import Any, List, Optional, Tuple, cast
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from finance_tracker.models import (
    LoanDB,
    LenderDB,
    DebtTransferDB,
    LoanPaymentDB,
    LoanStatus,
    PaymentStatus,
)
from finance_tracker.utils.validation import validate_uuid_format
from finance_tracker.utils.exceptions import (
    DatabaseError,
    InvalidTransferError,
    LoanNotFoundError,
    ValidationError,
)

# Настройка логирования
logger = logging.getLogger(__name__)


def _debt_transfer_extra(
    *,
    operation: str,
    status: str,
    entity_id: Optional[str] = None,
    **kwargs,
) -> dict:
    extra = {
        "event_type": "domain_journal",
        "operation": operation,
        "entity": "debt_transfer",
        "entity_id": entity_id,
        "status": status,
    }
    extra.update(kwargs)
    return extra


def update_payments_on_transfer(session: Session, loan_id: str, new_holder_id: str) -> int:
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
            "Updating pending payments after debt transfer",
            extra=_debt_transfer_extra(
                operation="debt_transfer_update_payments",
                status="start",
                entity_id=loan_id,
                loan_id=loan_id,
                new_holder_id=new_holder_id,
            ),
        )

        pending_payments = (
            session.query(LoanPaymentDB)
            .filter(LoanPaymentDB.loan_id == loan_id, LoanPaymentDB.status == PaymentStatus.PENDING)
            .all()
        )

        updated_count = 0
        for payment in pending_payments:
            payment_model = cast(Any, payment)
            payment_model.holder_id = new_holder_id
            updated_count += 1

        logger.info(
            "Pending payments updated after debt transfer",
            extra=_debt_transfer_extra(
                operation="debt_transfer_update_payments",
                status="success",
                entity_id=loan_id,
                loan_id=loan_id,
                new_holder_id=new_holder_id,
                updated_payments=updated_count,
            ),
        )
        return updated_count

    except SQLAlchemyError as exc:
        logger.error(
            "Database error while updating pending payments after debt transfer",
            extra=_debt_transfer_extra(
                operation="debt_transfer_update_payments",
                status="failure",
                entity_id=loan_id,
                loan_id=loan_id,
                new_holder_id=new_holder_id,
                error_type=type(exc).__name__,
            ),
        )
        raise


def validate_transfer(
    session: Session, loan_id: str, to_lender_id: str, transfer_amount: Decimal
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
            "Validating debt transfer request",
            extra=_debt_transfer_extra(
                operation="debt_transfer_validate",
                status="start",
                entity_id=loan_id,
                loan_id=loan_id,
                to_lender_id=to_lender_id,
            ),
        )

        try:
            validate_uuid_format(loan_id, "ID кредита")
        except ValueError as exc:
            error_msg = str(exc)
            logger.warning(
                "Debt transfer validation failed",
                extra=_debt_transfer_extra(
                    operation="debt_transfer_validate",
                    status="failure",
                    entity_id=loan_id,
                    loan_id=loan_id,
                    to_lender_id=to_lender_id,
                    error_type=type(exc).__name__,
                ),
            )
            return False, error_msg

        try:
            validate_uuid_format(to_lender_id, "ID кредитора")
        except ValueError as exc:
            error_msg = str(exc)
            logger.warning(
                "Debt transfer validation failed",
                extra=_debt_transfer_extra(
                    operation="debt_transfer_validate",
                    status="failure",
                    entity_id=loan_id,
                    loan_id=loan_id,
                    to_lender_id=to_lender_id,
                    error_type=type(exc).__name__,
                ),
            )
            return False, error_msg

        loan = session.query(LoanDB).filter_by(id=loan_id).first()
        if loan is None:
            error_msg = f"Кредит с ID {loan_id} не найден"
            logger.warning(
                "Debt transfer validation failed",
                extra=_debt_transfer_extra(
                    operation="debt_transfer_validate",
                    status="failure",
                    entity_id=loan_id,
                    loan_id=loan_id,
                    to_lender_id=to_lender_id,
                    error_type="LoanNotFound",
                ),
            )
            return False, error_msg

        to_lender = session.query(LenderDB).filter_by(id=to_lender_id).first()
        if to_lender is None:
            error_msg = f"Кредитор с ID {to_lender_id} не найден"
            logger.warning(
                "Debt transfer validation failed",
                extra=_debt_transfer_extra(
                    operation="debt_transfer_validate",
                    status="failure",
                    entity_id=loan_id,
                    loan_id=loan_id,
                    to_lender_id=to_lender_id,
                    error_type="LenderNotFound",
                ),
            )
            return False, error_msg

        loan_status_raw = cast(Any, loan.status)
        loan_status_value = getattr(loan_status_raw, "value", loan_status_raw)
        if loan_status_value == LoanStatus.PAID_OFF.value:
            error_msg = "Нельзя передать погашенный кредит"
            logger.warning(
                "Debt transfer validation failed",
                extra=_debt_transfer_extra(
                    operation="debt_transfer_validate",
                    status="failure",
                    entity_id=loan_id,
                    loan_id=loan_id,
                    to_lender_id=to_lender_id,
                    error_type="LoanPaidOff",
                ),
            )
            return False, error_msg

        current_holder_id = loan.effective_holder_id
        if to_lender_id == current_holder_id:
            error_msg = "Нельзя передать долг тому же кредитору"
            logger.warning(
                "Debt transfer validation failed",
                extra=_debt_transfer_extra(
                    operation="debt_transfer_validate",
                    status="failure",
                    entity_id=loan_id,
                    loan_id=loan_id,
                    to_lender_id=to_lender_id,
                    current_holder_id=current_holder_id,
                    error_type="SameLender",
                ),
            )
            return False, error_msg

        if transfer_amount <= Decimal("0"):
            error_msg = "Сумма передачи должна быть положительной"
            logger.warning(
                "Debt transfer validation failed",
                extra=_debt_transfer_extra(
                    operation="debt_transfer_validate",
                    status="failure",
                    entity_id=loan_id,
                    loan_id=loan_id,
                    to_lender_id=to_lender_id,
                    transfer_amount=transfer_amount,
                    error_type="NonPositiveAmount",
                ),
            )
            return False, error_msg

        logger.info(
            "Debt transfer validation succeeded",
            extra=_debt_transfer_extra(
                operation="debt_transfer_validate",
                status="success",
                entity_id=loan_id,
                loan_id=loan_id,
                to_lender_id=to_lender_id,
            ),
        )
        return True, None

    except SQLAlchemyError as exc:
        error_msg = f"Ошибка БД при валидации передачи: {exc}"
        logger.error(
            "Debt transfer validation failed with database error",
            extra=_debt_transfer_extra(
                operation="debt_transfer_validate",
                status="failure",
                entity_id=loan_id,
                loan_id=loan_id,
                to_lender_id=to_lender_id,
                error_type=type(exc).__name__,
            ),
        )
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
        logger.debug(
            "Calculating remaining debt",
            extra=_debt_transfer_extra(
                operation="debt_remaining_amount",
                status="start",
                entity_id=loan_id,
                loan_id=loan_id,
            ),
        )

        try:
            validate_uuid_format(loan_id, "ID кредита")
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        loan = session.query(LoanDB).filter_by(id=loan_id).first()
        if not loan:
            error_msg = f"Кредит с ID {loan_id} не найден"
            logger.warning(
                "Remaining debt calculation failed: loan not found",
                extra=_debt_transfer_extra(
                    operation="debt_remaining_amount",
                    status="failure",
                    entity_id=loan_id,
                    loan_id=loan_id,
                    error_type="LoanNotFound",
                ),
            )
            raise LoanNotFoundError(error_msg)

        executed_statuses = [PaymentStatus.EXECUTED, PaymentStatus.EXECUTED_LATE]
        executed_payments = (
            session.query(LoanPaymentDB)
            .filter(LoanPaymentDB.loan_id == loan_id, LoanPaymentDB.status.in_(executed_statuses))
            .all()
        )

        total_paid_principal = sum(
            (payment.principal_amount for payment in executed_payments), Decimal("0")
        )
        loan_amount = cast(Decimal, loan.amount)
        remaining_debt = loan_amount - total_paid_principal
        remaining_debt = max(remaining_debt, Decimal("0"))

        logger.info(
            "Remaining debt calculated",
            extra=_debt_transfer_extra(
                operation="debt_remaining_amount",
                status="success",
                entity_id=loan_id,
                loan_id=loan_id,
                remaining_debt=remaining_debt,
            ),
        )
        return cast(Decimal, remaining_debt)

    except (LoanNotFoundError, ValidationError):
        raise
    except SQLAlchemyError as exc:
        logger.error(
            "Database error while calculating remaining debt",
            extra=_debt_transfer_extra(
                operation="debt_remaining_amount",
                status="failure",
                entity_id=loan_id,
                loan_id=loan_id,
                error_type=type(exc).__name__,
            ),
        )
        raise DatabaseError(
            f"Ошибка БД при вычислении остатка долга по кредиту ID {loan_id}: {exc}"
        ) from exc


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
        logger.debug(
            "Fetching debt transfer history",
            extra=_debt_transfer_extra(
                operation="debt_transfer_history",
                status="start",
                entity_id=loan_id,
                loan_id=loan_id,
            ),
        )

        try:
            validate_uuid_format(loan_id, "ID кредита")
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        loan = session.query(LoanDB).filter_by(id=loan_id).first()
        if not loan:
            error_msg = f"Кредит с ID {loan_id} не найден"
            logger.warning(
                "Debt transfer history failed: loan not found",
                extra=_debt_transfer_extra(
                    operation="debt_transfer_history",
                    status="failure",
                    entity_id=loan_id,
                    loan_id=loan_id,
                    error_type="LoanNotFound",
                ),
            )
            raise LoanNotFoundError(error_msg)

        transfers = (
            session.query(DebtTransferDB)
            .filter(DebtTransferDB.loan_id == loan_id)
            .order_by(DebtTransferDB.transfer_date.asc())
            .all()
        )

        logger.info(
            "Debt transfer history fetched",
            extra=_debt_transfer_extra(
                operation="debt_transfer_history",
                status="success",
                entity_id=loan_id,
                loan_id=loan_id,
                records=len(transfers),
            ),
        )
        return transfers

    except (ValidationError, LoanNotFoundError):
        raise
    except SQLAlchemyError as exc:
        logger.error(
            "Database error while fetching debt transfer history",
            extra=_debt_transfer_extra(
                operation="debt_transfer_history",
                status="failure",
                entity_id=loan_id,
                loan_id=loan_id,
                error_type=type(exc).__name__,
            ),
        )
        raise DatabaseError(
            f"Ошибка БД при получении истории передач по кредиту ID {loan_id}: {exc}"
        ) from exc


def create_debt_transfer(
    session: Session,
    loan_id: str,
    to_lender_id: str,
    transfer_date: date,
    transfer_amount: Decimal,
    reason: Optional[str] = None,
    notes: Optional[str] = None,
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
        logger.info(
            "Debt transfer creation started",
            extra=_debt_transfer_extra(
                operation="debt_transfer_create",
                status="start",
                entity_id=loan_id,
                loan_id=loan_id,
                to_lender_id=to_lender_id,
                transfer_amount=transfer_amount,
            ),
        )

        is_valid, error_message = validate_transfer(session, loan_id, to_lender_id, transfer_amount)
        if not is_valid:
            raise InvalidTransferError(error_message or "Ошибка валидации передачи долга")

        loan = session.query(LoanDB).filter_by(id=loan_id).first()
        if not loan:
            error_msg = f"Кредит с ID {loan_id} не найден"
            raise LoanNotFoundError(error_msg)

        previous_amount = get_remaining_debt(session, loan_id)
        amount_difference = transfer_amount - previous_amount
        from_lender_id = loan.effective_holder_id

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
            notes=notes,
        )

        session.add(debt_transfer)
        loan_model = cast(Any, loan)
        loan_model.current_holder_id = to_lender_id

        if loan_model.original_lender_id is None:
            loan_model.original_lender_id = loan_model.lender_id

        updated_payments_count = update_payments_on_transfer(
            session=session, loan_id=loan_id, new_holder_id=to_lender_id
        )

        session.commit()

        logger.info(
            "Debt transfer created",
            extra=_debt_transfer_extra(
                operation="debt_transfer_create",
                status="success",
                entity_id=str(debt_transfer.id),
                loan_id=loan_id,
                from_lender_id=from_lender_id,
                to_lender_id=to_lender_id,
                transfer_amount=transfer_amount,
                amount_difference=amount_difference,
                updated_payments=updated_payments_count,
            ),
        )
        return debt_transfer

    except (InvalidTransferError, LoanNotFoundError, ValidationError):
        session.rollback()
        logger.warning(
            "Debt transfer creation rejected by domain guard",
            extra=_debt_transfer_extra(
                operation="debt_transfer_create",
                status="failure",
                entity_id=loan_id,
                loan_id=loan_id,
                to_lender_id=to_lender_id,
                transfer_amount=transfer_amount,
                error_type="DomainGuard",
            ),
        )
        raise
    except SQLAlchemyError as exc:
        session.rollback()
        logger.error(
            "Debt transfer creation failed with database error",
            extra=_debt_transfer_extra(
                operation="debt_transfer_create",
                status="failure",
                entity_id=loan_id,
                loan_id=loan_id,
                to_lender_id=to_lender_id,
                transfer_amount=transfer_amount,
                error_type=type(exc).__name__,
            ),
        )
        raise DatabaseError(f"Ошибка БД при создании передачи долга: {exc}") from exc

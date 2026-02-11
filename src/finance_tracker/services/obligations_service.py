import logging
from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Set

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from finance_tracker.models.enums import TransactionType
from finance_tracker.models.models import (
    CategoryDB,
    PlannedOccurrenceDB,
    PlannedTransactionDB,
    TransactionDB,
)
from finance_tracker.utils.exceptions import BusinessLogicError, ValidationError
from finance_tracker.utils.validation import validate_uuid_format


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ObligationMetrics:
    obligation_id: str
    month: date
    target: Decimal
    paid: Decimal
    remaining: Decimal


def get_obligation_metrics(
    session: Session,
    obligation_id: str,
    month: Optional[date] = None,
) -> ObligationMetrics:
    obligation = _get_obligation_or_raise(session, obligation_id)
    target_amount, resolved_month = _resolve_target_and_month(obligation, month)
    paid_amount = _calculate_paid_amount(session, obligation.id, resolved_month)

    remaining_amount = target_amount - paid_amount
    if remaining_amount < Decimal("0.00"):
        remaining_amount = Decimal("0.00")

    return ObligationMetrics(
        obligation_id=obligation.id,
        month=resolved_month,
        target=target_amount,
        paid=paid_amount,
        remaining=remaining_amount,
    )


def get_obligations_metrics_for_month(
    session: Session,
    month: date,
    category_id: Optional[str] = None,
) -> List[ObligationMetrics]:
    normalized_month = _normalize_month(month)

    if category_id is not None:
        _validate_uuid_or_raise(category_id, "category_id")

    query = session.query(PlannedTransactionDB).filter(
        PlannedTransactionDB.is_obligation.is_(True),
        PlannedTransactionDB.target_month == normalized_month,
    )
    if category_id is not None:
        query = query.filter(PlannedTransactionDB.category_id == category_id)

    obligations = query.order_by(PlannedTransactionDB.created_at.asc()).all()
    return [
        get_obligation_metrics(session, obligation.id, month=normalized_month)
        for obligation in obligations
    ]


def create_obligation(
    session: Session,
    *,
    category_id: str,
    target_amount: Decimal,
    target_month: date,
    t_type: TransactionType = TransactionType.EXPENSE,
    description: Optional[str] = None,
) -> ObligationMetrics:
    if target_amount <= Decimal("0"):
        raise ValidationError("Целевая сумма обязательства должна быть положительной")

    _validate_uuid_or_raise(category_id, "category_id")
    category = session.query(CategoryDB).filter_by(id=category_id).first()
    if not category:
        raise ValidationError(f"Категория с ID {category_id} не найдена")

    normalized_month = _normalize_month(target_month)

    try:
        obligation = PlannedTransactionDB(
            amount=target_amount,
            category_id=category_id,
            description=description,
            type=t_type,
            start_date=normalized_month,
            end_date=None,
            is_active=True,
            is_obligation=True,
            target_amount=target_amount,
            target_month=normalized_month,
        )
        session.add(obligation)
        session.commit()
        session.refresh(obligation)
    except SQLAlchemyError as exc:
        session.rollback()
        logger.error("Ошибка БД при создании obligation: %s", exc)
        raise

    return get_obligation_metrics(session, obligation.id, month=normalized_month)


def update_obligation_target(
    session: Session,
    obligation_id: str,
    target_amount: Decimal,
) -> ObligationMetrics:
    if target_amount <= Decimal("0"):
        raise ValidationError("Целевая сумма обязательства должна быть положительной")

    obligation = _get_obligation_or_raise(session, obligation_id)

    try:
        obligation.target_amount = target_amount
        session.commit()
        session.refresh(obligation)
    except SQLAlchemyError as exc:
        session.rollback()
        logger.error("Ошибка БД при обновлении target для obligation %s: %s", obligation_id, exc)
        raise

    return get_obligation_metrics(session, obligation.id)


def link_transaction_to_obligation(
    session: Session,
    transaction_id: str,
    obligation_id: str,
) -> ObligationMetrics:
    _validate_uuid_or_raise(transaction_id, "transaction_id")

    transaction = session.query(TransactionDB).filter_by(id=transaction_id).first()
    if not transaction:
        raise ValidationError(f"Транзакция с ID {transaction_id} не найдена")

    obligation = _get_obligation_or_raise(session, obligation_id)

    if transaction.obligation_id and transaction.obligation_id != obligation.id:
        raise BusinessLogicError(
            f"Транзакция {transaction_id} уже привязана к другому obligation "
            f"{transaction.obligation_id}"
        )

    metrics_before_link = get_obligation_metrics(session, obligation.id)

    if transaction.obligation_id == obligation.id:
        return metrics_before_link

    if transaction.amount > metrics_before_link.remaining:
        raise BusinessLogicError(
            "Нельзя привязать транзакцию к obligation: "
            f"сумма {transaction.amount} превышает остаток {metrics_before_link.remaining}"
        )

    try:
        transaction.obligation_id = obligation.id
        session.commit()
        session.refresh(transaction)
    except SQLAlchemyError as exc:
        session.rollback()
        logger.error(
            "Ошибка БД при привязке транзакции %s к obligation %s: %s",
            transaction_id,
            obligation_id,
            exc,
        )
        raise

    return get_obligation_metrics(session, obligation.id)


def _get_obligation_or_raise(session: Session, obligation_id: str) -> PlannedTransactionDB:
    _validate_uuid_or_raise(obligation_id, "obligation_id")

    obligation = session.query(PlannedTransactionDB).filter_by(id=obligation_id).first()
    if not obligation:
        raise ValidationError(f"Обязательство с ID {obligation_id} не найдено")

    if not obligation.is_obligation:
        raise ValidationError(f"Запись {obligation_id} не является obligation")

    return obligation


def _resolve_target_and_month(
    obligation: PlannedTransactionDB,
    month: Optional[date],
) -> tuple[Decimal, date]:
    resolved_month = _normalize_month(month) if month is not None else obligation.target_month
    if resolved_month is None:
        raise ValidationError(
            f"Для obligation {obligation.id} не задан target_month и не передан month"
        )

    resolved_month = _normalize_month(resolved_month)

    if obligation.target_amount is None:
        raise ValidationError(f"Для obligation {obligation.id} не задана target_amount")

    return obligation.target_amount, resolved_month


def _calculate_paid_amount(session: Session, obligation_id: str, month: date) -> Decimal:
    month_start, month_end = _get_month_date_bounds(month)

    paid_transactions_by_id: Dict[str, TransactionDB] = {}

    linked_transactions = (
        session.query(TransactionDB)
        .filter(
            TransactionDB.obligation_id == obligation_id,
            TransactionDB.transaction_date >= month_start,
            TransactionDB.transaction_date <= month_end,
        )
        .all()
    )

    for transaction in linked_transactions:
        paid_transactions_by_id[transaction.id] = transaction

    related_planned_ids = _get_related_planned_transaction_ids(session, obligation_id)

    occurrences = (
        session.query(PlannedOccurrenceDB.id, PlannedOccurrenceDB.actual_transaction_id)
        .filter(PlannedOccurrenceDB.planned_transaction_id.in_(related_planned_ids))
        .all()
    )

    occurrence_ids = [occurrence_id for occurrence_id, _ in occurrences]
    actual_transaction_ids = [
        transaction_id for _, transaction_id in occurrences if transaction_id is not None
    ]

    if occurrence_ids:
        transactions_from_occurrence_link = (
            session.query(TransactionDB)
            .filter(
                TransactionDB.planned_occurrence_id.in_(occurrence_ids),
                TransactionDB.transaction_date >= month_start,
                TransactionDB.transaction_date <= month_end,
            )
            .all()
        )
        for transaction in transactions_from_occurrence_link:
            paid_transactions_by_id[transaction.id] = transaction

    if actual_transaction_ids:
        transactions_from_actual_link = (
            session.query(TransactionDB)
            .filter(
                TransactionDB.id.in_(actual_transaction_ids),
                TransactionDB.transaction_date >= month_start,
                TransactionDB.transaction_date <= month_end,
            )
            .all()
        )
        for transaction in transactions_from_actual_link:
            paid_transactions_by_id[transaction.id] = transaction

    return sum(
        (transaction.amount for transaction in paid_transactions_by_id.values()), Decimal("0.00")
    )


def _get_related_planned_transaction_ids(session: Session, obligation_id: str) -> Set[str]:
    related_ids = {obligation_id}
    child_ids = (
        session.query(PlannedTransactionDB.id)
        .filter(PlannedTransactionDB.parent_planned_transaction_id == obligation_id)
        .all()
    )
    related_ids.update(child_id for (child_id,) in child_ids)
    return related_ids


def _get_month_date_bounds(month: date) -> tuple[date, date]:
    month_start = _normalize_month(month)
    last_day = monthrange(month_start.year, month_start.month)[1]
    month_end = date(month_start.year, month_start.month, last_day)
    return month_start, month_end


def _normalize_month(raw_month: date) -> date:
    return date(raw_month.year, raw_month.month, 1)


def _validate_uuid_or_raise(value: str, field_name: str) -> None:
    try:
        validate_uuid_format(value, field_name)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc

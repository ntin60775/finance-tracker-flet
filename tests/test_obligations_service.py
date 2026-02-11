from datetime import date
from decimal import Decimal
from typing import Optional

import pytest

from finance_tracker.models.enums import OccurrenceStatus, TransactionType
from finance_tracker.models.models import (
    CategoryDB,
    PlannedOccurrenceDB,
    PlannedTransactionDB,
    TransactionDB,
)
from finance_tracker.services.obligations_service import (
    get_obligation_metrics,
    get_obligations_metrics_for_month,
    link_transaction_to_obligation,
    update_obligation_target,
)
from finance_tracker.utils.exceptions import BusinessLogicError, ValidationError


def _create_category(session) -> CategoryDB:
    category = CategoryDB(name="Обязательства", type=TransactionType.EXPENSE, is_system=False)
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


def _create_obligation(
    session,
    category_id: str,
    target_amount: Decimal,
    target_month: date,
) -> PlannedTransactionDB:
    obligation = PlannedTransactionDB(
        amount=target_amount,
        category_id=category_id,
        description="Месячное обязательство",
        type=TransactionType.EXPENSE,
        is_obligation=True,
        target_amount=target_amount,
        target_month=date(target_month.year, target_month.month, 1),
        start_date=date(target_month.year, target_month.month, 1),
        is_active=True,
    )
    session.add(obligation)
    session.commit()
    session.refresh(obligation)
    return obligation


def _create_transaction(
    session,
    category_id: str,
    amount: Decimal,
    tx_date: date,
    planned_occurrence_id: Optional[str] = None,
) -> TransactionDB:
    transaction = TransactionDB(
        amount=amount,
        type=TransactionType.EXPENSE,
        category_id=category_id,
        description="Платеж",
        transaction_date=tx_date,
        planned_occurrence_id=planned_occurrence_id,
    )
    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction


def test_reject_link_when_transaction_amount_exceeds_remaining(db_session):
    category = _create_category(db_session)
    obligation = _create_obligation(
        db_session,
        category.id,
        target_amount=Decimal("1000.00"),
        target_month=date(2026, 2, 1),
    )
    transaction = _create_transaction(
        db_session,
        category.id,
        amount=Decimal("1200.00"),
        tx_date=date(2026, 2, 10),
    )

    with pytest.raises(BusinessLogicError, match="превышает остаток"):
        link_transaction_to_obligation(db_session, transaction.id, obligation.id)

    db_session.refresh(transaction)
    assert transaction.obligation_id is None


def test_reject_duplicate_link_to_another_obligation(db_session):
    category = _create_category(db_session)
    obligation_a = _create_obligation(
        db_session,
        category.id,
        target_amount=Decimal("1000.00"),
        target_month=date(2026, 2, 1),
    )
    obligation_b = _create_obligation(
        db_session,
        category.id,
        target_amount=Decimal("900.00"),
        target_month=date(2026, 2, 1),
    )
    transaction = _create_transaction(
        db_session,
        category.id,
        amount=Decimal("100.00"),
        tx_date=date(2026, 2, 5),
    )

    link_transaction_to_obligation(db_session, transaction.id, obligation_a.id)

    with pytest.raises(BusinessLogicError, match="уже привязана к другому obligation"):
        link_transaction_to_obligation(db_session, transaction.id, obligation_b.id)

    db_session.refresh(transaction)
    assert transaction.obligation_id == obligation_a.id


def test_multiple_obligations_same_category_month_are_calculated_independently(db_session):
    category = _create_category(db_session)
    obligation_a = _create_obligation(
        db_session,
        category.id,
        target_amount=Decimal("1000.00"),
        target_month=date(2026, 2, 1),
    )
    obligation_b = _create_obligation(
        db_session,
        category.id,
        target_amount=Decimal("500.00"),
        target_month=date(2026, 2, 1),
    )

    transaction_a = _create_transaction(
        db_session,
        category.id,
        amount=Decimal("300.00"),
        tx_date=date(2026, 2, 3),
    )
    transaction_b = _create_transaction(
        db_session,
        category.id,
        amount=Decimal("200.00"),
        tx_date=date(2026, 2, 4),
    )

    link_transaction_to_obligation(db_session, transaction_a.id, obligation_a.id)
    link_transaction_to_obligation(db_session, transaction_b.id, obligation_b.id)

    metrics = get_obligations_metrics_for_month(db_session, date(2026, 2, 1), category.id)
    metrics_by_id = {item.obligation_id: item for item in metrics}

    assert metrics_by_id[obligation_a.id].paid == Decimal("300.00")
    assert metrics_by_id[obligation_a.id].remaining == Decimal("700.00")
    assert metrics_by_id[obligation_b.id].paid == Decimal("200.00")
    assert metrics_by_id[obligation_b.id].remaining == Decimal("300.00")


def test_target_change_recomputes_remaining_immediately(db_session):
    category = _create_category(db_session)
    obligation = _create_obligation(
        db_session,
        category.id,
        target_amount=Decimal("1000.00"),
        target_month=date(2026, 2, 1),
    )
    transaction = _create_transaction(
        db_session,
        category.id,
        amount=Decimal("400.00"),
        tx_date=date(2026, 2, 6),
    )

    metrics_before = link_transaction_to_obligation(db_session, transaction.id, obligation.id)
    assert metrics_before.remaining == Decimal("600.00")

    metrics_after_update = update_obligation_target(db_session, obligation.id, Decimal("1500.00"))
    assert metrics_after_update.target == Decimal("1500.00")
    assert metrics_after_update.paid == Decimal("400.00")
    assert metrics_after_update.remaining == Decimal("1100.00")

    metrics_after_read = get_obligation_metrics(db_session, obligation.id)
    assert metrics_after_read.remaining == Decimal("1100.00")


def test_prevent_double_counting_for_planned_and_linked_transaction(db_session):
    category = _create_category(db_session)
    obligation = _create_obligation(
        db_session,
        category.id,
        target_amount=Decimal("500.00"),
        target_month=date(2026, 2, 1),
    )

    child_plan = PlannedTransactionDB(
        amount=Decimal("250.00"),
        category_id=category.id,
        description="Часть обязательства",
        type=TransactionType.EXPENSE,
        parent_planned_transaction_id=obligation.id,
        start_date=date(2026, 2, 1),
        is_active=True,
    )
    db_session.add(child_plan)
    db_session.commit()
    db_session.refresh(child_plan)

    occurrence = PlannedOccurrenceDB(
        planned_transaction_id=child_plan.id,
        occurrence_date=date(2026, 2, 15),
        amount=Decimal("250.00"),
        status=OccurrenceStatus.EXECUTED,
        executed_date=date(2026, 2, 15),
        executed_amount=Decimal("250.00"),
    )
    db_session.add(occurrence)
    db_session.commit()
    db_session.refresh(occurrence)

    transaction = _create_transaction(
        db_session,
        category.id,
        amount=Decimal("250.00"),
        tx_date=date(2026, 2, 15),
        planned_occurrence_id=occurrence.id,
    )

    occurrence.actual_transaction_id = transaction.id
    db_session.commit()

    metrics_before_link = get_obligation_metrics(db_session, obligation.id)
    assert metrics_before_link.paid == Decimal("250.00")

    metrics_after_link = link_transaction_to_obligation(db_session, transaction.id, obligation.id)
    assert metrics_after_link.paid == Decimal("250.00")
    assert metrics_after_link.remaining == Decimal("250.00")


def test_reject_link_with_invalid_obligation_uuid(db_session):
    category = _create_category(db_session)
    transaction = _create_transaction(
        db_session,
        category.id,
        amount=Decimal("100.00"),
        tx_date=date(2026, 2, 10),
    )

    with pytest.raises(ValidationError, match="Невалидный формат obligation_id"):
        link_transaction_to_obligation(db_session, transaction.id, "not-a-uuid")

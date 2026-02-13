from datetime import date
from decimal import Decimal

import pytest

from finance_tracker.models import (
    CategoryDB,
    PendingPaymentCreate,
    PendingPaymentPriority,
    PendingPaymentUpdate,
    PlannedTransactionCreate,
    TransactionCreate,
    TransactionType,
    TransactionUpdate,
)
from finance_tracker.services.pending_payment_service import (
    create_pending_payment,
    update_pending_payment,
)
from finance_tracker.services.planned_transaction_service import (
    create_planned_transaction,
    update_planned_transaction,
)
from finance_tracker.services.transaction_service import create_transaction, update_transaction


def _create_expense_hierarchy(db_session):
    parent = CategoryDB(name="Parent", type=TransactionType.EXPENSE, is_system=False)
    db_session.add(parent)
    db_session.flush()

    child = CategoryDB(
        name="Child",
        type=TransactionType.EXPENSE,
        parent_id=parent.id,
        is_system=False,
    )
    db_session.add(child)
    db_session.commit()
    return parent, child


def test_transaction_service_create_rejects_non_leaf_expense_category(db_session) -> None:
    parent, _ = _create_expense_hierarchy(db_session)

    payload = TransactionCreate(
        amount=Decimal("100.00"),
        type=TransactionType.EXPENSE,
        category_id=parent.id,
        description="tx",
        transaction_date=date.today(),
    )

    with pytest.raises(ValueError, match="конечные категории"):
        create_transaction(db_session, payload)


def test_transaction_service_update_rejects_non_leaf_expense_category(db_session) -> None:
    parent, child = _create_expense_hierarchy(db_session)

    created = create_transaction(
        db_session,
        TransactionCreate(
            amount=Decimal("100.00"),
            type=TransactionType.EXPENSE,
            category_id=child.id,
            description="tx",
            transaction_date=date.today(),
        ),
    )

    with pytest.raises(ValueError, match="конечные категории"):
        update_transaction(
            db_session,
            created.id,
            TransactionUpdate(category_id=parent.id, type=TransactionType.EXPENSE),
        )


def test_planned_transaction_service_create_rejects_non_leaf_expense_category(db_session) -> None:
    parent, _ = _create_expense_hierarchy(db_session)

    with pytest.raises(ValueError, match="конечные категории"):
        create_planned_transaction(
            db_session,
            PlannedTransactionCreate(
                amount=Decimal("200.00"),
                category_id=parent.id,
                description="plan",
                type=TransactionType.EXPENSE,
                start_date=date.today(),
                end_date=None,
                recurrence_rule=None,
                is_active=True,
            ),
        )


def test_planned_transaction_service_update_rejects_non_leaf_expense_category(db_session) -> None:
    parent, child = _create_expense_hierarchy(db_session)

    created = create_planned_transaction(
        db_session,
        PlannedTransactionCreate(
            amount=Decimal("200.00"),
            category_id=child.id,
            description="plan",
            type=TransactionType.EXPENSE,
            start_date=date.today(),
            end_date=None,
            recurrence_rule=None,
            is_active=True,
        ),
    )

    with pytest.raises(ValueError, match="конечные категории"):
        update_planned_transaction(
            db_session,
            created.id,
            PlannedTransactionCreate(
                amount=Decimal("210.00"),
                category_id=parent.id,
                description="plan updated",
                type=TransactionType.EXPENSE,
                start_date=date.today(),
                end_date=None,
                recurrence_rule=None,
                is_active=True,
            ),
        )


def test_pending_payment_service_create_rejects_non_leaf_expense_category(db_session) -> None:
    parent, _ = _create_expense_hierarchy(db_session)

    with pytest.raises(ValueError, match="конечные категории"):
        create_pending_payment(
            db_session,
            PendingPaymentCreate(
                amount=Decimal("300.00"),
                category_id=parent.id,
                description="pending",
                priority=PendingPaymentPriority.MEDIUM,
                planned_date=None,
            ),
        )


def test_pending_payment_service_update_rejects_non_leaf_expense_category(db_session) -> None:
    parent, child = _create_expense_hierarchy(db_session)

    created = create_pending_payment(
        db_session,
        PendingPaymentCreate(
            amount=Decimal("300.00"),
            category_id=child.id,
            description="pending",
            priority=PendingPaymentPriority.MEDIUM,
            planned_date=None,
        ),
    )

    with pytest.raises(ValueError, match="конечные категории"):
        update_pending_payment(
            db_session,
            created.id,
            PendingPaymentUpdate(category_id=parent.id),
        )

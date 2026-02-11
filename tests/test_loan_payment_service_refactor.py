from datetime import date
from decimal import Decimal

import pytest

from finance_tracker.models import CategoryDB, LenderDB, LoanDB, LoanStatus, LoanType
from finance_tracker.models.enums import LenderType, TransactionType
from finance_tracker.services.loan_payment_service import (
    _create_repayment_transaction,
    _get_loan_or_raise,
    _get_repayment_expense_category_id,
    _validate_create_payment_amounts,
)


def _create_loan(db_session):
    lender = LenderDB(name="Банк", lender_type=LenderType.BANK)
    db_session.add(lender)
    db_session.flush()

    loan = LoanDB(
        lender_id=lender.id,
        name="Кредит",
        loan_type=LoanType.CONSUMER,
        amount=Decimal("100000.00"),
        issue_date=date.today(),
        status=LoanStatus.ACTIVE,
    )
    db_session.add(loan)
    db_session.flush()
    return loan


def test_get_loan_or_raise_returns_existing_loan(db_session):
    loan = _create_loan(db_session)
    loaded = _get_loan_or_raise(db_session, loan.id)
    assert loaded.id == loan.id


def test_get_loan_or_raise_raises_for_missing_loan(db_session):
    with pytest.raises(ValueError, match="не найден"):
        _get_loan_or_raise(db_session, "00000000-0000-0000-0000-000000000000")


def test_validate_create_payment_amounts_checks_negative_and_total_mismatch():
    with pytest.raises(ValueError, match="основного долга"):
        _validate_create_payment_amounts(Decimal("-1"), Decimal("0"), Decimal("1"))

    with pytest.raises(ValueError, match="должна равняться"):
        _validate_create_payment_amounts(Decimal("10"), Decimal("5"), Decimal("20"))


def test_get_repayment_expense_category_id_returns_matching_category(db_session):
    category = CategoryDB(
        name="Выплата кредита (основной долг)",
        type=TransactionType.EXPENSE,
        is_system=False,
    )
    db_session.add(category)
    db_session.flush()

    assert _get_repayment_expense_category_id(db_session) == category.id


def test_create_repayment_transaction_builds_expense_transaction(db_session):
    category = CategoryDB(
        name="Выплата кредита",
        type=TransactionType.EXPENSE,
        is_system=False,
    )
    db_session.add(category)
    loan = _create_loan(db_session)

    transaction = _create_repayment_transaction(
        db_session,
        loan,
        Decimal("5000.00"),
        date(2026, 1, 15),
        "Тестовое погашение",
    )

    assert transaction.amount == Decimal("5000.00")
    assert transaction.type == TransactionType.EXPENSE
    assert transaction.category_id == category.id
    assert transaction.description == "Тестовое погашение"

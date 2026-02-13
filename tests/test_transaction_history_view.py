from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

from finance_tracker.models.enums import TransactionType
from finance_tracker.views.transaction_history_view import (
    _build_category_filter_metadata,
    _calculate_statistics,
    _filter_transactions,
    _resolve_selected_category_ids,
    _sort_transactions,
)
from ui_test_helpers import create_test_transaction


def _build_transaction(amount, transaction_type, category_id, description, transaction_date):
    transaction = create_test_transaction(
        amount=Decimal(amount),
        transaction_type=transaction_type,
        category_id=category_id,
        description=description,
        transaction_date=transaction_date,
    )
    transaction.category_id = category_id
    transaction.description = description
    transaction.transaction_date = transaction_date
    return transaction


def test_filter_transactions_applies_all_filters():
    today = date.today()
    transactions = [
        _build_transaction("100.00", TransactionType.EXPENSE, "cat-food", "Еда дома", today),
        _build_transaction("250.00", TransactionType.EXPENSE, "cat-car", "Топливо", today),
        _build_transaction("500.00", TransactionType.INCOME, "cat-food", "Кешбэк", today),
    ]

    filtered = _filter_transactions(
        transactions,
        selected_category_id="cat-food",
        selected_type=TransactionType.EXPENSE,
        search_query="еда",
    )

    assert len(filtered) == 1
    assert filtered[0].description == "Еда дома"


def test_build_category_filter_metadata_formats_child_category_label():
    categories = [
        SimpleNamespace(id="parent-1", name="Еда", parent_id=None),
        SimpleNamespace(id="child-1", name="Кафе", parent_id="parent-1"),
        SimpleNamespace(id="income-1", name="Зарплата", parent_id=None),
    ]

    labels_by_id, filter_ids_by_id = _build_category_filter_metadata(categories)

    assert labels_by_id["parent-1"] == "Еда"
    assert labels_by_id["child-1"] == "Еда / Кафе"
    assert labels_by_id["income-1"] == "Зарплата"
    assert filter_ids_by_id["parent-1"] == {"parent-1", "child-1"}
    assert filter_ids_by_id["child-1"] == {"child-1"}


def test_resolve_selected_category_ids_includes_children_for_parent():
    selected_ids = _resolve_selected_category_ids(
        "parent-1",
        {
            "parent-1": {"parent-1", "child-1"},
            "child-1": {"child-1"},
        },
    )

    assert selected_ids == {"parent-1", "child-1"}


def test_filter_transactions_parent_category_includes_children():
    today = date.today()
    transactions = [
        _build_transaction("100.00", TransactionType.EXPENSE, "child-1", "Кофе", today),
        _build_transaction("250.00", TransactionType.EXPENSE, "other", "Такси", today),
    ]

    filtered = _filter_transactions(
        transactions,
        selected_category_id="parent-1",
        selected_type=TransactionType.EXPENSE,
        search_query="",
        selected_category_ids={"parent-1", "child-1"},
    )

    assert len(filtered) == 1
    assert filtered[0].category_id == "child-1"


def test_sort_transactions_supports_date_and_amount_modes():
    today = date.today()
    older_date = today - timedelta(days=5)
    transactions = [
        _build_transaction("100.00", TransactionType.EXPENSE, "cat-1", "A", older_date),
        _build_transaction("300.00", TransactionType.EXPENSE, "cat-1", "B", today),
    ]

    by_date_desc = _sort_transactions(transactions, "date_desc")
    by_amount_asc = _sort_transactions(transactions, "amount_asc")

    assert by_date_desc[0].transaction_date == today
    assert by_amount_asc[0].amount == Decimal("100.00")


def test_calculate_statistics_returns_income_expense_balance_and_count():
    today = date.today()
    transactions = [
        _build_transaction("1000.00", TransactionType.INCOME, "cat-1", "Зарплата", today),
        _build_transaction("200.50", TransactionType.EXPENSE, "cat-2", "Покупки", today),
    ]

    total_income, total_expense, balance, count = _calculate_statistics(transactions)

    assert total_income == Decimal("1000.00")
    assert total_expense == Decimal("200.50")
    assert balance == Decimal("799.50")
    assert count == 2

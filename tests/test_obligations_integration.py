from datetime import date
from decimal import Decimal

from finance_tracker.models.enums import TransactionType
from finance_tracker.models.models import CategoryDB, PlannedTransactionDB, TransactionDB
from finance_tracker.services.obligations_service import (
    get_obligation_metrics,
    get_obligations_metrics_for_month,
    link_transaction_to_obligation,
    update_obligation_target,
)


def _create_category(db_session, *, category_id: str, name: str) -> CategoryDB:
    category = CategoryDB(
        id=category_id,
        name=name,
        type=TransactionType.EXPENSE,
        is_system=False,
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


def _create_obligation(
    db_session,
    *,
    obligation_id: str,
    category_id: str,
    target_amount: Decimal,
    target_month: date,
) -> PlannedTransactionDB:
    normalized_month = date(target_month.year, target_month.month, 1)
    obligation = PlannedTransactionDB(
        id=obligation_id,
        amount=target_amount,
        category_id=category_id,
        description="Интеграционное обязательство",
        type=TransactionType.EXPENSE,
        is_obligation=True,
        target_amount=target_amount,
        target_month=normalized_month,
        start_date=normalized_month,
        is_active=True,
    )
    db_session.add(obligation)
    db_session.commit()
    db_session.refresh(obligation)
    return obligation


def _create_transaction(
    db_session,
    *,
    transaction_id: str,
    category_id: str,
    amount: Decimal,
    transaction_date: date,
) -> TransactionDB:
    transaction = TransactionDB(
        id=transaction_id,
        amount=amount,
        type=TransactionType.EXPENSE,
        category_id=category_id,
        description="Интеграционный платеж",
        transaction_date=transaction_date,
    )
    db_session.add(transaction)
    db_session.commit()
    db_session.refresh(transaction)
    return transaction


def test_monthly_obligation_is_closed_by_partial_payments(db_session):
    month = date(2026, 3, 1)
    category = _create_category(
        db_session,
        category_id="11111111-1111-1111-1111-111111111111",
        name="Обязательства март",
    )
    obligation = _create_obligation(
        db_session,
        obligation_id="22222222-2222-2222-2222-222222222222",
        category_id=category.id,
        target_amount=Decimal("10000.00"),
        target_month=month,
    )
    tx_first = _create_transaction(
        db_session,
        transaction_id="33333333-3333-3333-3333-333333333333",
        category_id=category.id,
        amount=Decimal("4000.00"),
        transaction_date=date(2026, 3, 10),
    )
    tx_second = _create_transaction(
        db_session,
        transaction_id="44444444-4444-4444-4444-444444444444",
        category_id=category.id,
        amount=Decimal("6000.00"),
        transaction_date=date(2026, 3, 20),
    )

    link_transaction_to_obligation(db_session, tx_first.id, obligation.id)
    final_metrics = link_transaction_to_obligation(db_session, tx_second.id, obligation.id)

    assert final_metrics.target == Decimal("10000.00")
    assert final_metrics.paid == Decimal("10000.00")
    assert final_metrics.remaining == Decimal("0.00")

    persisted_metrics = get_obligation_metrics(db_session, obligation.id, month=month)
    assert persisted_metrics.remaining == Decimal("0.00")


def test_multiple_obligations_in_same_category_and_month_are_counted_independently(db_session):
    month = date(2026, 4, 1)
    category = _create_category(
        db_session,
        category_id="55555555-5555-5555-5555-555555555555",
        name="Обязательства апрель",
    )
    obligation_a = _create_obligation(
        db_session,
        obligation_id="66666666-6666-6666-6666-666666666666",
        category_id=category.id,
        target_amount=Decimal("7000.00"),
        target_month=month,
    )
    obligation_b = _create_obligation(
        db_session,
        obligation_id="77777777-7777-7777-7777-777777777777",
        category_id=category.id,
        target_amount=Decimal("5000.00"),
        target_month=month,
    )
    tx_a = _create_transaction(
        db_session,
        transaction_id="88888888-8888-8888-8888-888888888888",
        category_id=category.id,
        amount=Decimal("3000.00"),
        transaction_date=date(2026, 4, 7),
    )
    tx_b = _create_transaction(
        db_session,
        transaction_id="99999999-9999-9999-9999-999999999999",
        category_id=category.id,
        amount=Decimal("2000.00"),
        transaction_date=date(2026, 4, 8),
    )

    link_transaction_to_obligation(db_session, tx_a.id, obligation_a.id)
    link_transaction_to_obligation(db_session, tx_b.id, obligation_b.id)

    metrics = get_obligations_metrics_for_month(db_session, month, category.id)
    metrics_by_obligation_id = {item.obligation_id: item for item in metrics}

    assert obligation_a.id != obligation_b.id
    assert set(metrics_by_obligation_id) == {obligation_a.id, obligation_b.id}
    assert metrics_by_obligation_id[obligation_a.id].paid == Decimal("3000.00")
    assert metrics_by_obligation_id[obligation_a.id].remaining == Decimal("4000.00")
    assert metrics_by_obligation_id[obligation_b.id].paid == Decimal("2000.00")
    assert metrics_by_obligation_id[obligation_b.id].remaining == Decimal("3000.00")


def test_updating_target_recalculates_remaining(db_session):
    month = date(2026, 5, 1)
    category = _create_category(
        db_session,
        category_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        name="Обязательства май",
    )
    obligation = _create_obligation(
        db_session,
        obligation_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        category_id=category.id,
        target_amount=Decimal("10000.00"),
        target_month=month,
    )
    payment = _create_transaction(
        db_session,
        transaction_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
        category_id=category.id,
        amount=Decimal("4000.00"),
        transaction_date=date(2026, 5, 9),
    )

    metrics_before_update = link_transaction_to_obligation(db_session, payment.id, obligation.id)
    assert metrics_before_update.remaining == Decimal("6000.00")

    metrics_after_update = update_obligation_target(db_session, obligation.id, Decimal("12000.00"))
    assert metrics_after_update.target == Decimal("12000.00")
    assert metrics_after_update.paid == Decimal("4000.00")
    assert metrics_after_update.remaining == Decimal("8000.00")

    metrics_reloaded = get_obligation_metrics(db_session, obligation.id, month=month)
    assert metrics_reloaded.remaining == Decimal("8000.00")

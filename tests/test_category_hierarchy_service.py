from datetime import date
from decimal import Decimal
import uuid

import pytest

from finance_tracker.models import (
    CategoryDB,
    PendingPaymentDB,
    PlannedTransactionDB,
    TransactionDB,
    TransactionType,
)
from finance_tracker.services.category_service import (
    create_category,
    delete_category,
    get_expense_tree,
    get_selectable_leaf_categories,
    update_category,
)


def test_create_category_default_parent_id_is_none(db_session) -> None:
    category = create_category(db_session, "Быт", TransactionType.EXPENSE)

    assert category.parent_id is None


def test_create_category_with_parent_id_creates_child(db_session) -> None:
    parent = create_category(db_session, "Еда", TransactionType.EXPENSE)

    child = create_category(
        db_session,
        "Супермаркет",
        TransactionType.EXPENSE,
        parent_id=parent.id,
    )

    assert child.parent_id == parent.id


def test_create_category_rejects_missing_parent(db_session) -> None:
    missing_parent_id = str(uuid.uuid4())

    with pytest.raises(ValueError, match="не найдена"):
        create_category(
            db_session,
            "Подкатегория",
            TransactionType.EXPENSE,
            parent_id=missing_parent_id,
        )


def test_create_category_rejects_income_parent(db_session) -> None:
    income_parent = create_category(db_session, "Зарплата", TransactionType.INCOME)

    with pytest.raises(ValueError, match="должна быть типа EXPENSE"):
        create_category(
            db_session,
            "Неверный потомок",
            TransactionType.EXPENSE,
            parent_id=income_parent.id,
        )


def test_create_category_rejects_non_root_parent(db_session) -> None:
    root = create_category(db_session, "Транспорт", TransactionType.EXPENSE)
    child = create_category(
        db_session,
        "Такси",
        TransactionType.EXPENSE,
        parent_id=root.id,
    )

    with pytest.raises(ValueError, match="корневой"):
        create_category(
            db_session,
            "Глубина2",
            TransactionType.EXPENSE,
            parent_id=child.id,
        )


def test_create_category_rejects_income_child_with_parent_id(db_session) -> None:
    root = create_category(db_session, "Здоровье", TransactionType.EXPENSE)

    with pytest.raises(ValueError, match="только для категорий типа EXPENSE"):
        create_category(
            db_session,
            "Доход с родителем",
            TransactionType.INCOME,
            parent_id=root.id,
        )


def test_update_category_supports_parent_id(db_session) -> None:
    parent = create_category(db_session, "Дом", TransactionType.EXPENSE)
    category = create_category(db_session, "Коммуналка", TransactionType.EXPENSE)

    updated = update_category(
        db_session,
        category.id,
        "Коммунальные услуги",
        parent_id=parent.id,
    )

    assert updated.parent_id == parent.id
    assert updated.name == "Коммунальные услуги"


def test_update_category_without_parent_id_keeps_existing_parent(db_session) -> None:
    parent = create_category(db_session, "Авто", TransactionType.EXPENSE)
    child = create_category(
        db_session,
        "Мойка",
        TransactionType.EXPENSE,
        parent_id=parent.id,
    )

    updated = update_category(db_session, child.id, "Мойка авто")

    assert updated.parent_id == parent.id


def test_update_category_rejects_self_parent(db_session) -> None:
    category = create_category(db_session, "Спорт", TransactionType.EXPENSE)

    with pytest.raises(ValueError, match="сама себе"):
        update_category(db_session, category.id, "Спорт", parent_id=category.id)


def test_update_category_rejects_parent_of_wrong_type(db_session) -> None:
    income_parent = create_category(db_session, "Премия", TransactionType.INCOME)
    category = create_category(db_session, "Одежда", TransactionType.EXPENSE)

    with pytest.raises(ValueError, match="должна быть типа EXPENSE"):
        update_category(db_session, category.id, "Одежда", parent_id=income_parent.id)


def test_update_category_rejects_non_root_parent(db_session) -> None:
    root = create_category(db_session, "Питание", TransactionType.EXPENSE)
    child = create_category(
        db_session,
        "Кафе",
        TransactionType.EXPENSE,
        parent_id=root.id,
    )
    another_root = create_category(db_session, "Покупки", TransactionType.EXPENSE)

    with pytest.raises(ValueError, match="корневой"):
        update_category(db_session, another_root.id, "Покупки", parent_id=child.id)


def test_update_category_rejects_cycle(db_session) -> None:
    category_a = create_category(db_session, "A", TransactionType.EXPENSE)
    category_b = create_category(db_session, "B", TransactionType.EXPENSE)

    update_category(db_session, category_a.id, "A", parent_id=category_b.id)

    with pytest.raises(ValueError, match="корневой"):
        update_category(db_session, category_b.id, "B", parent_id=category_a.id)


def test_update_category_rejects_moving_parent_with_children_under_parent(db_session) -> None:
    root = create_category(db_session, "Root", TransactionType.EXPENSE)
    create_category(db_session, "Child", TransactionType.EXPENSE, parent_id=root.id)
    another_root = create_category(db_session, "AnotherRoot", TransactionType.EXPENSE)

    with pytest.raises(ValueError, match="оставаться корневой"):
        update_category(db_session, root.id, "Root", parent_id=another_root.id)


def test_create_child_rejects_used_parent_with_transactions(db_session) -> None:
    parent = create_category(db_session, "Связанный parent tx", TransactionType.EXPENSE)
    transaction = TransactionDB(
        amount=Decimal("100.00"),
        type=TransactionType.EXPENSE,
        category_id=parent.id,
        description="tx",
        transaction_date=date.today(),
    )
    db_session.add(transaction)
    db_session.commit()

    with pytest.raises(ValueError, match="уже используется"):
        create_category(
            db_session,
            "Child tx",
            TransactionType.EXPENSE,
            parent_id=parent.id,
        )


def test_create_child_rejects_used_parent_with_planned_transactions(db_session) -> None:
    parent = create_category(db_session, "Связанный parent plan", TransactionType.EXPENSE)
    planned = PlannedTransactionDB(
        amount=Decimal("200.00"),
        category_id=parent.id,
        description="planned",
        type=TransactionType.EXPENSE,
        start_date=date.today(),
    )
    db_session.add(planned)
    db_session.commit()

    with pytest.raises(ValueError, match="уже используется"):
        create_category(
            db_session,
            "Child plan",
            TransactionType.EXPENSE,
            parent_id=parent.id,
        )


def test_create_child_rejects_used_parent_with_pending_payments(db_session) -> None:
    parent = create_category(db_session, "Связанный parent pending", TransactionType.EXPENSE)
    pending = PendingPaymentDB(
        amount=Decimal("300.00"),
        category_id=parent.id,
        description="pending",
    )
    db_session.add(pending)
    db_session.commit()

    with pytest.raises(ValueError, match="уже используется"):
        create_category(
            db_session,
            "Child pending",
            TransactionType.EXPENSE,
            parent_id=parent.id,
        )


def test_delete_category_rejects_parent_with_children(db_session) -> None:
    parent = create_category(db_session, "Удаление root", TransactionType.EXPENSE)
    create_category(db_session, "Удаление child", TransactionType.EXPENSE, parent_id=parent.id)

    with pytest.raises(ValueError, match="дочерних категорий"):
        delete_category(db_session, parent.id)

    assert db_session.get(CategoryDB, parent.id) is not None


def test_get_expense_tree_returns_roots_with_children(db_session) -> None:
    parent = create_category(db_session, "Tree Root", TransactionType.EXPENSE)
    child = create_category(
        db_session,
        "Tree Child",
        TransactionType.EXPENSE,
        parent_id=parent.id,
    )
    root_without_children = create_category(db_session, "Single Leaf Root", TransactionType.EXPENSE)

    tree = get_expense_tree(db_session)

    by_root_id = {node["category"].id: node for node in tree}
    assert parent.id in by_root_id
    assert root_without_children.id in by_root_id
    assert child.id not in by_root_id
    assert [item.id for item in by_root_id[parent.id]["children"]] == [child.id]
    assert by_root_id[root_without_children.id]["children"] == []


def test_get_selectable_leaf_categories_returns_only_leaves_for_expense(db_session) -> None:
    parent = create_category(db_session, "Leaf Parent", TransactionType.EXPENSE)
    child = create_category(
        db_session,
        "Leaf Child",
        TransactionType.EXPENSE,
        parent_id=parent.id,
    )
    standalone_leaf = create_category(db_session, "Leaf Standalone", TransactionType.EXPENSE)
    income = create_category(db_session, "Income Leaf", TransactionType.INCOME)

    expense_leaves = get_selectable_leaf_categories(db_session, TransactionType.EXPENSE)
    income_leaves = get_selectable_leaf_categories(db_session, TransactionType.INCOME)

    expense_ids = {category.id for category in expense_leaves}
    income_ids = {category.id for category in income_leaves}

    assert parent.id not in expense_ids
    assert child.id in expense_ids
    assert standalone_leaf.id in expense_ids
    assert income.id in income_ids

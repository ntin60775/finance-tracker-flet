from datetime import datetime
import uuid

import pytest
from pydantic import ValidationError

from finance_tracker.database import init_default_categories
from finance_tracker.models import Category, CategoryCreate, CategoryDB, TransactionType


def test_category_create_accepts_expense_child_parent_id() -> None:
    parent_id = str(uuid.uuid4())

    category = CategoryCreate(
        name="Подкатегория расходов",
        type=TransactionType.EXPENSE,
        parent_id=parent_id,
    )

    assert category.parent_id == parent_id


def test_category_create_rejects_income_child() -> None:
    with pytest.raises(ValidationError, match="Категории доходов должны быть корневыми"):
        CategoryCreate(
            name="Доход с родителем",
            type=TransactionType.INCOME,
            parent_id=str(uuid.uuid4()),
        )


def test_category_create_rejects_non_uuid_parent_id() -> None:
    with pytest.raises(ValidationError, match="Невалидный UUID"):
        CategoryCreate(
            name="Некорректная категория",
            type=TransactionType.EXPENSE,
            parent_id="not-a-uuid",
        )


def test_category_contract_rejects_income_with_parent_id() -> None:
    with pytest.raises(ValidationError, match="Категории доходов должны быть корневыми"):
        Category(
            id=str(uuid.uuid4()),
            name="Доход",
            type=TransactionType.INCOME,
            parent_id=str(uuid.uuid4()),
            is_system=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )


def test_category_db_allows_expense_parent_child_one_level(db_session) -> None:
    parent = CategoryDB(name="Родитель", type=TransactionType.EXPENSE, is_system=False)
    db_session.add(parent)
    db_session.commit()

    child = CategoryDB(
        name="Потомок",
        type=TransactionType.EXPENSE,
        parent_id=parent.id,
        is_system=False,
    )
    db_session.add(child)
    db_session.commit()

    assert child.__dict__.get("parent_id") == parent.__dict__.get("id")


def test_category_db_rejects_third_level_expense(db_session) -> None:
    parent = CategoryDB(name="Уровень 1", type=TransactionType.EXPENSE, is_system=False)
    db_session.add(parent)
    db_session.commit()

    child = CategoryDB(
        name="Уровень 2", type=TransactionType.EXPENSE, parent=parent, is_system=False
    )
    db_session.add(child)
    db_session.commit()

    with pytest.raises(ValueError, match="одноуровневая иерархия"):
        CategoryDB(name="Уровень 3", type=TransactionType.EXPENSE, parent=child, is_system=False)


def test_category_db_rejects_income_parent_assignment(db_session) -> None:
    income_parent = CategoryDB(name="Доход-родитель", type=TransactionType.INCOME, is_system=False)
    db_session.add(income_parent)
    db_session.commit()

    with pytest.raises(ValueError, match="Родительская категория должна быть типа EXPENSE"):
        CategoryDB(
            name="Расход-потомок",
            type=TransactionType.EXPENSE,
            parent=income_parent,
            is_system=False,
        )


def test_category_db_rejects_income_parent_id(db_session) -> None:
    parent = CategoryDB(name="Root", type=TransactionType.EXPENSE, is_system=False)
    db_session.add(parent)
    db_session.commit()

    with pytest.raises(ValueError, match="Категории доходов должны быть корневыми"):
        CategoryDB(
            name="Income child",
            type=TransactionType.INCOME,
            parent_id=parent.id,
            is_system=False,
        )


def test_default_categories_initialization_keeps_root_level(db_session) -> None:
    init_default_categories(db_session)

    system_categories = db_session.query(CategoryDB).filter_by(is_system=True).all()

    assert system_categories
    assert all(category.__dict__.get("parent_id") is None for category in system_categories)

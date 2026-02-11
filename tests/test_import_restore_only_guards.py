import json
import logging
import uuid
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from finance_tracker.config import settings
from finance_tracker.mobile.export_service import SNAPSHOT_SCHEMA_VERSION, SNAPSHOT_TABLES
from finance_tracker.mobile.import_service import ImportService
from finance_tracker.models import Base
from finance_tracker.models.enums import TransactionType
from finance_tracker.models.models import CategoryDB, TransactionDB


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_class = sessionmaker(bind=engine)
    yield session_class
    engine.dispose()


def build_base_snapshot() -> dict[str, object]:
    snapshot: dict[str, object] = {
        "metadata": {
            "schema_version": SNAPSHOT_SCHEMA_VERSION,
            "app_version": settings.VERSION,
            "created_at": "2026-02-11T12:00:00",
        }
    }
    for table_name, _ in SNAPSHOT_TABLES:
        snapshot[table_name] = []
    return snapshot


def test_import_rejects_non_empty_user_data_state(session_factory, tmp_path):
    session = session_factory()
    now = datetime(2026, 2, 11, 10, 0, 0)

    system_category_id = str(uuid.uuid4())
    existing_transaction_id = str(uuid.uuid4())

    session.add(
        CategoryDB(
            id=system_category_id,
            name="Системная",
            type=TransactionType.EXPENSE,
            is_system=True,
            created_at=now,
            updated_at=now,
        )
    )
    session.add(
        TransactionDB(
            id=existing_transaction_id,
            amount=Decimal("30.00"),
            type=TransactionType.EXPENSE,
            category_id=system_category_id,
            description="Существующая транзакция",
            transaction_date=now.date(),
            planned_occurrence_id=None,
            created_at=now,
            updated_at=now,
        )
    )
    session.commit()

    snapshot = build_base_snapshot()
    new_category_id = str(uuid.uuid4())
    categories = snapshot["categories"]
    assert isinstance(categories, list)
    categories.append(
        {
            "id": new_category_id,
            "name": "Новая категория",
            "type": "expense",
            "is_system": False,
            "created_at": "2026-02-11T12:00:00",
            "updated_at": "2026-02-11T12:00:00",
        }
    )

    snapshot_path = tmp_path / "restore_only_guard.json"
    snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    with pytest.raises(ValueError, match="Restore-only импорт разрешен только для пустых"):
        ImportService.import_from_file(str(snapshot_path), _session=session)

    assert session.query(CategoryDB).count() == 1
    assert session.query(TransactionDB).count() == 1
    assert (
        session.query(TransactionDB).filter(TransactionDB.id == existing_transaction_id).count()
        == 1
    )

    session.close()


def test_import_is_atomic_and_rolls_back_on_commit_failure(session_factory, tmp_path):
    session = session_factory()
    now = datetime(2026, 2, 11, 11, 0, 0)

    original_system_category_id = str(uuid.uuid4())
    session.add(
        CategoryDB(
            id=original_system_category_id,
            name="Системная категория",
            type=TransactionType.INCOME,
            is_system=True,
            created_at=now,
            updated_at=now,
        )
    )
    session.commit()

    snapshot = build_base_snapshot()
    categories = snapshot["categories"]
    assert isinstance(categories, list)
    categories.extend(
        [
            {
                "id": str(uuid.uuid4()),
                "name": "Дубликат",
                "type": "expense",
                "is_system": False,
                "created_at": "2026-02-11T12:00:00",
                "updated_at": "2026-02-11T12:00:00",
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Дубликат",
                "type": "income",
                "is_system": False,
                "created_at": "2026-02-11T12:00:00",
                "updated_at": "2026-02-11T12:00:00",
            },
        ]
    )

    snapshot_path = tmp_path / "atomicity_failure.json"
    snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    with pytest.raises(ValueError, match="изменения откатены"):
        ImportService.import_from_file(str(snapshot_path), _session=session)

    existing_categories = session.query(CategoryDB).all()
    assert len(existing_categories) == 1
    assert existing_categories[0].id == original_system_category_id
    assert session.query(TransactionDB).count() == 0

    session.close()


def test_import_guard_logs_domain_journal_events(session_factory, tmp_path, caplog):
    session = session_factory()
    now = datetime(2026, 2, 11, 13, 0, 0)

    system_category_id = str(uuid.uuid4())
    existing_transaction_id = str(uuid.uuid4())

    session.add(
        CategoryDB(
            id=system_category_id,
            name="Системная",
            type=TransactionType.EXPENSE,
            is_system=True,
            created_at=now,
            updated_at=now,
        )
    )
    session.add(
        TransactionDB(
            id=existing_transaction_id,
            amount=Decimal("10.00"),
            type=TransactionType.EXPENSE,
            category_id=system_category_id,
            description="Существующая транзакция",
            transaction_date=now.date(),
            planned_occurrence_id=None,
            created_at=now,
            updated_at=now,
        )
    )
    session.commit()

    snapshot = build_base_snapshot()
    categories = snapshot["categories"]
    assert isinstance(categories, list)
    categories.append(
        {
            "id": str(uuid.uuid4()),
            "name": "Новая категория",
            "type": "expense",
            "is_system": False,
            "created_at": "2026-02-11T12:00:00",
            "updated_at": "2026-02-11T12:00:00",
        }
    )

    snapshot_path = tmp_path / "restore_only_guard_with_logs.json"
    snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    with caplog.at_level(logging.INFO):
        with pytest.raises(ValueError, match="Restore-only импорт разрешен только для пустых"):
            ImportService.import_from_file(str(snapshot_path), _session=session)

    journal_records = [
        record
        for record in caplog.records
        if getattr(record, "operation", None) == "snapshot_import"
    ]
    statuses = {getattr(record, "status", None) for record in journal_records}

    assert "start" in statuses
    assert "failure" in statuses

    session.close()

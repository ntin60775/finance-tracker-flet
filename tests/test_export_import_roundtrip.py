import json
import uuid
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from finance_tracker.config import settings
from finance_tracker.mobile.export_service import (
    SNAPSHOT_SCHEMA_VERSION,
    SNAPSHOT_TABLES,
    ExportService,
)
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


def build_empty_snapshot() -> dict[str, object]:
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


def test_export_import_roundtrip_preserves_counts_decimal_and_fk(session_factory, tmp_path):
    source_session = session_factory()
    now = datetime(2026, 2, 11, 9, 30, 0)
    source_category_id = str(uuid.uuid4())

    source_session.add(
        CategoryDB(
            id=source_category_id,
            name="Раундтрип",
            type=TransactionType.EXPENSE,
            is_system=False,
            created_at=now,
            updated_at=now,
        )
    )
    source_session.add(
        TransactionDB(
            id=str(uuid.uuid4()),
            amount=Decimal("123.45"),
            type=TransactionType.EXPENSE,
            category_id=source_category_id,
            description="Проверка round-trip",
            transaction_date=now.date(),
            planned_occurrence_id=None,
            created_at=now,
            updated_at=now,
        )
    )
    source_session.commit()

    snapshot_path = tmp_path / "roundtrip_snapshot.json"
    ExportService.export_to_file(str(snapshot_path), _session=source_session, _created_at=now)
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))

    for table_name, _ in SNAPSHOT_TABLES:
        assert table_name in payload
        assert isinstance(payload[table_name], list)

    assert len(payload["categories"]) == 1
    assert len(payload["transactions"]) == 1
    assert payload["transactions"][0]["amount"] == "123.45"

    target_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(target_engine)
    target_session_class = sessionmaker(bind=target_engine)
    target_session = target_session_class()

    baseline_system_id = str(uuid.uuid4())
    target_session.add(
        CategoryDB(
            id=baseline_system_id,
            name="Системная категория",
            type=TransactionType.INCOME,
            is_system=True,
            created_at=now,
            updated_at=now,
        )
    )
    target_session.commit()

    report = ImportService.import_from_file(str(snapshot_path), _session=target_session)

    expected_added = sum(len(payload[table_name]) for table_name, _ in SNAPSHOT_TABLES)
    assert report == {"added": expected_added, "skipped": 0, "conflicts": 0}
    assert target_session.query(CategoryDB).count() == 1
    assert target_session.query(TransactionDB).count() == 1
    assert target_session.query(CategoryDB).filter(CategoryDB.id == baseline_system_id).count() == 0

    imported_category = target_session.query(CategoryDB).one()
    imported_transaction = target_session.query(TransactionDB).one()

    assert imported_transaction.amount == Decimal("123.45")
    assert imported_transaction.category_id == imported_category.id
    assert imported_transaction.category is not None
    assert imported_transaction.category.id == imported_category.id

    source_session.close()
    target_session.close()
    target_engine.dispose()


def test_restore_only_rejection_keeps_existing_user_data_untouched(session_factory, tmp_path):
    session = session_factory()
    now = datetime(2026, 2, 11, 10, 0, 0)

    existing_category_id = str(uuid.uuid4())
    existing_transaction_id = str(uuid.uuid4())
    session.add(
        CategoryDB(
            id=existing_category_id,
            name="Существующая категория",
            type=TransactionType.EXPENSE,
            is_system=False,
            created_at=now,
            updated_at=now,
        )
    )
    session.add(
        TransactionDB(
            id=existing_transaction_id,
            amount=Decimal("30.00"),
            type=TransactionType.EXPENSE,
            category_id=existing_category_id,
            description="Существующая транзакция",
            transaction_date=now.date(),
            planned_occurrence_id=None,
            created_at=now,
            updated_at=now,
        )
    )
    session.commit()

    snapshot = build_empty_snapshot()
    categories = snapshot["categories"]
    assert isinstance(categories, list)
    categories.append(
        {
            "id": str(uuid.uuid4()),
            "name": "Категория из snapshot",
            "type": "expense",
            "is_system": False,
            "created_at": "2026-02-11T12:00:00",
            "updated_at": "2026-02-11T12:00:00",
        }
    )

    snapshot_path = tmp_path / "restore_only_non_destructive.json"
    snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    with pytest.raises(ValueError, match="Restore-only импорт разрешен только для пустых"):
        ImportService.import_from_file(str(snapshot_path), _session=session)

    assert session.query(CategoryDB).count() == 1
    assert session.query(TransactionDB).count() == 1

    existing_category = session.query(CategoryDB).one()
    existing_transaction = session.query(TransactionDB).one()
    assert existing_category.id == existing_category_id
    assert existing_transaction.id == existing_transaction_id
    assert existing_transaction.amount == Decimal("30.00")

    session.close()

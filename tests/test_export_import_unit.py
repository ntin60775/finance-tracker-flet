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


def test_export_writes_snapshot_with_metadata_and_domain_tables(session_factory, tmp_path):
    session = session_factory()
    now = datetime(2026, 2, 11, 12, 15, 0)
    category_id = str(uuid.uuid4())

    category = CategoryDB(
        id=category_id,
        name="Еда",
        type=TransactionType.EXPENSE,
        is_system=False,
        created_at=now,
        updated_at=now,
    )
    transaction = TransactionDB(
        id=str(uuid.uuid4()),
        amount=Decimal("123.45"),
        type=TransactionType.EXPENSE,
        category_id=category_id,
        description="Покупка",
        transaction_date=now.date(),
        planned_occurrence_id=None,
        created_at=now,
        updated_at=now,
    )
    session.add(category)
    session.add(transaction)
    session.commit()

    snapshot_path = tmp_path / "snapshot.json"
    exported_path = ExportService.export_to_file(
        str(snapshot_path),
        _session=session,
        _created_at=now,
    )

    assert exported_path == str(snapshot_path)
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))

    assert payload["metadata"] == {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "app_version": settings.VERSION,
        "created_at": "2026-02-11T12:15:00",
    }
    for table_name, _ in SNAPSHOT_TABLES:
        assert table_name in payload
        assert isinstance(payload[table_name], list)

    exported_transaction = payload["transactions"][0]
    assert exported_transaction["amount"] == "123.45"
    assert exported_transaction["transaction_date"] == "2026-02-11"
    assert exported_transaction["type"] == "expense"

    session.close()


def test_import_restores_snapshot_and_returns_report(session_factory, tmp_path):
    source_session = session_factory()
    now = datetime(2026, 2, 11, 9, 0, 0)
    source_category_id = str(uuid.uuid4())

    source_session.add(
        CategoryDB(
            id=source_category_id,
            name="Транспорт",
            type=TransactionType.EXPENSE,
            is_system=False,
            created_at=now,
            updated_at=now,
        )
    )
    source_session.add(
        TransactionDB(
            id=str(uuid.uuid4()),
            amount=Decimal("50.10"),
            type=TransactionType.EXPENSE,
            category_id=source_category_id,
            description="Метро",
            transaction_date=now.date(),
            planned_occurrence_id=None,
            created_at=now,
            updated_at=now,
        )
    )
    source_session.commit()

    snapshot_path = tmp_path / "snapshot_for_import.json"
    ExportService.export_to_file(str(snapshot_path), _session=source_session, _created_at=now)

    target_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(target_engine)
    target_session_class = sessionmaker(bind=target_engine)
    target_session = target_session_class()
    existing_system_id = str(uuid.uuid4())
    target_session.add(
        CategoryDB(
            id=existing_system_id,
            name="Системная категория",
            type=TransactionType.INCOME,
            is_system=True,
            created_at=now,
            updated_at=now,
        )
    )
    target_session.commit()

    report = ImportService.import_from_file(str(snapshot_path), _session=target_session)

    assert report == {"added": 2, "skipped": 0, "conflicts": 0}
    assert target_session.query(CategoryDB).count() == 1
    assert target_session.query(TransactionDB).count() == 1
    assert target_session.query(CategoryDB).filter(CategoryDB.id == existing_system_id).count() == 0

    imported_transaction = target_session.query(TransactionDB).one()
    assert imported_transaction.amount == Decimal("50.10")

    source_session.close()
    target_session.close()
    target_engine.dispose()


@pytest.mark.parametrize(
    ("field_name", "field_value", "error_message"),
    [
        ("schema_version", "9.9", "Неподдерживаемая версия snapshot schema_version"),
        ("app_version", "0.0.1", "не поддерживается для импорта"),
        ("created_at", "bad-date", "Некорректный формат metadata.created_at"),
    ],
)
def test_import_rejects_invalid_metadata(
    session_factory,
    tmp_path,
    field_name,
    field_value,
    error_message,
):
    session = session_factory()
    snapshot = build_empty_snapshot()
    metadata = snapshot["metadata"]
    assert isinstance(metadata, dict)
    metadata[field_name] = field_value

    snapshot_path = tmp_path / f"invalid_metadata_{field_name}.json"
    snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    with pytest.raises(ValueError, match=error_message):
        ImportService.import_from_file(str(snapshot_path), _session=session)

    session.close()


def test_import_rejects_invalid_uuid_format(session_factory, tmp_path):
    session = session_factory()
    snapshot = build_empty_snapshot()
    categories = snapshot["categories"]
    assert isinstance(categories, list)
    categories.append(
        {
            "id": "not-a-uuid",
            "name": "Категория",
            "type": "expense",
            "is_system": False,
            "created_at": "2026-02-11T12:00:00",
            "updated_at": "2026-02-11T12:00:00",
        }
    )

    snapshot_path = tmp_path / "invalid_uuid_snapshot.json"
    snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    with pytest.raises(ValueError, match="Невалидный формат categories.id"):
        ImportService.import_from_file(str(snapshot_path), _session=session)

    session.close()


def test_import_rejects_missing_fk_reference(session_factory, tmp_path):
    session = session_factory()
    snapshot = build_empty_snapshot()
    missing_category_id = str(uuid.uuid4())

    transactions = snapshot["transactions"]
    assert isinstance(transactions, list)
    transactions.append(
        {
            "id": str(uuid.uuid4()),
            "amount": "10.00",
            "type": "expense",
            "category_id": missing_category_id,
            "description": "Без категории",
            "transaction_date": "2026-02-11",
            "planned_occurrence_id": None,
            "created_at": "2026-02-11T12:00:00",
            "updated_at": "2026-02-11T12:00:00",
        }
    )

    snapshot_path = tmp_path / "missing_fk_snapshot.json"
    snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    with pytest.raises(ValueError, match="FK ссылка"):
        ImportService.import_from_file(str(snapshot_path), _session=session)

    session.close()


def test_import_rejects_decimal_not_string(session_factory, tmp_path):
    session = session_factory()
    snapshot = build_empty_snapshot()
    category_id = str(uuid.uuid4())

    categories = snapshot["categories"]
    assert isinstance(categories, list)
    categories.append(
        {
            "id": category_id,
            "name": "Категория",
            "type": "expense",
            "is_system": False,
            "created_at": "2026-02-11T12:00:00",
            "updated_at": "2026-02-11T12:00:00",
        }
    )

    transactions = snapshot["transactions"]
    assert isinstance(transactions, list)
    transactions.append(
        {
            "id": str(uuid.uuid4()),
            "amount": 10.0,
            "type": "expense",
            "category_id": category_id,
            "description": "Сумма не строкой",
            "transaction_date": "2026-02-11",
            "planned_occurrence_id": None,
            "created_at": "2026-02-11T12:00:00",
            "updated_at": "2026-02-11T12:00:00",
        }
    )

    snapshot_path = tmp_path / "invalid_decimal_snapshot.json"
    snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    with pytest.raises(ValueError, match="должно быть строкой для Decimal"):
        ImportService.import_from_file(str(snapshot_path), _session=session)

    session.close()

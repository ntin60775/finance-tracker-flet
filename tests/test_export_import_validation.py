import json
import uuid
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from finance_tracker.config import settings
from finance_tracker.mobile.export_service import SNAPSHOT_SCHEMA_VERSION, SNAPSHOT_TABLES
from finance_tracker.mobile.import_service import ImportService
from finance_tracker.models import Base
from finance_tracker.models.enums import TransactionType
from finance_tracker.models.models import CategoryDB


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


def test_import_rejects_corrupted_json_payload(session_factory, tmp_path):
    session = session_factory()
    snapshot_path = tmp_path / "corrupted_snapshot.json"
    snapshot_path.write_text('{"metadata": {"schema_version":', encoding="utf-8")

    with pytest.raises(ValueError, match="некорректный JSON"):
        ImportService.import_from_file(str(snapshot_path), _session=session)

    session.close()


def test_import_rejects_schema_version_mismatch(session_factory, tmp_path):
    session = session_factory()
    snapshot = build_empty_snapshot()
    metadata = snapshot["metadata"]
    assert isinstance(metadata, dict)
    metadata["schema_version"] = "9.9"

    snapshot_path = tmp_path / "schema_mismatch_snapshot.json"
    snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    with pytest.raises(ValueError, match="Неподдерживаемая версия snapshot schema_version"):
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


def test_import_rejects_invalid_parent_reference_and_rolls_back(session_factory, tmp_path):
    session = session_factory()
    now = datetime(2026, 2, 11, 12, 0, 0)
    existing_system_id = str(uuid.uuid4())
    missing_parent_id = str(uuid.uuid4())

    session.add(
        CategoryDB(
            id=existing_system_id,
            name="Системная категория",
            type=TransactionType.INCOME,
            is_system=True,
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
            "name": "Child",
            "type": "expense",
            "parent_id": missing_parent_id,
            "is_system": False,
            "created_at": "2026-02-11T12:00:00",
            "updated_at": "2026-02-11T12:00:00",
        }
    )

    snapshot_path = tmp_path / "invalid_parent_snapshot.json"
    snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    with pytest.raises(ValueError, match="Неразрешимая parent ссылка"):
        ImportService.import_from_file(str(snapshot_path), _session=session)

    remaining_categories = session.query(CategoryDB).all()
    assert len(remaining_categories) == 1
    assert remaining_categories[0].__dict__.get("id") == existing_system_id
    assert remaining_categories[0].__dict__.get("is_system") is True

    session.close()


def test_import_rejects_parent_cycle_in_categories_payload(session_factory, tmp_path):
    session = session_factory()
    first_id = str(uuid.uuid4())
    second_id = str(uuid.uuid4())

    snapshot = build_empty_snapshot()
    categories = snapshot["categories"]
    assert isinstance(categories, list)
    categories.extend(
        [
            {
                "id": first_id,
                "name": "A",
                "type": "expense",
                "parent_id": second_id,
                "is_system": False,
                "created_at": "2026-02-11T12:00:00",
                "updated_at": "2026-02-11T12:00:00",
            },
            {
                "id": second_id,
                "name": "B",
                "type": "expense",
                "parent_id": first_id,
                "is_system": False,
                "created_at": "2026-02-11T12:00:00",
                "updated_at": "2026-02-11T12:00:00",
            },
        ]
    )

    snapshot_path = tmp_path / "cycle_parent_snapshot.json"
    snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    with pytest.raises(ValueError, match="цикл"):
        ImportService.import_from_file(str(snapshot_path), _session=session)

    session.close()

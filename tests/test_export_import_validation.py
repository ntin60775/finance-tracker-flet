import json
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from finance_tracker.config import settings
from finance_tracker.mobile.export_service import SNAPSHOT_SCHEMA_VERSION, SNAPSHOT_TABLES
from finance_tracker.mobile.import_service import ImportService
from finance_tracker.models import Base


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

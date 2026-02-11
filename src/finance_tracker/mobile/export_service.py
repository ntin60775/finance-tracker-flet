from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from finance_tracker.config import settings
from finance_tracker.database import get_db_session
from finance_tracker.models import (
    CategoryDB,
    DebtTransferDB,
    LenderDB,
    LoanDB,
    LoanPaymentDB,
    PendingPaymentDB,
    PlannedOccurrenceDB,
    PlannedTransactionDB,
    RecurrenceRuleDB,
    TransactionDB,
)
from finance_tracker.utils.logger import get_logger

logger = get_logger(__name__)

SNAPSHOT_SCHEMA_VERSION = "1.0"

SNAPSHOT_TABLES: list[tuple[str, type[Any]]] = [
    ("categories", CategoryDB),
    ("planned_transactions", PlannedTransactionDB),
    ("recurrence_rules", RecurrenceRuleDB),
    ("planned_occurrences", PlannedOccurrenceDB),
    ("transactions", TransactionDB),
    ("lenders", LenderDB),
    ("loans", LoanDB),
    ("loan_payments", LoanPaymentDB),
    ("pending_payments", PendingPaymentDB),
    ("debt_transfers", DebtTransferDB),
]


def _serialize_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    return value


def _serialize_record(record: Any) -> dict[str, Any]:
    serialized: dict[str, Any] = {}
    for column in record.__table__.columns:
        serialized[column.name] = _serialize_value(getattr(record, column.name))
    return serialized


def _resolve_output_path(filepath: str | None, created_at: datetime) -> Path:
    if filepath:
        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path

    exports_dir = settings.user_data_dir / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    filename = f"snapshot_{created_at.strftime('%Y%m%d_%H%M%S')}.json"
    return exports_dir / filename


def _build_snapshot(session: Session, created_at: datetime) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "metadata": {
            "schema_version": SNAPSHOT_SCHEMA_VERSION,
            "app_version": settings.VERSION,
            "created_at": created_at.isoformat(),
        }
    }

    for table_name, model in SNAPSHOT_TABLES:
        rows = session.query(model).order_by(model.id).all()
        snapshot[table_name] = [_serialize_record(row) for row in rows]

    return snapshot


def _export_to_file(session: Session, filepath: str | None, created_at: datetime) -> str:
    output_path = _resolve_output_path(filepath=filepath, created_at=created_at)
    snapshot = _build_snapshot(session=session, created_at=created_at)

    with output_path.open("w", encoding="utf-8") as snapshot_file:
        json.dump(snapshot, snapshot_file, ensure_ascii=False, indent=2)

    logger.info(f"Snapshot экспортирован в файл: {output_path}")
    return str(output_path)


class ExportService:
    @staticmethod
    def export_to_file(
        filepath: str | None = None,
        *,
        _session: Session | None = None,
        _created_at: datetime | None = None,
    ) -> str:
        created_at = _created_at or datetime.now()

        if _session is not None:
            return _export_to_file(session=_session, filepath=filepath, created_at=created_at)

        with get_db_session() as session:
            return _export_to_file(session=session, filepath=filepath, created_at=created_at)

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Enum as SQLEnum, Integer, Numeric, String
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from finance_tracker.config import settings
from finance_tracker.database import get_db_session
from finance_tracker.mobile.export_service import SNAPSHOT_SCHEMA_VERSION, SNAPSHOT_TABLES
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
from finance_tracker.utils.exceptions import DatabaseError, ValidationError
from finance_tracker.utils.logger import get_logger
from finance_tracker.utils.validation import validate_uuid_format

logger = get_logger(__name__)

SNAPSHOT_MODEL_MAP: dict[str, type[Any]] = {
    table_name: model for table_name, model in SNAPSHOT_TABLES
}

DELETE_ORDER: list[type[Any]] = [
    DebtTransferDB,
    LoanPaymentDB,
    PendingPaymentDB,
    PlannedOccurrenceDB,
    LoanDB,
    TransactionDB,
    RecurrenceRuleDB,
    PlannedTransactionDB,
    LenderDB,
    CategoryDB,
]

IMPORT_ORDER: list[type[Any]] = [
    CategoryDB,
    PlannedTransactionDB,
    RecurrenceRuleDB,
    PlannedOccurrenceDB,
    TransactionDB,
    LenderDB,
    LoanDB,
    LoanPaymentDB,
    PendingPaymentDB,
    DebtTransferDB,
]

REPORT_TEMPLATE: dict[str, int] = {
    "added": 0,
    "skipped": 0,
    "conflicts": 0,
}

ROLLBACK_ERROR_MESSAGE = "Импорт snapshot завершился с ошибкой; изменения откатены."


def _snapshot_import_extra(filepath: str, status: str, **kwargs: Any) -> dict[str, Any]:
    extra: dict[str, Any] = {
        "event_type": "domain_journal",
        "operation": "snapshot_import",
        "entity": "snapshot",
        "entity_id": filepath,
        "status": status,
    }
    extra.update(kwargs)
    return extra


def _load_snapshot(filepath: str) -> dict[str, Any]:
    snapshot_path = Path(filepath)
    if not snapshot_path.exists() or not snapshot_path.is_file():
        raise ValueError(f"Snapshot файл не найден: {filepath}")

    try:
        with snapshot_path.open("r", encoding="utf-8") as snapshot_file:
            payload = json.load(snapshot_file)
    except json.JSONDecodeError as exc:
        raise ValueError("Snapshot файл содержит некорректный JSON.") from exc
    except OSError as exc:
        raise ValueError(f"Не удалось прочитать snapshot файл: {filepath}") from exc

    if not isinstance(payload, dict):
        raise ValueError("Snapshot должен быть JSON объектом.")
    return payload


def _require_key(mapping: dict[str, Any], key: str, location: str) -> Any:
    if key not in mapping:
        raise ValueError(f"Отсутствует обязательное поле {location}.{key}")
    return mapping[key]


def _validate_metadata(metadata: Any) -> None:
    if not isinstance(metadata, dict):
        raise ValueError("Поле metadata должно быть объектом.")

    schema_version = _require_key(metadata, "schema_version", "metadata")
    if schema_version != SNAPSHOT_SCHEMA_VERSION:
        raise ValueError(
            "Неподдерживаемая версия snapshot schema_version: "
            f"{schema_version}. Ожидается {SNAPSHOT_SCHEMA_VERSION}."
        )

    app_version = _require_key(metadata, "app_version", "metadata")
    if not isinstance(app_version, str) or not app_version.strip():
        raise ValueError("Некорректное значение metadata.app_version.")
    if app_version != settings.VERSION:
        raise ValueError(
            f"Версия приложения в snapshot ({app_version}) не поддерживается для импорта "
            f"в текущую версию ({settings.VERSION})."
        )

    created_at = _require_key(metadata, "created_at", "metadata")
    if not isinstance(created_at, str):
        raise ValueError("Некорректное значение metadata.created_at.")
    try:
        datetime.fromisoformat(created_at)
    except ValueError as exc:
        raise ValueError(
            "Некорректный формат metadata.created_at. Ожидается ISO datetime."
        ) from exc


def _parse_column_value(table_name: str, column: Any, raw_value: Any, row_index: int) -> Any:
    column_name = column.name
    location = f"{table_name}[{row_index}].{column_name}"

    if raw_value is None:
        if column.nullable:
            return None
        raise ValueError(f"Поле {location} не может быть null.")

    column_type = column.type

    if isinstance(column_type, Numeric):
        if not isinstance(raw_value, str):
            raise ValueError(f"Поле {location} должно быть строкой для Decimal.")
        try:
            return Decimal(raw_value)
        except InvalidOperation as exc:
            raise ValueError(f"Некорректный Decimal в поле {location}: {raw_value}") from exc

    if isinstance(column_type, DateTime):
        if not isinstance(raw_value, str):
            raise ValueError(f"Поле {location} должно быть строкой ISO datetime.")
        try:
            return datetime.fromisoformat(raw_value)
        except ValueError as exc:
            raise ValueError(f"Некорректный datetime в поле {location}: {raw_value}") from exc

    if isinstance(column_type, Date):
        if not isinstance(raw_value, str):
            raise ValueError(f"Поле {location} должно быть строкой ISO date.")
        try:
            return date.fromisoformat(raw_value)
        except ValueError as exc:
            raise ValueError(f"Некорректный date в поле {location}: {raw_value}") from exc

    if isinstance(column_type, SQLEnum):
        if not isinstance(raw_value, str):
            raise ValueError(f"Поле {location} должно быть строковым enum значением.")
        enum_class = column_type.enum_class
        if enum_class is None:
            raise ValueError(f"Некорректная enum конфигурация для поля {location}.")
        try:
            return enum_class(raw_value)
        except ValueError as exc:
            raise ValueError(f"Некорректное enum значение в поле {location}: {raw_value}") from exc

    if isinstance(column_type, Boolean):
        if not isinstance(raw_value, bool):
            raise ValueError(f"Поле {location} должно быть bool.")
        return raw_value

    if isinstance(column_type, Integer):
        if isinstance(raw_value, bool) or not isinstance(raw_value, int):
            raise ValueError(f"Поле {location} должно быть int.")
        return raw_value

    if isinstance(column_type, String):
        if not isinstance(raw_value, str):
            raise ValueError(f"Поле {location} должно быть строкой.")
        return raw_value

    return raw_value


def _parse_table_payload(table_name: str, records: Any) -> list[dict[str, Any]]:
    if not isinstance(records, list):
        raise ValueError(f"Поле {table_name} должно быть списком.")

    model = SNAPSHOT_MODEL_MAP[table_name]
    parsed_records: list[dict[str, Any]] = []

    for row_index, row_payload in enumerate(records):
        if not isinstance(row_payload, dict):
            raise ValueError(f"Элемент {table_name}[{row_index}] должен быть объектом.")

        parsed_row: dict[str, Any] = {}
        for column in model.__table__.columns:
            if column.name in row_payload:
                raw_value = row_payload[column.name]
            elif column.nullable:
                raw_value = None
            else:
                raise ValueError(
                    f"Отсутствует обязательное поле {table_name}[{row_index}].{column.name}"
                )

            parsed_value = _parse_column_value(
                table_name=table_name,
                column=column,
                raw_value=raw_value,
                row_index=row_index,
            )
            parsed_row[column.name] = parsed_value

            if column.name == "id" or column.name.endswith("_id"):
                if parsed_value is None:
                    continue
                if not isinstance(parsed_value, str):
                    raise ValueError(
                        f"Поле {table_name}[{row_index}].{column.name} должно быть UUID строкой."
                    )
                validate_uuid_format(parsed_value, f"{table_name}.{column.name}")

        parsed_records.append(parsed_row)

    seen_ids: set[str] = set()
    for row in parsed_records:
        row_id = row.get("id")
        if row_id in seen_ids:
            raise ValueError(f"Найден дубликат id в таблице {table_name}: {row_id}")
        if row_id is not None:
            seen_ids.add(row_id)

    return parsed_records


def _validate_foreign_keys(parsed_tables: dict[str, list[dict[str, Any]]]) -> None:
    ids_by_table: dict[str, set[str]] = {
        table_name: {row["id"] for row in rows if row.get("id") is not None}
        for table_name, rows in parsed_tables.items()
    }

    for table_name, model in SNAPSHOT_TABLES:
        rows = parsed_tables[table_name]
        for row_index, row in enumerate(rows):
            for column in model.__table__.columns:
                for foreign_key in column.foreign_keys:
                    local_value = row[column.name]
                    if local_value is None:
                        continue

                    referenced_table = foreign_key.column.table.name
                    referenced_column = foreign_key.column.name
                    if referenced_column != "id":
                        continue

                    if local_value not in ids_by_table[referenced_table]:
                        raise ValueError(
                            f"FK ссылка {table_name}[{row_index}].{column.name}={local_value} "
                            f"не найдена в {referenced_table}.id"
                        )


def _validate_category_parent_links(parsed_tables: dict[str, list[dict[str, Any]]]) -> None:
    categories = parsed_tables[CategoryDB.__tablename__]
    parent_by_id: dict[str, str | None] = {row["id"]: row.get("parent_id") for row in categories}

    for row_index, row in enumerate(categories):
        parent_id = row.get("parent_id")
        if parent_id is None:
            continue
        if parent_id not in parent_by_id:
            raise ValueError(
                f"Неразрешимая parent ссылка categories[{row_index}].parent_id={parent_id}"
            )

    visit_state: dict[str, int] = {}

    def _visit(category_id: str) -> None:
        state = visit_state.get(category_id, 0)
        if state == 1:
            raise ValueError(
                f"Неразрешимая parent ссылка: обнаружен цикл категорий с id={category_id}"
            )
        if state == 2:
            return

        visit_state[category_id] = 1
        parent_id = parent_by_id.get(category_id)
        if parent_id is not None:
            _visit(parent_id)
        visit_state[category_id] = 2

    for category_id in parent_by_id:
        _visit(category_id)


def _validate_and_parse_snapshot(
    snapshot_payload: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    metadata = _require_key(snapshot_payload, "metadata", "snapshot")
    _validate_metadata(metadata)

    parsed_tables: dict[str, list[dict[str, Any]]] = {}
    for table_name, _ in SNAPSHOT_TABLES:
        records = _require_key(snapshot_payload, table_name, "snapshot")
        parsed_tables[table_name] = _parse_table_payload(table_name=table_name, records=records)

    _validate_category_parent_links(parsed_tables)
    _validate_foreign_keys(parsed_tables)
    return parsed_tables


def _ensure_restore_only_state(session: Session) -> None:
    violations: list[str] = []

    non_system_categories = (
        session.query(CategoryDB).filter(CategoryDB.is_system.is_(False)).count()
    )
    if non_system_categories > 0:
        violations.append(f"categories(non_system)={non_system_categories}")

    for table_name, model in SNAPSHOT_TABLES:
        if model is CategoryDB:
            continue
        row_count = session.query(model).count()
        if row_count > 0:
            violations.append(f"{table_name}={row_count}")

    if violations:
        joined = ", ".join(violations)
        raise ValidationError(
            "Restore-only импорт разрешен только для пустых пользовательских данных. "
            f"Обнаружены записи: {joined}"
        )


def _clear_current_data(session: Session) -> None:
    for model in DELETE_ORDER:
        session.query(model).delete(synchronize_session=False)


def _insert_snapshot_data(
    session: Session,
    parsed_tables: dict[str, list[dict[str, Any]]],
) -> dict[str, int]:
    report = dict(REPORT_TEMPLATE)

    deferred_category_links: list[tuple[CategoryDB, str]] = []
    category_ids: set[str] = set()
    for row in parsed_tables[CategoryDB.__tablename__]:
        row_payload = dict(row)
        parent_id = row_payload.pop("parent_id", None)
        category_id = row_payload.get("id")
        if not isinstance(category_id, str):
            raise ValueError("Неразрешимая parent ссылка categories.id")
        category = CategoryDB(**row_payload)
        session.add(category)
        report["added"] += 1
        category_ids.add(category_id)
        if parent_id is not None:
            deferred_category_links.append((category, parent_id))

    session.flush()

    for category, parent_id in deferred_category_links:
        if parent_id not in category_ids:
            raise ValueError(f"Неразрешимая parent ссылка categories.parent_id={parent_id}")
        setattr(category, "parent_id", parent_id)

    session.flush()

    deferred_occurrence_links: list[tuple[PlannedOccurrenceDB, str]] = []

    for model in IMPORT_ORDER:
        if model is CategoryDB:
            continue

        table_name = model.__tablename__
        for row in parsed_tables[table_name]:
            row_payload = dict(row)
            if model is PlannedOccurrenceDB:
                actual_transaction_id = row_payload.pop("actual_transaction_id", None)
                occurrence = PlannedOccurrenceDB(**row_payload)
                session.add(occurrence)
                if actual_transaction_id is not None:
                    deferred_occurrence_links.append((occurrence, actual_transaction_id))
            else:
                session.add(model(**row_payload))
            report["added"] += 1

    for occurrence, actual_transaction_id in deferred_occurrence_links:
        setattr(occurrence, "actual_transaction_id", actual_transaction_id)

    return report


def _import_snapshot(session: Session, filepath: str) -> dict[str, int]:
    try:
        logger.info(
            "Snapshot import started",
            extra=_snapshot_import_extra(filepath=filepath, status="start"),
        )

        snapshot_payload = _load_snapshot(filepath)
        parsed_tables = _validate_and_parse_snapshot(snapshot_payload)
        _ensure_restore_only_state(session)

        _clear_current_data(session)
        report = _insert_snapshot_data(session=session, parsed_tables=parsed_tables)
        session.commit()

        logger.info(
            "Snapshot import succeeded",
            extra=_snapshot_import_extra(
                filepath=filepath,
                status="success",
                added=report["added"],
                skipped=report["skipped"],
                conflicts=report["conflicts"],
            ),
        )
        return report
    except ValidationError as exc:
        session.rollback()
        logger.warning(
            "Snapshot import blocked by restore-only guard",
            extra=_snapshot_import_extra(
                filepath=filepath,
                status="failure",
                error_type=type(exc).__name__,
            ),
        )
        raise
    except ValueError as exc:
        session.rollback()
        logger.warning(
            "Snapshot import failed validation",
            extra=_snapshot_import_extra(
                filepath=filepath,
                status="failure",
                error_type=type(exc).__name__,
            ),
        )
        raise
    except SQLAlchemyError as exc:
        session.rollback()
        logger.error(
            "Snapshot import failed with SQLAlchemy error",
            extra=_snapshot_import_extra(
                filepath=filepath,
                status="failure",
                error_type=type(exc).__name__,
            ),
        )
        raise DatabaseError(ROLLBACK_ERROR_MESSAGE) from exc
    except (TypeError, RuntimeError, AttributeError) as exc:
        session.rollback()
        logger.error(
            "Snapshot import failed with runtime error",
            extra=_snapshot_import_extra(
                filepath=filepath,
                status="failure",
                error_type=type(exc).__name__,
            ),
        )
        raise DatabaseError(ROLLBACK_ERROR_MESSAGE) from exc


class ImportService:
    @staticmethod
    def import_from_file(filepath: str, *, _session: Session | None = None) -> dict[str, int]:
        try:
            if _session is not None:
                return _import_snapshot(session=_session, filepath=filepath)

            with get_db_session() as session:
                return _import_snapshot(session=session, filepath=filepath)
        except (ValidationError, DatabaseError) as exc:
            raise ValueError(str(exc)) from exc

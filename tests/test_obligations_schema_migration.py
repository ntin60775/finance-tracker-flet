import sqlite3

import finance_tracker.database as database
from finance_tracker.config import settings


def _create_legacy_schema(db_path: str) -> tuple[str, str, str]:
    category_id = "11111111-1111-1111-1111-111111111111"
    planned_id = "22222222-2222-2222-2222-222222222222"
    transaction_id = "33333333-3333-3333-3333-333333333333"

    connection = sqlite3.connect(db_path)
    try:
        cursor = connection.cursor()
        cursor.executescript(
            """
            CREATE TABLE categories (
                id VARCHAR(36) PRIMARY KEY,
                name VARCHAR NOT NULL UNIQUE,
                type VARCHAR NOT NULL,
                is_system BOOLEAN,
                created_at DATETIME,
                updated_at DATETIME
            );

            CREATE TABLE planned_transactions (
                id VARCHAR(36) PRIMARY KEY,
                amount NUMERIC(10, 2) NOT NULL,
                category_id VARCHAR(36) NOT NULL,
                description VARCHAR,
                type VARCHAR NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE,
                is_active BOOLEAN,
                created_at DATETIME,
                updated_at DATETIME
            );

            CREATE TABLE transactions (
                id VARCHAR(36) PRIMARY KEY,
                amount NUMERIC(10, 2) NOT NULL,
                type VARCHAR NOT NULL,
                category_id VARCHAR(36) NOT NULL,
                description VARCHAR,
                transaction_date DATE NOT NULL,
                planned_occurrence_id VARCHAR(36),
                created_at DATETIME,
                updated_at DATETIME
            );
            """
        )

        cursor.execute(
            """
            INSERT INTO categories (id, name, type, is_system, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (category_id, "Legacy", "EXPENSE", 0, "2026-01-01 00:00:00", "2026-01-01 00:00:00"),
        )
        cursor.execute(
            """
            INSERT INTO planned_transactions (
                id, amount, category_id, description, type, start_date, end_date, is_active, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                planned_id,
                "1200.00",
                category_id,
                "legacy planned",
                "EXPENSE",
                "2026-01-01",
                None,
                1,
                "2026-01-01 00:00:00",
                "2026-01-01 00:00:00",
            ),
        )
        cursor.execute(
            """
            INSERT INTO transactions (
                id, amount, type, category_id, description, transaction_date, planned_occurrence_id, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                transaction_id,
                "1200.00",
                "EXPENSE",
                category_id,
                "legacy tx",
                "2026-01-02",
                None,
                "2026-01-02 00:00:00",
                "2026-01-02 00:00:00",
            ),
        )
        connection.commit()
    finally:
        connection.close()

    return category_id, planned_id, transaction_id


def _get_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row[1] for row in rows}


def test_init_db_migrates_obligations_columns_for_existing_db(monkeypatch, tmp_path):
    db_path = tmp_path / "legacy_finance.db"
    _, planned_id, transaction_id = _create_legacy_schema(str(db_path))

    original_db_path = settings.db_path
    database.close_db()
    monkeypatch.setattr(settings, "db_path", str(db_path))

    try:
        database.init_db()
        database.close_db()
        database.init_db()
    finally:
        database.close_db()
        monkeypatch.setattr(settings, "db_path", original_db_path)

    connection = sqlite3.connect(str(db_path))
    try:
        planned_columns = _get_columns(connection, "planned_transactions")
        transaction_columns = _get_columns(connection, "transactions")

        assert "parent_planned_transaction_id" in planned_columns
        assert "is_obligation" in planned_columns
        assert "target_amount" in planned_columns
        assert "target_month" in planned_columns
        assert "obligation_id" in transaction_columns

        planned_row = connection.execute(
            """
            SELECT parent_planned_transaction_id, is_obligation, target_amount, target_month
            FROM planned_transactions
            WHERE id = ?
            """,
            (planned_id,),
        ).fetchone()
        transaction_row = connection.execute(
            "SELECT obligation_id FROM transactions WHERE id = ?",
            (transaction_id,),
        ).fetchone()

        assert planned_row[0] is None
        assert planned_row[1] == 0
        assert planned_row[2] is None
        assert planned_row[3] is None
        assert transaction_row[0] is None

        planned_count = connection.execute("SELECT COUNT(*) FROM planned_transactions").fetchone()[
            0
        ]
        transaction_count = connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        assert planned_count == 1
        assert transaction_count == 1
    finally:
        connection.close()

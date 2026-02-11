import json
import logging

from finance_tracker.utils.logger import JsonFormatter


def test_formatter_adds_planned_transaction_delete_journal_fields():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Плановая транзакция ID tx-123 удалена",
        args=(),
        exc_info=None,
    )

    payload = json.loads(formatter.format(record))

    assert payload["event_type"] == "domain_journal"
    assert payload["operation"] == "planned_transaction_delete"
    assert payload["entity"] == "planned_transaction"
    assert payload["entity_id"] == "tx-123"
    assert payload["status"] == "success"


def test_formatter_adds_journal_fields_for_service_delete_message():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=30,
        msg="Удалена плановая транзакция ID tx-777, с сохранением фактических транзакций",
        args=(),
        exc_info=None,
    )

    payload = json.loads(formatter.format(record))

    assert payload["event_type"] == "domain_journal"
    assert payload["operation"] == "planned_transaction_delete"
    assert payload["entity"] == "planned_transaction"
    assert payload["entity_id"] == "tx-777"
    assert payload["status"] == "success"

"""Сервис импорта данных из файлов.

Публичный API сохранен, но полноценная реализация импорта
запланирована отдельной задачей.
"""

from finance_tracker.utils.logger import get_logger

logger = get_logger(__name__)

EXPORT_IMPORT_ISSUE_URL = "https://github.com/ntin60775/finance-tracker-flet/issues/4"


class ImportService:
    """API импорта данных приложения."""

    @staticmethod
    def import_from_file(filepath: str) -> dict[str, int]:
        """Импорт временно недоступен.

        Args:
            filepath: Сигнатура сохранена для совместимости API.

        Raises:
            NotImplementedError: Полная реализация не завершена.
        """
        _ = filepath
        message = (
            "Импорт данных временно недоступен. "
            f"Реализация запланирована: {EXPORT_IMPORT_ISSUE_URL}"
        )
        logger.warning(message)
        raise NotImplementedError(message)

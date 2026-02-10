"""Сервис экспорта данных в файлы.

Публичный API сохранен, но полноценная реализация экспорта
запланирована отдельной задачей.
"""

from finance_tracker.utils.logger import get_logger

logger = get_logger(__name__)

EXPORT_IMPORT_ISSUE_URL = "https://github.com/ntin60775/finance-tracker-flet/issues/4"


class ExportService:
    """API экспорта данных приложения."""

    @staticmethod
    def export_to_file(filepath: str | None = None) -> str:
        """Экспорт временно недоступен.

        Args:
            filepath: Сигнатура сохранена для совместимости API.

        Raises:
            NotImplementedError: Полная реализация не завершена.
        """
        _ = filepath
        message = (
            "Экспорт данных временно недоступен. "
            f"Реализация запланирована: {EXPORT_IMPORT_ISSUE_URL}"
        )
        logger.warning(message)
        raise NotImplementedError(message)

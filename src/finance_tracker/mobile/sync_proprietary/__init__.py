"""
Приватный модуль расширенной синхронизации.

Доступен только при наличии лицензии.
Этот модуль предназначен для подключения через Git submodule.
"""


EXPORT_IMPORT_ISSUE_URL = "https://github.com/ntin60775/finance-tracker-flet/issues/4"


class CloudSyncService:
    """
    Заглушка для облачной синхронизации.
    
    Реальная реализация доступна только в расширенной версии приложения
    через приватный Git submodule.
    """
    
    def __init__(self):
        raise NotImplementedError(
            "CloudSyncService доступен только в расширенной версии. "
            + f"Трекер реализации открытых backup API: {EXPORT_IMPORT_ISSUE_URL}"
        )


class RealtimeSyncService:
    """
    Заглушка для real-time синхронизации.
    
    Реальная реализация доступна только в расширенной версии приложения
    через приватный Git submodule.
    """
    
    def __init__(self):
        raise NotImplementedError(
            "RealtimeSyncService доступен только в расширенной версии. "
            + f"Трекер реализации открытых backup API: {EXPORT_IMPORT_ISSUE_URL}"
        )


__all__ = ["CloudSyncService", "RealtimeSyncService"]

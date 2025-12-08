"""
Приватный модуль расширенной синхронизации.

Доступен только при наличии лицензии.
Этот модуль предназначен для подключения через Git submodule.
"""


class CloudSyncService:
    """
    Заглушка для облачной синхронизации.
    
    Реальная реализация доступна только в расширенной версии приложения
    через приватный Git submodule.
    """
    
    def __init__(self):
        raise NotImplementedError(
            "CloudSyncService доступен только в расширенной версии. "
            "Используйте ExportService/ImportService для базового функционала."
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
            "Используйте ExportService/ImportService для базового функционала."
        )


__all__ = ["CloudSyncService", "RealtimeSyncService"]

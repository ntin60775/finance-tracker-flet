"""
Модуль мобильного функционала.

Содержит:
- Публичный API: экспорт/импорт (реализация запланирована)
- Приватный функционал (опционально): облачная синхронизация
"""

# Публичный функционал (всегда доступен)
from finance_tracker.mobile.export_service import ExportService
from finance_tracker.mobile.import_service import ImportService

def _load_proprietary_services():
    """Ленивая загрузка приватного submodule с безопасным fallback."""
    try:
        from finance_tracker.mobile.sync_proprietary import CloudSyncService, RealtimeSyncService
        return CloudSyncService, RealtimeSyncService, True
    except ImportError:
        return None, None, False


# Приватный функционал (доступен только если submodule установлен)
CloudSyncService, RealtimeSyncService, PROPRIETARY_AVAILABLE = _load_proprietary_services()

__all__ = [
    "ExportService",
    "ImportService",
    "CloudSyncService",
    "RealtimeSyncService",
    "PROPRIETARY_AVAILABLE",
]

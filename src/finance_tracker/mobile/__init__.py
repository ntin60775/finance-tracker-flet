"""
Модуль мобильного функционала.

Содержит:
- Публичный функционал: экспорт/импорт в файлы
- Приватный функционал (опционально): облачная синхронизация
"""

# Публичный функционал будет добавлен позже
# from finance_tracker.mobile.export_service import ExportService
# from finance_tracker.mobile.import_service import ImportService

# Приватный функционал (доступен только если submodule установлен)
try:
    from finance_tracker.mobile.sync_proprietary import CloudSyncService, RealtimeSyncService
    PROPRIETARY_AVAILABLE = True
except ImportError:
    # Заглушки для работы без приватного модуля
    CloudSyncService = None
    RealtimeSyncService = None
    PROPRIETARY_AVAILABLE = False

__all__ = [
    # "ExportService",
    # "ImportService",
    "CloudSyncService",
    "RealtimeSyncService",
    "PROPRIETARY_AVAILABLE",
]

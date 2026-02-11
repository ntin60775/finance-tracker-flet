"""Тесты публичного mobile API без приватного submodule."""

import pytest

from finance_tracker import mobile as finance_mobile
from finance_tracker.mobile import (
    CloudSyncService,
    ExportService,
    ImportService,
    PROPRIETARY_AVAILABLE,
    RealtimeSyncService,
)

ISSUE_MARKER = "issues/4"


class TestMobileModuleImport:
    """Базовые проверки импорта mobile-модуля."""

    def test_module_imports_successfully(self):
        assert finance_mobile is not None

    def test_export_service_available(self):
        assert ExportService is not None
        assert hasattr(ExportService, "export_to_file")

    def test_import_service_available(self):
        assert ImportService is not None
        assert hasattr(ImportService, "import_from_file")

    def test_proprietary_available_flag_is_boolean(self):
        assert isinstance(PROPRIETARY_AVAILABLE, bool)


class TestExportImportAvailability:
    """Экспорт/импорт доступны, но требуют инициализированную БД."""

    def test_export_requires_initialized_db(self):
        with pytest.raises(RuntimeError, match="не инициализирована"):
            ExportService.export_to_file()

    def test_import_requires_initialized_db(self):
        with pytest.raises(RuntimeError, match="не инициализирована"):
            ImportService.import_from_file("backup.json")


class TestProprietaryServicesStubs:
    """Поведение заглушек приватного submodule."""

    def test_cloud_sync_service_raises_not_implemented(self):
        if CloudSyncService is None:
            pytest.skip("CloudSyncService is None (without submodule)")

        with pytest.raises(NotImplementedError, match=ISSUE_MARKER):
            CloudSyncService()

    def test_realtime_sync_service_raises_not_implemented(self):
        if RealtimeSyncService is None:
            pytest.skip("RealtimeSyncService is None (without submodule)")

        with pytest.raises(NotImplementedError, match=ISSUE_MARKER):
            RealtimeSyncService()

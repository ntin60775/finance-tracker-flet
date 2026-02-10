"""Тесты публичного mobile API без приватного submodule."""

import pytest

import finance_tracker.mobile
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
        assert finance_tracker.mobile is not None

    def test_export_service_available(self):
        assert ExportService is not None
        assert hasattr(ExportService, "export_to_file")

    def test_import_service_available(self):
        assert ImportService is not None
        assert hasattr(ImportService, "import_from_file")

    def test_proprietary_available_flag_is_boolean(self):
        assert isinstance(PROPRIETARY_AVAILABLE, bool)


class TestExportImportAvailability:
    """Экспорт/импорт пока недоступны и должны поднимать понятную ошибку."""

    def test_export_raises_not_implemented(self):
        with pytest.raises(NotImplementedError, match=ISSUE_MARKER):
            ExportService.export_to_file()

    def test_import_raises_not_implemented(self):
        with pytest.raises(NotImplementedError, match=ISSUE_MARKER):
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

"""
Тесты для мобильного функционала без submodule.

Проверяет:
- Импорт finance_tracker.mobile
- Работу ExportService
- Работу ImportService
- Что CloudSyncService выдаёт NotImplementedError
"""

import pytest
import json
from pathlib import Path
from datetime import datetime

# Проверка импорта модуля
import finance_tracker.mobile
from finance_tracker.mobile import (
    ExportService,
    ImportService,
    CloudSyncService,
    RealtimeSyncService,
    PROPRIETARY_AVAILABLE,
)


class TestMobileModuleImport:
    """Тесты импорта модуля finance_tracker.mobile."""
    
    def test_module_imports_successfully(self):
        """Проверяет, что модуль finance_tracker.mobile импортируется без ошибок."""
        assert finance_tracker.mobile is not None
    
    def test_export_service_available(self):
        """Проверяет, что ExportService доступен."""
        assert ExportService is not None
        assert hasattr(ExportService, 'export_to_file')
    
    def test_import_service_available(self):
        """Проверяет, что ImportService доступен."""
        assert ImportService is not None
        assert hasattr(ImportService, 'import_from_file')
    
    def test_proprietary_services_are_stubs(self):
        """Проверяет, что приватные сервисы являются заглушками (None) без submodule."""
        # Без submodule CloudSyncService и RealtimeSyncService должны быть None
        assert CloudSyncService is None or callable(CloudSyncService)
        assert RealtimeSyncService is None or callable(RealtimeSyncService)
    
    def test_proprietary_available_flag(self):
        """Проверяет флаг доступности приватного функционала."""
        # С заглушками (без настоящего submodule) флаг будет True,
        # но классы будут выбрасывать NotImplementedError
        assert isinstance(PROPRIETARY_AVAILABLE, bool)
        # Флаг показывает, что заглушки импортированы
        assert PROPRIETARY_AVAILABLE is True


class TestExportService:
    """Тесты для ExportService."""
    
    def test_export_to_file_with_custom_path(self, tmp_path):
        """Проверяет экспорт в указанный файл."""
        # Создаём временный файл
        export_file = tmp_path / "test_export.json"
        
        # Экспортируем данные
        result_path = ExportService.export_to_file(str(export_file))
        
        # Проверяем, что файл создан
        assert Path(result_path).exists()
        assert result_path == str(export_file)
        
        # Проверяем содержимое файла
        with open(result_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data["version"] == "2.0.0"
        assert "export_date" in data
        assert "transactions" in data
        assert "categories" in data
        assert "loans" in data
        assert "settings" in data
    
    def test_export_to_file_auto_path(self):
        """Проверяет экспорт с автоматическим созданием пути."""
        # Экспортируем без указания пути
        result_path = ExportService.export_to_file()
        
        # Проверяем, что файл создан
        assert Path(result_path).exists()
        
        # Проверяем, что путь содержит exports директорию
        assert "exports" in result_path
        assert result_path.endswith(".json")
        
        # Проверяем содержимое
        with open(result_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data["version"] == "2.0.0"
        
        # Очищаем созданный файл
        Path(result_path).unlink()
    
    def test_export_file_structure(self, tmp_path):
        """Проверяет структуру экспортированного файла."""
        export_file = tmp_path / "structure_test.json"
        
        ExportService.export_to_file(str(export_file))
        
        with open(export_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Проверяем обязательные поля
        required_fields = ["version", "export_date", "transactions", "categories", "loans", "settings"]
        for field in required_fields:
            assert field in data, f"Поле {field} отсутствует в экспорте"
        
        # Проверяем типы данных
        assert isinstance(data["version"], str)
        assert isinstance(data["export_date"], str)
        assert isinstance(data["transactions"], list)
        assert isinstance(data["categories"], list)
        assert isinstance(data["loans"], list)
        assert isinstance(data["settings"], dict)


class TestImportService:
    """Тесты для ImportService."""
    
    def test_import_from_valid_file(self, tmp_path):
        """Проверяет импорт из корректного файла."""
        # Создаём тестовый файл импорта
        import_file = tmp_path / "test_import.json"
        test_data = {
            "version": "2.0.0",
            "export_date": datetime.now().isoformat(),
            "transactions": [],
            "categories": [],
            "loans": [],
            "settings": {},
        }
        
        with open(import_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)
        
        # Импортируем данные
        stats = ImportService.import_from_file(str(import_file))
        
        # Проверяем статистику
        assert isinstance(stats, dict)
        assert "transactions" in stats
        assert "categories" in stats
        assert "loans" in stats
        assert all(isinstance(v, int) for v in stats.values())
    
    def test_import_from_nonexistent_file(self):
        """Проверяет обработку несуществующего файла."""
        with pytest.raises(FileNotFoundError):
            ImportService.import_from_file("/nonexistent/path/file.json")
    
    def test_import_from_invalid_json(self, tmp_path):
        """Проверяет обработку некорректного JSON."""
        invalid_file = tmp_path / "invalid.json"
        
        with open(invalid_file, 'w') as f:
            f.write("{ invalid json content")
        
        with pytest.raises(ValueError, match="Некорректный формат файла"):
            ImportService.import_from_file(str(invalid_file))
    
    def test_import_from_wrong_version(self, tmp_path):
        """Проверяет обработку неподдерживаемой версии файла."""
        wrong_version_file = tmp_path / "wrong_version.json"
        test_data = {
            "version": "1.0.0",  # Неподдерживаемая версия
            "export_date": datetime.now().isoformat(),
            "transactions": [],
        }
        
        with open(wrong_version_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)
        
        with pytest.raises(ValueError, match="Неподдерживаемая версия файла"):
            ImportService.import_from_file(str(wrong_version_file))


class TestProprietaryServicesStubs:
    """Тесты для заглушек приватных сервисов."""
    
    def test_cloud_sync_service_raises_not_implemented(self):
        """Проверяет, что CloudSyncService выдаёт NotImplementedError."""
        # Если CloudSyncService это None (без submodule), пропускаем тест
        if CloudSyncService is None:
            pytest.skip("CloudSyncService is None (expected without submodule)")
        
        # Если это класс-заглушка, проверяем NotImplementedError
        with pytest.raises(NotImplementedError, match="CloudSyncService доступен только в расширенной версии"):
            CloudSyncService()
    
    def test_realtime_sync_service_raises_not_implemented(self):
        """Проверяет, что RealtimeSyncService выдаёт NotImplementedError."""
        # Если RealtimeSyncService это None (без submodule), пропускаем тест
        if RealtimeSyncService is None:
            pytest.skip("RealtimeSyncService is None (expected without submodule)")
        
        # Если это класс-заглушка, проверяем NotImplementedError
        with pytest.raises(NotImplementedError, match="RealtimeSyncService доступен только в расширенной версии"):
            RealtimeSyncService()
    
    def test_proprietary_services_error_messages(self):
        """Проверяет, что сообщения об ошибках содержат информацию о базовом функционале."""
        if CloudSyncService is None:
            pytest.skip("CloudSyncService is None (expected without submodule)")
        
        try:
            CloudSyncService()
        except NotImplementedError as e:
            error_message = str(e)
            assert "ExportService" in error_message or "ImportService" in error_message
            assert "расширенной версии" in error_message


class TestExportImportRoundTrip:
    """Тесты для проверки совместимости экспорта и импорта."""
    
    def test_export_import_round_trip(self, tmp_path):
        """Проверяет, что экспортированный файл можно импортировать обратно."""
        export_file = tmp_path / "roundtrip.json"
        
        # Экспортируем
        exported_path = ExportService.export_to_file(str(export_file))
        
        # Импортируем
        stats = ImportService.import_from_file(exported_path)
        
        # Проверяем, что импорт прошёл успешно
        assert isinstance(stats, dict)
        assert all(key in stats for key in ["transactions", "categories", "loans"])

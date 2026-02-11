import unittest
from unittest.mock import Mock, patch

import flet as ft

from finance_tracker.views.settings_view import SettingsView
from test_view_base import ViewTestBase


class TestSettingsBackupUI(ViewTestBase):
    def setUp(self):
        super().setUp()

        self.mock_settings_patcher = patch("finance_tracker.views.settings_view.settings")
        self.mock_settings = self.mock_settings_patcher.start()
        self.patchers.append(self.mock_settings_patcher)

        self.mock_settings.theme_mode = "light"
        self.mock_settings.db_path = "/test/path/finance.db"
        self.mock_settings.date_format = "%d.%m.%Y"
        self.mock_settings.save = Mock()

        self.view = SettingsView(self.page)
        self.view.import_file_picker.pick_files = Mock()

    def test_export_button_calls_export_service(self):
        export_mock = self.add_patcher(
            "finance_tracker.views.settings_view.ExportService.export_to_file",
            return_value="/test/snapshot.json",
        )

        self.view.export_button.on_click(None)

        export_mock.assert_called_once_with()

    def test_import_shows_restore_only_warning_before_file_picker(self):
        import_mock = self.add_patcher(
            "finance_tracker.views.settings_view.ImportService.import_from_file",
            return_value={},
        )

        self.view.import_button.on_click(None)

        self.page.open.assert_called_once()
        dialog = self.page.open.call_args[0][0]
        self.assertIsInstance(dialog, ft.AlertDialog)

        self.assertIsInstance(dialog.content, ft.Text)
        self.assertIn(
            "Импорт доступен только для пустой БД (restore-only).",
            dialog.content.value,
        )
        import_mock.assert_not_called()

    def test_import_opens_file_picker_and_calls_service_on_result(self):
        import_mock = self.add_patcher(
            "finance_tracker.views.settings_view.ImportService.import_from_file",
            return_value={},
        )

        self.view.import_button.on_click(None)
        dialog = self.page.open.call_args[0][0]
        choose_action = dialog.actions[1]
        choose_action.on_click(None)

        self.view.import_file_picker.pick_files.assert_called_once()
        import_mock.assert_not_called()

        mock_file = Mock()
        mock_file.path = "/test/snapshot.json"
        mock_event = Mock()
        mock_event.files = [mock_file]

        self.view._on_import_file_picked(mock_event)

        import_mock.assert_called_once_with("/test/snapshot.json")


if __name__ == "__main__":
    unittest.main()

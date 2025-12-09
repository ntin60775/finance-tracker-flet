"""
Тесты для SettingsView.

Проверяет:
- Инициализацию View
- Загрузку текущих настроек
- Изменение темы
- Изменение формата даты
- Сохранение настроек
"""
import unittest
from unittest.mock import Mock, patch
import flet as ft

from finance_tracker.views.settings_view import SettingsView
from test_view_base import ViewTestBase


class TestSettingsView(ViewTestBase):
    """Тесты для SettingsView."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        super().setUp()
        
        # Патчим settings для изоляции тестов
        self.mock_settings_patcher = patch('finance_tracker.views.settings_view.settings')
        self.mock_settings = self.mock_settings_patcher.start()
        self.patchers.append(self.mock_settings_patcher)
        
        # Настраиваем значения по умолчанию для settings
        self.mock_settings.theme_mode = "light"
        self.mock_settings.db_path = "/test/path/finance.db"
        self.mock_settings.date_format = "%d.%m.%Y"
        self.mock_settings.save = Mock()
        
        # Создаем экземпляр SettingsView
        self.view = SettingsView(self.page)

    def test_initialization(self):
        """
        Тест инициализации SettingsView.
        
        Проверяет:
        - View создается без исключений
        - Атрибут page установлен
        - UI компоненты созданы (заголовок, dropdown'ы, кнопки)
        
        Validates: Requirements 13.1
        """
        # Проверяем, что View создан
        self.assertIsInstance(self.view, SettingsView)
        
        # Проверяем атрибуты
        self.assertEqual(self.view.page, self.page)
        
        # Проверяем, что UI компоненты созданы
        self.assert_view_has_controls(self.view)
        self.assertIsNotNone(self.view.header)
        self.assertIsNotNone(self.view.theme_dropdown)
        self.assertIsNotNone(self.view.db_path_field)
        self.assertIsNotNone(self.view.date_format_dropdown)
        self.assertIsNotNone(self.view.save_button)

    def test_load_current_settings(self):
        """
        Тест загрузки текущих настроек.
        
        Проверяет:
        - При инициализации значения контролов устанавливаются из settings
        - theme_dropdown содержит текущую тему
        - db_path_field содержит текущий путь к БД
        - date_format_dropdown содержит текущий формат даты
        
        Validates: Requirements 13.1
        """
        # Проверяем, что значения загружены из settings
        self.assertEqual(self.view.theme_dropdown.value, "light")
        self.assertEqual(self.view.db_path_field.value, "/test/path/finance.db")
        self.assertEqual(self.view.date_format_dropdown.value, "%d.%m.%Y")

    def test_load_settings_with_dark_theme(self):
        """
        Тест загрузки настроек с тёмной темой.
        
        Проверяет:
        - При инициализации с тёмной темой dropdown показывает "dark"
        
        Validates: Requirements 13.1
        """
        # Настраиваем settings на тёмную тему
        self.mock_settings.theme_mode = "dark"
        
        # Создаем новый экземпляр View
        view = SettingsView(self.page)
        
        # Проверяем, что тема загружена
        self.assertEqual(view.theme_dropdown.value, "dark")

    def test_change_theme_to_dark(self):
        """
        Тест изменения темы на тёмную.
        
        Проверяет:
        - При изменении dropdown на "dark" вызывается обновление темы
        - settings.theme_mode устанавливается в "dark"
        - page.theme_mode устанавливается в ThemeMode.DARK
        - page.update() вызывается для применения изменений
        
        Validates: Requirements 13.2
        """
        # Имитируем изменение темы
        self.view.theme_dropdown.value = "dark"
        self.view._on_theme_changed(None)
        
        # Проверяем, что settings обновлён
        self.assertEqual(self.mock_settings.theme_mode, "dark")
        
        # Проверяем, что page.theme_mode установлен
        self.assertEqual(self.page.theme_mode, ft.ThemeMode.DARK)
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)

    def test_change_theme_to_light(self):
        """
        Тест изменения темы на светлую.
        
        Проверяет:
        - При изменении dropdown на "light" вызывается обновление темы
        - settings.theme_mode устанавливается в "light"
        - page.theme_mode устанавливается в ThemeMode.LIGHT
        - page.update() вызывается для применения изменений
        
        Validates: Requirements 13.2
        """
        # Устанавливаем начальную тему как тёмную
        self.mock_settings.theme_mode = "dark"
        self.page.theme_mode = ft.ThemeMode.DARK
        
        # Имитируем изменение темы на светлую
        self.view.theme_dropdown.value = "light"
        self.view._on_theme_changed(None)
        
        # Проверяем, что settings обновлён
        self.assertEqual(self.mock_settings.theme_mode, "light")
        
        # Проверяем, что page.theme_mode установлен
        self.assertEqual(self.page.theme_mode, ft.ThemeMode.LIGHT)
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)

    def test_change_date_format(self):
        """
        Тест изменения формата даты.
        
        Проверяет:
        - При изменении date_format_dropdown обновляется settings.date_format
        - Новый формат сохраняется в настройках
        
        Validates: Requirements 13.3
        """
        # Имитируем изменение формата даты
        self.view.date_format_dropdown.value = "%Y-%m-%d"
        self.view._on_date_format_changed(None)
        
        # Проверяем, что settings обновлён
        self.assertEqual(self.mock_settings.date_format, "%Y-%m-%d")

    def test_change_date_format_to_us_style(self):
        """
        Тест изменения формата даты на американский стиль.
        
        Проверяет:
        - При изменении на "%m/%d/%Y" settings обновляется
        
        Validates: Requirements 13.3
        """
        # Имитируем изменение формата даты на американский
        self.view.date_format_dropdown.value = "%m/%d/%Y"
        self.view._on_date_format_changed(None)
        
        # Проверяем, что settings обновлён
        self.assertEqual(self.mock_settings.date_format, "%m/%d/%Y")

    def test_save_settings(self):
        """
        Тест сохранения настроек.
        
        Проверяет:
        - При нажатии кнопки "Сохранить" вызывается settings.save()
        - Отображается SnackBar с сообщением об успехе
        - page.update() вызывается для отображения SnackBar
        
        Validates: Requirements 13.5
        """
        # Создаем мок события
        mock_event = Mock()
        
        # Вызываем метод сохранения
        self.view._save_settings(mock_event)
        
        # Проверяем, что settings.save был вызван
        self.mock_settings.save.assert_called_once()
        
        # Проверяем, что SnackBar установлен
        self.assertIsNotNone(self.page.snack_bar)
        self.assertTrue(self.page.snack_bar.open)
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)

    def test_save_settings_shows_success_message(self):
        """
        Тест отображения сообщения об успешном сохранении.
        
        Проверяет:
        - SnackBar содержит текст "успешно сохранены"
        - SnackBar имеет зелёный цвет (успех)
        
        Validates: Requirements 13.5
        """
        # Создаем мок события
        mock_event = Mock()
        
        # Вызываем метод сохранения
        self.view._save_settings(mock_event)
        
        # Проверяем, что SnackBar содержит правильное сообщение
        snack_bar = self.page.snack_bar
        self.assertIsNotNone(snack_bar)
        self.assertIn("успешно", snack_bar.content.value.lower())
        self.assertEqual(snack_bar.bgcolor, ft.Colors.GREEN)

    def test_db_path_field_is_readonly(self):
        """
        Тест, что поле пути к БД только для чтения.
        
        Проверяет:
        - db_path_field имеет атрибут read_only=True
        - Пользователь не может редактировать путь к БД через UI
        
        Validates: Requirements 13.1
        """
        # Проверяем, что поле только для чтения
        self.assertTrue(self.view.db_path_field.read_only)

    def test_theme_dropdown_has_options(self):
        """
        Тест наличия опций в dropdown темы.
        
        Проверяет:
        - theme_dropdown содержит опции "light" и "dark"
        - Опции доступны для выбора
        
        Validates: Requirements 13.2
        """
        # Проверяем, что dropdown имеет опции
        self.assertIsNotNone(self.view.theme_dropdown.options)
        self.assertGreater(len(self.view.theme_dropdown.options), 0)
        
        # Проверяем наличие конкретных опций
        option_keys = [opt.key for opt in self.view.theme_dropdown.options]
        self.assertIn("light", option_keys)
        self.assertIn("dark", option_keys)

    def test_date_format_dropdown_has_options(self):
        """
        Тест наличия опций в dropdown формата даты.
        
        Проверяет:
        - date_format_dropdown содержит различные форматы
        - Доступны минимум 3 формата даты
        
        Validates: Requirements 13.3
        """
        # Проверяем, что dropdown имеет опции
        self.assertIsNotNone(self.view.date_format_dropdown.options)
        self.assertGreaterEqual(len(self.view.date_format_dropdown.options), 3)
        
        # Проверяем наличие конкретных форматов
        option_keys = [opt.key for opt in self.view.date_format_dropdown.options]
        self.assertIn("%d.%m.%Y", option_keys)
        self.assertIn("%Y-%m-%d", option_keys)
        self.assertIn("%m/%d/%Y", option_keys)

    def test_settings_persistence_after_changes(self):
        """
        Тест персистентности настроек после изменений.
        
        Проверяет:
        - После изменения темы и формата даты, при сохранении
          все изменения сохраняются в settings
        
        Validates: Requirements 13.5
        """
        # Изменяем тему
        self.view.theme_dropdown.value = "dark"
        self.view._on_theme_changed(None)
        
        # Изменяем формат даты
        self.view.date_format_dropdown.value = "%Y-%m-%d"
        self.view._on_date_format_changed(None)
        
        # Сохраняем настройки
        self.view._save_settings(Mock())
        
        # Проверяем, что все изменения сохранены
        self.assertEqual(self.mock_settings.theme_mode, "dark")
        self.assertEqual(self.mock_settings.date_format, "%Y-%m-%d")
        self.mock_settings.save.assert_called_once()

    def test_multiple_theme_changes(self):
        """
        Тест множественных изменений темы.
        
        Проверяет:
        - При нескольких изменениях темы каждое применяется корректно
        - page.update() вызывается для каждого изменения
        
        Validates: Requirements 13.2
        """
        # Сбрасываем счетчик вызовов
        self.page.update.reset_mock()
        
        # Изменяем тему несколько раз
        self.view.theme_dropdown.value = "dark"
        self.view._on_theme_changed(None)
        
        self.view.theme_dropdown.value = "light"
        self.view._on_theme_changed(None)
        
        self.view.theme_dropdown.value = "dark"
        self.view._on_theme_changed(None)
        
        # Проверяем, что page.update вызван 3 раза
        self.assertEqual(self.page.update.call_count, 3)
        
        # Проверяем финальное состояние
        self.assertEqual(self.mock_settings.theme_mode, "dark")
        self.assertEqual(self.page.theme_mode, ft.ThemeMode.DARK)


if __name__ == '__main__':
    unittest.main()

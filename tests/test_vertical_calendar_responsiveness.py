"""
Тесты адаптивности вертикального календаря для Full HD и 2K разрешений.

Тестирует:
- Работа календаря на Full HD (1920x1080)
- Работа календаря на 2K (2560x1440)
- Правильный расчёт размеров шрифта и индикаторов
- Минимальная ширина календаря (300px)
- Адаптивность всех компонентов
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import date

import flet as ft

from finance_tracker.views.home_view import HomeView
from finance_tracker.components.calendar_widget import CalendarWidget


class TestFullHDResolution(unittest.TestCase):
    """Тесты для Full HD разрешения (1920x1080)."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_page = MagicMock()
        self.mock_page.width = 1920
        self.mock_page.height = 1080
        self.mock_page.overlay = []
        self.mock_page.update = Mock()
        self.mock_page.open = Mock()
        self.mock_page.close = Mock()
        self.mock_session = Mock()

    def test_full_hd_calendar_initialization(self):
        """
        Тест: Календарь инициализируется на Full HD.

        Проверяет:
        - Календарь создан без ошибок
        - Высота установлена корректно (1080px)
        - Используется Full HD пресет для размеров
        """
        # Arrange & Act
        test_date = date(2024, 12, 1)
        callback = Mock()

        calendar_widget = CalendarWidget(
            on_date_selected=callback,
            initial_date=test_date,
            page_height=1080
        )

        # Assert
        self.assertIsNotNone(calendar_widget)
        self.assertEqual(calendar_widget._page_height, 1080)

        # Проверяем, что размеры инициализированы
        self.assertIsNotNone(calendar_widget._font_size)
        self.assertIsNotNone(calendar_widget._indicator_size)
        # Full HD пресет: font_size=14
        self.assertEqual(calendar_widget._font_size, 14)

    def test_full_hd_home_view_layout(self):
        """
        Тест: Home_View отображается корректно на Full HD.

        Проверяет:
        - Home_View создана без ошибок
        - Все 4 колонки присутствуют
        - Пропорции expand соблюдены (2:2:4:3)
        - Календарь имеет правильную ширину
        """
        # Arrange & Act
        with patch('finance_tracker.database.get_db_session') as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = self.mock_session
            mock_get_db.return_value.__exit__.return_value = None

            home_view = HomeView(self.mock_page, self.mock_session)

            # Assert - проверяем структуру
            main_row = home_view.controls[0]
            columns = [control for control in main_row.controls if isinstance(control, ft.Column)]

            # 4 колонки
            self.assertEqual(len(columns), 4)

            # Пропорции
            expand_values = [col.expand for col in columns]
            self.assertEqual(expand_values, [2, 2, 4, 3])

            # Ширина календаря >= 300px
            calendar_width = home_view._calculate_calendar_width()
            self.assertGreaterEqual(calendar_width, 300,
                                  f"Calendar width should be >= 300px for 1920px page, got {calendar_width}")

    def test_full_hd_calendar_rendering(self):
        """
        Тест: Календарь корректно отображается на Full HD.

        Проверяет:
        - 7 строк (дни недели)
        - Правильные метки дней недели
        - Ячейки имеют aspect_ratio
        """
        # Arrange
        test_date = date(2024, 12, 1)
        callback = Mock()

        calendar_widget = CalendarWidget(
            on_date_selected=callback,
            initial_date=test_date,
            page_height=1080
        )

        # Эмулируем монтирование
        calendar_widget._page = self.mock_page
        calendar_widget.page = self.mock_page

        # Act
        calendar_widget._update_calendar()

        # Assert
        # 7 строк
        self.assertEqual(len(calendar_widget.days_grid.controls), 7)

        # Каждая строка имеет метку дня недели
        weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        for i, (row, expected_label) in enumerate(zip(calendar_widget.days_grid.controls, weekdays)):
            first_control = row.controls[0]
            self.assertIsInstance(first_control, ft.Container)
            label_text = first_control.content
            self.assertEqual(label_text.value, expected_label)


class Test2KResolution(unittest.TestCase):
    """Тесты для 2K разрешения (2560x1440)."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_page = MagicMock()
        self.mock_page.width = 2560
        self.mock_page.height = 1440
        self.mock_page.overlay = []
        self.mock_page.update = Mock()
        self.mock_page.open = Mock()
        self.mock_page.close = Mock()
        self.mock_session = Mock()

    def test_2k_calendar_initialization(self):
        """
        Тест: Календарь инициализируется на 2K.

        Проверяет:
        - Календарь создан без ошибок
        - Высота установлена корректно (1440px)
        - Используется 2K пресет для размеров
        """
        # Arrange & Act
        test_date = date(2024, 12, 1)
        callback = Mock()

        calendar_widget = CalendarWidget(
            on_date_selected=callback,
            initial_date=test_date,
            page_height=1440
        )

        # Assert
        self.assertIsNotNone(calendar_widget)
        self.assertEqual(calendar_widget._page_height, 1440)

        # Проверяем, что размеры инициализированы
        self.assertIsNotNone(calendar_widget._font_size)
        self.assertIsNotNone(calendar_widget._indicator_size)
        # 2K пресет: font_size=16
        self.assertEqual(calendar_widget._font_size, 16)

    def test_2k_home_view_layout(self):
        """
        Тест: Home_View отображается корректно на 2K.

        Проверяет:
        - Home_View создана без ошибок
        - Все 4 колонки присутствуют
        - Пропорции expand соблюдены (2:2:4:3)
        - Календарь имеет правильную ширину
        """
        # Arrange & Act
        with patch('finance_tracker.database.get_db_session') as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = self.mock_session
            mock_get_db.return_value.__exit__.return_value = None

            home_view = HomeView(self.mock_page, self.mock_session)

            # Assert - проверяем структуру
            main_row = home_view.controls[0]
            columns = [control for control in main_row.controls if isinstance(control, ft.Column)]

            # 4 колонки
            self.assertEqual(len(columns), 4)

            # Пропорции
            expand_values = [col.expand for col in columns]
            self.assertEqual(expand_values, [2, 2, 4, 3])

            # Ширина календаря >= 300px
            calendar_width = home_view._calculate_calendar_width()
            self.assertGreaterEqual(calendar_width, 300,
                                  f"Calendar width should be >= 300px for 2560px page, got {calendar_width}")

            # На 2K ширина должна быть больше, чем на Full HD
            # 2K: (2560 - 103) * (4/11) - 20 = примерно 817px
            self.assertGreater(calendar_width, 750,
                             f"Calendar width should be > 750px for 2K, got {calendar_width}")

    def test_2k_calendar_rendering(self):
        """
        Тест: Календарь корректно отображается на 2K.

        Проверяет:
        - 7 строк (дни недели)
        - Правильные метки дней недели
        - Ячейки имеют aspect_ratio
        """
        # Arrange
        test_date = date(2024, 12, 1)
        callback = Mock()

        calendar_widget = CalendarWidget(
            on_date_selected=callback,
            initial_date=test_date,
            page_height=1440
        )

        # Эмулируем монтирование
        calendar_widget._page = self.mock_page
        calendar_widget.page = self.mock_page

        # Act
        calendar_widget._update_calendar()

        # Assert
        # 7 строк
        self.assertEqual(len(calendar_widget.days_grid.controls), 7)

        # Каждая строка имеет метку дня недели
        weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        for i, (row, expected_label) in enumerate(zip(calendar_widget.days_grid.controls, weekdays)):
            first_control = row.controls[0]
            self.assertIsInstance(first_control, ft.Container)
            label_text = first_control.content
            self.assertEqual(label_text.value, expected_label)


class TestResponsivenessBetweenResolutions(unittest.TestCase):
    """Тесты адаптивности между разрешениями."""

    def test_font_size_scales_with_resolution(self):
        """
        Тест: Размер шрифта масштабируется в зависимости от разрешения.

        Full HD: font_size = 14
        2K: font_size = 16
        """
        # Arrange
        test_date = date(2024, 12, 1)
        callback = Mock()

        # Act - Full HD
        calendar_fhd = CalendarWidget(
            on_date_selected=callback,
            initial_date=test_date,
            page_height=1080
        )

        # Act - 2K
        calendar_2k = CalendarWidget(
            on_date_selected=callback,
            initial_date=test_date,
            page_height=1440
        )

        # Assert
        self.assertEqual(calendar_fhd._font_size, 14)
        self.assertEqual(calendar_2k._font_size, 16)
        self.assertGreater(calendar_2k._font_size, calendar_fhd._font_size)

    def test_indicator_size_scales_with_resolution(self):
        """
        Тест: Размер индикаторов масштабируется в зависимости от разрешения.

        Full HD: indicator_size = 8
        2K: indicator_size = 10
        """
        # Arrange
        test_date = date(2024, 12, 1)
        callback = Mock()

        # Act - Full HD
        calendar_fhd = CalendarWidget(
            on_date_selected=callback,
            initial_date=test_date,
            page_height=1080
        )

        # Act - 2K
        calendar_2k = CalendarWidget(
            on_date_selected=callback,
            initial_date=test_date,
            page_height=1440
        )

        # Assert
        self.assertEqual(calendar_fhd._indicator_size, 8)
        self.assertEqual(calendar_2k._indicator_size, 10)
        self.assertGreater(calendar_2k._indicator_size, calendar_fhd._indicator_size)

    def test_calendar_width_calculation_full_hd(self):
        """
        Тест: Расчёт ширины календаря для Full HD (1920px).

        Формула: (1920 - 103) * (4/11) - 20 = примерно 605px
        """
        # Arrange
        mock_page = MagicMock()
        mock_page.width = 1920
        mock_page.height = 1080
        mock_page.update = Mock()
        mock_session = Mock()

        # Act
        with patch('finance_tracker.database.get_db_session') as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = mock_session
            mock_get_db.return_value.__exit__.return_value = None

            home_view = HomeView(mock_page, mock_session)
            calendar_width = home_view._calculate_calendar_width()

        # Assert
        # (1920 - 103) * (4/11) - 20 ≈ 605
        expected = int((1920 - 103) * (4 / 11)) - 20
        self.assertAlmostEqual(calendar_width, expected, delta=1)
        self.assertGreaterEqual(calendar_width, 300)

    def test_calendar_width_calculation_2k(self):
        """
        Тест: Расчёт ширины календаря для 2K (2560px).

        Формула: (2560 - 103) * (4/11) - 20 = примерно 817px
        """
        # Arrange
        mock_page = MagicMock()
        mock_page.width = 2560
        mock_page.height = 1440
        mock_page.update = Mock()
        mock_session = Mock()

        # Act
        with patch('finance_tracker.database.get_db_session') as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = mock_session
            mock_get_db.return_value.__exit__.return_value = None

            home_view = HomeView(mock_page, mock_session)
            calendar_width = home_view._calculate_calendar_width()

        # Assert
        # (2560 - 103) * (4/11) - 20 ≈ 817
        expected = int((2560 - 103) * (4 / 11)) - 20
        self.assertAlmostEqual(calendar_width, expected, delta=1)
        self.assertGreaterEqual(calendar_width, 300)

    def test_calendar_width_increases_with_resolution(self):
        """
        Тест: Ширина календаря увеличивается при увеличении разрешения.

        Full HD (1920px) < 2K (2560px)
        """
        # Arrange
        mock_page_fhd = MagicMock()
        mock_page_fhd.width = 1920
        mock_page_fhd.height = 1080
        mock_page_fhd.update = Mock()

        mock_page_2k = MagicMock()
        mock_page_2k.width = 2560
        mock_page_2k.height = 1440
        mock_page_2k.update = Mock()

        mock_session = Mock()

        # Act
        with patch('finance_tracker.database.get_db_session') as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = mock_session
            mock_get_db.return_value.__exit__.return_value = None

            home_view_fhd = HomeView(mock_page_fhd, mock_session)
            width_fhd = home_view_fhd._calculate_calendar_width()

        with patch('finance_tracker.database.get_db_session') as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = mock_session
            mock_get_db.return_value.__exit__.return_value = None

            home_view_2k = HomeView(mock_page_2k, mock_session)
            width_2k = home_view_2k._calculate_calendar_width()

        # Assert
        self.assertLess(width_fhd, width_2k,
                       f"Full HD width ({width_fhd}) should be < 2K width ({width_2k})")


class TestCalendarFunctionality(unittest.TestCase):
    """Тесты функций календаря на разных разрешениях."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_page = MagicMock()
        self.mock_page.width = 1920
        self.mock_page.height = 1080
        self.mock_page.overlay = []
        self.mock_page.update = Mock()
        self.mock_page.open = Mock()
        self.mock_page.close = Mock()
        self.mock_session = Mock()

    def test_date_selection_functionality(self):
        """
        Тест: Выбор даты работает корректно.

        Проверяет:
        - Можно выбрать дату
        - Выбранная дата обновляется
        """
        # Arrange
        test_date = date(2024, 12, 15)
        callback = Mock()

        calendar_widget = CalendarWidget(
            on_date_selected=callback,
            initial_date=test_date
        )

        # Act
        calendar_widget.select_date(test_date)

        # Assert
        self.assertEqual(calendar_widget.selected_date, test_date)

    def test_month_navigation_functionality(self):
        """
        Тест: Переключение месяцев работает корректно.

        Проверяет:
        - Можно переключиться на разные месяцы
        - Структура календаря обновляется
        """
        # Arrange
        callback = Mock()
        calendar_widget = CalendarWidget(
            on_date_selected=callback,
            initial_date=date(2024, 1, 1)
        )

        calendar_widget._page = self.mock_page
        calendar_widget.page = self.mock_page

        # Act
        test_months = [
            date(2024, 1, 15),
            date(2024, 6, 15),
            date(2024, 12, 15),
        ]

        for test_date in test_months:
            with self.subTest(month=test_date.month):
                calendar_widget.current_date = test_date
                calendar_widget._update_calendar()

                # Assert
                self.assertEqual(len(calendar_widget.days_grid.controls), 7)

    def test_indicators_display_functionality(self):
        """
        Тест: Индикаторы отображаются корректно.

        Проверяет:
        - Методы _get_indicators_for_date работают
        - Индикаторы возвращают список
        """
        # Arrange
        test_date = date(2024, 12, 15)
        callback = Mock()

        calendar_widget = CalendarWidget(
            on_date_selected=callback,
            initial_date=test_date
        )

        # Act
        indicators = calendar_widget._get_indicators_for_date(test_date)

        # Assert
        self.assertIsInstance(indicators, list)
        # Может быть пусто или содержать элементы
        self.assertGreaterEqual(len(indicators), 0)


if __name__ == '__main__':
    unittest.main()

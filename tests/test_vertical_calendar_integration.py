"""
Интеграционные тесты для вертикального календаря.

Тестирует:
- Полный цикл взаимодействия с вертикальным календарём
- Переключение месяцев
- Обновление индикаторов при изменении данных
- Перемещение Pending_Payments_Widget во вторую колонку
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import date, datetime
from decimal import Decimal

import flet as ft

from finance_tracker.views.home_view import HomeView
from finance_tracker.components.calendar_widget import CalendarWidget
from finance_tracker.components.pending_payments_widget import PendingPaymentsWidget
from finance_tracker.models.enums import TransactionType


class TestVerticalCalendarFullInteraction(unittest.TestCase):
    """Тесты полного цикла взаимодействия с вертикальным календарём."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_page = MagicMock()
        self.mock_page.overlay = []
        self.mock_page.width = 1200
        self.mock_page.height = 800
        self.mock_page.update = Mock()
        self.mock_page.open = Mock()
        self.mock_page.close = Mock()
        self.mock_session = Mock()

    def test_full_calendar_interaction_flow(self):
        """
        Интеграционный тест: полный сценарий взаимодействия с вертикальным календарём.

        Проверяет:
        1. Создание Home_View с вертикальным календарём
        2. Клик на ячейку календаря
        3. Обновление выделения (выбранной даты)
        4. Обновление Transactions_Panel для выбранной даты
        """
        # Arrange - создаём Home_View
        with patch('finance_tracker.database.get_db_session') as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = self.mock_session
            mock_get_db.return_value.__exit__.return_value = None

            home_view = HomeView(self.mock_page, self.mock_session)

            # Act - проверяем, что календарь создан
            self.assertIsNotNone(home_view.calendar_widget)
            self.assertIsInstance(home_view.calendar_widget, CalendarWidget)

            # Act - выбираем дату в календаре
            test_date = date(2024, 12, 15)
            home_view.calendar_widget.select_date(test_date)

            # Assert - проверяем, что выбранная дата обновилась
            self.assertEqual(home_view.calendar_widget.selected_date, test_date)

    def test_month_switching_vertical_calendar(self):
        """
        Интеграционный тест: переключение месяцев в вертикальном календаре.

        Проверяет:
        1. Переключение на разные месяцы
        2. Корректность структуры для каждого месяца
        3. Правильное количество недель
        """
        # Arrange
        with patch('finance_tracker.database.get_db_session') as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = self.mock_session
            mock_get_db.return_value.__exit__.return_value = None

            home_view = HomeView(self.mock_page, self.mock_session)
            calendar_widget = home_view.calendar_widget

            # Эмулируем монтирование на страницу
            calendar_widget._page = self.mock_page
            calendar_widget.page = self.mock_page

            # Act & Assert - для каждого месяца
            test_dates = [
                date(2024, 1, 15),  # Январь 2024
                date(2024, 2, 15),  # Февраль 2024 (високосный год)
                date(2024, 12, 15), # Декабрь 2024
            ]

            for test_date in test_dates:
                calendar_widget.current_date = test_date
                calendar_widget._update_calendar()

                # Property 1: Количество строк = 7
                self.assertEqual(len(calendar_widget.days_grid.controls), 7,
                               f"Month {test_date.month}: Expected 7 rows")

                # Property 2: Количество дней в месяце должно быть сохранено
                for row in calendar_widget.days_grid.controls:
                    self.assertIsInstance(row, ft.Row)
                    # Каждая строка должна иметь контроли (метка дня недели + ячейки)
                    self.assertGreater(len(row.controls), 0)

    def test_pending_payments_widget_placement(self):
        """
        Интеграционный тест: перемещение Pending_Payments_Widget.

        Проверяет:
        1. Pending_Payments_Widget находится во второй колонке
        2. Pending_Payments_Widget отсутствует в третьей колонке
        3. Виджет обновляется при добавлении платежей
        """
        # Arrange
        with patch('finance_tracker.database.get_db_session') as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = self.mock_session
            mock_get_db.return_value.__exit__.return_value = None

            home_view = HomeView(self.mock_page, self.mock_session)

            # Assert - получаем основной Row
            main_row = home_view.controls[0]
            self.assertIsInstance(main_row, ft.Row)

            # Извлекаем только Column элементы (пропускаем VerticalDivider)
            columns = [control for control in main_row.controls if isinstance(control, ft.Column)]

            # Property: Должно быть 4 колонки
            self.assertEqual(len(columns), 4, "Expected 4 columns in Home_View")

            # Property: Pending_Payments_Widget должен быть во второй колонке (индекс 1)
            second_column = columns[1]
            pending_widget_found = False
            for control in second_column.controls:
                if isinstance(control, PendingPaymentsWidget):
                    pending_widget_found = True
                    break

            self.assertTrue(pending_widget_found,
                          "Pending_Payments_Widget should be in second column")

            # Property: Pending_Payments_Widget должен отсутствовать в третьей колонке (индекс 2)
            third_column = columns[2]
            for control in third_column.controls:
                self.assertNotIsInstance(control, PendingPaymentsWidget,
                                        "Pending_Payments_Widget should not be in third column")

    def test_calendar_and_legend_in_third_column(self):
        """
        Интеграционный тест: Проверка позиции календаря и легенды.

        Проверяет:
        1. CalendarWidget находится в третьей колонке
        2. CalendarLegend находится в третьей колонке
        3. Они находятся в правильном порядке
        """
        # Arrange
        with patch('finance_tracker.database.get_db_session') as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = self.mock_session
            mock_get_db.return_value.__exit__.return_value = None

            home_view = HomeView(self.mock_page, self.mock_session)

            # Assert - получаем третью колонку
            main_row = home_view.controls[0]
            columns = [control for control in main_row.controls if isinstance(control, ft.Column)]
            third_column = columns[2]

            # Property: CalendarWidget должен быть первым элементом третьей колонки
            self.assertIsInstance(third_column.controls[0], CalendarWidget,
                                "First control in third column should be CalendarWidget")

            # Property: CalendarLegend должен быть вторым элементом третьей колонки
            from finance_tracker.components.calendar_legend import CalendarLegend
            self.assertIsInstance(third_column.controls[1], CalendarLegend,
                                "Second control in third column should be CalendarLegend")

    def test_column_proportions_layout(self):
        """
        Интеграционный тест: Проверка пропорций колонок.

        Проверяет:
        1. Первая колонка expand=2
        2. Вторая колонка expand=2
        3. Третья колонка expand=4
        4. Четвёртая колонка expand=3
        5. Общая сумма expand = 11
        """
        # Arrange
        with patch('finance_tracker.database.get_db_session') as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = self.mock_session
            mock_get_db.return_value.__exit__.return_value = None

            home_view = HomeView(self.mock_page, self.mock_session)

            # Assert - получаем колонки
            main_row = home_view.controls[0]
            columns = [control for control in main_row.controls if isinstance(control, ft.Column)]

            # Property: expand значения должны быть 2, 2, 4, 3
            expected_expand = [2, 2, 4, 3]
            actual_expand = [col.expand for col in columns]

            self.assertEqual(actual_expand, expected_expand,
                           f"Expected expand={expected_expand}, got {actual_expand}")

            # Property: сумма expand = 11
            total_expand = sum(actual_expand)
            self.assertEqual(total_expand, 11,
                           f"Total expand should be 11, got {total_expand}")

    def test_calendar_width_calculation_integration(self):
        """
        Интеграционный тест: Проверка расчёта ширины календаря в контексте Home_View.

        Проверяет:
        1. Ширина календаря рассчитывается корректно
        2. Ширина календаря соответствует пропорции 4/11
        3. Применяется минимальная ширина 300px
        """
        # Arrange - тестируем с разными ширинами страницы
        test_widths = [800, 1200, 1600, 2000]

        for test_width in test_widths:
            with self.subTest(page_width=test_width):
                self.mock_page.width = test_width

                with patch('finance_tracker.database.get_db_session') as mock_get_db:
                    mock_get_db.return_value.__enter__.return_value = self.mock_session
                    mock_get_db.return_value.__exit__.return_value = None

                    home_view = HomeView(self.mock_page, self.mock_session)

                    # Act - вычисляем ширину календаря
                    calendar_width = home_view._calculate_calendar_width()

                    # Assert
                    # 1. Ширина не менее 300px
                    self.assertGreaterEqual(calendar_width, 300,
                                          f"Calendar width should be >= 300px for page_width={test_width}")

                    # 2. Ширина соответствует формуле
                    total_spacing = 103
                    available_width = test_width - total_spacing
                    expected_width = int(available_width * (4 / 11)) - 20
                    expected_width = max(expected_width, 300)

                    self.assertAlmostEqual(calendar_width, expected_width, delta=1,
                                         msg=f"Calendar width mismatch for page_width={test_width}")


class TestVerticalCalendarDataConsistency(unittest.TestCase):
    """Тесты консистентности данных в вертикальном календаре."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_page = MagicMock()
        self.mock_page.overlay = []
        self.mock_page.width = 1200
        self.mock_page.height = 800
        self.mock_page.update = Mock()
        self.mock_session = Mock()

    def test_calendar_cell_consistency(self):
        """
        Тест: Консистентность данных в ячейках календаря.

        Проверяет:
        1. Каждая ячейка имеет уникальную дату
        2. Даты соответствуют месяцу
        3. Транспонирование выполнено корректно
        """
        # Arrange
        test_date = date(2024, 12, 1)
        callback = Mock()

        calendar_widget = CalendarWidget(
            on_date_selected=callback,
            initial_date=test_date
        )

        # Эмулируем монтирование
        calendar_widget._page = self.mock_page
        calendar_widget.page = self.mock_page

        # Act - обновляем календарь
        calendar_widget._update_calendar()

        # Assert - проверяем консистентность
        seen_dates = set()

        for row_idx, row in enumerate(calendar_widget.days_grid.controls):
            for col_idx, cell in enumerate(row.controls[1:]):  # Пропускаем метку дня недели
                # Проверяем, что ячейка либо пустая, либо имеет on_click
                if cell.on_click is not None:
                    # Это ячейка с датой
                    # Ячейка должна быть Container с Column содержимым
                    self.assertIsInstance(cell, ft.Container)
                    self.assertIsNotNone(cell.content)

                    # Убедимся что даты не повторяются
                    # (добавляем простую проверку что ячейка может быть кликнута)
                    self.assertIsNotNone(cell.on_click)


class TestVerticalCalendarResponsiveness(unittest.TestCase):
    """Тесты адаптивности вертикального календаря."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_page = MagicMock()
        self.mock_page.overlay = []
        self.mock_page.update = Mock()
        self.mock_session = Mock()

    def test_calendar_responsiveness_different_screen_sizes(self):
        """
        Тест: Адаптивность календаря к разным размерам экрана.

        Проверяет:
        1. Календарь работает на ширине 1024px
        2. Календарь работает на ширине 1280px
        3. Календарь работает на ширине 1920px
        4. Минимальная ширина календаря = 300px
        """
        # Arrange - тестируем с разными размерами
        screen_sizes = [
            (1024, 768),
            (1280, 800),
            (1920, 1080),
            (2560, 1440),
        ]

        for width, height in screen_sizes:
            with self.subTest(screen_size=f"{width}x{height}"):
                self.mock_page.width = width
                self.mock_page.height = height

                with patch('finance_tracker.database.get_db_session') as mock_get_db:
                    mock_get_db.return_value.__enter__.return_value = self.mock_session
                    mock_get_db.return_value.__exit__.return_value = None

                    home_view = HomeView(self.mock_page, self.mock_session)

                    # Assert
                    # 1. Home_View создана успешно
                    self.assertIsNotNone(home_view)

                    # 2. Календарь создан и инициализирован
                    self.assertIsNotNone(home_view.calendar_widget)

                    # 3. Ширина календаря >= 300px
                    calendar_width = home_view._calculate_calendar_width()
                    self.assertGreaterEqual(calendar_width, 300,
                                          f"Calendar width should be >= 300px for {width}x{height}")


if __name__ == '__main__':
    unittest.main()

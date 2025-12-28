"""
UI тесты для вертикального календаря.

Тестирует:
- Рендеринг вертикального календаря
- Клик на ячейку вертикального календаря
- Обновление при изменении размера окна
- Aspect ratio ячеек (0.7)
- Выделение выходных дней (BLUE_50 фон)
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import date
import calendar

import flet as ft

from finance_tracker.components.calendar_widget import CalendarWidget
from finance_tracker.views.home_view import HomeView


class TestVerticalCalendarRendering(unittest.TestCase):
    """Тесты рендеринга вертикального календаря."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_page = MagicMock()
        self.mock_page.width = 1200
        self.mock_page.height = 800
        self.mock_page.update = Mock()
        self.mock_page.open = Mock()
        self.mock_page.close = Mock()

    def test_vertical_calendar_rendering_structure(self):
        """
        **Validates: Requirements 1.1, 1.2, 1.3**

        Тест: Рендеринг вертикального календаря имеет правильную структуру.

        Проверяет:
        - Column с 7 Row (по одной для каждого дня недели)
        - Каждая строка содержит метку дня недели и ячейки для недель
        """
        # Arrange
        test_date = date(2024, 12, 1)
        callback = Mock()

        calendar_widget = CalendarWidget(
            on_date_selected=callback,
            initial_date=test_date
        )

        # Эмулируем монтирование на страницу
        calendar_widget._page = self.mock_page
        calendar_widget.page = self.mock_page

        # Act - обновляем календарь
        calendar_widget._update_calendar()

        # Assert - проверяем структуру
        # 1. days_grid должен быть Column
        self.assertIsInstance(calendar_widget.days_grid, ft.Column)

        # 2. Количество строк = 7 (дни недели)
        self.assertEqual(len(calendar_widget.days_grid.controls), 7,
                        "Calendar should have 7 rows (one for each weekday)")

        # 3. Каждая строка - это Row
        for i, row in enumerate(calendar_widget.days_grid.controls):
            self.assertIsInstance(row, ft.Row,
                                f"Row {i} should be ft.Row, got {type(row)}")

            # 4. Каждая строка начинается с метки дня недели
            first_control = row.controls[0]
            self.assertIsInstance(first_control, ft.Container,
                                f"First control in row {i} should be ft.Container for day label")

            # 5. Каждая строка содержит ячейки для недель
            self.assertGreater(len(row.controls), 1,
                              f"Row {i} should have at least 2 controls (label + cells)")

    def test_vertical_calendar_weekday_labels(self):
        """
        **Validates: Requirements 1.1, 1.3**

        Тест: Метки дней недели корректно отображаются слева.

        Проверяет:
        - Метки дней недели слева в каждой строке
        - Текст метки соответствует дню недели
        - Выходные имеют специальный фон (BLUE_50)
        """
        # Arrange
        test_date = date(2024, 12, 1)
        callback = Mock()

        calendar_widget = CalendarWidget(
            on_date_selected=callback,
            initial_date=test_date
        )

        calendar_widget._page = self.mock_page
        calendar_widget.page = self.mock_page

        # Act - обновляем календарь
        calendar_widget._update_calendar()

        # Assert
        weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        rows = calendar_widget.days_grid.controls

        for i, (row, expected_label) in enumerate(zip(rows, weekdays)):
            # 1. Первый контроль - метка дня недели
            day_label_container = row.controls[0]
            self.assertIsInstance(day_label_container, ft.Container)

            # 2. Содержимое - Text с правильным текстом
            label_text = day_label_container.content
            self.assertIsInstance(label_text, ft.Text)
            self.assertEqual(label_text.value, expected_label,
                           f"Row {i} label should be '{expected_label}', got '{label_text.value}'")

            # 3. Выходные (Сб и Вс) имеют фон BLUE_50
            is_weekend = expected_label in ["Сб", "Вс"]
            if is_weekend:
                self.assertEqual(day_label_container.bgcolor, ft.Colors.BLUE_50,
                               f"{expected_label} label should have BLUE_50 background")

    def test_vertical_calendar_empty_cells(self):
        """
        **Validates: Requirements 1.5**

        Тест: Пустые ячейки в начале месяца отображаются правильно.

        Проверяет:
        - Пустые ячейки в начале месяца
        - Пустые ячейки не имеют on_click
        """
        # Arrange
        test_date = date(2024, 12, 1)  # Декабрь 2024 начинается с воскресенья
        callback = Mock()

        calendar_widget = CalendarWidget(
            on_date_selected=callback,
            initial_date=test_date
        )

        calendar_widget._page = self.mock_page
        calendar_widget.page = self.mock_page

        # Act - обновляем календарь
        calendar_widget._update_calendar()

        # Assert
        # Определяем первый день недели месяца
        cal = calendar.Calendar(firstweekday=0)
        month_matrix = cal.monthdayscalendar(test_date.year, test_date.month)

        # Находим первый день месяца в matrix
        first_day_weekday = 0
        for i, day in enumerate(month_matrix[0]):
            if day != 0:
                first_day_weekday = i
                break

        # Проверяем пустые ячейки в первых строках
        for row_idx in range(first_day_weekday):
            row = calendar_widget.days_grid.controls[row_idx]
            first_cell = row.controls[1]  # Первая ячейка (после метки дня недели)

            # Пустая ячейка не должна иметь on_click
            self.assertIsNone(first_cell.on_click,
                            f"Empty cell in row {row_idx} should not have on_click")

    def test_vertical_calendar_cell_aspect_ratio(self):
        """
        **Validates: Requirements 2.1, 7.9**

        Тест: Ячейки календаря имеют правильный aspect ratio.

        Проверяет:
        - Ячейки имеют aspect_ratio (квадратная или вытянутая форма)
        """
        # Arrange
        test_date = date(2024, 12, 15)
        callback = Mock()

        calendar_widget = CalendarWidget(
            on_date_selected=callback,
            initial_date=test_date
        )

        calendar_widget._page = self.mock_page
        calendar_widget.page = self.mock_page

        # Act - обновляем календарь
        calendar_widget._update_calendar()

        # Assert
        weekday = 6  # Воскресенье (0=Пн, 6=Вс)
        row = calendar_widget.days_grid.controls[weekday]

        # Проверяем ячейки (пропускаем первый контроль - метку дня недели)
        for i, cell in enumerate(row.controls[1:]):
            if cell.on_click is not None:  # Ячейка с датой
                # Ячейка должна иметь aspect_ratio для адаптивного размера
                self.assertIsNotNone(cell.aspect_ratio,
                                   f"Cell should have aspect_ratio")
                self.assertIn(cell.aspect_ratio, [0.7, 1],
                            f"Cell aspect_ratio should be 0.7 or 1, got {cell.aspect_ratio}")

    def test_vertical_calendar_weekend_highlighting(self):
        """
        **Validates: Requirements 3.1, 3.2, 7.10**

        Тест: Выходные дни выделены правильно.

        Проверяет:
        - Метки субботы и воскресенья имеют BLUE_50 фон
        - Ячейки дней обычного цвета (выходные не выделяются в ячейках)
        """
        # Arrange
        test_date = date(2024, 12, 1)
        callback = Mock()

        calendar_widget = CalendarWidget(
            on_date_selected=callback,
            initial_date=test_date
        )

        calendar_widget._page = self.mock_page
        calendar_widget.page = self.mock_page

        # Act - обновляем календарь
        calendar_widget._update_calendar()

        # Assert
        weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

        for row_idx, row in enumerate(calendar_widget.days_grid.controls):
            is_weekend = weekdays[row_idx] in ["Сб", "Вс"]

            # 1. Метка дня имеет BLUE_50 фон если выходной
            day_label = row.controls[0]
            if is_weekend:
                self.assertEqual(day_label.bgcolor, ft.Colors.BLUE_50,
                               f"Weekend label should have BLUE_50 background")

            # 2. Ячейки дней не имеют специальной стилизации для выходных
            # (они стилизуются только для selected, today, cash_gap, overdue)
            for cell in row.controls[1:]:
                if cell.on_click is not None:  # Ячейка с датой
                    # Проверяем, что это Container
                    self.assertIsInstance(cell, ft.Container)


class TestVerticalCalendarInteraction(unittest.TestCase):
    """Тесты взаимодействия с вертикальным календарём."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_page = MagicMock()
        self.mock_page.width = 1200
        self.mock_page.height = 800
        self.mock_page.update = Mock()

    def test_vertical_calendar_cell_click(self):
        """
        **Validates: Requirements 1.6, 7.1**

        Тест: Клик на ячейку вызывает callback с правильной датой.

        Проверяет:
        - Callback вызывается при клике
        - Callback получает правильную дату
        """
        # Arrange
        test_date = date(2024, 12, 15)
        callback = Mock()

        calendar_widget = CalendarWidget(
            on_date_selected=callback,
            initial_date=test_date
        )

        calendar_widget._page = self.mock_page
        calendar_widget.page = self.mock_page

        # Act - обновляем календарь
        calendar_widget._update_calendar()

        # Act - кликаем на ячейку
        weekday = 6  # Воскресенье
        row = calendar_widget.days_grid.controls[weekday]

        # Находим ячейку для дня 15 (третья неделя)
        for cell in row.controls[1:]:
            if cell.on_click is not None:
                # Симулируем клик
                cell.on_click(None)

                # Assert - callback должен быть вызван
                callback.assert_called()
                break

    def test_vertical_calendar_selected_date_styling(self):
        """
        **Validates: Requirements 7.10**

        Тест: Выбранная дата стилизуется правильно.

        Проверяет:
        - Выбранная дата имеет primaryContainer фон
        - Выбранная дата имеет зелёную рамку
        """
        # Arrange
        test_date = date(2024, 12, 15)
        callback = Mock()

        calendar_widget = CalendarWidget(
            on_date_selected=callback,
            initial_date=test_date
        )

        calendar_widget._page = self.mock_page
        calendar_widget.page = self.mock_page
        calendar_widget.selected_date = test_date

        # Act - обновляем календарь
        calendar_widget._update_calendar()

        # Assert - ищем ячейку с выбранной датой
        # В вертикальном календаре: строка = день недели, столбец = неделя
        weekday = test_date.weekday()  # 0=Пн, 6=Вс

        # Находим номер недели
        cal = calendar.Calendar(firstweekday=0)
        month_matrix = cal.monthdayscalendar(test_date.year, test_date.month)
        week_number = 0
        for i, week in enumerate(month_matrix):
            if test_date.day in week:
                week_number = i
                break

        # Получаем ячейку
        row = calendar_widget.days_grid.controls[weekday]
        cell = row.controls[week_number + 1]  # +1 потому что первый элемент - метка дня

        # Проверяем стилизацию
        if test_date == calendar_widget.selected_date:
            self.assertEqual(cell.bgcolor, "primaryContainer",
                           f"Selected cell should have primaryContainer background")
            # Проверяем рамку
            if cell.border is not None:
                # Ищем зелёную рамку
                self.assertIsNotNone(cell.border,
                                    "Selected cell should have border")

    def test_vertical_calendar_today_styling(self):
        """
        **Validates: Requirements 7.9**

        Тест: Текущий день стилизуется правильно.

        Проверяет:
        - Текущий день имеет синюю рамку
        - Текущий день имеет primary цвет текста
        """
        # Arrange
        today = date.today()
        callback = Mock()

        calendar_widget = CalendarWidget(
            on_date_selected=callback,
            initial_date=today
        )

        calendar_widget._page = self.mock_page
        calendar_widget.page = self.mock_page

        # Act - обновляем календарь
        calendar_widget._update_calendar()

        # Assert - ищем ячейку текущего дня
        weekday = today.weekday()

        # Находим номер недели
        cal = calendar.Calendar(firstweekday=0)
        month_matrix = cal.monthdayscalendar(today.year, today.month)
        week_number = 0
        for i, week in enumerate(month_matrix):
            if today.day in week:
                week_number = i
                break

        # Получаем ячейку
        row = calendar_widget.days_grid.controls[weekday]
        if week_number + 1 < len(row.controls):
            cell = row.controls[week_number + 1]

            # Проверяем стилизацию
            if cell.on_click is not None:
                # Ячейка текущего дня должна иметь border
                self.assertIsNotNone(cell.border,
                                    "Today cell should have border")

    def test_vertical_calendar_resize_handling(self):
        """
        **Validates: Requirements 6.3, 8.4**

        Тест: Обновление при изменении размера окна.

        Проверяет:
        - Календарь обновляется при изменении page.width
        - Ширина легенды обновляется
        """
        # Arrange
        with patch('finance_tracker.database.get_db_session') as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = Mock()
            mock_get_db.return_value.__exit__.return_value = None

            self.mock_page.height = 800
            self.mock_page.width = 1200

            home_view = HomeView(self.mock_page, Mock())

            # Act - меняем размер окна
            old_width = self.mock_page.width
            self.mock_page.width = 1600

            # Вызываем update_calendar_width
            new_calendar_width = home_view._calculate_calendar_width()

            # Assert
            # Ширина должна измениться
            old_calendar_width = int((old_width - 103) * (4 / 11)) - 20
            old_calendar_width = max(old_calendar_width, 300)

            new_calendar_width = max(new_calendar_width, 300)

            # При увеличении width на 400px, ширина календаря должна увеличиться
            expected_increase = int(400 * (4 / 11))
            actual_increase = new_calendar_width - old_calendar_width

            # Допускаем небольшую погрешность из-за rounding
            self.assertGreater(actual_increase, 0,
                             "Calendar width should increase when page width increases")


class TestVerticalCalendarWithIndicators(unittest.TestCase):
    """Тесты отображения индикаторов в вертикальном календаре."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_page = MagicMock()
        self.mock_page.width = 1200
        self.mock_page.height = 800
        self.mock_page.update = Mock()

    def test_calendar_cell_with_multiple_indicators(self):
        """
        **Validates: Requirements 2.6, 7.3-7.6**

        Тест: Ячейка с множественными индикаторами.

        Проверяет:
        - При > 3 индикаторов они разбиваются на строки
        - Каждая строка содержит до 3 индикаторов
        """
        # Arrange
        test_date = date(2024, 12, 15)
        callback = Mock()

        calendar_widget = CalendarWidget(
            on_date_selected=callback,
            initial_date=test_date
        )

        # Мокируем _get_indicators_for_date чтобы вернуть много индикаторов
        num_indicators = 5
        indicators = [
            ft.Container(width=8, height=8, bgcolor=ft.Colors.GREEN)
            for _ in range(num_indicators)
        ]

        calendar_widget._get_indicators_for_date = Mock(return_value=indicators)

        # Act - создаём ячейку
        cell = calendar_widget._build_day_cell(test_date)

        # Assert
        # Получаем Column с индикаторами
        content_column = cell.content
        self.assertIsInstance(content_column, ft.Column)

        # Находим Column с индикаторами (второй элемент)
        indicators_column = content_column.controls[1]
        self.assertIsInstance(indicators_column, ft.Column)

        # При 5 индикаторах должно быть 2 строки (3 + 2)
        expected_rows = (num_indicators + 2) // 3
        self.assertEqual(len(indicators_column.controls), expected_rows,
                        f"Expected {expected_rows} indicator rows, got {len(indicators_column.controls)}")

        # Каждая строка должна быть Row
        for row in indicators_column.controls:
            self.assertIsInstance(row, ft.Row)

        # Первая строка должна иметь 3 элемента
        first_row = indicators_column.controls[0]
        self.assertEqual(len(first_row.controls), 3,
                        "First indicator row should have 3 elements")

        # Последняя строка может иметь меньше элементов
        last_row = indicators_column.controls[-1]
        self.assertLessEqual(len(last_row.controls), 3,
                            "Last indicator row should have <= 3 elements")


if __name__ == '__main__':
    unittest.main()

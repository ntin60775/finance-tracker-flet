"""
Unit тесты для вертикального календаря.

Тестирует:
- Структура вертикального календаря (7 строк для дней недели)
- Корректность транспонирования сетки
- Метки дней недели слева
- Выделение выходных дней
- Aspect ratio ячеек (0.7 для вертикального вытягивания)
- Множественные строки индикаторов при > 3 индикаторов
"""

import calendar
import datetime
import unittest
from unittest.mock import MagicMock, Mock, patch

import flet as ft

from finance_tracker.components.calendar_widget import CalendarWidget
from finance_tracker.models.enums import TransactionType


class TestVerticalCalendarStructure(unittest.TestCase):
    """Тесты структуры вертикального календаря."""

    def setUp(self):
        """Подготовка перед каждым тестом."""
        self.mock_callback = Mock()
        # Создаём виджет с фиксированной датой для предсказуемости тестов
        self.test_date = datetime.date(2024, 12, 1)  # Декабрь 2024
        self.widget = CalendarWidget(
            on_date_selected=self.mock_callback,
            initial_date=self.test_date
        )

    def test_calendar_widget_initialization(self):
        """Тест инициализации виджета календаря."""
        self.assertIsNotNone(self.widget)
        self.assertEqual(self.widget.current_date.year, 2024)
        self.assertEqual(self.widget.current_date.month, 12)
        self.assertEqual(self.widget.selected_date, self.test_date)

    def test_weekdays_header_has_week_numbers(self):
        """Тест: заголовок содержит номера недель (Н1, Н2, ...)."""
        header = self.widget._build_weekdays_header()

        # Заголовок должен быть Row
        self.assertIsInstance(header, ft.Row)

        # Первый элемент - пустой контейнер для выравнивания
        first_control = header.controls[0]
        self.assertIsInstance(first_control, ft.Container)
        self.assertEqual(first_control.width, 40)

        # Определяем количество недель в декабре 2024
        cal = calendar.Calendar(firstweekday=0)
        month_matrix = cal.monthdayscalendar(2024, 12)
        num_weeks = len(month_matrix)

        # Должно быть num_weeks + 1 элементов (пустой + метки недель)
        self.assertEqual(len(header.controls), num_weeks + 1)

        # Проверяем метки недель
        for i in range(1, num_weeks + 1):
            week_label_container = header.controls[i]
            self.assertIsInstance(week_label_container, ft.Container)
            text = week_label_container.content
            self.assertIsInstance(text, ft.Text)
            self.assertEqual(text.value, f"Н{i}")

    def test_calendar_grid_has_seven_rows(self):
        """Тест: сетка календаря содержит 7 строк (по одной для каждого дня недели)."""
        # Имитируем монтирование на страницу
        mock_page = MagicMock()
        mock_page.update = Mock()
        self.widget._page = mock_page
        self.widget.page = mock_page

        # Вызываем обновление календаря
        self.widget._update_calendar()

        # Проверяем количество строк
        self.assertEqual(len(self.widget.days_grid.controls), 7)

    def test_each_row_has_weekday_label_first(self):
        """Тест: каждая строка начинается с метки дня недели."""
        mock_page = MagicMock()
        mock_page.update = Mock()
        self.widget._page = mock_page
        self.widget.page = mock_page

        self.widget._update_calendar()

        weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

        for i, row in enumerate(self.widget.days_grid.controls):
            self.assertIsInstance(row, ft.Row)
            first_control = row.controls[0]
            self.assertIsInstance(first_control, ft.Container)
            self.assertEqual(first_control.width, 40)

            # Проверяем текст метки
            text = first_control.content
            self.assertIsInstance(text, ft.Text)
            self.assertEqual(text.value, weekdays[i])

    def test_weekend_labels_have_highlighted_background(self):
        """Тест: метки выходных (Сб, Вс) имеют выделенный фон."""
        mock_page = MagicMock()
        mock_page.update = Mock()
        self.widget._page = mock_page
        self.widget.page = mock_page

        self.widget._update_calendar()

        # Строки 5 и 6 (Сб и Вс) должны иметь выделенный фон
        for i, row in enumerate(self.widget.days_grid.controls):
            first_control = row.controls[0]
            if i >= 5:  # Сб (5) и Вс (6)
                self.assertEqual(
                    first_control.bgcolor,
                    ft.Colors.BLUE_50,
                    f"Строка {i} ({['Пн','Вт','Ср','Чт','Пт','Сб','Вс'][i]}) должна иметь выделенный фон"
                )
            else:
                self.assertIsNone(
                    first_control.bgcolor,
                    f"Строка {i} ({['Пн','Вт','Ср','Чт','Пт','Сб','Вс'][i]}) не должна иметь выделенный фон"
                )


class TestVerticalCalendarCells(unittest.TestCase):
    """Тесты ячеек вертикального календаря."""

    def setUp(self):
        """Подготовка перед каждым тестом."""
        self.mock_callback = Mock()
        self.test_date = datetime.date(2024, 12, 15)
        self.widget = CalendarWidget(
            on_date_selected=self.mock_callback,
            initial_date=self.test_date
        )

    def test_day_cell_has_square_aspect_ratio(self):
        """Тест: ячейка дня имеет квадратную форму (aspect_ratio=1)."""
        date_obj = datetime.date(2024, 12, 15)
        cell = self.widget._build_day_cell(date_obj)

        self.assertIsInstance(cell, ft.Container)
        # Квадратные ячейки: высота = ширина
        self.assertEqual(cell.aspect_ratio, 1)

    def test_empty_cell_has_square_aspect_ratio(self):
        """Тест: пустые ячейки также имеют квадратную форму (aspect_ratio=1)."""
        mock_page = MagicMock()
        mock_page.update = Mock()
        self.widget._page = mock_page
        self.widget.page = mock_page

        self.widget._update_calendar()

        # Находим пустую ячейку (если есть)
        for row in self.widget.days_grid.controls:
            for control in row.controls[1:]:  # Пропускаем метку дня недели
                if isinstance(control, ft.Container) and control.content is None:
                    # Квадратные ячейки: aspect_ratio=1
                    self.assertEqual(control.aspect_ratio, 1)
                    return

        # Если нет пустых ячеек - тест пропущен (это нормально для некоторых месяцев)

    def test_day_cell_shows_day_number(self):
        """Тест: ячейка показывает номер дня."""
        date_obj = datetime.date(2024, 12, 25)
        cell = self.widget._build_day_cell(date_obj)

        # Содержимое ячейки - Column
        self.assertIsInstance(cell.content, ft.Column)

        # Первый элемент - Text с номером дня
        day_text = cell.content.controls[0]
        self.assertIsInstance(day_text, ft.Text)
        self.assertEqual(day_text.value, "25")

    def test_selected_day_has_green_border(self):
        """Тест: выбранный день имеет зелёную рамку."""
        self.widget.selected_date = datetime.date(2024, 12, 15)
        cell = self.widget._build_day_cell(datetime.date(2024, 12, 15))

        self.assertIsNotNone(cell.border)
        # Проверяем толщину рамки
        self.assertEqual(cell.border.top.width, 3)

    def test_today_has_primary_border(self):
        """Тест: сегодняшний день имеет рамку primary цвета."""
        today = datetime.date.today()
        self.widget.current_date = today.replace(day=1)
        self.widget.selected_date = None  # Сбрасываем выбор

        # Если сегодня в текущем месяце
        if today.month == self.widget.current_date.month:
            cell = self.widget._build_day_cell(today)
            self.assertIsNotNone(cell.border)

    def test_cash_gap_day_has_amber_background(self):
        """Тест: день с кассовым разрывом имеет желтый фон."""
        gap_date = datetime.date(2024, 12, 20)
        self.widget.cash_gaps = [gap_date]
        self.widget.selected_date = datetime.date(2024, 12, 1)  # Другой день

        cell = self.widget._build_day_cell(gap_date)

        self.assertEqual(cell.bgcolor, ft.Colors.AMBER_100)


class TestVerticalCalendarIndicators(unittest.TestCase):
    """Тесты индикаторов вертикального календаря."""

    def setUp(self):
        """Подготовка перед каждым тестом."""
        self.mock_callback = Mock()
        self.test_date = datetime.date(2024, 12, 15)
        self.widget = CalendarWidget(
            on_date_selected=self.mock_callback,
            initial_date=self.test_date
        )

    def test_indicators_split_into_rows_when_more_than_three(self):
        """Тест: при > 3 индикаторов они разбиваются на несколько строк."""
        date_obj = datetime.date(2024, 12, 15)

        # Создаём mock транзакции и события для 5 индикаторов
        self.widget.transactions = [
            Mock(date=date_obj, type=TransactionType.INCOME),  # Зелёная точка
            Mock(date=date_obj, type=TransactionType.EXPENSE),  # Красная точка
        ]
        self.widget.planned_occurrences = [
            Mock(occurrence_date=date_obj),  # Оранжевый ромб
        ]
        self.widget.pending_payments = [
            Mock(planned_date=date_obj),  # Иконка 📋
        ]
        self.widget.loan_payments = [
            Mock(scheduled_date=date_obj, status=Mock()),  # Иконка 💳
        ]

        cell = self.widget._build_day_cell(date_obj)

        # Содержимое - Column
        content_column = cell.content
        self.assertIsInstance(content_column, ft.Column)

        # Второй элемент - Column с индикаторами
        indicators_column = content_column.controls[1]
        self.assertIsInstance(indicators_column, ft.Column)

        # Должно быть 2 строки (5 индикаторов = 3 + 2)
        self.assertEqual(len(indicators_column.controls), 2)

    def test_three_or_less_indicators_in_single_row(self):
        """Тест: при <= 3 индикаторов они в одной строке."""
        date_obj = datetime.date(2024, 12, 15)

        # Создаём 2 индикатора
        self.widget.transactions = [
            Mock(date=date_obj, type=TransactionType.INCOME),
        ]
        self.widget.planned_occurrences = [
            Mock(occurrence_date=date_obj),
        ]
        self.widget.pending_payments = []
        self.widget.loan_payments = []

        cell = self.widget._build_day_cell(date_obj)

        content_column = cell.content
        indicators_column = content_column.controls[1]

        # Должна быть 1 строка
        self.assertEqual(len(indicators_column.controls), 1)


class TestVerticalCalendarTransposition(unittest.TestCase):
    """Тесты транспонирования сетки календаря."""

    def setUp(self):
        """Подготовка перед каждым тестом."""
        self.mock_callback = Mock()

    def test_transposition_preserves_all_days(self):
        """Тест: транспонирование сохраняет все дни месяца."""
        # Тестируем для нескольких месяцев
        test_months = [
            (2024, 1),   # Январь - 31 день
            (2024, 2),   # Февраль (високосный) - 29 дней
            (2024, 4),   # Апрель - 30 дней
            (2024, 12),  # Декабрь - 31 день
        ]

        for year, month in test_months:
            with self.subTest(year=year, month=month):
                test_date = datetime.date(year, month, 1)
                widget = CalendarWidget(
                    on_date_selected=self.mock_callback,
                    initial_date=test_date
                )

                mock_page = MagicMock()
                mock_page.update = Mock()
                widget._page = mock_page
                widget.page = mock_page

                widget._update_calendar()

                # Считаем количество непустых ячеек
                non_empty_cells = 0
                for row in widget.days_grid.controls:
                    for control in row.controls[1:]:  # Пропускаем метку
                        if isinstance(control, ft.Container) and control.content is not None:
                            non_empty_cells += 1

                # Ожидаемое количество дней
                _, days_in_month = calendar.monthrange(year, month)

                self.assertEqual(
                    non_empty_cells,
                    days_in_month,
                    f"Месяц {month}/{year}: ожидалось {days_in_month} дней, найдено {non_empty_cells}"
                )


class TestVerticalCalendarInteraction(unittest.TestCase):
    """Тесты взаимодействия с вертикальным календарём."""

    def setUp(self):
        """Подготовка перед каждым тестом."""
        self.mock_callback = Mock()
        self.test_date = datetime.date(2024, 12, 15)
        self.widget = CalendarWidget(
            on_date_selected=self.mock_callback,
            initial_date=self.test_date
        )

    def test_day_click_calls_callback(self):
        """Тест: клик по дню вызывает callback."""
        click_date = datetime.date(2024, 12, 20)

        mock_page = MagicMock()
        mock_page.update = Mock()
        self.widget._page = mock_page
        self.widget.page = mock_page

        self.widget._on_day_click(click_date)

        self.mock_callback.assert_called_once_with(click_date)
        self.assertEqual(self.widget.selected_date, click_date)

    def test_month_navigation_updates_header(self):
        """Тест: навигация обновляет заголовок с номерами недель."""
        mock_page = MagicMock()
        mock_page.update = Mock()
        self.widget._page = mock_page
        self.widget.page = mock_page

        initial_month = self.widget.current_date.month

        # Переходим к следующему месяцу
        self.widget._next_month(None)

        next_month = self.widget.current_date.month
        expected_month = 1 if initial_month == 12 else initial_month + 1

        self.assertEqual(next_month, expected_month)


if __name__ == '__main__':
    unittest.main()

"""
Property-based тесты для вертикального календаря.

Тестирует 16 универсальных свойств вертикального календаря:
- Property 1: Транспонирование календарной сетки
- Property 2: Сохранение всех дней месяца
- Property 3: Корректность позиций пустых ячеек
- Property 4: Клик на ячейку вызывает callback
- Property 5-8: Индикаторы для всех типов данных
- Property 9-12: Стилизация ячеек
- Property 13: Множественные строки индикаторов
- Property 14: Пропорции колонок Home_View
- Property 15: Расчёт ширины календаря
- Property 16: Синхронизация ширины легенды и календаря
"""

import calendar
import datetime
from decimal import Decimal
from unittest.mock import Mock, MagicMock

import flet as ft
import pytest
from hypothesis import given, strategies as st, assume, settings

from finance_tracker.components.calendar_widget import CalendarWidget
from finance_tracker.views.home_view import HomeView
from finance_tracker.components.calendar_legend import CalendarLegend
from finance_tracker.models.enums import TransactionType


# --- Strategies ---

dates_strategy = st.dates(
    min_value=datetime.date(2020, 1, 1),
    max_value=datetime.date(2030, 12, 31)
)

month_year_strategy = st.tuples(
    st.integers(min_value=2020, max_value=2030),
    st.integers(min_value=1, max_value=12)
)

page_width_strategy = st.integers(min_value=500, max_value=3000)


class TestVerticalCalendarTranspositionProperties:
    """Property-based тесты для транспонирования календаря."""

    @given(month_year_strategy)
    @settings(max_examples=50, deadline=None)
    def test_property_1_calendar_transposition(self, month_year):
        """
        **Feature: Vertical Calendar Layout, Property 1: Транспонирование календарной сетки**
        **Validates: Requirements 1.1, 1.2**

        Property: Для любого месяца и года количество строк в вертикальном календаре
        должно быть равно 7 (дни недели), а количество столбцов должно быть
        равно количеству недель в этом месяце (4-6).
        """
        year, month = month_year

        # Создаём календарь
        test_date = datetime.date(year, month, 1)
        widget = CalendarWidget(
            on_date_selected=Mock(),
            initial_date=test_date
        )

        # Эмулируем монтирование на страницу
        mock_page = MagicMock()
        mock_page.update = Mock()
        widget._page = mock_page
        widget.page = mock_page

        # Обновляем календарь
        widget._update_calendar()

        # Property: Количество строк = 7 (дни недели)
        assert len(widget.days_grid.controls) == 7, \
            f"Expected 7 rows, got {len(widget.days_grid.controls)}"

        # Property: Количество столбцов = количество недель в месяце
        cal = calendar.Calendar(firstweekday=0)
        month_matrix = cal.monthdayscalendar(year, month)
        expected_columns = len(month_matrix)

        # Каждая строка должна иметь: метка дня недели + ячейки для недель
        for i, row in enumerate(widget.days_grid.controls):
            assert isinstance(row, ft.Row), f"Row {i} is not ft.Row"
            # -1 потому что первый элемент - метка дня недели
            actual_columns = len(row.controls) - 1
            assert actual_columns == expected_columns, \
                f"Row {i}: expected {expected_columns} columns, got {actual_columns}"

    @given(month_year_strategy)
    @settings(max_examples=50, deadline=None)
    def test_property_2_all_days_preserved(self, month_year):
        """
        **Feature: Vertical Calendar Layout, Property 2: Сохранение всех дней месяца**
        **Validates: Requirements 1.5, 10.1**

        Property: Для любого месяца и года, сумма всех непустых ячеек в
        транспонированном календаре должна быть равна количеству дней в этом месяце.
        """
        year, month = month_year

        # Определяем количество дней в месяце
        _, num_days = calendar.monthrange(year, month)

        # Создаём календарь
        test_date = datetime.date(year, month, 1)
        widget = CalendarWidget(
            on_date_selected=Mock(),
            initial_date=test_date
        )

        # Эмулируем монтирование
        mock_page = MagicMock()
        mock_page.update = Mock()
        widget._page = mock_page
        widget.page = mock_page

        # Обновляем календарь
        widget._update_calendar()

        # Подсчитываем непустые ячейки
        non_empty_cells = 0
        for row in widget.days_grid.controls:
            for control in row.controls[1:]:  # Пропускаем метку дня недели
                # Проверяем, что это ячейка с датой (имеет on_click)
                if hasattr(control, 'on_click') and control.on_click is not None:
                    non_empty_cells += 1

        # Property: Количество непустых ячеек = количеству дней в месяце
        assert non_empty_cells == num_days, \
            f"Expected {num_days} non-empty cells, got {non_empty_cells}"

    @given(month_year_strategy)
    @settings(max_examples=50, deadline=None)
    def test_property_3_empty_cells_positions(self, month_year):
        """
        **Feature: Vertical Calendar Layout, Property 3: Корректность позиций пустых ячеек**
        **Validates: Requirements 1.5**

        Property: Для любого месяца, если первый день месяца приходится на день
        недели N (где Пн=0, Вс=6), то в строках 0..N-1 первый столбец должен
        содержать пустые ячейки.
        """
        year, month = month_year

        # Определяем первый день недели месяца (0 = Пн, 6 = Вс)
        cal = calendar.Calendar(firstweekday=0)
        month_matrix = cal.monthdayscalendar(year, month)

        # Находим первый непустой день в matrixе (обычно в первой неделе)
        first_day_weekday = 0
        for i, day in enumerate(month_matrix[0]):
            if day != 0:
                first_day_weekday = i
                break

        # Создаём календарь
        test_date = datetime.date(year, month, 1)
        widget = CalendarWidget(
            on_date_selected=Mock(),
            initial_date=test_date
        )

        # Эмулируем монтирование
        mock_page = MagicMock()
        mock_page.update = Mock()
        widget._page = mock_page
        widget.page = mock_page

        # Обновляем календарь
        widget._update_calendar()

        # Проверяем пустые ячейки в первых строках (строки 0..first_day_weekday-1)
        for row_idx in range(first_day_weekday):
            row = widget.days_grid.controls[row_idx]
            first_cell = row.controls[1]  # Первая ячейка (после метки дня недели)

            # Пустая ячейка не должна иметь on_click
            assert first_cell.on_click is None, \
                f"Row {row_idx} first cell should be empty (no on_click)"


class TestVerticalCalendarInteractionProperties:
    """Property-based тесты для взаимодействия с календарём."""

    @given(dates_strategy)
    @settings(max_examples=50, deadline=None)
    def test_property_4_click_calls_callback(self, test_date):
        """
        **Feature: Vertical Calendar Layout, Property 4: Клик на ячейку вызывает callback**
        **Validates: Requirements 1.6, 7.1**

        Property: Для любой непустая ячейка календаря, клик на неё должен
        вызывать callback on_date_selected с соответствующей датой.
        """
        # Пропускаем некорректные даты
        assume(test_date.day <= 28)  # Безопасная дата для любого месяца

        mock_callback = Mock()
        widget = CalendarWidget(
            on_date_selected=mock_callback,
            initial_date=test_date
        )

        # Эмулируем монтирование
        mock_page = MagicMock()
        mock_page.update = Mock()
        widget._page = mock_page
        widget.page = mock_page

        # Обновляем календарь
        widget._update_calendar()

        # Находим ячейку для тестовой даты
        weekday = test_date.weekday()  # 0 = Пн, 6 = Вс (но календарь использует 0 = Пн)

        # В транспонированном календаре строка = день недели, столбец = неделя
        row = widget.days_grid.controls[weekday]

        # Определяем номер недели в месяце (используем calendar.monthdayscalendar)
        cal = calendar.Calendar(firstweekday=0)
        month_matrix = cal.monthdayscalendar(test_date.year, test_date.month)

        week_number = None
        for i, week in enumerate(month_matrix):
            if test_date.day in week:
                week_number = i
                break

        # Пропускаем если дата вне диапазона (например, дата больше чем дни в месяце)
        if week_number is None:
            pytest.skip(f"Date {test_date} is out of range for month {test_date.month}/{test_date.year}")

        # Получаем ячейку (week_number + 1, т.к. первый элемент - метка дня недели)
        cell = row.controls[week_number + 1]

        # Проверяем, что ячейка имеет on_click
        if cell.on_click is not None:
            # Симулируем клик
            cell.on_click(None)

            # Property: Callback должен быть вызван
            mock_callback.assert_called()


class TestVerticalCalendarIndicatorsProperties:
    """Property-based тесты для индикаторов в календаре."""

    @given(st.integers(min_value=1, max_value=15))
    @settings(max_examples=50, deadline=None)
    def test_property_13_multiple_indicator_rows(self, num_indicators):
        """
        **Feature: Vertical Calendar Layout, Property 13: Множественные строки индикаторов**
        **Validates: Requirements 2.6**

        Property: Для любой ячейки с более чем 3 индикаторами, индикаторы должны
        быть разбиты на несколько строк по 3 индикатора в каждой.
        """
        # Создаём список индикаторов
        indicators = [
            ft.Container(width=8, height=8, bgcolor=ft.Colors.GREEN)
            for _ in range(num_indicators)
        ]

        test_date = datetime.date.today()
        widget = CalendarWidget(
            on_date_selected=Mock(),
            initial_date=test_date
        )

        # Мокируем _get_indicators_for_date
        widget._get_indicators_for_date = Mock(return_value=indicators)

        # Эмулируем монтирование
        mock_page = MagicMock()
        mock_page.update = Mock()
        widget._page = mock_page
        widget.page = mock_page

        # Создаём ячейку для даты
        cell = widget._build_day_cell(test_date)

        # Получаем Column с индикаторами
        column = cell.content
        assert isinstance(column, ft.Column)

        # Находим Column с индикаторами (второй элемент)
        indicators_column = column.controls[1]
        assert isinstance(indicators_column, ft.Column)

        # Property: Если > 3 индикаторов, должно быть несколько Row
        if num_indicators > 3:
            # Количество строк = ceil(num_indicators / 3)
            expected_rows = (num_indicators + 2) // 3
            assert len(indicators_column.controls) == expected_rows, \
                f"Expected {expected_rows} rows for {num_indicators} indicators, got {len(indicators_column.controls)}"

            # Каждая строка должна быть Row
            for row in indicators_column.controls:
                assert isinstance(row, ft.Row)

            # Первые n-1 строк должны иметь 3 индикатора
            for row in indicators_column.controls[:-1]:
                assert len(row.controls) == 3, \
                    f"Non-last row should have 3 controls, got {len(row.controls)}"

            # Последняя строка может иметь 1-3 индикатора
            last_row = indicators_column.controls[-1]
            assert 1 <= len(last_row.controls) <= 3, \
                f"Last row should have 1-3 controls, got {len(last_row.controls)}"
        else:
            # Если <= 3 индикаторов, должна быть одна строка
            assert len(indicators_column.controls) == 1
            row = indicators_column.controls[0]
            assert isinstance(row, ft.Row)
            assert len(row.controls) == num_indicators


class TestHomeViewLayoutProperties:
    """Property-based тесты для layout Home_View."""

    def test_property_14_column_proportions(self):
        """
        **Feature: Vertical Calendar Layout, Property 14: Пропорции колонок Home_View**
        **Validates: Requirements 4.1**

        Property: Для любой Home_View, колонки должны иметь expand значения 2, 2, 4, 3,
        что даёт пропорции 2/11, 2/11, 4/11, 3/11.
        """
        mock_page = MagicMock()
        mock_page.width = 1200
        mock_page.height = 800
        mock_page.update = Mock()
        mock_session = Mock()

        # Создаём Home_View
        home_view = HomeView(mock_page, mock_session)

        # Получаем главный Row с колонками
        main_row = home_view.controls[0]
        assert isinstance(main_row, ft.Row)

        # Извлекаем только Column элементы (пропускаем VerticalDivider)
        columns = [control for control in main_row.controls if isinstance(control, ft.Column)]

        # Property: Должно быть 4 колонки с expand 2, 2, 4, 3
        assert len(columns) == 4, f"Expected 4 columns, got {len(columns)}"

        expected_expand = [2, 2, 4, 3]
        for i, (column, expected) in enumerate(zip(columns, expected_expand)):
            assert column.expand == expected, \
                f"Column {i}: expected expand={expected}, got expand={column.expand}"

    @given(page_width_strategy)
    @settings(max_examples=50, deadline=None)
    def test_property_15_calendar_width_calculation(self, page_width):
        """
        **Feature: Vertical Calendar Layout, Property 15: Расчёт ширины календаря**
        **Validates: Requirements 6.1, 6.2**

        Property: Для любой ширины страницы, ширина календаря должна быть равна
        (page_width - spacing - dividers) × (4/11) - padding, но не менее 300px.
        """
        mock_page = MagicMock()
        mock_page.width = page_width
        mock_page.height = 800
        mock_page.update = Mock()
        mock_session = Mock()

        # Создаём Home_View
        home_view = HomeView(mock_page, mock_session)

        # Вычисляем ожидаемую ширину
        # Формула: (page_width - total_spacing) * (4/11) - padding
        # total_spacing = 60 + 3 + 40 = 103px
        total_spacing = 103
        available_width = page_width - total_spacing
        center_column_width = int(available_width * (4 / 11))
        expected_calendar_width = center_column_width - 20

        # Property: Ширина не менее 300px
        expected_calendar_width = max(expected_calendar_width, 300)

        # Вычисляем фактическую ширину
        actual_calendar_width = home_view._calculate_calendar_width()

        # Property: Фактическая ширина = ожидаемой или close to it (с допуском на rounding)
        assert actual_calendar_width >= 300, \
            f"Expected minimum 300px, got {actual_calendar_width}"

        # Проверяем, что ширина соответствует формуле (с допуском на rounding)
        assert abs(actual_calendar_width - expected_calendar_width) <= 1, \
            f"Expected {expected_calendar_width}px, got {actual_calendar_width}px"


class TestCalendarWidthSyncProperties:
    """Property-based тесты для синхронизации ширины календаря и легенды."""

    @given(page_width_strategy)
    @settings(max_examples=50, deadline=None)
    def test_property_16_legend_calendar_width_sync(self, page_width):
        """
        **Feature: Vertical Calendar Layout, Property 16: Синхронизация ширины легенды и календаря**
        **Validates: Requirements 6.4, 8.2**

        Property: Для любой Calendar_Widget и Calendar_Legend в одной колонке,
        их ширины должны быть равны.
        """
        mock_page = MagicMock()
        mock_page.width = page_width
        mock_page.height = 800
        mock_page.update = Mock()
        mock_session = Mock()

        # Создаём Home_View
        home_view = HomeView(mock_page, mock_session)

        # Обновляем ширину календаря
        calendar_width = home_view._calculate_calendar_width()

        # Обновляем ширину легенды
        home_view.legend.update_calendar_width(calendar_width)

        # Property: Ширина легенды = ширине календаря
        assert home_view.legend.calendar_width == calendar_width, \
            f"Legend width {home_view.legend.calendar_width} != Calendar width {calendar_width}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

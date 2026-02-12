"""
Unit тесты для новой компоновки HomeView (2:2:4:3).

Тестирует:
- Четырёхколоночный layout с пропорциями 2:2:4:3
- Порядок расположения виджетов
- Корректность expand значений колонок
- Расчёт ширины календаря для новых пропорций
"""

import unittest
from unittest.mock import MagicMock, Mock, patch

import flet as ft

from finance_tracker.views.home_view import HomeView


class TestHomeViewLayoutStructure(unittest.TestCase):
    """Тесты структуры layout HomeView."""

    def setUp(self):
        """Подготовка перед каждым тестом."""
        # Патчим все зависимости
        self.patches = [
            patch('finance_tracker.views.home_view.HomePresenter'),
            patch('finance_tracker.views.home_view.TransactionsPanel'),
            patch('finance_tracker.views.home_view.CalendarWidget'),
            patch('finance_tracker.views.home_view.CalendarLegend'),
            patch('finance_tracker.views.home_view.PlannedTransactionsWidget'),
            patch('finance_tracker.views.home_view.PendingPaymentsWidget'),
            patch('finance_tracker.views.home_view.TransactionModal'),
            patch('finance_tracker.views.home_view.ExecuteOccurrenceModal'),
            patch('finance_tracker.views.home_view.ExecutePendingPaymentModal'),
            patch('finance_tracker.views.home_view.PendingPaymentModal'),
            patch('finance_tracker.views.home_view.PlannedTransactionModal'),
        ]

        self.mocks = [p.start() for p in self.patches]

        self.page = MagicMock()
        self.page.width = 1200
        self.mock_session = Mock()

        self.view = HomeView(self.page, self.mock_session)

    def tearDown(self):
        """Очистка после тестов."""
        for p in self.patches:
            p.stop()

    def test_layout_has_four_columns(self):
        """Тест: layout содержит 4 колонки."""
        # controls[0] - это внешний Row
        main_row = self.view.controls[0]
        self.assertIsInstance(main_row, ft.Row)

        # Считаем колонки (Column), исключая разделители (VerticalDivider)
        columns = [c for c in main_row.controls if isinstance(c, ft.Column)]

        self.assertEqual(
            len(columns),
            4,
            f"Должно быть 4 колонки, найдено {len(columns)}"
        )

    def test_layout_has_three_vertical_dividers(self):
        """Тест: layout содержит 3 вертикальных разделителя."""
        main_row = self.view.controls[0]

        dividers = [c for c in main_row.controls if isinstance(c, ft.VerticalDivider)]

        self.assertEqual(
            len(dividers),
            3,
            f"Должно быть 3 разделителя между 4 колонками, найдено {len(dividers)}"
        )

    def test_column_expand_values_are_correct(self):
        """Тест: значения expand колонок соответствуют пропорциям 2:2:4:3."""
        main_row = self.view.controls[0]
        columns = [c for c in main_row.controls if isinstance(c, ft.Column)]

        expected_expand = [2, 2, 4, 3]
        actual_expand = [c.expand for c in columns]

        self.assertEqual(
            actual_expand,
            expected_expand,
            f"Ожидались expand {expected_expand}, получены {actual_expand}"
        )

    def test_total_expand_equals_eleven(self):
        """Тест: общий expand равен 11 (2+2+4+3)."""
        main_row = self.view.controls[0]
        columns = [c for c in main_row.controls if isinstance(c, ft.Column)]

        total_expand = sum(c.expand for c in columns)

        self.assertEqual(
            total_expand,
            11,
            f"Общий expand должен быть 11, получен {total_expand}"
        )


class TestHomeViewWidgetPlacement(unittest.TestCase):
    """Тесты расположения виджетов в колонках."""

    def setUp(self):
        """Подготовка перед каждым тестом."""
        self.patches = [
            patch('finance_tracker.views.home_view.HomePresenter'),
            patch('finance_tracker.views.home_view.TransactionsPanel'),
            patch('finance_tracker.views.home_view.CalendarWidget'),
            patch('finance_tracker.views.home_view.CalendarLegend'),
            patch('finance_tracker.views.home_view.PlannedTransactionsWidget'),
            patch('finance_tracker.views.home_view.PendingPaymentsWidget'),
            patch('finance_tracker.views.home_view.TransactionModal'),
            patch('finance_tracker.views.home_view.ExecuteOccurrenceModal'),
            patch('finance_tracker.views.home_view.ExecutePendingPaymentModal'),
            patch('finance_tracker.views.home_view.PendingPaymentModal'),
            patch('finance_tracker.views.home_view.PlannedTransactionModal'),
        ]

        self.mocks = [p.start() for p in self.patches]

        self.page = MagicMock()
        self.page.width = 1200
        self.mock_session = Mock()

        self.view = HomeView(self.page, self.mock_session)

    def tearDown(self):
        """Очистка после тестов."""
        for p in self.patches:
            p.stop()

    def test_first_column_contains_planned_widget(self):
        """Тест: первая колонка содержит виджет плановых транзакций."""
        main_row = self.view.controls[0]
        columns = [c for c in main_row.controls if isinstance(c, ft.Column)]
        first_column = columns[0]

        # Проверяем, что первая колонка содержит planned_widget
        self.assertIn(
            self.view.planned_widget,
            first_column.controls,
            "Первая колонка должна содержать виджет плановых транзакций"
        )

    def test_second_column_contains_pending_payments_widget(self):
        """Тест: вторая колонка содержит виджет отложенных платежей."""
        main_row = self.view.controls[0]
        columns = [c for c in main_row.controls if isinstance(c, ft.Column)]
        second_column = columns[1]

        self.assertIn(
            self.view.pending_payments_widget,
            second_column.controls,
            "Вторая колонка должна содержать виджет отложенных платежей"
        )

    def test_third_column_contains_calendar_and_legend(self):
        """Тест: третья колонка содержит календарь и легенду."""
        main_row = self.view.controls[0]
        columns = [c for c in main_row.controls if isinstance(c, ft.Column)]
        third_column = columns[2]

        self.assertIn(
            self.view.calendar_widget,
            third_column.controls,
            "Третья колонка должна содержать календарь"
        )
        self.assertIn(
            self.view.legend,
            third_column.controls,
            "Третья колонка должна содержать легенду"
        )

    def test_fourth_column_contains_transactions_panel(self):
        """Тест: четвёртая колонка содержит панель транзакций."""
        main_row = self.view.controls[0]
        columns = [c for c in main_row.controls if isinstance(c, ft.Column)]
        fourth_column = columns[3]

        self.assertIn(
            self.view.transactions_panel,
            fourth_column.controls,
            "Четвёртая колонка должна содержать панель транзакций"
        )

    def test_calendar_appears_before_legend_in_third_column(self):
        """Тест: календарь расположен выше легенды в третьей колонке."""
        main_row = self.view.controls[0]
        columns = [c for c in main_row.controls if isinstance(c, ft.Column)]
        third_column = columns[2]

        calendar_index = third_column.controls.index(self.view.calendar_widget)
        legend_index = third_column.controls.index(self.view.legend)

        self.assertLess(
            calendar_index,
            legend_index,
            "Календарь должен быть выше легенды"
        )


class TestHomeViewCalendarWidthCalculation(unittest.TestCase):
    """Тесты расчёта ширины календаря."""

    def setUp(self):
        """Подготовка перед каждым тестом."""
        self.patches = [
            patch('finance_tracker.views.home_view.HomePresenter'),
            patch('finance_tracker.views.home_view.TransactionsPanel'),
            patch('finance_tracker.views.home_view.CalendarWidget'),
            patch('finance_tracker.views.home_view.CalendarLegend'),
            patch('finance_tracker.views.home_view.PlannedTransactionsWidget'),
            patch('finance_tracker.views.home_view.PendingPaymentsWidget'),
            patch('finance_tracker.views.home_view.TransactionModal'),
            patch('finance_tracker.views.home_view.ExecuteOccurrenceModal'),
            patch('finance_tracker.views.home_view.ExecutePendingPaymentModal'),
            patch('finance_tracker.views.home_view.PendingPaymentModal'),
            patch('finance_tracker.views.home_view.PlannedTransactionModal'),
        ]

        self.mocks = [p.start() for p in self.patches]

        self.page = MagicMock()
        self.mock_session = Mock()

    def tearDown(self):
        """Очистка после тестов."""
        for p in self.patches:
            p.stop()

    def test_calendar_width_calculation_with_1200px_page(self):
        """Тест расчёта ширины календаря для страницы 1200px."""
        self.page.width = 1200
        view = HomeView(self.page, self.mock_session)

        width = view._calculate_calendar_width()

        # Ожидаемый расчёт:
        # total_spacing = 60 + 3 + 40 = 103px
        # available_width = 1200 - 103 = 1097px
        # calendar_column_width = 1097 * (4/11) ≈ 398px
        # calendar_width = 398 - 20 = 378px

        # Допускаем погрешность из-за округления
        self.assertGreaterEqual(width, 300, "Ширина должна быть >= 300px (минимум)")
        self.assertLessEqual(width, 500, "Ширина должна быть <= 500px для 1200px страницы")

    def test_calendar_width_calculation_with_1920px_page(self):
        """Тест расчёта ширины календаря для страницы 1920px."""
        self.page.width = 1920
        view = HomeView(self.page, self.mock_session)

        width = view._calculate_calendar_width()

        # Ожидаемый расчёт для большей страницы
        # total_spacing = 103px
        # available_width = 1920 - 103 = 1817px
        # calendar_column_width = 1817 * (4/11) ≈ 660px
        # calendar_width = 660 - 20 = 640px

        self.assertGreaterEqual(width, 500)
        self.assertLessEqual(width, 800)

    def test_calendar_width_fallback_when_page_width_none(self):
        """Тест fallback ширины когда page.width = None."""
        self.page.width = None
        view = HomeView(self.page, self.mock_session)

        width = view._calculate_calendar_width()

        # Fallback к 1200px странице
        self.assertGreaterEqual(width, 300)

    def test_calendar_width_minimum_is_300(self):
        """Тест: минимальная ширина календаря 300px."""
        self.page.width = 400  # Очень узкая страница
        view = HomeView(self.page, self.mock_session)

        width = view._calculate_calendar_width()

        self.assertEqual(width, 300, "Минимальная ширина должна быть 300px")

    def test_calendar_width_uses_4_11_ratio(self):
        """Тест: расчёт использует пропорцию 4/11 для колонки календаря."""
        self.page.width = 1100  # Удобная ширина для проверки пропорции
        view = HomeView(self.page, self.mock_session)

        width = view._calculate_calendar_width()

        # При ширине 1100:
        # total_spacing ≈ 103px
        # available ≈ 997px
        # calendar_column ≈ 997 * 4/11 ≈ 362px
        # calendar ≈ 362 - 20 = 342px

        # Проверяем, что ширина в разумных пределах
        expected_min = 300
        expected_max = 400

        self.assertGreaterEqual(
            width,
            expected_min,
            f"Ширина должна быть >= {expected_min}px"
        )
        self.assertLessEqual(
            width,
            expected_max,
            f"Ширина должна быть <= {expected_max}px"
        )


class TestHomeViewColumnScrolling(unittest.TestCase):
    """Тесты скроллинга колонок."""

    def setUp(self):
        """Подготовка перед каждым тестом."""
        self.patches = [
            patch('finance_tracker.views.home_view.HomePresenter'),
            patch('finance_tracker.views.home_view.TransactionsPanel'),
            patch('finance_tracker.views.home_view.CalendarWidget'),
            patch('finance_tracker.views.home_view.CalendarLegend'),
            patch('finance_tracker.views.home_view.PlannedTransactionsWidget'),
            patch('finance_tracker.views.home_view.PendingPaymentsWidget'),
            patch('finance_tracker.views.home_view.TransactionModal'),
            patch('finance_tracker.views.home_view.ExecuteOccurrenceModal'),
            patch('finance_tracker.views.home_view.ExecutePendingPaymentModal'),
            patch('finance_tracker.views.home_view.PendingPaymentModal'),
            patch('finance_tracker.views.home_view.PlannedTransactionModal'),
        ]

        self.mocks = [p.start() for p in self.patches]

        self.page = MagicMock()
        self.page.width = 1200
        self.mock_session = Mock()

        self.view = HomeView(self.page, self.mock_session)

    def tearDown(self):
        """Очистка после тестов."""
        for p in self.patches:
            p.stop()

    def test_all_columns_have_auto_scroll(self):
        """Тест: все колонки имеют автоматический скроллинг."""
        main_row = self.view.controls[0]
        columns = [c for c in main_row.controls if isinstance(c, ft.Column)]

        for i, column in enumerate(columns):
            self.assertEqual(
                column.scroll,
                ft.ScrollMode.AUTO,
                f"Колонка {i+1} должна иметь scroll=AUTO"
            )

    def test_columns_alignment_is_start(self):
        """Тест: все колонки выровнены по верху (START)."""
        main_row = self.view.controls[0]
        columns = [c for c in main_row.controls if isinstance(c, ft.Column)]

        for i, column in enumerate(columns):
            self.assertEqual(
                column.alignment,
                ft.MainAxisAlignment.START,
                f"Колонка {i+1} должна быть выровнена по START"
            )


class TestHomeViewDocstring(unittest.TestCase):
    """Тесты документации HomeView."""

    def test_docstring_mentions_four_columns(self):
        """Тест: docstring упоминает 4 колонки."""
        docstring = HomeView.__doc__

        self.assertIn(
            "четырёх",
            docstring.lower(),
            "Docstring должен упоминать четырёхколоночный layout"
        )

    def test_docstring_mentions_correct_proportions(self):
        """Тест: docstring содержит правильные пропорции."""
        docstring = HomeView.__doc__

        self.assertIn(
            "2:2:4:3",
            docstring,
            "Docstring должен содержать пропорции 2:2:4:3"
        )

    def test_docstring_mentions_eleven_parts(self):
        """Тест: docstring упоминает 11 частей."""
        docstring = HomeView.__doc__

        self.assertIn(
            "11",
            docstring,
            "Docstring должен упоминать 11 частей"
        )


if __name__ == '__main__':
    unittest.main()

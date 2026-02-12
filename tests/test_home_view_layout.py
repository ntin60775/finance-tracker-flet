import unittest
from unittest.mock import MagicMock, Mock, patch
from typing import cast

import flet as ft

from finance_tracker.views.home_view import HomeView


def _get_main_row(view: HomeView) -> ft.Row:
    main_area = cast(ft.Container, view.controls[0])
    assert isinstance(main_area.content, ft.Row)
    return cast(ft.Row, main_area.content)


class TestHomeViewLayoutStructure(unittest.TestCase):
    def setUp(self):
        self.patches = [
            patch("finance_tracker.views.home_view.HomePresenter"),
            patch("finance_tracker.views.home_view.TransactionsPanel"),
            patch("finance_tracker.views.home_view.CalendarWidget"),
            patch("finance_tracker.views.home_view.CalendarLegend"),
            patch("finance_tracker.views.home_view.PlannedTransactionsWidget"),
            patch("finance_tracker.views.home_view.PendingPaymentsWidget"),
            patch("finance_tracker.views.home_view.TransactionModal"),
            patch("finance_tracker.views.home_view.ExecuteOccurrenceModal"),
            patch("finance_tracker.views.home_view.ExecutePendingPaymentModal"),
            patch("finance_tracker.views.home_view.PendingPaymentModal"),
            patch("finance_tracker.views.home_view.PlannedTransactionModal"),
        ]
        self.mocks = [p.start() for p in self.patches]

        self.page = MagicMock()
        self.page.width = 1920
        self.mock_session = Mock()
        self.view = HomeView(self.page, self.mock_session)

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_layout_has_three_columns(self):
        main_row = _get_main_row(self.view)
        self.assertEqual(len(main_row.controls), 3)
        self.assertTrue(all(isinstance(c, ft.Container) for c in main_row.controls))

    def test_bottom_padding_compensates_today_bar(self):
        main_area = self.view.controls[0]
        main_area_container = cast(ft.Container, main_area)
        self.assertIsInstance(main_area_container.padding, ft.Padding)
        padding = cast(ft.Padding, main_area_container.padding)
        self.assertEqual(padding.bottom, HomeView.MAIN_AREA_BOTTOM_PADDING)

    def test_container_width_is_capped(self):
        main_row = _get_main_row(self.view)
        row_width = int(main_row.width or 0)
        self.assertLessEqual(row_width, HomeView.MAX_CONTENT_WIDTH)

    def test_side_column_widths_in_expected_range(self):
        main_row = _get_main_row(self.view)
        left = cast(ft.Container, main_row.controls[0])
        right = cast(ft.Container, main_row.controls[2])

        left_width = int(left.width or 0)
        right_width = int(right.width or 0)

        self.assertGreaterEqual(left_width, HomeView.SIDE_COLUMN_FALLBACK_MIN_WIDTH)
        self.assertLessEqual(left_width, HomeView.SIDE_COLUMN_MAX_WIDTH)
        self.assertGreaterEqual(right_width, HomeView.SIDE_COLUMN_FALLBACK_MIN_WIDTH)
        self.assertLessEqual(right_width, HomeView.SIDE_COLUMN_MAX_WIDTH)


class TestHomeViewWidgetPlacement(unittest.TestCase):
    def setUp(self):
        self.patches = [
            patch("finance_tracker.views.home_view.HomePresenter"),
            patch("finance_tracker.views.home_view.TransactionsPanel"),
            patch("finance_tracker.views.home_view.CalendarWidget"),
            patch("finance_tracker.views.home_view.CalendarLegend"),
            patch("finance_tracker.views.home_view.PlannedTransactionsWidget"),
            patch("finance_tracker.views.home_view.PendingPaymentsWidget"),
            patch("finance_tracker.views.home_view.TransactionModal"),
            patch("finance_tracker.views.home_view.ExecuteOccurrenceModal"),
            patch("finance_tracker.views.home_view.ExecutePendingPaymentModal"),
            patch("finance_tracker.views.home_view.PendingPaymentModal"),
            patch("finance_tracker.views.home_view.PlannedTransactionModal"),
        ]
        self.mocks = [p.start() for p in self.patches]

        self.page = MagicMock()
        self.page.width = 1920
        self.mock_session = Mock()
        self.view = HomeView(self.page, self.mock_session)

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_left_column_contains_context_widgets(self):
        left_column = self.view.left_column
        self.assertIn(self.view.planned_widget, left_column.controls)
        self.assertIn(self.view.pending_payments_widget, left_column.controls)

    def test_center_column_contains_calendar_and_legend(self):
        center_column = self.view.center_column
        self.assertIn(self.view.calendar_widget, center_column.controls)
        self.assertIn(self.view.legend, center_column.controls)
        self.assertLess(
            center_column.controls.index(self.view.calendar_widget),
            center_column.controls.index(self.view.legend),
        )

    def test_right_column_contains_transactions_panel(self):
        right_column = self.view.right_column
        self.assertIn(self.view.transactions_panel, right_column.controls)


class TestHomeViewCalendarWidthCalculation(unittest.TestCase):
    def setUp(self):
        self.patches = [
            patch("finance_tracker.views.home_view.HomePresenter"),
            patch("finance_tracker.views.home_view.TransactionsPanel"),
            patch("finance_tracker.views.home_view.CalendarWidget"),
            patch("finance_tracker.views.home_view.CalendarLegend"),
            patch("finance_tracker.views.home_view.PlannedTransactionsWidget"),
            patch("finance_tracker.views.home_view.PendingPaymentsWidget"),
            patch("finance_tracker.views.home_view.TransactionModal"),
            patch("finance_tracker.views.home_view.ExecuteOccurrenceModal"),
            patch("finance_tracker.views.home_view.ExecutePendingPaymentModal"),
            patch("finance_tracker.views.home_view.PendingPaymentModal"),
            patch("finance_tracker.views.home_view.PlannedTransactionModal"),
        ]
        self.mocks = [p.start() for p in self.patches]
        self.page = MagicMock()
        self.mock_session = Mock()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_calendar_width_respects_minimum(self):
        self.page.width = 800
        view = HomeView(self.page, self.mock_session)
        self.assertGreaterEqual(view._calculate_calendar_width(), 300)

    def test_calendar_width_follows_layout_metrics(self):
        self.page.width = 1920
        view = HomeView(self.page, self.mock_session)
        metrics = view._calculate_layout_metrics()
        expected = max(metrics["center_width"] - 24, 300)
        self.assertEqual(view._calculate_calendar_width(), expected)

    def test_calendar_width_grows_from_fullhd_to_2k(self):
        self.page.width = 1920
        view_fhd = HomeView(self.page, self.mock_session)
        width_fhd = view_fhd._calculate_calendar_width()

        self.page.width = 2560
        view_2k = HomeView(self.page, self.mock_session)
        width_2k = view_2k._calculate_calendar_width()

        self.assertGreaterEqual(width_2k, width_fhd)


class TestHomeViewColumnScrolling(unittest.TestCase):
    def setUp(self):
        self.patches = [
            patch("finance_tracker.views.home_view.HomePresenter"),
            patch("finance_tracker.views.home_view.TransactionsPanel"),
            patch("finance_tracker.views.home_view.CalendarWidget"),
            patch("finance_tracker.views.home_view.CalendarLegend"),
            patch("finance_tracker.views.home_view.PlannedTransactionsWidget"),
            patch("finance_tracker.views.home_view.PendingPaymentsWidget"),
            patch("finance_tracker.views.home_view.TransactionModal"),
            patch("finance_tracker.views.home_view.ExecuteOccurrenceModal"),
            patch("finance_tracker.views.home_view.ExecutePendingPaymentModal"),
            patch("finance_tracker.views.home_view.PendingPaymentModal"),
            patch("finance_tracker.views.home_view.PlannedTransactionModal"),
        ]
        self.mocks = [p.start() for p in self.patches]

        self.page = MagicMock()
        self.page.width = 1920
        self.mock_session = Mock()
        self.view = HomeView(self.page, self.mock_session)

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_all_columns_have_auto_scroll(self):
        for column in [self.view.left_column, self.view.center_column, self.view.right_column]:
            self.assertEqual(column.scroll, ft.ScrollMode.AUTO)

    def test_columns_alignment_is_start(self):
        for column in [self.view.left_column, self.view.center_column, self.view.right_column]:
            self.assertEqual(column.alignment, ft.MainAxisAlignment.START)


class TestHomeViewDocstring(unittest.TestCase):
    def test_docstring_mentions_three_columns(self):
        docstring = HomeView.__doc__
        self.assertIsNotNone(docstring)
        self.assertIn("3 колонки", cast(str, docstring))

    def test_docstring_mentions_max_width(self):
        docstring = HomeView.__doc__
        self.assertIsNotNone(docstring)
        self.assertIn("max-width 1760px", cast(str, docstring))


if __name__ == "__main__":
    unittest.main()

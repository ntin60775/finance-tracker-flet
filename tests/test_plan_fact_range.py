import unittest
from datetime import date
from unittest.mock import Mock

from finance_tracker.views.plan_fact_view import PlanFactView
from test_view_base import ViewTestBase


class TestPlanFactRange(ViewTestBase):
    def setUp(self):
        super().setUp()
        self.mock_db_cm = self.create_mock_db_context()
        self.mock_get_db = self.add_patcher(
            "finance_tracker.views.plan_fact_view.get_db",
            return_value=self.mock_db_cm,
        )
        self.mock_get_plan_fact_analysis = self.add_patcher(
            "finance_tracker.views.plan_fact_view.get_plan_fact_analysis",
            return_value={
                "total_occurrences": 0,
                "executed_count": 0,
                "skipped_count": 0,
                "pending_count": 0,
                "avg_amount_deviation": 0,
                "avg_date_deviation_days": 0.0,
                "on_time_percentage": 0.0,
                "skipped_percentage": 0.0,
                "occurrences": [],
            },
        )
        self.mock_get_all_categories = self.add_patcher(
            "finance_tracker.views.plan_fact_view.get_all_categories",
            return_value=[],
        )
        self.view = PlanFactView()
        self.view.page = self.page

    def test_preset_application_updates_date_range(self):
        preset_start = date(2025, 1, 5)
        preset_end = date(2025, 1, 25)
        self.view._get_preset_range = Mock(return_value=(preset_start, preset_end))
        self.mock_get_plan_fact_analysis.reset_mock()
        self.page.open.reset_mock()
        self.page.close.reset_mock()

        self.view._open_date_picker(None)

        dialog = self.page.open.call_args[0][0]
        preset_button = dialog.content.controls[0].controls[0]
        apply_button = dialog.actions[1]
        preset_button.on_click(None)
        apply_button.on_click(None)

        self.view._get_preset_range.assert_called_once_with("current_month")
        self.assertEqual(self.view.start_date, preset_start)
        self.assertEqual(self.view.end_date, preset_end)
        self.page.close.assert_called_once_with(dialog)
        self.assert_service_called_once(
            self.mock_get_plan_fact_analysis,
            self.mock_session,
            preset_start,
            preset_end,
            None,
        )

    def test_comparison_toggle_calculates_and_clears_previous_period(self):
        self.view.start_date = date(2025, 4, 10)
        self.view.end_date = date(2025, 4, 20)
        self.mock_get_plan_fact_analysis.reset_mock()

        self.view.comparison_checkbox.value = True
        self.view._on_comparison_toggle(None)

        self.assertTrue(self.view.comparison_enabled)
        self.assertEqual(self.view.comparison_start_date, date(2025, 3, 30))
        self.assertEqual(self.view.comparison_end_date, date(2025, 4, 9))

        self.view.comparison_checkbox.value = False
        self.view._on_comparison_toggle(None)

        self.assertFalse(self.view.comparison_enabled)
        self.assertIsNone(self.view.comparison_start_date)
        self.assertIsNone(self.view.comparison_end_date)
        self.assertEqual(self.mock_get_plan_fact_analysis.call_count, 2)

    def test_saved_filter_restore_affects_next_data_load(self):
        saved_start = date(2025, 2, 1)
        saved_end = date(2025, 2, 28)
        saved_category = 7

        self.view.start_date = saved_start
        self.view.end_date = saved_end
        self.view.selected_category_id = saved_category
        self.view.comparison_enabled = True
        self.view._apply_comparison_state()
        expected_comparison_start = self.view.comparison_start_date
        expected_comparison_end = self.view.comparison_end_date
        self.view._save_filters_state()

        self.view.start_date = date(2025, 5, 1)
        self.view.end_date = date(2025, 5, 31)
        self.view.selected_category_id = None
        self.view.comparison_enabled = False
        self.view.comparison_start_date = None
        self.view.comparison_end_date = None

        self.view._restore_filters_state()

        self.assertEqual(self.view.start_date, saved_start)
        self.assertEqual(self.view.end_date, saved_end)
        self.assertEqual(self.view.selected_category_id, saved_category)
        self.assertTrue(self.view.comparison_enabled)
        self.assertEqual(self.view.comparison_start_date, expected_comparison_start)
        self.assertEqual(self.view.comparison_end_date, expected_comparison_end)

        self.mock_get_plan_fact_analysis.reset_mock()
        self.view._load_data()
        self.assert_service_called_once(
            self.mock_get_plan_fact_analysis,
            self.mock_session,
            saved_start,
            saved_end,
            saved_category,
        )


if __name__ == "__main__":
    unittest.main()

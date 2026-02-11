import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

import flet as ft

from finance_tracker.models import PlannedTransactionDB, CategoryDB
from finance_tracker.models.enums import TransactionType
from finance_tracker.services.obligations_service import ObligationMetrics
from finance_tracker.utils.exceptions import BusinessLogicError
from finance_tracker.views.planned_transactions_view import PlannedTransactionsView
from test_view_base import ViewTestBase


class TestObligationsUI(ViewTestBase):
    def setUp(self):
        super().setUp()

        self.mock_db_cm = self.create_mock_db_context()
        self.add_patcher(
            "finance_tracker.views.planned_transactions_view.get_db_session",
            return_value=self.mock_db_cm,
        )

        self.mock_create_obligation = self.add_patcher(
            "finance_tracker.views.planned_transactions_view.create_obligation"
        )
        self.mock_update_target = self.add_patcher(
            "finance_tracker.views.planned_transactions_view.update_obligation_target"
        )
        self.mock_get_metrics_for_month = self.add_patcher(
            "finance_tracker.views.planned_transactions_view.get_obligations_metrics_for_month",
            return_value=[],
        )
        self.mock_link_tx = self.add_patcher(
            "finance_tracker.views.planned_transactions_view.link_transaction_to_obligation"
        )

        self.view = PlannedTransactionsView(self.page)

    def test_obligation_creation_calls_service_and_shows_snack(self):
        self.view.refresh_data = Mock()

        metrics = ObligationMetrics(
            obligation_id="ob1",
            month=date(2026, 2, 1),
            target=Decimal("1000.00"),
            paid=Decimal("0.00"),
            remaining=Decimal("1000.00"),
        )
        self.mock_create_obligation.return_value = metrics

        payload = {
            "obligation_id": None,
            "target_amount": Decimal("1000.00"),
            "target_month": date(2026, 2, 1),
            "category_id": "cat1",
            "type": TransactionType.EXPENSE,
            "description": "Кредит",
        }

        self.view._on_obligation_saved(payload)

        self.mock_create_obligation.assert_called_once_with(
            self.mock_session,
            category_id="cat1",
            target_amount=Decimal("1000.00"),
            target_month=date(2026, 2, 1),
            t_type=TransactionType.EXPENSE,
            description="Кредит",
        )

        opened = [c.args[0] for c in self.page.open.call_args_list]
        self.assertTrue(any(isinstance(x, ft.SnackBar) for x in opened))
        self.assertTrue(
            any(
                isinstance(x, ft.SnackBar)
                and isinstance(x.content, ft.Text)
                and x.content.value == "Обязательство создано"
                for x in opened
            )
        )
        self.view.refresh_data.assert_called_once()

    def test_grouped_obligations_block_renders_metrics_text(self):
        metrics = ObligationMetrics(
            obligation_id="ob1",
            month=date(2026, 2, 1),
            target=Decimal("1000.00"),
            paid=Decimal("250.00"),
            remaining=Decimal("750.00"),
        )
        self.mock_get_metrics_for_month.return_value = [metrics]

        obligation = Mock(spec=PlannedTransactionDB)
        obligation.id = "ob1"
        obligation.category_id = "cat1"
        obligation.description = "Погашение кредита"
        obligation.type = TransactionType.EXPENSE

        category = Mock(spec=CategoryDB)
        category.name = "Кредиты"

        planned_query = Mock()
        planned_query.filter_by.return_value.first.return_value = obligation

        category_query = Mock()
        category_query.filter_by.return_value.first.return_value = category

        def query_side_effect(model):
            if model is PlannedTransactionDB:
                return planned_query
            if model is CategoryDB:
                return category_query
            return Mock()

        self.mock_session.query.side_effect = query_side_effect

        self.view.obligations_month = date(2026, 2, 1)
        self.view._refresh_obligations_block()

        self.assertEqual(len(self.view.obligations_list.controls), 1)
        card = self.view.obligations_list.controls[0]
        metrics_text = card.content.controls[1]
        self.assertIsInstance(metrics_text, ft.Text)
        self.assertIn("цель:", metrics_text.value)
        self.assertIn("оплачено:", metrics_text.value)
        self.assertIn("остаток:", metrics_text.value)

    def test_link_flow_shows_warning_when_amount_exceeds_remaining(self):
        self.mock_link_tx.side_effect = BusinessLogicError(
            "Нельзя привязать транзакцию к obligation: сумма 100 превышает остаток 50"
        )

        metrics = ObligationMetrics(
            obligation_id="ob1",
            month=date(2026, 2, 1),
            target=Decimal("100.00"),
            paid=Decimal("50.00"),
            remaining=Decimal("50.00"),
        )
        self.mock_get_metrics_for_month.return_value = [metrics]

        obligation = Mock(spec=PlannedTransactionDB)
        obligation.id = "ob1"
        obligation.description = "Погашение"

        planned_query = Mock()
        planned_query.filter_by.return_value.first.return_value = obligation
        self.mock_session.query.side_effect = lambda model: planned_query

        self.view.open_link_to_obligation_dialog(
            transaction_id="tx1",
            category_id="cat1",
            month=date(2026, 2, 15),
        )

        self.page.open.assert_called()
        dlg = self.page.open.call_args_list[0].args[0]
        self.assertIsInstance(dlg, ft.AlertDialog)

        obligation_dropdown = dlg.content.controls[1]
        obligation_dropdown.value = "ob1"

        link_button = dlg.actions[1]
        link_button.on_click(None)

        opened = [c.args[0] for c in self.page.open.call_args_list]
        self.assertTrue(
            any(
                isinstance(x, ft.SnackBar)
                and isinstance(x.content, ft.Text)
                and "разбейте транзакцию вручную" in x.content.value
                for x in opened
            )
        )


if __name__ == "__main__":
    unittest.main()

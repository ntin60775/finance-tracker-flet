import datetime
import unittest
from unittest.mock import MagicMock, Mock, patch

import flet as ft

from finance_tracker.views.home_view import HomeView


def _find_by_key(root: object, key: str):
    queue = [root]
    seen_ids = set()

    while queue:
        ctrl = queue.pop(0)
        if ctrl is None:
            continue

        ctrl_id = id(ctrl)
        if ctrl_id in seen_ids:
            continue
        seen_ids.add(ctrl_id)

        if getattr(ctrl, "key", None) == key:
            return ctrl

        children = []
        if hasattr(ctrl, "controls") and isinstance(getattr(ctrl, "controls"), list):
            children.extend(getattr(ctrl, "controls"))

        if hasattr(ctrl, "content") and getattr(ctrl, "content") is not None:
            children.append(getattr(ctrl, "content"))

        queue.extend(children)

    return None


class TestTodaySection(unittest.TestCase):
    def setUp(self):
        self.presenter_patcher = patch("finance_tracker.views.home_view.HomePresenter")
        self.transactions_panel_patcher = patch("finance_tracker.views.home_view.TransactionsPanel")

        self.presenter_patcher.start()
        self.transactions_panel_patcher.start()

        self.page = MagicMock()
        self.page.open = Mock()
        self.page.close = Mock()
        self.session = Mock()

    def tearDown(self):
        self.presenter_patcher.stop()
        self.transactions_panel_patcher.stop()

    def test_today_section_controls_present(self):
        view = HomeView(self.page, self.session, navigate_callback=Mock())

        assert _find_by_key(view, "today_section") is not None
        assert _find_by_key(view, "today_balance_value") is not None
        assert _find_by_key(view, "today_mandatory_value") is not None
        assert _find_by_key(view, "today_risk_7_value") is not None
        assert _find_by_key(view, "today_risk_30_value") is not None

        assert _find_by_key(view, "today_action_add_tx") is not None
        assert _find_by_key(view, "today_action_mark_payment") is not None
        assert _find_by_key(view, "today_action_open_risk") is not None

    def test_quick_action_add_transaction_invokes_callback(self):
        view = HomeView(self.page, self.session, navigate_callback=Mock())
        view.open_add_transaction_modal = Mock()

        btn = _find_by_key(view, "today_action_add_tx")
        assert btn is not None
        assert callable(btn.on_click)

        btn.on_click(Mock())
        view.open_add_transaction_modal.assert_called_once()

    def test_quick_action_mark_payment_navigates_to_pending_payments(self):
        navigate = Mock()
        view = HomeView(self.page, self.session, navigate_callback=navigate)

        btn = _find_by_key(view, "today_action_mark_payment")
        assert btn is not None
        btn.on_click(Mock())

        navigate.assert_called_once_with(3)

    def test_quick_action_open_risk_opens_dialog(self):
        view = HomeView(self.page, self.session, navigate_callback=Mock())
        view._today_cash_gaps_30 = [
            datetime.date(2025, 1, 2),
            datetime.date(2025, 1, 5),
        ]

        btn = _find_by_key(view, "today_action_open_risk")
        assert btn is not None
        btn.on_click(Mock())

        self.page.open.assert_called_once()
        opened = self.page.open.call_args[0][0]
        assert isinstance(opened, ft.AlertDialog)

    def test_update_transactions_refreshes_today_metrics_only_for_today(self):
        view = HomeView(self.page, self.session, navigate_callback=Mock())
        view.refresh_today_metrics = Mock()

        view.update_transactions(datetime.date(2000, 1, 1), [], [])
        view.refresh_today_metrics.assert_not_called()

        view.update_transactions(datetime.date.today(), [], [])
        view.refresh_today_metrics.assert_called_once()

"""
Тесты для HomeView.
"""
import unittest
from unittest.mock import Mock, MagicMock, patch, ANY
import datetime

from finance_tracker.views.home_view import HomeView

class TestHomeView(unittest.TestCase):
    """Тесты для HomeView."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_get_db_patcher = patch('finance_tracker.views.home_view.get_db_session')
        self.mock_get_transactions_by_date_patcher = patch('finance_tracker.views.home_view.get_transactions_by_date')
        self.mock_get_by_date_range_patcher = patch('finance_tracker.views.home_view.get_by_date_range')
        self.mock_get_pending_occurrences_patcher = patch('finance_tracker.views.home_view.get_pending_occurrences')
        self.mock_get_occurrences_by_date_patcher = patch('finance_tracker.views.home_view.get_occurrences_by_date')
        self.mock_get_occurrences_by_date_range_patcher = patch('finance_tracker.views.home_view.get_occurrences_by_date_range')
        self.mock_get_all_pending_payments_patcher = patch('finance_tracker.views.home_view.get_all_pending_payments')
        self.mock_get_pending_payments_statistics_patcher = patch('finance_tracker.views.home_view.get_pending_payments_statistics')
        self.mock_transactions_panel_patcher = patch('finance_tracker.views.home_view.TransactionsPanel')

        self.mock_get_db = self.mock_get_db_patcher.start()
        self.mock_get_transactions_by_date = self.mock_get_transactions_by_date_patcher.start()
        self.mock_get_by_date_range = self.mock_get_by_date_range_patcher.start()
        self.mock_get_pending_occurrences = self.mock_get_pending_occurrences_patcher.start()
        self.mock_get_occurrences_by_date = self.mock_get_occurrences_by_date_patcher.start()
        self.mock_get_occurrences_by_date_range = self.mock_get_occurrences_by_date_range_patcher.start()
        self.mock_get_all_pending_payments = self.mock_get_all_pending_payments_patcher.start()
        self.mock_get_pending_payments_statistics = self.mock_get_pending_payments_statistics_patcher.start()
        self.mock_transactions_panel = self.mock_transactions_panel_patcher.start()

        self.page = MagicMock()
        
        # Мокируем сессию БД
        self.mock_session = Mock()
        self.mock_get_db.return_value.__enter__.return_value = self.mock_session
        
        # Мокаем возвращаемые значения по умолчанию
        self.mock_get_transactions_by_date.return_value = []
        self.mock_get_by_date_range.return_value = []
        self.mock_get_pending_occurrences.return_value = []
        self.mock_get_occurrences_by_date.return_value = []
        self.mock_get_occurrences_by_date_range.return_value = []
        self.mock_get_all_pending_payments.return_value = []
        self.mock_get_pending_payments_statistics.return_value = (0, 0)

        # Создаем экземпляр HomeView
        self.view = HomeView(self.page)

    def tearDown(self):
        self.mock_get_db_patcher.stop()
        self.mock_get_transactions_by_date_patcher.stop()
        self.mock_get_by_date_range_patcher.stop()
        self.mock_get_pending_occurrences_patcher.stop()
        self.mock_get_occurrences_by_date_patcher.stop()
        self.mock_get_occurrences_by_date_range_patcher.stop()
        self.mock_get_all_pending_payments_patcher.stop()
        self.mock_get_pending_payments_statistics_patcher.stop()
        self.mock_transactions_panel_patcher.stop()
        
    def test_initialization(self):
        """Тест инициализации HomeView."""
        self.assertIsInstance(self.view, HomeView)
        self.assertEqual(self.view.page, self.page)
        self.assertIsNotNone(self.view.calendar_widget)
        self.assertIsNotNone(self.view.transactions_panel)
        # Проверяем, что load_data был вызван при инициализации
        self.mock_get_by_date_range.assert_called()
        self.mock_get_occurrences_by_date_range.assert_called()

    def test_load_data_calls_services(self):
        """Тест, что load_data вызывает все необходимые сервисы."""
        self.view.load_data()
        
        self.mock_get_by_date_range.assert_called_with(self.mock_session, ANY, ANY)
        self.mock_get_occurrences_by_date_range.assert_called_with(self.mock_session, ANY, ANY)
        self.mock_get_transactions_by_date.assert_called_with(self.mock_session, self.view.selected_date)
        self.mock_get_occurrences_by_date.assert_called_with(self.mock_session, self.view.selected_date)
        self.mock_get_pending_occurrences.assert_called_with(self.mock_session)
        self.mock_get_all_pending_payments.assert_called_with(self.mock_session)
        self.mock_get_pending_payments_statistics.assert_called_with(self.mock_session)
    
    def test_on_date_selected(self):
        """Тест выбора даты в календаре."""
        new_date = datetime.date(2024, 10, 5)
        
        self.view.on_date_selected(new_date)
        
        self.assertEqual(self.view.selected_date, new_date)
        self.mock_get_transactions_by_date.assert_called_with(self.mock_session, new_date)
        self.mock_get_occurrences_by_date.assert_called_with(self.mock_session, new_date)
        # Проверяем, что transactions_panel.set_data был вызван
        self.mock_transactions_panel.return_value.set_data.assert_called_with(new_date, [], [])


if __name__ == '__main__':
    unittest.main()

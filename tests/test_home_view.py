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
        self.mock_presenter_patcher = patch('finance_tracker.views.home_view.HomePresenter')
        self.mock_transactions_panel_patcher = patch('finance_tracker.views.home_view.TransactionsPanel')

        self.mock_presenter = self.mock_presenter_patcher.start()
        self.mock_transactions_panel = self.mock_transactions_panel_patcher.start()

        self.page = MagicMock()

        # Мокируем сессию БД
        self.mock_session = Mock()

        # Создаем экземпляр HomeView с передачей Session через DI
        self.view = HomeView(self.page, self.mock_session)

    def tearDown(self):
        self.mock_presenter_patcher.stop()
        self.mock_transactions_panel_patcher.stop()
        
    def test_initialization(self):
        """Тест инициализации HomeView."""
        self.assertIsInstance(self.view, HomeView)
        self.assertEqual(self.view.page, self.page)
        self.assertEqual(self.view.session, self.mock_session)
        self.assertIsNotNone(self.view.calendar_widget)
        self.assertIsNotNone(self.view.transactions_panel)
        # Проверяем, что HomePresenter был создан
        self.mock_presenter.assert_called_once_with(self.mock_session, self.view)
        # Проверяем, что load_initial_data был вызван при инициализации
        self.mock_presenter.return_value.load_initial_data.assert_called_once()

    def test_load_data_calls_services(self):
        """Тест, что данные загружаются через Presenter."""
        # Проверяем, что при инициализации Presenter вызывает load_initial_data
        self.mock_presenter.return_value.load_initial_data.assert_called_once()

    def test_on_date_selected(self):
        """Тест выбора даты в календаре делегирует в Presenter."""
        new_date = datetime.date(2024, 10, 5)

        self.view.on_date_selected(new_date)

        # Проверяем, что вызван метод Presenter
        self.mock_presenter.return_value.on_date_selected.assert_called_once_with(new_date)


if __name__ == '__main__':
    unittest.main()

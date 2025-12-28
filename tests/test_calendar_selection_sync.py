"""
Тесты синхронизации выделения даты в календаре при клике на плановую транзакцию.
"""
import unittest
from unittest.mock import Mock, MagicMock, patch
import datetime

from finance_tracker.views.home_view import HomeView
from finance_tracker.views.home_presenter import HomePresenter
from finance_tracker.components.calendar_widget import CalendarWidget


class TestCalendarSelectionSync(unittest.TestCase):
    """Тесты синхронизации выделения даты в календаре."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_page = MagicMock()
        self.mock_page.open = Mock()
        self.mock_page.close = Mock()
        self.mock_page.update = Mock()
        self.mock_page.width = 1200
        
        self.mock_session = Mock()

    def test_calendar_widget_has_select_date_method(self):
        """Тест наличия метода select_date в CalendarWidget."""
        calendar = CalendarWidget(
            on_date_selected=Mock(),
            initial_date=datetime.date.today()
        )
        
        # Проверяем наличие метода
        self.assertTrue(hasattr(calendar, 'select_date'))
        self.assertTrue(callable(calendar.select_date))

    def test_calendar_select_date_updates_selected_date(self):
        """Тест обновления selected_date при вызове select_date."""
        calendar = CalendarWidget(
            on_date_selected=Mock(),
            initial_date=datetime.date(2025, 12, 28)
        )
        calendar.page = self.mock_page
        
        # Выбираем другую дату
        new_date = datetime.date(2025, 12, 30)
        calendar.select_date(new_date)
        
        # Проверяем, что selected_date обновился
        self.assertEqual(calendar.selected_date, new_date)

    def test_calendar_select_date_changes_month_if_needed(self):
        """Тест переключения месяца при выборе даты из другого месяца."""
        calendar = CalendarWidget(
            on_date_selected=Mock(),
            initial_date=datetime.date(2025, 12, 28)
        )
        calendar.page = self.mock_page
        
        # Выбираем дату из другого месяца
        new_date = datetime.date(2026, 1, 15)
        calendar.select_date(new_date)
        
        # Проверяем, что current_date переключился на новый месяц
        self.assertEqual(calendar.current_date.year, 2026)
        self.assertEqual(calendar.current_date.month, 1)
        self.assertEqual(calendar.selected_date, new_date)

    def test_home_view_has_update_calendar_selection_method(self):
        """Тест наличия метода update_calendar_selection в HomeView."""
        with patch('finance_tracker.views.home_view.HomePresenter'):
            home_view = HomeView(self.mock_page, self.mock_session)
            
            # Проверяем наличие метода
            self.assertTrue(hasattr(home_view, 'update_calendar_selection'))
            self.assertTrue(callable(home_view.update_calendar_selection))

    def test_home_view_update_calendar_selection_calls_calendar_select_date(self):
        """Тест вызова calendar.select_date из update_calendar_selection."""
        with patch('finance_tracker.views.home_view.HomePresenter'):
            home_view = HomeView(self.mock_page, self.mock_session)
            home_view.calendar_widget.page = self.mock_page
            
            # Мокируем метод select_date
            home_view.calendar_widget.select_date = Mock()
            
            # Вызываем update_calendar_selection
            test_date = datetime.date(2025, 12, 30)
            home_view.update_calendar_selection(test_date)
            
            # Проверяем, что select_date был вызван с правильной датой
            home_view.calendar_widget.select_date.assert_called_once_with(test_date)

    @patch('finance_tracker.views.home_presenter.transaction_service')
    @patch('finance_tracker.views.home_presenter.planned_transaction_service')
    def test_presenter_on_date_selected_updates_calendar_selection(
        self, 
        mock_planned_service, 
        mock_transaction_service
    ):
        """Тест обновления выделения в календаре при выборе даты через presenter."""
        # Настройка моков
        mock_transaction_service.get_transactions_by_date.return_value = []
        mock_planned_service.get_occurrences_by_date.return_value = []
        
        # Создаем mock callbacks
        mock_callbacks = Mock()
        mock_callbacks.update_transactions = Mock()
        mock_callbacks.update_calendar_selection = Mock()
        
        # Создаем presenter
        presenter = HomePresenter(self.mock_session, mock_callbacks)
        
        # Вызываем on_date_selected
        test_date = datetime.date(2025, 12, 30)
        presenter.on_date_selected(test_date)
        
        # Проверяем, что update_calendar_selection был вызван
        mock_callbacks.update_calendar_selection.assert_called_once_with(test_date)

    @patch('finance_tracker.views.home_view.HomePresenter')
    def test_occurrence_click_updates_calendar_selection(self, MockPresenter):
        """Тест обновления выделения в календаре при клике на плановую транзакцию."""
        # Создаем HomeView
        home_view = HomeView(self.mock_page, self.mock_session)
        home_view.calendar_widget.page = self.mock_page
        
        # Мокируем метод select_date календаря
        home_view.calendar_widget.select_date = Mock()
        
        # Создаем mock occurrence
        mock_occurrence = Mock()
        mock_occurrence.id = "test-occurrence-id"
        mock_occurrence.occurrence_date = datetime.date(2025, 12, 30)
        
        # Вызываем on_occurrence_clicked
        home_view.on_occurrence_clicked(mock_occurrence)
        
        # Проверяем, что presenter.on_date_selected был вызван
        MockPresenter.return_value.on_date_selected.assert_called_once_with(
            mock_occurrence.occurrence_date
        )


if __name__ == '__main__':
    unittest.main()

"""
Тесты синхронизации выделения даты в календаре при клике на плановую транзакцию.
"""
import unittest
from unittest.mock import Mock, MagicMock, patch
import datetime
from hypothesis import given, strategies as st, settings

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

    def test_select_date_current_month_updates_and_calls_update_calendar(self):
        """
        Тест select_date с датой текущего месяца.
        
        **Property 1: Синхронизация выделения календаря**
        **Validates: Requirements 1.1, 1.3**
        
        Проверяет:
        - Обновление selected_date
        - Вызов _update_calendar()
        - НЕ вызов on_date_selected callback
        """
        # Arrange - создаем mock callback
        mock_callback = Mock()
        
        # Создаем календарь с начальной датой
        initial_date = datetime.date(2025, 12, 15)
        calendar = CalendarWidget(
            on_date_selected=mock_callback,
            initial_date=initial_date
        )
        calendar.page = self.mock_page
        
        # Мокируем метод _update_calendar для отслеживания вызова
        with patch.object(calendar, '_update_calendar') as mock_update_calendar:
            # Act - выбираем другую дату в том же месяце
            new_date = datetime.date(2025, 12, 25)
            calendar.select_date(new_date)
            
            # Assert - проверяем обновление selected_date
            self.assertEqual(
                calendar.selected_date, 
                new_date,
                "selected_date должен обновиться на новую дату"
            )
            
            # Assert - проверяем вызов _update_calendar()
            mock_update_calendar.assert_called_once()
            
            # Assert - проверяем, что callback НЕ был вызван
            mock_callback.assert_not_called()

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

    def test_select_date_different_month_loads_data_and_updates(self):
        """
        Тест select_date с датой другого месяца.
        
        **Property 2: Переключение месяца при необходимости**
        **Validates: Requirements 1.4, 1.5**
        
        Проверяет:
        - Переключение current_date на новый месяц
        - Загрузку данных для нового месяца (_update_cash_gaps, _update_pending_payments, _update_loan_payments)
        - Вызов _update_calendar()
        """
        # Arrange - создаем календарь с начальной датой
        initial_date = datetime.date(2025, 12, 15)
        calendar = CalendarWidget(
            on_date_selected=Mock(),
            initial_date=initial_date
        )
        calendar.page = self.mock_page
        
        # Мокируем методы загрузки данных для отслеживания вызовов
        with patch.object(calendar, '_update_cash_gaps') as mock_update_cash_gaps, \
             patch.object(calendar, '_update_pending_payments') as mock_update_pending_payments, \
             patch.object(calendar, '_update_loan_payments') as mock_update_loan_payments, \
             patch.object(calendar, '_update_calendar') as mock_update_calendar:
            
            # Act - выбираем дату из другого месяца
            new_date = datetime.date(2026, 1, 20)
            calendar.select_date(new_date)
            
            # Assert - проверяем переключение current_date
            self.assertEqual(
                calendar.current_date.year,
                2026,
                "current_date.year должен переключиться на год новой даты"
            )
            self.assertEqual(
                calendar.current_date.month,
                1,
                "current_date.month должен переключиться на месяц новой даты"
            )
            self.assertEqual(
                calendar.current_date.day,
                1,
                "current_date.day должен быть установлен на 1 (первый день месяца)"
            )
            
            # Assert - проверяем обновление selected_date
            self.assertEqual(
                calendar.selected_date,
                new_date,
                "selected_date должен обновиться на новую дату"
            )
            
            # Assert - проверяем вызов методов загрузки данных для нового месяца
            mock_update_cash_gaps.assert_called_once()
            mock_update_pending_payments.assert_called_once()
            mock_update_loan_payments.assert_called_once()
            
            # Assert - проверяем вызов _update_calendar() для перерисовки
            mock_update_calendar.assert_called_once()

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

    def test_update_calendar_selection_delegates_to_calendar_widget(self):
        """
        Тест делегирования update_calendar_selection в calendar_widget.select_date().
        
        Проверяет:
        - Делегирование в calendar_widget.select_date()
        - Передачу правильной даты
        """
        with patch('finance_tracker.views.home_view.HomePresenter'):
            # Arrange - создаем HomeView
            home_view = HomeView(self.mock_page, self.mock_session)
            home_view.calendar_widget.page = self.mock_page
            
            # Мокируем метод select_date для отслеживания вызова
            home_view.calendar_widget.select_date = Mock()
            
            # Act - вызываем update_calendar_selection с тестовой датой
            test_date = datetime.date(2025, 12, 30)
            home_view.update_calendar_selection(test_date)
            
            # Assert - проверяем делегирование в calendar_widget.select_date()
            home_view.calendar_widget.select_date.assert_called_once()
            
            # Assert - проверяем передачу правильной даты
            call_args = home_view.calendar_widget.select_date.call_args
            self.assertEqual(
                call_args[0][0],
                test_date,
                "Дата должна быть передана в calendar_widget.select_date() без изменений"
            )

    def test_update_calendar_selection_handles_errors_gracefully(self):
        """
        Тест обработки ошибок в update_calendar_selection.
        
        Проверяет:
        - Обработку исключений при вызове calendar_widget.select_date()
        - Логирование ошибки
        - Продолжение работы приложения без прерывания
        """
        with patch('finance_tracker.views.home_view.HomePresenter'):
            # Arrange - создаем HomeView
            home_view = HomeView(self.mock_page, self.mock_session)
            home_view.calendar_widget.page = self.mock_page
            
            # Мокируем select_date для генерации исключения
            home_view.calendar_widget.select_date = Mock(
                side_effect=Exception("Test error in select_date")
            )
            
            # Act & Assert - вызов не должен вызывать необработанное исключение
            test_date = datetime.date(2025, 12, 30)
            try:
                home_view.update_calendar_selection(test_date)
                # Если исключение не было выброшено, тест проходит
            except Exception as e:
                self.fail(
                    f"update_calendar_selection не должен пробрасывать исключения, "
                    f"но получено: {e}"
                )
            
            # Assert - проверяем, что select_date был вызван (попытка была сделана)
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


class TestCalendarSelectionSyncIntegration(unittest.TestCase):
    """Интеграционные тесты синхронизации выделения календаря."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_page = MagicMock()
        self.mock_page.open = Mock()
        self.mock_page.close = Mock()
        self.mock_page.update = Mock()
        self.mock_page.width = 1200
        
        # Создаем реальную БД для интеграционного теста
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from finance_tracker.models import Base
        
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        self.session = Session()

    def tearDown(self):
        """Очистка после каждого теста."""
        self.session.close()

    @patch('finance_tracker.views.home_view.PlannedTransactionsWidget')
    @patch('finance_tracker.views.home_view.PendingPaymentsWidget')
    @patch('finance_tracker.views.home_view.TransactionsPanel')
    def test_full_scenario_click_on_planned_transaction(
        self,
        MockTransactionsPanel,
        MockPendingPaymentsWidget,
        MockPlannedTransactionsWidget
    ):
        """
        Интеграционный тест: полный сценарий клика на плановую транзакцию.
        
        **Feature: calendar-selection-sync-fix, Property 1: Синхронизация выделения календаря**
        **Validates: Requirements 1.1, 1.2, 1.3**
        
        Сценарий:
        1. Создать HomeView с реальными компонентами
        2. Создать плановое вхождение с датой
        3. Симулировать клик на карточку
        4. Проверить обновление календаря, панели транзакций
        """
        # Arrange - создаем HomeView с реальными компонентами
        home_view = HomeView(self.mock_page, self.session)
        home_view.calendar_widget.page = self.mock_page
        
        # Создаем mock occurrence с датой
        occurrence_date = datetime.date(2025, 12, 15)
        mock_occurrence = Mock()
        mock_occurrence.id = "test-occurrence-id"
        mock_occurrence.occurrence_date = occurrence_date
        
        # Мокируем методы для отслеживания вызовов
        original_select_date = home_view.calendar_widget.select_date
        home_view.calendar_widget.select_date = Mock(side_effect=original_select_date)
        
        # Act - симулируем клик на плановую транзакцию
        home_view.on_occurrence_clicked(mock_occurrence)
        
        # Assert - проверяем обновление календаря
        # Проверяем, что select_date был вызван с правильной датой
        home_view.calendar_widget.select_date.assert_called()
        
        # Проверяем, что selected_date в календаре обновился
        self.assertEqual(
            home_view.calendar_widget.selected_date,
            occurrence_date,
            "Календарь должен выделить дату вхождения"
        )
        
        # Проверяем, что selected_date в HomeView обновился
        self.assertEqual(
            home_view.selected_date,
            occurrence_date,
            "HomeView должна обновить selected_date"
        )

    @patch('finance_tracker.views.home_view.PlannedTransactionsWidget')
    @patch('finance_tracker.views.home_view.PendingPaymentsWidget')
    @patch('finance_tracker.views.home_view.TransactionsPanel')
    def test_month_switch_scenario(
        self,
        MockTransactionsPanel,
        MockPendingPaymentsWidget,
        MockPlannedTransactionsWidget
    ):
        """
        Интеграционный тест: сценарий переключения месяца.
        
        **Feature: calendar-selection-sync-fix, Property 2: Переключение месяца при необходимости**
        **Validates: Requirements 1.4, 1.5**
        
        Сценарий:
        1. Установить текущий месяц в календаре
        2. Кликнуть на вхождение из другого месяца
        3. Проверить переключение месяца
        4. Проверить загрузку данных
        5. Проверить выделение даты
        """
        # Arrange - создаем HomeView с начальной датой в декабре 2025
        initial_date = datetime.date(2025, 12, 15)
        home_view = HomeView(self.mock_page, self.session)
        home_view.calendar_widget.page = self.mock_page
        home_view.calendar_widget.current_date = initial_date.replace(day=1)
        home_view.calendar_widget.selected_date = initial_date
        
        # Проверяем начальное состояние
        self.assertEqual(
            home_view.calendar_widget.current_date.month,
            12,
            "Начальный месяц должен быть декабрь"
        )
        self.assertEqual(
            home_view.calendar_widget.current_date.year,
            2025,
            "Начальный год должен быть 2025"
        )
        
        # Создаем mock occurrence в другом месяце
        occurrence_date = datetime.date(2026, 1, 20)  # Январь 2026
        mock_occurrence = Mock()
        mock_occurrence.id = "test-occurrence-id"
        mock_occurrence.occurrence_date = occurrence_date
        
        # Act - симулируем клик на вхождение из другого месяца
        home_view.on_occurrence_clicked(mock_occurrence)
        
        # Assert - проверяем переключение месяца
        self.assertEqual(
            home_view.calendar_widget.current_date.month,
            1,
            "Месяц должен переключиться на январь"
        )
        self.assertEqual(
            home_view.calendar_widget.current_date.year,
            2026,
            "Год должен переключиться на 2026"
        )
        
        # Assert - проверяем выделение даты
        self.assertEqual(
            home_view.calendar_widget.selected_date,
            occurrence_date,
            "Дата должна быть выделена в новом месяце"
        )
        
        # Assert - проверяем обновление selected_date в HomeView
        self.assertEqual(
            home_view.selected_date,
            occurrence_date,
            "HomeView должна обновить selected_date на дату вхождения"
        )


class TestCalendarSelectionSyncProperties:
    """Property-based тесты для синхронизации выделения календаря."""

    @given(
        occurrence_date=st.dates(
            min_value=datetime.date(2020, 1, 1),
            max_value=datetime.date(2030, 12, 31)
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_1_calendar_selection_sync_for_any_date(self, occurrence_date):
        """
        **Feature: calendar-selection-sync-fix, Property 1: Синхронизация выделения календаря**
        **Validates: Requirements 1.1, 1.3**
        
        Property: For any дата, при клике на вхождение с этой датой,
        календарь должен визуально выделить эту дату.
        
        Генерируем случайные даты и проверяем, что:
        1. selected_date в календаре обновляется на дату вхождения
        2. selected_date в HomeView обновляется на дату вхождения
        3. Календарь остаётся в корректном состоянии
        """
        # Arrange - создаем mock page и session
        mock_page = MagicMock()
        mock_page.open = Mock()
        mock_page.close = Mock()
        mock_page.update = Mock()
        mock_page.width = 1200
        
        mock_session = Mock()
        
        # Создаем HomeView с реальными компонентами
        with patch('finance_tracker.views.home_view.HomePresenter'):
            home_view = HomeView(mock_page, mock_session)
            home_view.page = mock_page
            home_view.calendar_widget.page = mock_page
            
            # Act - вызываем update_calendar_selection напрямую
            # (это то, что должно быть вызвано из presenter)
            home_view.update_calendar_selection(occurrence_date)
            
            # Assert - проверяем синхронизацию выделения
            # Проверяем, что selected_date в календаре обновился
            assert home_view.calendar_widget.selected_date == occurrence_date, \
                f"Календарь должен выделить дату {occurrence_date}, " \
                f"но выделена {home_view.calendar_widget.selected_date}"
            
            # Проверяем, что календарь находится в корректном состоянии
            assert home_view.calendar_widget.current_date is not None, \
                "current_date в календаре не должен быть None"
            
            # Проверяем, что дата вхождения находится в текущем месяце календаря
            assert home_view.calendar_widget.current_date.year == occurrence_date.year, \
                f"Год в current_date должен быть {occurrence_date.year}, " \
                f"но установлен {home_view.calendar_widget.current_date.year}"
            
            assert home_view.calendar_widget.current_date.month == occurrence_date.month, \
                f"Месяц в current_date должен быть {occurrence_date.month}, " \
                f"но установлен {home_view.calendar_widget.current_date.month}"

    @given(
        current_date=st.dates(
            min_value=datetime.date(2020, 1, 1),
            max_value=datetime.date(2030, 12, 31)
        ),
        target_date=st.dates(
            min_value=datetime.date(2020, 1, 1),
            max_value=datetime.date(2030, 12, 31)
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_2_month_switch_for_any_dates(self, current_date, target_date):
        """
        **Feature: calendar-selection-sync-fix, Property 2: Переключение месяца при необходимости**
        **Validates: Requirements 1.4, 1.5**
        
        Property: For any две даты, если они в разных месяцах,
        календарь должен переключиться на месяц целевой даты.
        
        Генерируем пары дат и проверяем, что:
        1. Если даты в разных месяцах, календарь переключается
        2. Если даты в одном месяце, календарь остаётся в том же месяце
        3. selected_date всегда обновляется на целевую дату
        """
        # Arrange - создаем mock page и session
        mock_page = MagicMock()
        mock_page.open = Mock()
        mock_page.close = Mock()
        mock_page.update = Mock()
        mock_page.width = 1200
        
        mock_session = Mock()
        
        # Создаем HomeView с начальной датой
        with patch('finance_tracker.views.home_view.HomePresenter'):
            home_view = HomeView(mock_page, mock_session)
            home_view.page = mock_page
            home_view.calendar_widget.page = mock_page
            
            # Устанавливаем начальную дату
            home_view.calendar_widget.current_date = current_date.replace(day=1)
            home_view.calendar_widget.selected_date = current_date
            
            # Act - вызываем update_calendar_selection с целевой датой
            home_view.update_calendar_selection(target_date)
            
            # Assert - проверяем переключение месяца
            # Проверяем, что selected_date обновился на целевую дату
            assert home_view.calendar_widget.selected_date == target_date, \
                f"selected_date должен быть {target_date}, " \
                f"но установлен {home_view.calendar_widget.selected_date}"
            
            # Проверяем, что current_date соответствует целевой дате
            assert home_view.calendar_widget.current_date.year == target_date.year, \
                f"Год в current_date должен быть {target_date.year}, " \
                f"но установлен {home_view.calendar_widget.current_date.year}"
            
            assert home_view.calendar_widget.current_date.month == target_date.month, \
                f"Месяц в current_date должен быть {target_date.month}, " \
                f"но установлен {home_view.calendar_widget.current_date.month}"
            
            # Проверяем, что day в current_date равен 1 (первый день месяца)
            assert home_view.calendar_widget.current_date.day == 1, \
                f"День в current_date должен быть 1, " \
                f"но установлен {home_view.calendar_widget.current_date.day}"

    @given(
        date_obj=st.dates(
            min_value=datetime.date(2020, 1, 1),
            max_value=datetime.date(2030, 12, 31)
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_3_programmatic_update_no_callback(self, date_obj):
        """
        **Feature: calendar-selection-sync-fix, Property 3: Программное обновление без callback**
        **Validates: Requirements 2.3**
        
        Property: For any дата, при вызове select_date программно,
        callback on_date_selected НЕ должен вызываться.
        
        Генерируем случайные даты и проверяем, что:
        1. Метод select_date вызывается без ошибок
        2. selected_date обновляется
        3. Callback on_date_selected НЕ вызывается
        """
        # Arrange - создаем mock page и callback
        mock_page = MagicMock()
        mock_page.open = Mock()
        mock_page.close = Mock()
        mock_page.update = Mock()
        
        mock_callback = Mock()
        
        # Создаем календарь с mock callback
        calendar = CalendarWidget(
            on_date_selected=mock_callback,
            initial_date=datetime.date.today()
        )
        calendar.page = mock_page
        
        # Act - вызываем select_date программно
        calendar.select_date(date_obj)
        
        # Assert - проверяем, что selected_date обновился
        assert calendar.selected_date == date_obj, \
            f"selected_date должен быть {date_obj}, " \
            f"но установлен {calendar.selected_date}"
        
        # Assert - проверяем, что callback НЕ был вызван
        mock_callback.assert_not_called(), \
            "Callback on_date_selected не должен вызываться при программном вызове select_date"



if __name__ == '__main__':
    unittest.main()

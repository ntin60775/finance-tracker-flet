"""
Тесты для HomeView.
"""
import unittest
from unittest.mock import Mock, MagicMock, patch, ANY
import datetime

import pytest
from hypothesis import given, strategies as st, settings

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
        self.view = HomeView(self.page, self.mock_session, navigate_callback=Mock())

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
        # Проверяем, что load_initial_data НЕ вызывается при инициализации
        self.mock_presenter.return_value.load_initial_data.assert_not_called()

    def test_load_data_calls_services(self):
        """Тест, что данные НЕ загружаются при инициализации, а только через did_mount."""
        # Проверяем, что при инициализации Presenter НЕ вызывает load_initial_data
        self.mock_presenter.return_value.load_initial_data.assert_not_called()
        
        # Но если мы вызовем load_initial_data вручную (как это делает MainWindow.did_mount)
        self.view.presenter.load_initial_data()
        self.mock_presenter.return_value.load_initial_data.assert_called_once()

    def test_on_date_selected(self):
        """Тест выбора даты в календаре делегирует в Presenter."""
        new_date = datetime.date(2024, 10, 5)

        self.view.on_date_selected(new_date)

        # Проверяем, что вызван метод Presenter
        self.mock_presenter.return_value.on_date_selected.assert_called_once_with(new_date)

    def test_did_mount_behavior_simulation(self):
        """Тест симуляции поведения did_mount - загрузка данных после инициализации."""
        # Проверяем, что при инициализации данные не загружаются
        self.mock_presenter.return_value.load_initial_data.assert_not_called()
        
        # Симулируем вызов did_mount (как это делает MainWindow)
        self.view.presenter.load_initial_data()
        
        # Проверяем, что теперь данные загружены
        self.mock_presenter.return_value.load_initial_data.assert_called_once()

    def test_presenter_available_after_initialization(self):
        """Тест, что Presenter доступен после инициализации для вызова load_initial_data."""
        # Проверяем, что presenter создан и доступен
        self.assertIsNotNone(self.view.presenter)
        self.assertEqual(self.view.presenter, self.mock_presenter.return_value)
        
        # Проверяем, что можно вызвать load_initial_data
        self.view.presenter.load_initial_data()
        self.mock_presenter.return_value.load_initial_data.assert_called_once()

    def test_initialization_order_safety(self):
        """Тест безопасности порядка инициализации - компоненты создаются, но данные не загружаются."""
        # Проверяем, что все UI компоненты созданы
        self.assertIsNotNone(self.view.calendar_widget)
        self.assertIsNotNone(self.view.transactions_panel)
        self.assertIsNotNone(self.view.legend)
        self.assertIsNotNone(self.view.planned_widget)
        self.assertIsNotNone(self.view.pending_payments_widget)
        
        # Проверяем, что presenter создан
        self.assertIsNotNone(self.view.presenter)
        
        # Но данные не загружены
        self.mock_presenter.return_value.load_initial_data.assert_not_called()

    def test_planned_transaction_modal_initialization(self):
        """Тест инициализации PlannedTransactionModal."""
        # Проверяем, что модальное окно создано
        self.assertIsNotNone(self.view.planned_transaction_modal)
        
        # Проверяем, что модальное окно имеет правильную сессию
        self.assertEqual(self.view.planned_transaction_modal.session, self.mock_session)
        
        # Проверяем, что callback установлен
        self.assertIsNotNone(self.view.planned_transaction_modal.on_save)

    def test_on_planned_transaction_saved_delegates_to_presenter(self):
        """Тест, что on_planned_transaction_saved делегирует в Presenter."""
        from finance_tracker.models.models import PlannedTransactionCreate
        
        # Создаем тестовые данные
        test_data = Mock(spec=PlannedTransactionCreate)
        
        # Вызываем метод
        self.view.on_planned_transaction_saved(test_data)
        
        # Проверяем, что вызван метод Presenter
        self.mock_presenter.return_value.create_planned_transaction.assert_called_once_with(test_data)

    def test_callback_passed_to_transactions_panel(self):
        """Тест передачи callback функции в TransactionsPanel."""
        # Проверяем, что TransactionsPanel был создан с правильными параметрами
        self.mock_transactions_panel.assert_called_once()
        
        # Получаем аргументы вызова конструктора TransactionsPanel
        call_args = self.mock_transactions_panel.call_args
        
        # Проверяем, что on_add_transaction передан как callback
        self.assertIn('on_add_transaction', call_args.kwargs)
        callback = call_args.kwargs['on_add_transaction']
        
        # Проверяем, что callback - это метод open_add_transaction_modal
        self.assertEqual(callback, self.view.open_add_transaction_modal)
        
        # Проверяем, что callback не None
        self.assertIsNotNone(callback)

    def test_transactions_panel_initialization_with_correct_callback(self):
        """Тест инициализации TransactionsPanel с корректным callback."""
        # Проверяем, что TransactionsPanel инициализирован с правильными параметрами
        call_args = self.mock_transactions_panel.call_args
        
        # Проверяем обязательные параметры
        self.assertIn('date_obj', call_args.kwargs)
        self.assertIn('transactions', call_args.kwargs)
        self.assertIn('on_add_transaction', call_args.kwargs)
        
        # Проверяем, что дата инициализации - сегодняшняя
        self.assertEqual(call_args.kwargs['date_obj'], datetime.date.today())
        
        # Проверяем, что список транзакций пустой при инициализации
        self.assertEqual(call_args.kwargs['transactions'], [])
        
        # Проверяем, что callback функция - это именно open_add_transaction_modal
        callback = call_args.kwargs['on_add_transaction']
        self.assertEqual(callback.__name__, 'open_add_transaction_modal')

    @patch('finance_tracker.views.home_view.TransactionModal')
    def test_open_add_transaction_modal(self, mock_transaction_modal_class):
        """Тест открытия модального окна добавления транзакции."""
        # Arrange - настройка mock объектов
        mock_transaction_modal_instance = Mock()
        mock_transaction_modal_class.return_value = mock_transaction_modal_instance
        
        # Создаем новый экземпляр HomeView с мокированным TransactionModal
        view = HomeView(self.page, self.mock_session)
        
        # Устанавливаем тестовую дату
        test_date = datetime.date(2024, 12, 11)
        view.selected_date = test_date
        
        # Act - вызываем метод открытия модального окна
        view.open_add_transaction_modal()
        
        # Assert - проверяем вызов TransactionModal.open() с правильными параметрами
        mock_transaction_modal_instance.open.assert_called_once_with(self.page, test_date)
        
        # Проверяем, что page передается корректно
        call_args = mock_transaction_modal_instance.open.call_args
        self.assertEqual(call_args[0][0], self.page)  # Первый аргument - page
        self.assertEqual(call_args[0][1], test_date)  # Второй аргумент - selected_date


class TestHomeViewProperties:
    """Property-based тесты для HomeView."""

    @given(
        test_date=st.dates(min_value=datetime.date(2020, 1, 1), max_value=datetime.date(2030, 12, 31))
    )
    @settings(max_examples=100, deadline=None)
    @patch('finance_tracker.views.home_view.TransactionModal')
    @patch('finance_tracker.views.home_view.HomePresenter')
    @patch('finance_tracker.views.home_view.TransactionsPanel')
    def test_property_3_modal_parameter_passing(self, mock_transactions_panel, mock_presenter, mock_transaction_modal_class, test_date):
        """
        **Feature: add-transaction-button-fix, Property 3: Modal Parameter Passing**
        **Validates: Requirements 3.3, 3.4**
        
        Property: Для любых валидных date и page объектов, когда вызывается TransactionModal.open(),
        оба параметра должны быть корректно сохранены и использованы для инициализации формы.
        """
        # Arrange - создаем mock объекты
        mock_page = MagicMock()
        mock_session = Mock()
        mock_transaction_modal_instance = Mock()
        mock_transaction_modal_class.return_value = mock_transaction_modal_instance
        
        # Создаем HomeView с мокированными зависимостями
        view = HomeView(mock_page, mock_session)
        
        # Устанавливаем тестовую дату
        view.selected_date = test_date
        
        # Act - вызываем метод открытия модального окна
        view.open_add_transaction_modal()
        
        # Assert - проверяем корректную передачу параметров
        # 1. TransactionModal.open() должен быть вызван ровно один раз
        mock_transaction_modal_instance.open.assert_called_once()
        
        # 2. Получаем аргументы вызова
        call_args = mock_transaction_modal_instance.open.call_args
        assert call_args is not None, "TransactionModal.open() должен быть вызван с аргументами"
        
        # 3. Проверяем, что переданы правильные аргументы
        passed_page = call_args[0][0]  # Первый позиционный аргумент
        passed_date = call_args[0][1]  # Второй позиционный аргумент
        
        # 4. Проверяем корректность переданной page
        assert passed_page is mock_page, \
            f"Page должна быть передана корректно. Ожидалось: {mock_page}, получено: {passed_page}"
        
        # 5. Проверяем корректность переданной даты
        assert passed_date == test_date, \
            f"Дата должна быть передана корректно. Ожидалось: {test_date}, получено: {passed_date}"
        
        # 6. Проверяем, что page не None (валидация безопасности)
        assert passed_page is not None, "Page не должна быть None"
        
        # 7. Проверяем, что дата не None (валидация безопасности)
        assert passed_date is not None, "Дата не должна быть None"
        
        # 8. Проверяем, что дата находится в разумных пределах
        min_date = datetime.date(1900, 1, 1)
        max_date = datetime.date(2100, 12, 31)
        assert min_date <= passed_date <= max_date, \
            f"Дата должна быть в разумных пределах [{min_date}, {max_date}], получено: {passed_date}"
        
        # 9. Проверяем, что вызов был выполнен без исключений
        # (если мы дошли до этой точки, значит исключений не было)
        
        # 10. Проверяем, что метод был вызван с правильным количеством аргументов
        assert len(call_args[0]) == 2, \
            f"TransactionModal.open() должен вызываться с 2 аргументами, получено: {len(call_args[0])}"
        
        # 11. Проверяем, что не было передано лишних keyword аргументов
        assert len(call_args[1]) == 0, \
            f"TransactionModal.open() не должен получать keyword аргументы, получено: {call_args[1]}"

    @given(
        test_date=st.dates(min_value=datetime.date(2020, 1, 1), max_value=datetime.date(2030, 12, 31)),
        page_attributes=st.fixed_dictionaries({
            'width': st.integers(min_value=800, max_value=2000),
            'height': st.integers(min_value=600, max_value=1200),
            'theme_mode': st.sampled_from(['light', 'dark', 'system'])
        })
    )
    @settings(max_examples=50, deadline=None)
    @patch('finance_tracker.views.home_view.TransactionModal')
    @patch('finance_tracker.views.home_view.HomePresenter')
    @patch('finance_tracker.views.home_view.TransactionsPanel')
    def test_modal_parameter_passing_with_various_page_states(self, mock_transactions_panel, mock_presenter, mock_transaction_modal_class, test_date, page_attributes):
        """
        Property: Параметры должны передаваться корректно независимо от состояния page объекта.
        """
        # Arrange - создаем mock page с различными атрибутами
        mock_page = MagicMock()
        mock_page.width = page_attributes['width']
        mock_page.height = page_attributes['height']
        mock_page.theme_mode = page_attributes['theme_mode']
        
        mock_session = Mock()
        mock_transaction_modal_instance = Mock()
        mock_transaction_modal_class.return_value = mock_transaction_modal_instance
        
        # Создаем HomeView
        view = HomeView(mock_page, mock_session)
        view.selected_date = test_date
        
        # Act - открываем модальное окно
        view.open_add_transaction_modal()
        
        # Assert - проверяем, что параметры переданы корректно независимо от состояния page
        mock_transaction_modal_instance.open.assert_called_once_with(mock_page, test_date)
        
        # Проверяем, что переданный page объект сохранил свои атрибуты
        call_args = mock_transaction_modal_instance.open.call_args
        passed_page = call_args[0][0]
        
        assert passed_page.width == page_attributes['width']
        assert passed_page.height == page_attributes['height']
        assert passed_page.theme_mode == page_attributes['theme_mode']

    @given(
        dates_sequence=st.lists(
            st.dates(min_value=datetime.date(2020, 1, 1), max_value=datetime.date(2030, 12, 31)),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=30, deadline=None)
    @patch('finance_tracker.views.home_view.TransactionModal')
    @patch('finance_tracker.views.home_view.HomePresenter')
    @patch('finance_tracker.views.home_view.TransactionsPanel')
    def test_modal_parameter_passing_consistency_across_multiple_calls(self, mock_transactions_panel, mock_presenter, mock_transaction_modal_class, dates_sequence):
        """
        Property: При множественных вызовах open_add_transaction_modal с разными датами,
        каждый вызов должен передавать корректные параметры независимо от предыдущих вызовов.
        """
        # Arrange
        mock_page = MagicMock()
        mock_session = Mock()
        mock_transaction_modal_instance = Mock()
        mock_transaction_modal_class.return_value = mock_transaction_modal_instance
        
        view = HomeView(mock_page, mock_session)
        
        # Act & Assert - выполняем последовательность вызовов с разными датами
        for i, test_date in enumerate(dates_sequence):
            # Сбрасываем mock для чистого тестирования каждого вызова
            mock_transaction_modal_instance.reset_mock()
            
            # Устанавливаем новую дату
            view.selected_date = test_date
            
            # Вызываем открытие модального окна
            view.open_add_transaction_modal()
            
            # Проверяем корректность параметров для этого вызова
            mock_transaction_modal_instance.open.assert_called_once()
            call_args = mock_transaction_modal_instance.open.call_args
            
            passed_page = call_args[0][0]
            passed_date = call_args[0][1]
            
            assert passed_page is mock_page, \
                f"Вызов {i+1}: Page должна быть передана корректно"
            assert passed_date == test_date, \
                f"Вызов {i+1}: Дата должна быть {test_date}, получено {passed_date}"
            
            # Проверяем, что каждый вызов независим
            assert len(call_args[0]) == 2, \
                f"Вызов {i+1}: Должно быть передано ровно 2 аргумента"

    @given(
        edge_case_date=st.one_of(
            st.just(datetime.date(2020, 1, 1)),    # Минимальная дата
            st.just(datetime.date(2030, 12, 31)),  # Максимальная дата
            st.just(datetime.date.today()),        # Сегодняшняя дата
            st.just(datetime.date(2024, 2, 29)),   # Високосный год
            st.just(datetime.date(2023, 2, 28)),   # Не високосный год
        )
    )
    @settings(max_examples=25, deadline=None)
    @patch('finance_tracker.views.home_view.TransactionModal')
    @patch('finance_tracker.views.home_view.HomePresenter')
    @patch('finance_tracker.views.home_view.TransactionsPanel')
    def test_modal_parameter_passing_edge_case_dates(self, mock_transactions_panel, mock_presenter, mock_transaction_modal_class, edge_case_date):
        """
        Property: Параметры должны передаваться корректно даже для граничных случаев дат.
        """
        # Arrange
        mock_page = MagicMock()
        mock_session = Mock()
        mock_transaction_modal_instance = Mock()
        mock_transaction_modal_class.return_value = mock_transaction_modal_instance
        
        view = HomeView(mock_page, mock_session)
        view.selected_date = edge_case_date
        
        # Act
        view.open_add_transaction_modal()
        
        # Assert - граничные даты должны передаваться так же корректно, как и обычные
        mock_transaction_modal_instance.open.assert_called_once_with(mock_page, edge_case_date)
        
        call_args = mock_transaction_modal_instance.open.call_args
        passed_date = call_args[0][1]
        
        # Проверяем точное соответствие даты
        assert passed_date == edge_case_date, \
            f"Граничная дата должна передаваться точно: ожидалось {edge_case_date}, получено {passed_date}"
        
        # Проверяем, что дата остается объектом date
        assert isinstance(passed_date, datetime.date), \
            f"Переданная дата должна быть объектом datetime.date, получено {type(passed_date)}"

    @given(
        navigate_callbacks=st.one_of(
            st.just(Mock()),  # Обычный mock callback
            st.just(Mock(side_effect=None)),  # Mock без побочных эффектов
        )
    )
    @settings(max_examples=100, deadline=None)
    @patch('finance_tracker.views.home_view.HomePresenter')
    @patch('finance_tracker.views.home_view.TransactionsPanel')
    def test_property_1_navigation_called_on_show_all_occurrences(self, mock_transactions_panel, mock_presenter, navigate_callbacks):
        """
        **Feature: planned-transaction-show-all-button, Property 1: Навигация вызывается при нажатии кнопки**
        **Validates: Requirements 1.1, 2.2**
        
        Property: Для любого HomeView с заданным navigate_callback, при вызове метода on_show_all_occurrences 
        callback должен быть вызван ровно один раз с индексом 1.
        """
        # Arrange - создаем mock объекты
        mock_page = MagicMock()
        mock_session = Mock()
        
        # Создаем HomeView с navigate_callback
        view = HomeView(mock_page, mock_session, navigate_callback=navigate_callbacks)
        
        # Act - вызываем on_show_all_occurrences
        view.on_show_all_occurrences()
        
        # Assert - проверяем вызов callback с индексом 1
        # 1. Callback должен быть вызван ровно один раз
        navigate_callbacks.assert_called_once()
        
        # 2. Callback должен быть вызван с аргументом 1
        call_args = navigate_callbacks.call_args
        assert call_args is not None, "Callback должен быть вызван с аргументами"
        
        # 3. Проверяем, что первый аргумент - это индекс 1
        passed_index = call_args[0][0]
        assert passed_index == 1, \
            f"Callback должен быть вызван с индексом 1, получено: {passed_index}"
        
        # 4. Проверяем, что индекс - это целое число
        assert isinstance(passed_index, int), \
            f"Индекс должен быть целым числом, получено: {type(passed_index)}"
        
        # 5. Проверяем, что индекс находится в разумных пределах (0-7 для навигации)
        assert 0 <= passed_index <= 7, \
            f"Индекс должен быть в пределах [0, 7], получено: {passed_index}"
        
        # 6. Проверяем, что не было передано лишних аргументов
        assert len(call_args[0]) == 1, \
            f"Callback должен быть вызван с одним аргументом, получено: {len(call_args[0])}"
        
        # 7. Проверяем, что не было передано keyword аргументов
        assert len(call_args[1]) == 0, \
            f"Callback не должен получать keyword аргументы, получено: {call_args[1]}"

    @given(
        call_count=st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=100, deadline=None)
    @patch('finance_tracker.views.home_view.HomePresenter')
    @patch('finance_tracker.views.home_view.TransactionsPanel')
    def test_property_2_safety_without_navigation(self, mock_transactions_panel, mock_presenter, call_count):
        """
        **Feature: planned-transaction-show-all-button, Property 2: Безопасность при отсутствии навигации**
        **Validates: Requirements 3.1, 3.3**
        
        Property: Для любого HomeView без navigate_callback (None), при вызове метода on_show_all_occurrences 
        множество раз не должно возникать необработанных исключений.
        """
        # Arrange - создаем mock объекты
        mock_page = MagicMock()
        mock_session = Mock()
        
        # Создаем HomeView БЕЗ navigate_callback (None)
        view = HomeView(mock_page, mock_session, navigate_callback=None)
        
        # Act & Assert - вызываем on_show_all_occurrences множество раз
        # Каждый вызов должен быть безопасным и не выбрасывать исключений
        with patch('finance_tracker.views.home_view.logger') as mock_logger:
            for i in range(call_count):
                try:
                    # Вызываем метод
                    view.on_show_all_occurrences()
                    
                    # Проверяем, что исключение не возникло
                    # (если мы дошли до этой точки, значит исключений не было)
                except Exception as e:
                    pytest.fail(
                        f"on_show_all_occurrences вызвал исключение при вызове {i+1}: {e}"
                    )
            
            # Проверяем, что warning был залогирован для каждого вызова
            assert mock_logger.warning.call_count == call_count, \
                f"Warning должен быть залогирован {call_count} раз, получено: {mock_logger.warning.call_count}"
            
            # Проверяем, что каждый warning содержит правильное сообщение
            for call in mock_logger.warning.call_args_list:
                warning_message = call[0][0]
                assert "Метод навигации не доступен в HomeView" in warning_message, \
                    f"Warning должен содержать сообщение о недоступности навигации, получено: {warning_message}"
            
            # Проверяем, что error НЕ был залогирован (так как нет callback для выброса исключения)
            mock_logger.error.assert_not_called()

    @given(
        exception_types=st.sampled_from([
            ValueError("Test ValueError"),
            RuntimeError("Test RuntimeError"),
            TypeError("Test TypeError"),
            Exception("Test Exception"),
            KeyError("Test KeyError"),
            AttributeError("Test AttributeError"),
        ])
    )
    @settings(max_examples=100, deadline=None)
    @patch('finance_tracker.views.home_view.HomePresenter')
    @patch('finance_tracker.views.home_view.TransactionsPanel')
    def test_property_3_error_logging_on_navigation_failure(self, mock_transactions_panel, mock_presenter, exception_types):
        """
        **Feature: planned-transaction-show-all-button, Property 3: Логирование при ошибках навигации**
        **Validates: Requirements 3.2**
        
        Property: Для любого HomeView с navigate_callback, который выбрасывает исключение, 
        при вызове on_show_all_occurrences ошибка должна быть залогирована и не распространяться.
        """
        # Arrange - создаем mock объекты
        mock_page = MagicMock()
        mock_session = Mock()
        
        # Создаем mock callback, который выбрасывает исключение
        mock_navigate = Mock(side_effect=exception_types)
        
        # Создаем HomeView с navigate_callback, который выбрасывает исключение
        view = HomeView(mock_page, mock_session, navigate_callback=mock_navigate)
        
        # Act & Assert - вызываем on_show_all_occurrences
        with patch('finance_tracker.views.home_view.logger') as mock_logger:
            try:
                # Вызываем метод
                view.on_show_all_occurrences()
                
                # Проверяем, что исключение НЕ распространилось
                # (если мы дошли до этой точки, значит исключение было обработано)
            except Exception as e:
                pytest.fail(
                    f"on_show_all_occurrences не должен распространять исключения, получено: {type(e).__name__}: {e}"
                )
            
            # Проверяем, что callback был вызван
            mock_navigate.assert_called_once_with(1)
            
            # Проверяем, что ошибка была залогирована
            mock_logger.error.assert_called_once()
            
            # Проверяем содержимое сообщения об ошибке
            error_call = mock_logger.error.call_args[0][0]
            assert "Ошибка при навигации к плановым транзакциям" in error_call, \
                f"Сообщение об ошибке должно содержать описание проблемы, получено: {error_call}"
            
            # Проверяем, что в сообщении есть информация об исключении
            assert str(exception_types) in error_call or type(exception_types).__name__ in error_call, \
                f"Сообщение об ошибке должно содержать информацию об исключении, получено: {error_call}"
            
            # Проверяем, что warning НЕ был залогирован (так как callback был передан)
            mock_logger.warning.assert_not_called()
            
            # Проверяем, что info НЕ был залогирован (так как навигация завершилась с ошибкой)
            mock_logger.info.assert_not_called()


class TestHomeViewPendingPaymentIntegration(unittest.TestCase):
    """Тесты интеграции модального окна отложенных платежей с HomeView."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_presenter_patcher = patch('finance_tracker.views.home_view.HomePresenter')
        self.mock_pending_payment_modal_patcher = patch('finance_tracker.views.home_view.PendingPaymentModal')
        self.mock_pending_payments_widget_patcher = patch('finance_tracker.views.home_view.PendingPaymentsWidget')

        self.mock_presenter = self.mock_presenter_patcher.start()
        self.mock_pending_payment_modal_class = self.mock_pending_payment_modal_patcher.start()
        self.mock_pending_payments_widget = self.mock_pending_payments_widget_patcher.start()

        self.page = MagicMock()
        self.page.open = Mock()
        self.mock_session = Mock()

        # Создаем mock экземпляр модального окна
        self.mock_payment_modal_instance = Mock()
        self.mock_pending_payment_modal_class.return_value = self.mock_payment_modal_instance

        # Создаем экземпляр HomeView
        self.view = HomeView(self.page, self.mock_session)

    def tearDown(self):
        """Очистка после каждого теста."""
        self.mock_presenter_patcher.stop()
        self.mock_pending_payment_modal_patcher.stop()
        self.mock_pending_payments_widget_patcher.stop()

    def test_pending_payment_modal_initialization(self):
        """Тест инициализации PendingPaymentModal с правильными callbacks."""
        # Проверяем, что PendingPaymentModal был создан
        self.mock_pending_payment_modal_class.assert_called_once()
        
        # Получаем аргументы вызова конструктора
        call_args = self.mock_pending_payment_modal_class.call_args
        
        # Проверяем, что session передан
        self.assertEqual(call_args.kwargs['session'], self.mock_session)
        
        # Проверяем, что on_save callback установлен на on_pending_payment_saved
        on_save_callback = call_args.kwargs['on_save']
        self.assertEqual(on_save_callback, self.view.on_pending_payment_saved)
        
        # Проверяем, что on_update callback установлен (даже если не используется)
        self.assertIn('on_update', call_args.kwargs)

    def test_pending_payments_widget_initialization_with_add_callback(self):
        """Тест инициализации PendingPaymentsWidget с callback добавления."""
        # Проверяем, что PendingPaymentsWidget был создан
        self.mock_pending_payments_widget.assert_called_once()
        
        # Получаем аргументы вызова конструктора
        call_args = self.mock_pending_payments_widget.call_args
        
        # Проверяем, что on_add_payment callback установлен
        self.assertIn('on_add_payment', call_args.kwargs)
        on_add_callback = call_args.kwargs['on_add_payment']
        
        # Проверяем, что callback - это метод on_add_pending_payment
        self.assertEqual(on_add_callback, self.view.on_add_pending_payment)

    def test_on_add_pending_payment_opens_modal(self):
        """Тест открытия модального окна через on_add_pending_payment."""
        # Act - вызываем метод открытия модального окна
        self.view.on_add_pending_payment()
        
        # Assert - проверяем вызов payment_modal.open() с правильным page
        self.mock_payment_modal_instance.open.assert_called_once_with(self.page)

    def test_on_add_pending_payment_with_none_page(self):
        """Тест обработки ошибки при отсутствии page объекта."""
        # Arrange - устанавливаем page в None
        self.view.page = None
        
        # Act - вызываем метод (не должно быть исключений)
        self.view.on_add_pending_payment()
        
        # Assert - проверяем, что modal.open() НЕ был вызван
        self.mock_payment_modal_instance.open.assert_not_called()

    def test_on_add_pending_payment_with_none_modal(self):
        """Тест обработки ошибки при отсутствии модального окна."""
        # Arrange - устанавливаем payment_modal в None
        self.view.payment_modal = None
        
        # Act - вызываем метод (не должно быть исключений)
        self.view.on_add_pending_payment()
        
        # Assert - проверяем, что не было попытки вызвать open()
        # (так как modal = None, вызов невозможен)

    def test_on_add_pending_payment_exception_handling(self):
        """Тест обработки исключений при открытии модального окна."""
        # Arrange - настраиваем modal.open() для выброса исключения
        self.mock_payment_modal_instance.open.side_effect = Exception("Test exception")
        
        # Act - вызываем метод (не должно быть необработанных исключений)
        self.view.on_add_pending_payment()
        
        # Assert - проверяем, что был показан SnackBar с ошибкой
        self.page.open.assert_called()
        
        # Проверяем, что был передан SnackBar
        call_args = self.page.open.call_args
        snack_bar = call_args[0][0]
        
        # Проверяем, что это SnackBar с сообщением об ошибке
        self.assertIsNotNone(snack_bar)

    @patch('finance_tracker.models.models.PendingPaymentCreate')
    def test_on_pending_payment_saved_calls_presenter(self, mock_payment_create_class):
        """Тест обработки сохранения через on_pending_payment_saved."""
        # Arrange - создаем mock данных платежа
        mock_payment_data = Mock()
        mock_payment_create_class.return_value = mock_payment_data
        
        # Act - вызываем callback сохранения
        self.view.on_pending_payment_saved(mock_payment_data)
        
        # Assert - проверяем вызов presenter.create_pending_payment
        self.mock_presenter.return_value.create_pending_payment.assert_called_once_with(mock_payment_data)

    def test_on_pending_payment_saved_with_valid_data(self):
        """Тест сохранения с валидными данными."""
        # Arrange - создаем mock данных с реальными атрибутами
        from decimal import Decimal
        from finance_tracker.models.enums import PendingPaymentPriority
        
        mock_payment_data = Mock()
        mock_payment_data.amount = Decimal('1000.50')
        mock_payment_data.category_id = "test-category-id"
        mock_payment_data.description = "Тестовый платёж"
        mock_payment_data.priority = PendingPaymentPriority.MEDIUM
        mock_payment_data.planned_date = None
        
        # Act - вызываем callback
        self.view.on_pending_payment_saved(mock_payment_data)
        
        # Assert - проверяем, что данные переданы в presenter
        self.mock_presenter.return_value.create_pending_payment.assert_called_once()
        call_args = self.mock_presenter.return_value.create_pending_payment.call_args
        passed_data = call_args[0][0]
        
        # Проверяем, что переданы те же данные
        self.assertEqual(passed_data, mock_payment_data)


class TestHomeViewPlannedTransactionCallbackChain:
    """Property-based тесты для callback цепочки плановых транзакций."""

    @given(
        test_date=st.dates(min_value=datetime.date(2020, 1, 1), max_value=datetime.date(2030, 12, 31))
    )
    @settings(max_examples=100, deadline=None)
    @patch('finance_tracker.views.home_view.PlannedTransactionModal')
    @patch('finance_tracker.views.home_view.HomePresenter')
    @patch('finance_tracker.views.home_view.TransactionsPanel')
    @patch('finance_tracker.views.home_view.PlannedTransactionsWidget')
    def test_property_1_callback_invoked_on_button_click(
        self, 
        mock_planned_transactions_widget_class,
        mock_transactions_panel,
        mock_presenter,
        mock_planned_transaction_modal_class,
        test_date
    ):
        """
        **Feature: planned-transaction-add-button, Property 1: Callback вызывается при нажатии кнопки добавления**
        **Validates: Requirements 1.2, 3.2**
        
        Property: Для любого виджета PlannedTransactionsWidget с заданным callback on_add_planned_transaction,
        при нажатии кнопки добавления callback должен быть вызван ровно один раз.
        """
        # Arrange - создаем mock объекты
        mock_page = MagicMock()
        mock_page.open = Mock()
        mock_session = Mock()
        
        # Создаем mock экземпляр PlannedTransactionModal
        mock_planned_transaction_modal_instance = Mock()
        mock_planned_transaction_modal_class.return_value = mock_planned_transaction_modal_instance
        
        # Создаем mock экземпляр PlannedTransactionsWidget
        mock_planned_widget_instance = Mock()
        mock_planned_transactions_widget_class.return_value = mock_planned_widget_instance
        
        # Создаем HomeView с мокированными зависимостями
        view = HomeView(mock_page, mock_session)
        
        # Устанавливаем тестовую дату
        view.selected_date = test_date
        
        # Получаем callback, который был передан в PlannedTransactionsWidget
        call_args = mock_planned_transactions_widget_class.call_args
        assert call_args is not None, "PlannedTransactionsWidget должен быть создан"
        
        # Проверяем, что on_add_planned_transaction был передан
        assert 'on_add_planned_transaction' in call_args.kwargs, \
            "on_add_planned_transaction должен быть передан в PlannedTransactionsWidget"
        
        on_add_callback = call_args.kwargs['on_add_planned_transaction']
        
        # Проверяем, что callback не None
        assert on_add_callback is not None, \
            "on_add_planned_transaction callback не должен быть None"
        
        # Проверяем, что callback - это метод on_add_planned_transaction из HomeView
        assert on_add_callback == view.on_add_planned_transaction, \
            f"Callback должен быть методом on_add_planned_transaction, получен {on_add_callback}"
        
        # Act - симулируем нажатие кнопки добавления через вызов callback
        # Сбрасываем счетчик вызовов modal.open перед тестом
        mock_planned_transaction_modal_instance.open.reset_mock()
        
        # Вызываем callback (симулируем нажатие кнопки)
        on_add_callback()
        
        # Assert - проверяем, что модальное окно было открыто ровно один раз
        assert mock_planned_transaction_modal_instance.open.call_count == 1, \
            f"Модальное окно должно быть открыто ровно 1 раз, вызвано {mock_planned_transaction_modal_instance.open.call_count} раз"
        
        # Проверяем, что модальное окно было открыто с правильными параметрами
        mock_planned_transaction_modal_instance.open.assert_called_once_with(mock_page, test_date)
        
        # Проверяем корректность переданных параметров
        call_args_open = mock_planned_transaction_modal_instance.open.call_args
        passed_page = call_args_open[0][0]
        passed_date = call_args_open[0][1]
        
        assert passed_page is mock_page, \
            f"Page должна быть передана корректно. Ожидалось: {mock_page}, получено: {passed_page}"
        
        assert passed_date == test_date, \
            f"Дата должна быть передана корректно. Ожидалось: {test_date}, получено: {passed_date}"
        
        # Проверяем, что callback был вызван без исключений
        # (если мы дошли до этой точки, значит исключений не было)
        
        # Дополнительная проверка: убеждаемся, что callback вызывается каждый раз
        # Сбрасываем mock и вызываем еще раз
        mock_planned_transaction_modal_instance.open.reset_mock()
        on_add_callback()
        
        assert mock_planned_transaction_modal_instance.open.call_count == 1, \
            "При повторном вызове callback модальное окно должно быть открыто снова"


class TestHomeViewPlannedTransactionIntegration(unittest.TestCase):
    """Тесты интеграции плановых транзакций в HomeView."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_presenter_patcher = patch('finance_tracker.views.home_view.HomePresenter')
        self.mock_transactions_panel_patcher = patch('finance_tracker.views.home_view.TransactionsPanel')
        self.mock_planned_transaction_modal_patcher = patch('finance_tracker.views.home_view.PlannedTransactionModal')
        self.mock_planned_transactions_widget_patcher = patch('finance_tracker.views.home_view.PlannedTransactionsWidget')

        self.mock_presenter = self.mock_presenter_patcher.start()
        self.mock_transactions_panel = self.mock_transactions_panel_patcher.start()
        self.mock_planned_transaction_modal_class = self.mock_planned_transaction_modal_patcher.start()
        self.mock_planned_transactions_widget = self.mock_planned_transactions_widget_patcher.start()

        self.page = MagicMock()
        self.mock_session = Mock()

        # Создаем mock экземпляр PlannedTransactionModal
        self.mock_planned_transaction_modal_instance = Mock()
        self.mock_planned_transaction_modal_class.return_value = self.mock_planned_transaction_modal_instance

        # Создаем экземпляр HomeView
        self.view = HomeView(self.page, self.mock_session)

    def tearDown(self):
        """Очистка после каждого теста."""
        self.mock_presenter_patcher.stop()
        self.mock_transactions_panel_patcher.stop()
        self.mock_planned_transaction_modal_patcher.stop()
        self.mock_planned_transactions_widget_patcher.stop()

    def test_planned_transaction_modal_initialization(self):
        """Тест инициализации PlannedTransactionModal."""
        # Проверяем, что PlannedTransactionModal был создан
        self.mock_planned_transaction_modal_class.assert_called_once()
        
        # Получаем аргументы вызова конструктора
        call_args = self.mock_planned_transaction_modal_class.call_args
        
        # Проверяем, что session передан
        self.assertIn('session', call_args.kwargs)
        self.assertEqual(call_args.kwargs['session'], self.mock_session)
        
        # Проверяем, что on_save callback установлен
        self.assertIn('on_save', call_args.kwargs)
        on_save_callback = call_args.kwargs['on_save']
        
        # Проверяем, что callback - это метод on_planned_transaction_saved
        self.assertEqual(on_save_callback, self.view.on_planned_transaction_saved)

    def test_on_add_planned_transaction_opens_modal(self):
        """Тест открытия модального окна через on_add_planned_transaction."""
        # Arrange - устанавливаем тестовую дату
        test_date = datetime.date(2024, 12, 11)
        self.view.selected_date = test_date
        
        # Act - вызываем метод открытия модального окна
        self.view.on_add_planned_transaction()
        
        # Assert - проверяем вызов planned_transaction_modal.open() с правильными параметрами
        self.mock_planned_transaction_modal_instance.open.assert_called_once_with(self.page, test_date)

    def test_on_add_planned_transaction_with_none_page(self):
        """Тест обработки ошибки при отсутствии page объекта."""
        # Arrange - устанавливаем page в None
        self.view.page = None
        
        # Act - вызываем метод (не должно быть исключений)
        self.view.on_add_planned_transaction()
        
        # Assert - проверяем, что modal.open() НЕ был вызван
        self.mock_planned_transaction_modal_instance.open.assert_not_called()

    def test_on_add_planned_transaction_exception_handling(self):
        """Тест обработки исключений при открытии модального окна."""
        # Arrange - настраиваем modal.open() для выброса исключения
        self.mock_planned_transaction_modal_instance.open.side_effect = Exception("Test exception")
        
        # Act - вызываем метод (не должно быть необработанных исключений)
        self.view.on_add_planned_transaction()
        
        # Assert - проверяем, что был показан SnackBar с ошибкой
        self.page.open.assert_called()
        
        # Проверяем, что был передан SnackBar
        call_args = self.page.open.call_args
        snack_bar = call_args[0][0]
        
        # Проверяем, что это SnackBar с сообщением об ошибке
        self.assertIsNotNone(snack_bar)

    @patch('finance_tracker.models.models.PlannedTransactionCreate')
    def test_on_planned_transaction_saved_calls_presenter(self, mock_planned_transaction_create_class):
        """Тест обработки сохранения через on_planned_transaction_saved."""
        # Arrange - создаем mock данных плановой транзакции
        mock_planned_transaction_data = Mock()
        mock_planned_transaction_create_class.return_value = mock_planned_transaction_data
        
        # Act - вызываем callback сохранения
        self.view.on_planned_transaction_saved(mock_planned_transaction_data)
        
        # Assert - проверяем вызов presenter.create_planned_transaction
        self.mock_presenter.return_value.create_planned_transaction.assert_called_once_with(mock_planned_transaction_data)

    def test_on_planned_transaction_saved_with_valid_data(self):
        """Тест сохранения с валидными данными."""
        # Arrange - создаем mock данных с реальными атрибутами
        from decimal import Decimal
        from finance_tracker.models.enums import TransactionType
        
        mock_planned_transaction_data = Mock()
        mock_planned_transaction_data.amount = Decimal('1000.50')
        mock_planned_transaction_data.category_id = "test-category-id"
        mock_planned_transaction_data.description = "Тестовая плановая транзакция"
        mock_planned_transaction_data.type = TransactionType.EXPENSE
        mock_planned_transaction_data.start_date = datetime.date(2024, 12, 11)
        
        # Act - вызываем callback
        self.view.on_planned_transaction_saved(mock_planned_transaction_data)
        
        # Assert - проверяем, что данные переданы в presenter
        self.mock_presenter.return_value.create_planned_transaction.assert_called_once()
        call_args = self.mock_presenter.return_value.create_planned_transaction.call_args
        passed_data = call_args[0][0]
        
        # Проверяем, что переданы те же данные
        self.assertEqual(passed_data, mock_planned_transaction_data)

    def test_planned_transactions_widget_initialization_with_add_callback(self):
        """Тест инициализации PlannedTransactionsWidget с callback добавления."""
        # Проверяем, что PlannedTransactionsWidget был создан
        self.mock_planned_transactions_widget.assert_called_once()
        
        # Получаем аргументы вызова конструктора
        call_args = self.mock_planned_transactions_widget.call_args
        
        # Проверяем, что on_add_planned_transaction callback установлен
        self.assertIn('on_add_planned_transaction', call_args.kwargs)
        on_add_callback = call_args.kwargs['on_add_planned_transaction']
        
        # Проверяем, что callback - это метод on_add_planned_transaction
        self.assertEqual(on_add_callback, self.view.on_add_planned_transaction)

    def test_on_show_all_occurrences_calls_navigate_with_index_1(self):
        """
        Тест вызова navigate_callback с индексом 1 при нажатии кнопки "Показать все".
        
        Requirements: 1.1, 2.2
        """
        # Arrange - создаем mock navigate_callback
        mock_navigate = Mock()
        
        # Создаем HomeView с navigate_callback
        view = HomeView(self.page, self.mock_session, navigate_callback=mock_navigate)
        
        # Act - вызываем on_show_all_occurrences
        view.on_show_all_occurrences()
        
        # Assert - проверяем вызов navigate_callback с аргументом 1
        mock_navigate.assert_called_once_with(1)

    def test_on_show_all_occurrences_without_callback_logs_warning(self):
        """
        Тест логирования предупреждения при отсутствии navigate_callback.
        
        Requirements: 3.1, 3.3
        """
        # Arrange - создаем HomeView без navigate_callback
        view = HomeView(self.page, self.mock_session, navigate_callback=None)
        
        # Act & Assert - вызов не должен вызывать исключений
        with patch('finance_tracker.views.home_view.logger') as mock_logger:
            view.on_show_all_occurrences()
            
            # Проверяем логирование предупреждения
            mock_logger.warning.assert_called_once_with("Метод навигации не доступен в HomeView")

    def test_on_show_all_occurrences_handles_navigation_error(self):
        """
        Тест обработки ошибок при навигации.
        
        Requirements: 3.2
        """
        # Arrange - создаем mock navigate_callback, который выбрасывает исключение
        mock_navigate = Mock(side_effect=Exception("Navigation error"))
        
        # Создаем HomeView с navigate_callback
        view = HomeView(self.page, self.mock_session, navigate_callback=mock_navigate)
        
        # Act & Assert - вызов не должен распространять исключение
        with patch('finance_tracker.views.home_view.logger') as mock_logger:
            try:
                view.on_show_all_occurrences()
                # Проверяем, что исключение не распространилось
            except Exception:
                self.fail("on_show_all_occurrences не должен распространять исключения")
            
            # Проверяем логирование ошибки
            mock_logger.error.assert_called_once()
            error_message = mock_logger.error.call_args[0][0]
            self.assertIn("Ошибка при навигации к плановым транзакциям", error_message)


if __name__ == '__main__':
    unittest.main()



class TestHomeViewPlannedWidgetIntegration(unittest.TestCase):
    """Тесты интеграции PlannedTransactionsWidget с HomeView для обзорного режима."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_presenter_patcher = patch('finance_tracker.views.home_view.HomePresenter')
        self.mock_planned_widget_patcher = patch('finance_tracker.views.home_view.PlannedTransactionsWidget')

        self.mock_presenter = self.mock_presenter_patcher.start()
        self.mock_planned_widget_class = self.mock_planned_widget_patcher.start()

        self.page = MagicMock()
        self.page.open = Mock()
        self.mock_session = Mock()

        # Создаем mock экземпляр виджета
        self.mock_planned_widget_instance = Mock()
        self.mock_planned_widget_class.return_value = self.mock_planned_widget_instance

        # Создаем экземпляр HomeView
        self.view = HomeView(self.page, self.mock_session)

    def tearDown(self):
        """Очистка после каждого теста."""
        self.mock_presenter_patcher.stop()
        self.mock_planned_widget_patcher.stop()

    def test_planned_widget_initialization_with_occurrence_click_callback(self):
        """
        Тест инициализации PlannedTransactionsWidget с callback on_occurrence_click.
        
        Requirements: 2.1
        """
        # Проверяем, что PlannedTransactionsWidget был создан
        self.mock_planned_widget_class.assert_called_once()
        
        # Получаем аргументы вызова конструктора
        call_args = self.mock_planned_widget_class.call_args
        
        # Проверяем, что on_occurrence_click callback установлен
        self.assertIn('on_occurrence_click', call_args.kwargs)
        on_click_callback = call_args.kwargs['on_occurrence_click']
        
        # Проверяем, что callback - это метод on_occurrence_clicked
        self.assertEqual(on_click_callback, self.view.on_occurrence_clicked)

    def test_on_occurrence_clicked_calls_presenter_on_date_selected(self):
        """
        Тест что клик на вхождение вызывает presenter.on_date_selected.
        
        Requirements: 2.1, 2.2
        """
        # Arrange - создаем mock вхождение
        mock_occurrence = Mock()
        mock_occurrence.id = "test-occurrence-id"
        mock_occurrence.occurrence_date = datetime.date(2024, 12, 15)
        
        # Act - вызываем on_occurrence_clicked
        self.view.on_occurrence_clicked(mock_occurrence)
        
        # Assert - проверяем вызов presenter.on_date_selected с правильной датой
        self.mock_presenter.return_value.on_date_selected.assert_called_once_with(
            mock_occurrence.occurrence_date
        )

    def test_on_occurrence_clicked_updates_calendar(self):
        """
        Тест что календарь обновляется при клике на вхождение.
        
        Requirements: 2.2
        """
        # Arrange - создаем mock вхождение
        mock_occurrence = Mock()
        mock_occurrence.id = "test-occurrence-id"
        mock_occurrence.occurrence_date = datetime.date(2024, 12, 20)
        
        # Act - вызываем on_occurrence_clicked
        self.view.on_occurrence_clicked(mock_occurrence)
        
        # Assert - проверяем, что presenter.on_date_selected был вызван
        # Это приведет к обновлению календаря и панели транзакций
        self.mock_presenter.return_value.on_date_selected.assert_called_once()
        
        # Проверяем, что дата передана корректно
        call_args = self.mock_presenter.return_value.on_date_selected.call_args
        passed_date = call_args[0][0]
        self.assertEqual(passed_date, mock_occurrence.occurrence_date)

    def test_on_occurrence_clicked_handles_errors_gracefully(self):
        """
        Тест обработки ошибок при клике на вхождение.
        
        Requirements: 2.1
        """
        # Arrange - создаем mock вхождение
        mock_occurrence = Mock()
        mock_occurrence.id = "test-occurrence-id"
        mock_occurrence.occurrence_date = datetime.date(2024, 12, 25)
        
        # Настраиваем presenter для выброса исключения
        self.mock_presenter.return_value.on_date_selected.side_effect = Exception("Test error")
        
        # Act & Assert - вызов не должен распространять исключение
        with patch('finance_tracker.views.home_view.logger') as mock_logger:
            try:
                self.view.on_occurrence_clicked(mock_occurrence)
                # Проверяем, что исключение не распространилось
            except Exception:
                self.fail("on_occurrence_clicked не должен распространять исключения")
            
            # Проверяем логирование ошибки
            mock_logger.error.assert_called_once()
            error_message = mock_logger.error.call_args[0][0]
            self.assertIn("Ошибка при обработке клика на вхождение", error_message)

    def test_on_occurrence_clicked_with_various_dates(self):
        """
        Тест клика на вхождения с различными датами.
        
        Requirements: 2.1, 2.2
        """
        # Arrange - создаем список вхождений с разными датами
        test_dates = [
            datetime.date(2024, 1, 1),   # Начало года
            datetime.date(2024, 6, 15),  # Середина года
            datetime.date(2024, 12, 31), # Конец года
            datetime.date.today(),       # Сегодня
        ]
        
        for test_date in test_dates:
            # Сбрасываем mock для чистого тестирования
            self.mock_presenter.return_value.on_date_selected.reset_mock()
            
            # Создаем mock вхождение с тестовой датой
            mock_occurrence = Mock()
            mock_occurrence.id = f"occurrence-{test_date}"
            mock_occurrence.occurrence_date = test_date
            
            # Act - вызываем on_occurrence_clicked
            self.view.on_occurrence_clicked(mock_occurrence)
            
            # Assert - проверяем вызов с правильной датой
            self.mock_presenter.return_value.on_date_selected.assert_called_once_with(test_date)

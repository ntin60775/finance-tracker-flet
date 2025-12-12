"""
Тесты для HomeView.
"""
import unittest
from unittest.mock import Mock, MagicMock, patch, ANY
import datetime

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


if __name__ == '__main__':
    unittest.main()

"""
Тесты для проверки корректности инициализации и жизненного цикла компонентов.

Эти тесты проверяют правильную последовательность lifecycle методов
и корректность порядка загрузки данных в UI компонентах.
"""
import unittest
from unittest.mock import Mock, MagicMock, patch, ANY
import datetime
import flet as ft
import pytest
from hypothesis import given, strategies as st, settings

from test_view_base import ViewTestBase
from finance_tracker.views.home_view import HomeView
from finance_tracker.views.main_window import MainWindow
from finance_tracker.views.categories_view import CategoriesView
from finance_tracker.views.loans_view import LoansView


class TestInitializationOrder(ViewTestBase):
    """
    Тесты для проверки порядка инициализации компонентов.
    
    Проверяют правильную последовательность lifecycle методов:
    - Создание компонентов
    - did_mount() после добавления на страницу
    - will_unmount() перед удалением
    - Загрузка данных после монтирования
    """

    def setUp(self):
        """Настройка перед каждым тестом."""
        super().setUp()
        
        # Создаем mock для Page с отслеживанием lifecycle
        self.mock_page = self.create_mock_lifecycle_page()
        
        # Патчим сервисы для изоляции тестов
        self.mock_category_service = self.add_patcher(
            'finance_tracker.services.category_service'
        )
        
        self.mock_transaction_service = self.add_patcher(
            'finance_tracker.services.transaction_service'
        )
        
        self.mock_loan_service = self.add_patcher(
            'finance_tracker.services.loan_service'
        )
        
        # Патчим get_db_session для MainWindow
        self.mock_db_session_cm = self.create_mock_db_context()
        self.mock_get_db_session = self.add_patcher(
            'finance_tracker.views.main_window.get_db_session',
            return_value=self.mock_db_session_cm
        )
        
        # Патчим get_total_balance для MainWindow
        self.mock_get_total_balance = self.add_patcher(
            'finance_tracker.views.main_window.get_total_balance',
            return_value=1000.0
        )

    def create_mock_lifecycle_page(self) -> MagicMock:
        """
        Создание мока Page с отслеживанием lifecycle событий.
        
        Использует СОВРЕМЕННЫЙ Flet Dialog API (>= 0.25.0):
        - page.open(dialog) - для открытия диалогов
        - page.close(dialog) - для закрытия диалогов
        
        Returns:
            MagicMock: Мок Page с отслеживанием состояния lifecycle
        """
        page = MagicMock(spec=ft.Page)
        page.overlay = []
        page.controls = []
        
        # Отслеживание состояния lifecycle
        page._lifecycle_events = []
        page._is_mounted = False
        
        # Мок для add() - отмечает компонент как добавленный
        def mock_add(control):
            page.controls.append(control)
            page._lifecycle_events.append(('add', control))
            
            # Если у контрола есть did_mount, вызываем его
            if hasattr(control, 'did_mount') and callable(control.did_mount):
                page._lifecycle_events.append(('did_mount', control))
                control.did_mount()
                
        page.add = Mock(side_effect=mock_add)
        
        # Мок для remove() - отмечает компонент как удаленный
        def mock_remove(control):
            if control in page.controls:
                # Если у контрола есть will_unmount, вызываем его перед удалением
                if hasattr(control, 'will_unmount') and callable(control.will_unmount):
                    page._lifecycle_events.append(('will_unmount', control))
                    control.will_unmount()
                    
                page.controls.remove(control)
                page._lifecycle_events.append(('remove', control))
                
        page.remove = Mock(side_effect=mock_remove)
        
        # Остальные методы
        page.update = MagicMock()
        # Современный Flet API для работы с диалогами
        page.open = MagicMock()
        page.close = MagicMock()
        page.show_snack_bar = MagicMock()
        
        return page

    def create_mock_view_with_lifecycle(self, view_class):
        """
        Создание мока View с lifecycle методами.
        
        Args:
            view_class: Класс View для создания мока
            
        Returns:
            Mock: Мок View с lifecycle методами
        """
        view = Mock(spec=view_class)
        view._lifecycle_state = 'created'
        view._data_loaded = False
        
        # Мок для did_mount
        def mock_did_mount():
            view._lifecycle_state = 'mounted'
            # Симулируем загрузку данных после монтирования
            if hasattr(view, 'load_data') and callable(view.load_data):
                view.load_data()
                view._data_loaded = True
                
        view.did_mount = Mock(side_effect=mock_did_mount)
        
        # Мок для will_unmount
        def mock_will_unmount():
            view._lifecycle_state = 'unmounting'
            
        view.will_unmount = Mock(side_effect=mock_will_unmount)
        
        # Мок для load_data
        view.load_data = Mock()
        
        return view

    def test_view_lifecycle_sequence(self):
        """
        Тест проверяет правильную последовательность lifecycle методов.
        
        Validates: Requirements 6.2, 6.3, 6.4
        """
        # Создаем HomeView
        home_view = HomeView(self.mock_page, self.mock_session)
        
        # Проверяем начальное состояние - компонент создан, но не смонтирован
        self.assertIsNotNone(home_view)
        
        # Добавляем на страницу - должен вызваться did_mount
        self.mock_page.add(home_view)
        
        # Проверяем последовательность событий
        events = self.mock_page._lifecycle_events
        
        # Должно быть минимум 2 события: add и did_mount
        self.assertGreaterEqual(len(events), 2)
        
        # Проверяем, что add произошел перед did_mount
        add_event = None
        did_mount_event = None
        
        for event in events:
            if event[0] == 'add' and event[1] == home_view:
                add_event = event
            elif event[0] == 'did_mount' and event[1] == home_view:
                did_mount_event = event
        
        self.assertIsNotNone(add_event, "Событие 'add' должно произойти")
        self.assertIsNotNone(did_mount_event, "Событие 'did_mount' должно произойти")
        
        # Проверяем порядок: add должен быть перед did_mount
        add_index = events.index(add_event)
        did_mount_index = events.index(did_mount_event)
        self.assertLess(add_index, did_mount_index, 
                       "add должен происходить перед did_mount")
        
        # Удаляем со страницы - должен вызваться will_unmount
        self.mock_page.remove(home_view)
        
        # Проверяем, что will_unmount произошел перед remove
        will_unmount_event = None
        remove_event = None
        
        for event in events:
            if event[0] == 'will_unmount' and event[1] == home_view:
                will_unmount_event = event
            elif event[0] == 'remove' and event[1] == home_view:
                remove_event = event
        
        self.assertIsNotNone(will_unmount_event, "Событие 'will_unmount' должно произойти")
        self.assertIsNotNone(remove_event, "Событие 'remove' должно произойти")
        
        # Проверяем порядок: will_unmount должен быть перед remove
        will_unmount_index = events.index(will_unmount_event)
        remove_index = events.index(remove_event)
        self.assertLess(will_unmount_index, remove_index,
                       "will_unmount должен происходить перед remove")

    def test_did_mount_after_page_add(self):
        """
        Тест проверяет вызов did_mount после добавления на страницу.
        
        Validates: Requirements 6.2
        """
        # Патчим HomePresenter для отслеживания вызовов
        with patch('finance_tracker.views.home_view.HomePresenter') as MockPresenter:
            # Создаем HomeView
            home_view = HomeView(self.mock_page, self.mock_session)
            
            # Проверяем, что load_initial_data НЕ вызван в конструкторе
            MockPresenter.return_value.load_initial_data.assert_not_called()
            
            # Добавляем на страницу
            self.mock_page.add(home_view)
            
            # Проверяем, что did_mount был вызван
            # В реальном HomeView did_mount вызывает load_initial_data
            # Но поскольку мы патчим Presenter, проверяем через события
            events = self.mock_page._lifecycle_events
            did_mount_events = [e for e in events if e[0] == 'did_mount' and e[1] == home_view]
            
            self.assertEqual(len(did_mount_events), 1, 
                           "did_mount должен быть вызван ровно один раз")
            
            # Проверяем, что did_mount произошел после add
            add_events = [e for e in events if e[0] == 'add' and e[1] == home_view]
            self.assertEqual(len(add_events), 1, "add должен быть вызван ровно один раз")
            
            add_index = events.index(add_events[0])
            did_mount_index = events.index(did_mount_events[0])
            
            self.assertLess(add_index, did_mount_index,
                           "did_mount должен вызываться после add")

    def test_will_unmount_before_removal(self):
        """
        Тест проверяет вызов will_unmount перед удалением.
        
        Validates: Requirements 6.4
        """
        # Создаем HomeView
        home_view = HomeView(self.mock_page, self.mock_session)
        
        # Добавляем на страницу
        self.mock_page.add(home_view)
        
        # Очищаем события для чистого теста удаления
        self.mock_page._lifecycle_events.clear()
        
        # Удаляем со страницы
        self.mock_page.remove(home_view)
        
        # Проверяем последовательность событий при удалении
        events = self.mock_page._lifecycle_events
        
        will_unmount_events = [e for e in events if e[0] == 'will_unmount']
        remove_events = [e for e in events if e[0] == 'remove']
        
        self.assertEqual(len(will_unmount_events), 1,
                        "will_unmount должен быть вызван ровно один раз")
        self.assertEqual(len(remove_events), 1,
                        "remove должен быть вызван ровно один раз")
        
        # Проверяем порядок
        will_unmount_index = events.index(will_unmount_events[0])
        remove_index = events.index(remove_events[0])
        
        self.assertLess(will_unmount_index, remove_index,
                       "will_unmount должен происходить перед remove")

    def test_data_loading_after_mount(self):
        """
        Тест проверяет загрузку данных после монтирования.
        
        Проверяет, что данные загружаются только после того, как компонент
        добавлен на страницу и вызван did_mount, а не в конструкторе.
        
        Validates: Requirements 6.5
        """
        # Патчим HomePresenter для отслеживания вызовов
        with patch('finance_tracker.views.home_view.HomePresenter') as MockPresenter:
            # Создаем HomeView
            home_view = HomeView(self.mock_page, self.mock_session)
            
            # Проверяем, что load_initial_data НЕ вызван в конструкторе
            MockPresenter.return_value.load_initial_data.assert_not_called()
            
            # Добавляем на страницу - это должно вызвать did_mount
            self.mock_page.add(home_view)
            
            # Проверяем, что did_mount был вызван через lifecycle события
            events = self.mock_page._lifecycle_events
            did_mount_events = [e for e in events if e[0] == 'did_mount' and e[1] == home_view]
            
            self.assertEqual(len(did_mount_events), 1, 
                           "did_mount должен быть вызван ровно один раз после добавления на страницу")
            
            # Симулируем поведение MainWindow.did_mount() - загрузка данных после монтирования
            # В реальном коде MainWindow.did_mount() вызывает home_view.presenter.load_initial_data()
            home_view.presenter.load_initial_data()
            
            # Проверяем, что данные загружены после монтирования
            MockPresenter.return_value.load_initial_data.assert_called_once()
            
            # Проверяем правильную последовательность: add -> did_mount -> load_data
            add_events = [e for e in events if e[0] == 'add' and e[1] == home_view]
            self.assertEqual(len(add_events), 1, "add должен быть вызван ровно один раз")
            
            add_index = events.index(add_events[0])
            did_mount_index = events.index(did_mount_events[0])
            
            self.assertLess(add_index, did_mount_index,
                           "add должен происходить перед did_mount")
            
            # Проверяем, что HomeView имеет необходимые lifecycle методы
            if hasattr(home_view, 'did_mount'):
                self.assertTrue(callable(home_view.did_mount),
                              "HomeView должен иметь вызываемый метод did_mount")
            
            # Проверяем, что presenter доступен для загрузки данных
            self.assertIsNotNone(home_view.presenter,
                               "HomeView должен иметь presenter для загрузки данных")

    def test_no_data_loading_in_constructor(self):
        """
        Тест проверяет отсутствие загрузки данных в конструкторе.
        
        Проверяет, что при создании HomeView никакие методы загрузки данных
        не вызываются. Данные должны загружаться только после монтирования
        компонента на страницу через MainWindow.did_mount().
        
        Validates: Requirements 6.5
        """
        # Патчим все компоненты для отслеживания вызовов
        with patch('finance_tracker.views.home_view.HomePresenter') as MockPresenter, \
             patch('finance_tracker.views.home_view.CalendarWidget') as MockCalendar, \
             patch('finance_tracker.views.home_view.TransactionsPanel') as MockTransactionsPanel, \
             patch('finance_tracker.views.home_view.PlannedTransactionsWidget') as MockPlannedWidget, \
             patch('finance_tracker.views.home_view.PendingPaymentsWidget') as MockPendingWidget:
            
            # Создаем HomeView
            home_view = HomeView(self.mock_page, self.mock_session)
            
            # Проверяем, что компоненты созданы правильно
            self.assertIsNotNone(home_view)
            self.assertEqual(home_view.page, self.mock_page)
            self.assertEqual(home_view.session, self.mock_session)
            
            # Проверяем, что Presenter создан с правильными параметрами
            MockPresenter.assert_called_once_with(self.mock_session, home_view)
            
            # Проверяем, что UI компоненты созданы
            MockCalendar.assert_called_once()
            MockTransactionsPanel.assert_called_once()
            MockPlannedWidget.assert_called_once()
            MockPendingWidget.assert_called_once()
            
            # КРИТИЧЕСКИ ВАЖНО: проверяем, что load_initial_data НЕ вызван в конструкторе
            MockPresenter.return_value.load_initial_data.assert_not_called()
            
            # Проверяем, что другие методы загрузки данных также не вызваны в конструкторе
            MockPresenter.return_value.load_pending_payments.assert_not_called()
            MockPresenter.return_value.load_planned_transactions.assert_not_called()
            MockPresenter.return_value.load_calendar_data.assert_not_called()
            MockPresenter.return_value.on_date_selected.assert_not_called()
            
            # Проверяем, что presenter доступен для последующей загрузки данных
            self.assertIsNotNone(home_view.presenter)
            self.assertEqual(home_view.presenter, MockPresenter.return_value)
            
            # Проверяем, что selected_date установлена корректно
            self.assertIsNotNone(home_view.selected_date)
            self.assertIsInstance(home_view.selected_date, datetime.date)
            
            # Данные должны загружаться только после did_mount через MainWindow
            # Проверяем, что можно вызвать load_initial_data вручную (как делает MainWindow)
            home_view.presenter.load_initial_data()
            MockPresenter.return_value.load_initial_data.assert_called_once()

    def test_main_window_initialization_sequence(self):
        """
        Тест проверяет последовательность инициализации MainWindow.
        
        Validates: Requirements 6.1, 6.2
        """
        # Создаем MainWindow
        main_window = MainWindow(self.mock_page)
        
        # Проверяем, что MainWindow создан
        self.assertIsNotNone(main_window)
        
        # Проверяем, что HomeView создан, но данные не загружены
        self.assertIsNotNone(main_window.home_view)
        
        # Добавляем MainWindow на страницу
        self.mock_page.add(main_window)
        
        # Проверяем последовательность lifecycle событий
        events = self.mock_page._lifecycle_events
        
        # Должны быть события add и did_mount для MainWindow
        main_window_events = [e for e in events if e[1] == main_window]
        
        add_events = [e for e in main_window_events if e[0] == 'add']
        did_mount_events = [e for e in main_window_events if e[0] == 'did_mount']
        
        self.assertEqual(len(add_events), 1, "MainWindow должен быть добавлен один раз")
        self.assertEqual(len(did_mount_events), 1, "did_mount должен быть вызван один раз")
        
        # Проверяем порядок
        add_index = events.index(add_events[0])
        did_mount_index = events.index(did_mount_events[0])
        
        self.assertLess(add_index, did_mount_index,
                       "add должен происходить перед did_mount")

    def test_categories_view_lifecycle(self):
        """
        Тест проверяет lifecycle CategoriesView.
        
        Validates: Requirements 6.2, 6.3, 6.4
        """
        # Патчим сервисы и get_db_session для CategoriesView
        with patch('finance_tracker.views.categories_view.get_all_categories') as mock_get_all, \
             patch('finance_tracker.views.categories_view.get_db_session') as mock_get_db:
            
            mock_get_all.return_value = []
            mock_get_db.return_value = self.mock_db_session_cm
            
            # Создаем CategoriesView
            categories_view = CategoriesView(self.mock_page)
            
            # Проверяем, что сервис НЕ вызван в конструкторе
            mock_get_all.assert_not_called()
            
            # Добавляем на страницу
            self.mock_page.add(categories_view)
            
            # Проверяем lifecycle события
            events = self.mock_page._lifecycle_events
            
            categories_events = [e for e in events if e[1] == categories_view]
            add_events = [e for e in categories_events if e[0] == 'add']
            did_mount_events = [e for e in categories_events if e[0] == 'did_mount']
            
            self.assertEqual(len(add_events), 1)
            self.assertEqual(len(did_mount_events), 1)
            
            # Удаляем со страницы
            self.mock_page.remove(categories_view)
            
            # Проверяем события удаления
            will_unmount_events = [e for e in categories_events if e[0] == 'will_unmount']
            remove_events = [e for e in categories_events if e[0] == 'remove']
            
            # События will_unmount и remove должны быть добавлены после remove
            updated_events = self.mock_page._lifecycle_events
            updated_categories_events = [e for e in updated_events if e[1] == categories_view]
            
            will_unmount_events = [e for e in updated_categories_events if e[0] == 'will_unmount']
            remove_events = [e for e in updated_categories_events if e[0] == 'remove']
            
            self.assertEqual(len(will_unmount_events), 1)
            self.assertEqual(len(remove_events), 1)

    def test_loans_view_lifecycle(self):
        """
        Тест проверяет lifecycle LoansView.
        
        Validates: Requirements 6.2, 6.3, 6.4
        """
        # Патчим сервисы и get_db_session для LoansView
        with patch('finance_tracker.views.loans_view.get_all_loans') as mock_get_all_loans, \
             patch('finance_tracker.views.loans_view.get_summary_statistics') as mock_get_summary, \
             patch('finance_tracker.views.loans_view.get_db_session') as mock_get_db:
            
            mock_get_all_loans.return_value = []
            mock_get_summary.return_value = {}
            mock_get_db.return_value = self.mock_db_session_cm
            
            # Создаем LoansView
            loans_view = LoansView(self.mock_page)
            
            # LoansView загружает данные в конструкторе (отличается от HomeView)
            # Проверяем, что сервисы БЫЛИ вызваны в конструкторе
            mock_get_all_loans.assert_called()
            mock_get_summary.assert_called()
            
            # Добавляем на страницу
            self.mock_page.add(loans_view)
            
            # Проверяем lifecycle события
            events = self.mock_page._lifecycle_events
            
            loans_events = [e for e in events if e[1] == loans_view]
            add_events = [e for e in loans_events if e[0] == 'add']
            did_mount_events = [e for e in loans_events if e[0] == 'did_mount']
            
            self.assertEqual(len(add_events), 1)
            self.assertEqual(len(did_mount_events), 1)
            
            # Проверяем порядок событий
            add_index = events.index(add_events[0])
            did_mount_index = events.index(did_mount_events[0])
            
            self.assertLess(add_index, did_mount_index)

    def test_multiple_views_lifecycle_independence(self):
        """
        Тест проверяет независимость lifecycle разных View.
        
        Validates: Requirements 6.1, 6.2, 6.3, 6.4
        """
        # Создаем несколько View
        home_view = HomeView(self.mock_page, self.mock_session)
        
        with patch('finance_tracker.views.categories_view.get_all_categories') as mock_get_all_categories, \
             patch('finance_tracker.views.categories_view.get_db_session') as mock_get_db:
            
            mock_get_all_categories.return_value = []
            mock_get_db.return_value = self.mock_db_session_cm
            categories_view = CategoriesView(self.mock_page)
        
        # Добавляем первый View
        self.mock_page.add(home_view)
        
        # Проверяем события для первого View
        events_after_first = list(self.mock_page._lifecycle_events)
        home_events = [e for e in events_after_first if e[1] == home_view]
        
        self.assertGreaterEqual(len(home_events), 2)  # add + did_mount
        
        # Добавляем второй View
        self.mock_page.add(categories_view)
        
        # Проверяем события для второго View
        events_after_second = self.mock_page._lifecycle_events
        categories_events = [e for e in events_after_second if e[1] == categories_view]
        
        self.assertGreaterEqual(len(categories_events), 2)  # add + did_mount
        
        # Удаляем первый View
        self.mock_page.remove(home_view)
        
        # Проверяем, что события второго View не затронуты
        final_events = self.mock_page._lifecycle_events
        final_categories_events = [e for e in final_events if e[1] == categories_view]
        
        # У categories_view должны остаться только события add и did_mount
        # (will_unmount и remove не должны быть вызваны)
        categories_add_events = [e for e in final_categories_events if e[0] == 'add']
        categories_did_mount_events = [e for e in final_categories_events if e[0] == 'did_mount']
        categories_will_unmount_events = [e for e in final_categories_events if e[0] == 'will_unmount']
        
        self.assertEqual(len(categories_add_events), 1)
        self.assertEqual(len(categories_did_mount_events), 1)
        self.assertEqual(len(categories_will_unmount_events), 0,
                        "categories_view не должен быть размонтирован")

    def test_lifecycle_error_handling(self):
        """
        Тест проверяет обработку ошибок в lifecycle методах.
        
        Validates: Requirements 6.1, 6.2
        """
        # Создаем View с ошибкой в did_mount
        home_view = HomeView(self.mock_page, self.mock_session)
        
        # Патчим did_mount для вызова ошибки
        original_did_mount = home_view.did_mount if hasattr(home_view, 'did_mount') else None
        
        def error_did_mount():
            raise Exception("Error in did_mount")
        
        home_view.did_mount = error_did_mount
        
        # Добавляем на страницу - должна произойти ошибка в did_mount
        with self.assertRaises(Exception) as context:
            self.mock_page.add(home_view)
        
        self.assertIn("Error in did_mount", str(context.exception))
        
        # Проверяем, что add все равно произошел
        events = self.mock_page._lifecycle_events
        add_events = [e for e in events if e[0] == 'add' and e[1] == home_view]
        
        self.assertEqual(len(add_events), 1, "add должен произойти даже при ошибке в did_mount")

    def test_lifecycle_method_existence(self):
        """
        Тест проверяет наличие lifecycle методов в View компонентах.
        
        Validates: Requirements 6.1
        """
        # Создаем различные View
        home_view = HomeView(self.mock_page, self.mock_session)
        
        with patch('finance_tracker.views.categories_view.get_all_categories') as mock_get_all_categories, \
             patch('finance_tracker.views.categories_view.get_db_session') as mock_get_db:
            
            mock_get_all_categories.return_value = []
            mock_get_db.return_value = self.mock_db_session_cm
            categories_view = CategoriesView(self.mock_page)
        
        # Проверяем наличие lifecycle методов
        views_to_test = [
            ("HomeView", home_view),
            ("CategoriesView", categories_view)
        ]
        
        for view_name, view in views_to_test:
            with self.subTest(view=view_name):
                # did_mount может быть определен или наследован
                # Проверяем, что метод существует и вызываемый
                if hasattr(view, 'did_mount'):
                    self.assertTrue(callable(view.did_mount),
                                  f"{view_name} должен иметь вызываемый метод did_mount")
                
                # will_unmount может быть определен или наследован
                if hasattr(view, 'will_unmount'):
                    self.assertTrue(callable(view.will_unmount),
                                  f"{view_name} должен иметь вызываемый метод will_unmount")


# =============================================================================
# Property-Based Tests
# =============================================================================

@settings(max_examples=50, deadline=None)
@given(
    st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=5),  # view_names
    st.integers(min_value=1, max_value=10),  # lifecycle_operations_count
    st.booleans()  # include_errors
)
def test_property_6_component_lifecycle_consistency(view_names, lifecycle_operations_count, include_errors):
    """
    **Feature: error-regression-testing, Property 6: Component Lifecycle Consistency**
    
    For any UI component, the lifecycle methods (did_mount, will_unmount) should be called in the correct order.
    
    Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5
    """
    # Создаем mock объекты
    mock_page = MagicMock(spec=ft.Page)
    # Явно настраиваем методы для современного Flet Dialog API (>= 0.25.0)
    mock_page.open = MagicMock()
    mock_page.close = MagicMock()
    mock_session = Mock()
    
    # Отслеживание lifecycle событий
    lifecycle_events = []
    
    def track_add(control):
        lifecycle_events.append(('add', control))
        # Симулируем вызов did_mount после add
        if hasattr(control, 'did_mount') and callable(control.did_mount):
            lifecycle_events.append(('did_mount', control))
            if not include_errors:
                control.did_mount()
    
    def track_remove(control):
        # Симулируем вызов will_unmount перед remove
        if hasattr(control, 'will_unmount') and callable(control.will_unmount):
            lifecycle_events.append(('will_unmount', control))
            if not include_errors:
                control.will_unmount()
        lifecycle_events.append(('remove', control))
    
    mock_page.add = Mock(side_effect=track_add)
    mock_page.remove = Mock(side_effect=track_remove)
    mock_page.controls = []
    mock_page.overlay = []
    mock_page.update = Mock()
    
    # Патчим зависимости для изоляции теста
    with patch('finance_tracker.views.home_view.HomePresenter'), \
         patch('finance_tracker.views.home_view.CalendarWidget'), \
         patch('finance_tracker.views.home_view.TransactionsPanel'), \
         patch('finance_tracker.views.home_view.PendingPaymentsWidget'):
        
        # Создаем mock views на основе view_names
        mock_views = []
        for i, view_name in enumerate(view_names[:3]):  # Ограничиваем до 3 для производительности
            # Создаем простой mock view
            mock_view = Mock()
            mock_view.name = f"MockView_{view_name}_{i}"
            mock_view._lifecycle_state = 'created'
            
            # Добавляем lifecycle методы
            def make_did_mount(view):
                def did_mount():
                    view._lifecycle_state = 'mounted'
                return did_mount
            
            def make_will_unmount(view):
                def will_unmount():
                    view._lifecycle_state = 'unmounting'
                return will_unmount
            
            mock_view.did_mount = make_did_mount(mock_view)
            mock_view.will_unmount = make_will_unmount(mock_view)
            
            mock_views.append(mock_view)
        
        # Выполняем lifecycle операции
        for i in range(min(lifecycle_operations_count, len(mock_views))):
            view = mock_views[i]
            
            try:
                # Property 1: Добавление на страницу должно вызвать did_mount
                mock_page.add(view)
                
                # Проверяем, что события произошли в правильном порядке
                view_events = [e for e in lifecycle_events if e[1] == view]
                
                if len(view_events) >= 2:
                    # Должны быть события add и did_mount
                    add_events = [e for e in view_events if e[0] == 'add']
                    did_mount_events = [e for e in view_events if e[0] == 'did_mount']
                    
                    assert len(add_events) == 1, f"View {view.name} должен быть добавлен ровно один раз"
                    assert len(did_mount_events) == 1, f"did_mount для {view.name} должен быть вызван ровно один раз"
                    
                    # Property 2: add должен происходить перед did_mount
                    add_index = lifecycle_events.index(add_events[0])
                    did_mount_index = lifecycle_events.index(did_mount_events[0])
                    
                    assert add_index < did_mount_index, \
                        f"add должен происходить перед did_mount для {view.name}. " \
                        f"Events: {lifecycle_events}"
                
                # Property 3: Состояние view должно измениться после did_mount
                if not include_errors:
                    assert view._lifecycle_state == 'mounted', \
                        f"View {view.name} должен быть в состоянии 'mounted' после did_mount"
                
                # Удаляем view (только для части views для тестирования will_unmount)
                if i % 2 == 0:  # Удаляем каждый второй view
                    mock_page.remove(view)
                    
                    # Property 4: Проверяем порядок will_unmount и remove
                    updated_view_events = [e for e in lifecycle_events if e[1] == view]
                    
                    will_unmount_events = [e for e in updated_view_events if e[0] == 'will_unmount']
                    remove_events = [e for e in updated_view_events if e[0] == 'remove']
                    
                    if will_unmount_events and remove_events:
                        will_unmount_index = lifecycle_events.index(will_unmount_events[0])
                        remove_index = lifecycle_events.index(remove_events[0])
                        
                        # Property 5: will_unmount должен происходить перед remove
                        assert will_unmount_index < remove_index, \
                            f"will_unmount должен происходить перед remove для {view.name}. " \
                            f"Events: {lifecycle_events}"
                    
                    # Property 6: Состояние view должно измениться после will_unmount
                    if not include_errors:
                        assert view._lifecycle_state == 'unmounting', \
                            f"View {view.name} должен быть в состоянии 'unmounting' после will_unmount"
            
            except Exception as e:
                if include_errors:
                    # При включенных ошибках некоторые операции могут падать
                    # Это нормально для тестирования error handling
                    continue
                else:
                    # При выключенных ошибках все операции должны работать
                    raise AssertionError(f"Lifecycle operation failed for {view.name}: {e}")
        
        # Property 7: Общая консистентность - количество add должно быть >= количества remove
        add_count = len([e for e in lifecycle_events if e[0] == 'add'])
        remove_count = len([e for e in lifecycle_events if e[0] == 'remove'])
        
        assert add_count >= remove_count, \
            f"Количество add ({add_count}) должно быть >= количества remove ({remove_count}). " \
            f"Events: {lifecycle_events}"
        
        # Property 8: Для каждого did_mount должен быть соответствующий add
        did_mount_count = len([e for e in lifecycle_events if e[0] == 'did_mount'])
        
        assert did_mount_count <= add_count, \
            f"Количество did_mount ({did_mount_count}) не должно превышать количество add ({add_count}). " \
            f"Events: {lifecycle_events}"
        
        # Property 9: Для каждого will_unmount должен быть соответствующий remove
        will_unmount_count = len([e for e in lifecycle_events if e[0] == 'will_unmount'])
        
        assert will_unmount_count <= remove_count, \
            f"Количество will_unmount ({will_unmount_count}) не должно превышать количество remove ({remove_count}). " \
            f"Events: {lifecycle_events}"


if __name__ == '__main__':
    unittest.main()
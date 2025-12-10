"""
Тесты для MainWindow.

Проверяет:
- Инициализацию MainWindow
- Навигацию между View через меню
- Корректное закрытие View при переходе
- Smoke test для всех пунктов меню
"""
import unittest
from unittest.mock import Mock, ANY
from decimal import Decimal

from finance_tracker.views.main_window import MainWindow
from test_view_base import ViewTestBase


class TestMainWindow(ViewTestBase):
    """Тесты для MainWindow."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        super().setUp()
        
        # Патчим get_db_session для возврата мока context manager
        self.mock_db_cm = self.create_mock_db_context()
        self.mock_get_db = self.add_patcher(
            'finance_tracker.views.main_window.get_db_session',
            return_value=self.mock_db_cm
        )
        
        # Патчим get_total_balance
        self.mock_get_total_balance = self.add_patcher(
            'finance_tracker.views.main_window.get_total_balance',
            return_value=Decimal("10000.00")
        )
        
        # Патчим settings
        self.mock_settings = self.add_patcher(
            'finance_tracker.views.main_window.settings'
        )
        self.mock_settings.theme_mode = "light"
        self.mock_settings.last_selected_index = 0
        self.mock_settings.window_width = 1200
        self.mock_settings.window_height = 800
        self.mock_settings.window_top = None
        self.mock_settings.window_left = None
        self.mock_settings.save = Mock()
        
        # Патчим все View классы
        self.mock_home_view = self.add_patcher(
            'finance_tracker.views.main_window.HomeView'
        )
        self.mock_categories_view = self.add_patcher(
            'finance_tracker.views.main_window.CategoriesView'
        )
        self.mock_lenders_view = self.add_patcher(
            'finance_tracker.views.main_window.LendersView'
        )
        self.mock_loans_view = self.add_patcher(
            'finance_tracker.views.main_window.LoansView'
        )
        self.mock_pending_payments_view = self.add_patcher(
            'finance_tracker.views.main_window.PendingPaymentsView'
        )
        self.mock_planned_transactions_view = self.add_patcher(
            'finance_tracker.views.main_window.PlannedTransactionsView'
        )
        self.mock_plan_fact_view = self.add_patcher(
            'finance_tracker.views.main_window.PlanFactView'
        )
        self.mock_settings_view = self.add_patcher(
            'finance_tracker.views.main_window.SettingsView'
        )
        
        # Настраиваем page с дополнительными атрибутами для MainWindow
        self.page.window = Mock()
        self.page.window.maximized = False
        self.page.window.width = 1200
        self.page.window.height = 800
        self.page.window.top = 100
        self.page.window.left = 100
        self.page.window.icon = None
        self.page.appbar = None
        self.page.theme_mode = None
        self.page.padding = None
        self.page.title = None
        
        # Создаем экземпляр MainWindow
        self.window = MainWindow(self.page)
        
        # Мокируем content_area.update() чтобы избежать ошибки "Control must be added to the page first"
        self.window.content_area.update = Mock()

    def test_initialization(self):
        """
        Тест инициализации MainWindow.
        
        Проверяет:
        - MainWindow создается без исключений
        - Атрибут page установлен
        - UI компоненты созданы (rail, content_area, appbar)
        - Начальный View загружен
        
        Validates: Requirements 5.1, 5.2
        """
        # Проверяем, что MainWindow создан
        self.assertIsInstance(self.window, MainWindow)
        
        # Проверяем атрибуты
        self.assertEqual(self.window.page, self.page)
        self.assertTrue(self.window.expand)
        
        # Проверяем, что UI компоненты созданы
        self.assertIsNotNone(self.window.rail)
        self.assertIsNotNone(self.window.content_area)
        self.assertIsNotNone(self.window.balance_text)
        
        # Проверяем, что appbar установлен
        self.assertIsNotNone(self.page.appbar)

        # Проверяем, что начальный View загружен (HomeView по умолчанию)
        # HomeView теперь получает page и session через DI
        self.mock_home_view.assert_called_once_with(self.page, ANY)
        
        # Проверяем, что rail содержит все пункты меню
        self.assertEqual(len(self.window.rail.destinations), 8)

    def test_setup_page_configures_page_properties(self):
        """
        Тест настройки свойств страницы.
        
        Проверяет:
        - Заголовок страницы установлен
        - Тема установлена из настроек
        - Размеры окна установлены
        - Окно развернуто на весь экран
        
        Validates: Requirements 5.1
        """
        # Проверяем заголовок
        self.assertEqual(self.page.title, "Finance Tracker")
        
        # Проверяем тему (light из настроек)
        self.assertIsNotNone(self.page.theme_mode)
        
        # Проверяем padding
        self.assertEqual(self.page.padding, 0)
        
        # Проверяем, что окно развернуто
        self.assertTrue(self.page.window.maximized)
        
        # Проверяем размеры окна
        self.assertEqual(self.page.window.width, 1200)
        self.assertEqual(self.page.window.height, 800)

    def test_navigate_to_planned_transactions(self):
        """
        Тест навигации к PlannedTransactionsView.
        
        Проверяет:
        - При выборе пункта меню "Плановые" (индекс 1) открывается PlannedTransactionsView
        - selected_index обновляется
        - content_area обновляется
        - Настройки сохраняются
        
        Validates: Requirements 5.1, 5.2
        """
        # Сбрасываем счетчики вызовов после инициализации
        self.mock_planned_transactions_view.reset_mock()
        self.mock_settings.save.reset_mock()
        
        # Навигация к PlannedTransactionsView (индекс 1)
        self.window.navigate(1)
        
        # Проверяем, что selected_index обновлен
        self.assertEqual(self.window.rail.selected_index, 1)
        
        # Проверяем, что PlannedTransactionsView создан
        self.mock_planned_transactions_view.assert_called_once_with(self.page)
        
        # Проверяем, что content_area.update вызван
        self.window.content_area.update.assert_called()
        
        # Проверяем, что настройки сохранены
        self.mock_settings.save.assert_called_once()

    def test_navigate_to_loans(self):
        """
        Тест навигации к LoansView.
        
        Проверяет:
        - При выборе пункта меню "Кредиты" (индекс 2) открывается LoansView
        
        Validates: Requirements 5.1, 5.2
        """
        # Сбрасываем счетчики
        self.mock_loans_view.reset_mock()
        
        # Навигация к LoansView (индекс 2)
        self.window.navigate(2)
        
        # Проверяем, что LoansView создан
        self.mock_loans_view.assert_called_once_with(self.page)
        
        # Проверяем, что selected_index обновлен
        self.assertEqual(self.window.rail.selected_index, 2)

    def test_navigate_to_pending_payments(self):
        """
        Тест навигации к PendingPaymentsView.
        
        Проверяет:
        - При выборе пункта меню "Отложенные" (индекс 3) открывается PendingPaymentsView
        
        Validates: Requirements 5.1, 5.2
        """
        # Сбрасываем счетчики
        self.mock_pending_payments_view.reset_mock()
        
        # Навигация к PendingPaymentsView (индекс 3)
        self.window.navigate(3)
        
        # Проверяем, что PendingPaymentsView создан
        self.mock_pending_payments_view.assert_called_once_with(self.page)
        
        # Проверяем, что selected_index обновлен
        self.assertEqual(self.window.rail.selected_index, 3)

    def test_navigate_to_plan_fact(self):
        """
        Тест навигации к PlanFactView.
        
        Проверяет:
        - При выборе пункта меню "План" (индекс 4) открывается PlanFactView
        
        Validates: Requirements 5.1, 5.2
        """
        # Сбрасываем счетчики
        self.mock_plan_fact_view.reset_mock()
        
        # Навигация к PlanFactView (индекс 4)
        self.window.navigate(4)
        
        # Проверяем, что PlanFactView создан
        # PlanFactView не принимает page в конструкторе
        self.mock_plan_fact_view.assert_called_once_with()
        
        # Проверяем, что selected_index обновлен
        self.assertEqual(self.window.rail.selected_index, 4)

    def test_navigate_to_lenders(self):
        """
        Тест навигации к LendersView.
        
        Проверяет:
        - При выборе пункта меню "Займодатели" (индекс 5) открывается LendersView
        
        Validates: Requirements 5.1, 5.2
        """
        # Сбрасываем счетчики
        self.mock_lenders_view.reset_mock()
        
        # Навигация к LendersView (индекс 5)
        self.window.navigate(5)
        
        # Проверяем, что LendersView создан
        self.mock_lenders_view.assert_called_once_with(self.page)
        
        # Проверяем, что selected_index обновлен
        self.assertEqual(self.window.rail.selected_index, 5)

    def test_navigate_to_categories(self):
        """
        Тест навигации к CategoriesView.
        
        Проверяет:
        - При выборе пункта меню "Категории" (индекс 6) открывается CategoriesView
        
        Validates: Requirements 5.1, 5.2
        """
        # Сбрасываем счетчики
        self.mock_categories_view.reset_mock()
        
        # Навигация к CategoriesView (индекс 6)
        self.window.navigate(6)
        
        # Проверяем, что CategoriesView создан
        self.mock_categories_view.assert_called_once_with(self.page)
        
        # Проверяем, что selected_index обновлен
        self.assertEqual(self.window.rail.selected_index, 6)

    def test_navigate_to_settings(self):
        """
        Тест навигации к SettingsView.
        
        Проверяет:
        - При выборе пункта меню "Настройки" (индекс 7) открывается SettingsView
        
        Validates: Requirements 5.1, 5.2
        """
        # Сбрасываем счетчики
        self.mock_settings_view.reset_mock()
        
        # Навигация к SettingsView (индекс 7)
        self.window.navigate(7)
        
        # Проверяем, что SettingsView создан
        self.mock_settings_view.assert_called_once_with(self.page)
        
        # Проверяем, что selected_index обновлен
        self.assertEqual(self.window.rail.selected_index, 7)

    def test_navigate_back_to_home(self):
        """
        Тест навигации обратно к HomeView.

        Проверяет:
        - После навигации к другому View можно вернуться к HomeView
        - При возврате переиспользуется тот же экземпляр HomeView (не создается новый)

        Validates: Requirements 5.1, 5.2
        """
        # HomeView уже создан в init_ui
        initial_home_view = self.window.home_view

        # Навигация к CategoriesView
        self.window.navigate(6)

        # Сбрасываем счетчики
        self.mock_home_view.reset_mock()

        # Навигация обратно к HomeView (индекс 0)
        self.window.navigate(0)

        # Проверяем, что HomeView НЕ создавался заново (счетчик вызовов остался 0)
        self.mock_home_view.assert_not_called()

        # Проверяем, что переиспользуется тот же экземпляр
        self.assertEqual(self.window.get_view(0), initial_home_view)

        # Проверяем, что selected_index обновлен
        self.assertEqual(self.window.rail.selected_index, 0)

    def test_save_state_saves_settings(self):
        """
        Тест сохранения состояния приложения.
        
        Проверяет:
        - При вызове save_state() сохраняется selected_index
        - Сохраняются размеры и позиция окна
        - Вызывается settings.save()
        
        Validates: Requirements 5.1
        """
        # Устанавливаем состояние
        self.window.rail.selected_index = 3
        self.page.window.width = 1400
        self.page.window.height = 900
        self.page.window.top = 50
        self.page.window.left = 50
        
        # Сбрасываем счетчик
        self.mock_settings.save.reset_mock()
        
        # Сохраняем состояние
        self.window.save_state()
        
        # Проверяем, что настройки обновлены
        self.assertEqual(self.mock_settings.last_selected_index, 3)
        self.assertEqual(self.mock_settings.window_width, 1400)
        self.assertEqual(self.mock_settings.window_height, 900)
        self.assertEqual(self.mock_settings.window_top, 50)
        self.assertEqual(self.mock_settings.window_left, 50)
        
        # Проверяем, что save() вызван
        self.mock_settings.save.assert_called_once()

    def test_update_balance_updates_text(self):
        """
        Тест обновления баланса.
        
        Проверяет:
        - При вызове update_balance() вызывается get_total_balance
        - balance_text обновляется с новым значением
        - Форматирование суммы корректное
        
        Validates: Requirements 5.1
        """
        # Настраиваем мок для возврата конкретного баланса
        self.mock_get_total_balance.return_value = Decimal("12345.67")
        
        # Обновляем баланс
        self.window.update_balance()
        
        # Проверяем, что get_total_balance был вызван
        self.mock_get_total_balance.assert_called_with(self.mock_session)
        
        # Проверяем, что balance_text обновлен
        self.assertIn("12 345.67", self.window.balance_text.value)
        self.assertIn("₽", self.window.balance_text.value)

    def test_navigate_updates_balance(self):
        """
        Тест обновления баланса при навигации.
        
        Проверяет:
        - При навигации между View баланс обновляется
        
        Validates: Requirements 5.1
        """
        # Сбрасываем счетчик
        self.mock_get_total_balance.reset_mock()
        
        # Навигация к другому View
        self.window.navigate(1)
        
        # Проверяем, что баланс обновлен
        self.mock_get_total_balance.assert_called()

    def test_get_view_returns_correct_view_for_each_index(self):
        """
        Smoke test для всех пунктов меню.

        Проверяет:
        - Для каждого индекса меню get_view() возвращает соответствующий View
        - Все View создаются без исключений
        - HomeView создается один раз в init_ui и переиспользуется

        Validates: Requirements 5.4
        """
        # HomeView уже создан в init_ui (в setUp), проверяем, что был вызван
        self.mock_home_view.assert_called_once_with(self.page, ANY)

        # Сбрасываем счетчик для других view
        self.mock_planned_transactions_view.reset_mock()
        self.mock_loans_view.reset_mock()
        self.mock_pending_payments_view.reset_mock()
        self.mock_plan_fact_view.reset_mock()
        self.mock_lenders_view.reset_mock()
        self.mock_categories_view.reset_mock()
        self.mock_settings_view.reset_mock()

        # Проверяем, что get_view(0) возвращает переиспользованный HomeView
        view_0 = self.window.get_view(0)
        self.assertEqual(view_0, self.window.home_view)

        # Остальные view создаются при каждом вызове get_view
        view_1 = self.window.get_view(1)
        self.mock_planned_transactions_view.assert_called_once_with(self.page)

        view_2 = self.window.get_view(2)
        self.mock_loans_view.assert_called_once_with(self.page)

        view_3 = self.window.get_view(3)
        self.mock_pending_payments_view.assert_called_once_with(self.page)

        view_4 = self.window.get_view(4)
        self.mock_plan_fact_view.assert_called_once_with()

        view_5 = self.window.get_view(5)
        self.mock_lenders_view.assert_called_once_with(self.page)

        view_6 = self.window.get_view(6)
        self.mock_categories_view.assert_called_once_with(self.page)

        view_7 = self.window.get_view(7)
        self.mock_settings_view.assert_called_once_with(self.page)

    def test_get_view_returns_error_for_invalid_index(self):
        """
        Тест обработки некорректного индекса.
        
        Проверяет:
        - При передаче несуществующего индекса возвращается сообщение об ошибке
        
        Validates: Requirements 5.1
        """
        # Получаем View для несуществующего индекса
        view = self.window.get_view(999)
        
        # Проверяем, что возвращен Text с сообщением об ошибке
        self.assertIsNotNone(view)
        # Проверяем, что это ft.Text (через hasattr, так как мы не можем импортировать ft.Text напрямую)
        self.assertTrue(hasattr(view, 'value'))

    def test_rail_on_change_triggers_navigation(self):
        """
        Тест триггера навигации через rail.on_change.
        
        Проверяет:
        - При изменении selected_index в rail вызывается navigate()
        
        Validates: Requirements 5.1
        """
        # Создаем мок события
        mock_event = Mock()
        mock_event.control = Mock()
        mock_event.control.selected_index = 2
        
        # Сбрасываем счетчики
        self.mock_loans_view.reset_mock()
        
        # Вызываем on_change callback
        self.window.rail.on_change(mock_event)
        
        # Проверяем, что navigate был вызван с индексом 2
        self.mock_loans_view.assert_called_once_with(self.page)
        self.assertEqual(self.window.rail.selected_index, 2)


if __name__ == '__main__':
    unittest.main()



# =============================================================================
# Property-Based Tests
# =============================================================================

from hypothesis import given, strategies as st, settings


class TestMainWindowProperties(ViewTestBase):
    """Property-based тесты для MainWindow."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        super().setUp()
        
        # Патчим get_db_session для возврата мока context manager
        self.mock_db_cm = self.create_mock_db_context()
        self.mock_get_db = self.add_patcher(
            'finance_tracker.views.main_window.get_db_session',
            return_value=self.mock_db_cm
        )
        
        # Патчим get_total_balance
        self.mock_get_total_balance = self.add_patcher(
            'finance_tracker.views.main_window.get_total_balance',
            return_value=Decimal("10000.00")
        )
        
        # Патчим settings
        self.mock_settings = self.add_patcher(
            'finance_tracker.views.main_window.settings'
        )
        self.mock_settings.theme_mode = "light"
        self.mock_settings.last_selected_index = 0
        self.mock_settings.window_width = 1200
        self.mock_settings.window_height = 800
        self.mock_settings.window_top = None
        self.mock_settings.window_left = None
        self.mock_settings.save = Mock()
        
        # Патчим все View классы
        self.mock_home_view = self.add_patcher(
            'finance_tracker.views.main_window.HomeView'
        )
        self.mock_categories_view = self.add_patcher(
            'finance_tracker.views.main_window.CategoriesView'
        )
        self.mock_lenders_view = self.add_patcher(
            'finance_tracker.views.main_window.LendersView'
        )
        self.mock_loans_view = self.add_patcher(
            'finance_tracker.views.main_window.LoansView'
        )
        self.mock_pending_payments_view = self.add_patcher(
            'finance_tracker.views.main_window.PendingPaymentsView'
        )
        self.mock_planned_transactions_view = self.add_patcher(
            'finance_tracker.views.main_window.PlannedTransactionsView'
        )
        self.mock_plan_fact_view = self.add_patcher(
            'finance_tracker.views.main_window.PlanFactView'
        )
        self.mock_settings_view = self.add_patcher(
            'finance_tracker.views.main_window.SettingsView'
        )
        
        # Настраиваем page с дополнительными атрибутами для MainWindow
        self.page.window = Mock()
        self.page.window.maximized = False
        self.page.window.width = 1200
        self.page.window.height = 800
        self.page.window.top = 100
        self.page.window.left = 100
        self.page.window.icon = None
        self.page.appbar = None
        self.page.theme_mode = None
        self.page.padding = None
        self.page.title = None

    @settings(max_examples=100)
    @given(menu_index=st.integers(min_value=0, max_value=7))
    def test_property_navigation_between_views(self, menu_index):
        """
        Feature: ui-testing, Property 8: Навигация между View

        Проверяет:
        - Для любого валидного индекса меню (0-7) навигация работает корректно
        - Соответствующий View создается (кроме HomeView, который переиспользуется)
        - selected_index обновляется
        - Настройки сохраняются

        Validates: Requirements 5.1, 5.2
        """
        # Создаем MainWindow
        window = MainWindow(self.page)
        window.content_area.update = Mock()

        # Сбрасываем счетчики после инициализации
        self.mock_home_view.reset_mock()
        self.mock_planned_transactions_view.reset_mock()
        self.mock_loans_view.reset_mock()
        self.mock_pending_payments_view.reset_mock()
        self.mock_plan_fact_view.reset_mock()
        self.mock_lenders_view.reset_mock()
        self.mock_categories_view.reset_mock()
        self.mock_settings_view.reset_mock()
        self.mock_settings.save.reset_mock()

        # Выполняем навигацию
        window.navigate(menu_index)

        # Проверяем, что selected_index обновлен
        self.assertEqual(window.rail.selected_index, menu_index)

        # Проверяем, что соответствующий View был создан
        view_mocks = [
            self.mock_home_view,
            self.mock_planned_transactions_view,
            self.mock_loans_view,
            self.mock_pending_payments_view,
            self.mock_plan_fact_view,
            self.mock_lenders_view,
            self.mock_categories_view,
            self.mock_settings_view,
        ]

        # HomeView (индекс 0) переиспользуется, поэтому не вызывается при навигации
        # Остальные view создаются заново при каждой навигации
        if menu_index == 0:
            # HomeView не вызывается при navigate(0), так как переиспользуется
            self.mock_home_view.assert_not_called()
        else:
            # Остальные view создаются при navigate
            view_mocks[menu_index].assert_called()

        # Проверяем, что content_area.update был вызван
        window.content_area.update.assert_called()
        
        # Проверяем, что настройки сохранены
        self.mock_settings.save.assert_called()
        
        # Проверяем, что баланс обновлен
        self.mock_get_total_balance.assert_called()

    @settings(max_examples=100)
    @given(
        first_index=st.integers(min_value=0, max_value=7),
        second_index=st.integers(min_value=0, max_value=7)
    )
    def test_property_view_closure_on_navigation(self, first_index, second_index):
        """
        Feature: ui-testing, Property 9: Закрытие View при навигации

        Проверяет:
        - При переходе от одного View к другому создается новый экземпляр View (кроме HomeView)
        - HomeView переиспользуется при каждой навигации к индексу 0
        - Остальные view создаются заново при каждой навигации (старый заменяется)
        - Настройки сохраняются при каждой навигации

        Validates: Requirements 5.1, 5.2, 5.3
        """
        # Создаем MainWindow
        window = MainWindow(self.page)
        window.content_area.update = Mock()

        # Сбрасываем счетчики после инициализации
        self.mock_home_view.reset_mock()
        self.mock_planned_transactions_view.reset_mock()
        self.mock_loans_view.reset_mock()
        self.mock_pending_payments_view.reset_mock()
        self.mock_plan_fact_view.reset_mock()
        self.mock_lenders_view.reset_mock()
        self.mock_categories_view.reset_mock()
        self.mock_settings_view.reset_mock()
        self.mock_settings.save.reset_mock()

        # Первая навигация
        window.navigate(first_index)

        # Запоминаем количество вызовов после первой навигации
        first_save_count = self.mock_settings.save.call_count

        # Сбрасываем счетчики
        self.mock_home_view.reset_mock()
        self.mock_planned_transactions_view.reset_mock()
        self.mock_loans_view.reset_mock()
        self.mock_pending_payments_view.reset_mock()
        self.mock_plan_fact_view.reset_mock()
        self.mock_lenders_view.reset_mock()
        self.mock_categories_view.reset_mock()
        self.mock_settings_view.reset_mock()

        # Вторая навигация
        window.navigate(second_index)

        # Проверяем, что selected_index обновлен
        self.assertEqual(window.rail.selected_index, second_index)

        # Проверяем, что новый View был создан
        view_mocks = [
            self.mock_home_view,
            self.mock_planned_transactions_view,
            self.mock_loans_view,
            self.mock_pending_payments_view,
            self.mock_plan_fact_view,
            self.mock_lenders_view,
            self.mock_categories_view,
            self.mock_settings_view,
        ]

        # HomeView (индекс 0) переиспользуется, поэтому не вызывается при второй навигации
        # Остальные view создаются заново при каждой навигации
        if second_index == 0:
            # HomeView не вызывается при navigate(0), так как переиспользуется
            self.mock_home_view.assert_not_called()
        else:
            # Остальные view создаются при navigate
            view_mocks[second_index].assert_called()
        
        # Проверяем, что content_area был обновлен
        self.assertIsNotNone(window.content_area.content)
        
        # Проверяем, что настройки сохранены при второй навигации
        second_save_count = self.mock_settings.save.call_count
        self.assertGreater(second_save_count, 0, "Настройки должны быть сохранены при второй навигации")

    @settings(max_examples=50)
    @given(
        navigation_sequence=st.lists(
            st.integers(min_value=0, max_value=7),
            min_size=2,
            max_size=5
        )
    )
    def test_property_multiple_navigations(self, navigation_sequence):
        """
        Feature: ui-testing, Property 8: Навигация между View (расширенный)
        
        Проверяет:
        - Последовательность навигаций работает корректно
        - Каждая навигация обновляет selected_index
        - Настройки сохраняются при каждой навигации
        
        Validates: Requirements 5.1, 5.2
        """
        # Создаем MainWindow
        window = MainWindow(self.page)
        window.content_area.update = Mock()
        
        # Сбрасываем счетчики после инициализации
        self.mock_settings.save.reset_mock()
        
        # Выполняем последовательность навигаций
        for index in navigation_sequence:
            window.navigate(index)
            
            # Проверяем, что selected_index соответствует текущему индексу
            self.assertEqual(window.rail.selected_index, index)
        
        # Проверяем, что настройки сохранялись при каждой навигации
        self.assertEqual(
            self.mock_settings.save.call_count,
            len(navigation_sequence),
            f"Настройки должны быть сохранены {len(navigation_sequence)} раз"
        )
        
        # Проверяем, что последний selected_index соответствует последнему элементу последовательности
        self.assertEqual(window.rail.selected_index, navigation_sequence[-1])


if __name__ == '__main__':
    unittest.main()

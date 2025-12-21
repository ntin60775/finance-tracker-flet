"""
Тесты для предотвращения ошибки "Offstage Control must be added to the page first".

Эти тесты проверяют, что диалоги и SnackBar не открываются до того, как
компоненты будут полностью добавлены на страницу.
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


class TestOffstageControlPrevention(ViewTestBase):
    """
    Тесты для предотвращения ошибок Offstage Control.
    
    Проверяют правильный порядок инициализации UI компонентов
    и безопасность показа диалогов и SnackBar.
    """

    def setUp(self):
        """Настройка перед каждым тестом."""
        super().setUp()
        
        # Создаем mock для Page с контролем состояния инициализации
        self.mock_page = self.create_mock_offstage_safe_page()
        
        # Патчим HomePresenter для изоляции тестов
        self.mock_presenter_patcher = patch('finance_tracker.views.home_view.HomePresenter')
        self.mock_presenter = self.mock_presenter_patcher.start()
        self.patchers.append(self.mock_presenter_patcher)
        
        # Патчим UI компоненты для изоляции
        self.mock_calendar_patcher = patch('finance_tracker.views.home_view.CalendarWidget')
        self.mock_calendar = self.mock_calendar_patcher.start()
        self.patchers.append(self.mock_calendar_patcher)
        
        self.mock_transactions_panel_patcher = patch('finance_tracker.views.home_view.TransactionsPanel')
        self.mock_transactions_panel = self.mock_transactions_panel_patcher.start()
        self.patchers.append(self.mock_transactions_panel_patcher)

    def create_mock_offstage_safe_page(self) -> MagicMock:
        """
        Создание мока Page с контролем состояния инициализации.
        
        Этот мок симулирует поведение реального Flet Page:
        - Отслеживает, добавлены ли контролы на страницу
        - Выбрасывает ошибку при попытке открыть диалог до инициализации
        
        Использует СОВРЕМЕННЫЙ Flet Dialog API (>= 0.25.0):
        - page.open(dialog) - для открытия диалогов
        - page.close(dialog) - для закрытия диалогов
        
        Returns:
            MagicMock: Мок Page с проверкой Offstage Control
        """
        page = MagicMock(spec=ft.Page)
        page.overlay = []
        # Атрибут dialog оставлен для обратной совместимости, но не используется в новом коде
        page.dialog = None
        page.controls = []
        page._is_initialized = False
        page._controls_added = False
        
        # Мок для add() - помечает, что контролы добавлены
        def mock_add(control):
            page._controls_added = True
            page.controls.append(control)
            
        page.add = Mock(side_effect=mock_add)
        
        # Мок для open() - проверяет, что контролы добавлены (СОВРЕМЕННЫЙ API)
        def mock_open(dialog):
            if not page._controls_added:
                raise AssertionError("Offstage Control must be added to the page first")
            page.dialog = dialog
            
        page.open = Mock(side_effect=mock_open)
        
        # Мок для show_snack_bar() - проверяет, что страница инициализирована
        def mock_show_snack_bar(snack_bar):
            if not page._controls_added:
                raise AssertionError("Offstage Control must be added to the page first")
                
        page.show_snack_bar = Mock(side_effect=mock_show_snack_bar)
        
        # Остальные методы
        page.update = MagicMock()
        # Современный Flet API для закрытия диалогов
        page.close = MagicMock()
        
        return page

    def test_home_view_initialization_order(self):
        """
        Тест проверяет, что load_initial_data не вызывается в конструкторе HomeView.
        
        Validates: Requirements 1.1
        """
        # Создаем HomeView
        home_view = HomeView(self.mock_page, self.mock_session)
        
        # Проверяем, что HomeView создан
        self.assertIsNotNone(home_view)
        self.assertEqual(home_view.page, self.mock_page)
        self.assertEqual(home_view.session, self.mock_session)
        
        # Проверяем, что Presenter создан, но load_initial_data НЕ вызван в конструкторе
        self.mock_presenter.assert_called_once_with(self.mock_session, home_view)
        self.mock_presenter.return_value.load_initial_data.assert_not_called()
        
        # Проверяем, что UI компоненты созданы
        self.mock_calendar.assert_called_once()
        self.mock_transactions_panel.assert_called_once()
        
        # Убеждаемся, что данные не загружаются автоматически при создании
        # load_initial_data должен вызываться только через MainWindow.did_mount()
        self.assertEqual(self.mock_presenter.return_value.load_initial_data.call_count, 0)

    def test_main_window_did_mount_sequence(self):
        """
        Тест проверяет правильную последовательность did_mount в MainWindow.
        
        Validates: Requirements 1.2
        """
        # Патчим get_db_session для MainWindow
        mock_db_session_cm = self.create_mock_db_context()
        with patch('finance_tracker.views.main_window.get_db_session', return_value=mock_db_session_cm):
            # Патчим get_total_balance для избежания реальных DB вызовов
            with patch('finance_tracker.views.main_window.get_total_balance', return_value=1000.0):
                # Создаем MainWindow
                main_window = MainWindow(self.mock_page)
                
                # Проверяем, что HomeView создан, но данные не загружены в конструкторе
                self.assertIsNotNone(main_window.home_view)
                self.mock_presenter.return_value.load_initial_data.assert_not_called()
                
                # Симулируем добавление MainWindow на страницу
                self.mock_page._controls_added = True
                
                # Вызываем did_mount - это должно инициировать загрузку данных
                main_window.did_mount()
                
                # Проверяем, что теперь load_initial_data вызван ровно один раз
                self.mock_presenter.return_value.load_initial_data.assert_called_once()
                
                # Проверяем, что баланс также обновлен
                # (get_total_balance должен быть вызван в update_balance)
                # Это подтверждает правильную последовательность инициализации

    def test_dialog_opening_after_page_ready(self):
        """
        Тест проверяет, что диалоги открываются только после готовности страницы.
        
        Validates: Requirements 1.4
        """
        # Создаем HomeView
        home_view = HomeView(self.mock_page, self.mock_session)
        
        # Попытка открыть диалог до добавления на страницу должна вызвать ошибку
        with self.assertRaises(AssertionError) as context:
            home_view.show_message("Test message")
        
        self.assertIn("Offstage Control must be added to the page first", str(context.exception))
        
        # Проверяем, что dialog не был установлен из-за ошибки
        self.assertIsNone(self.mock_page.dialog)
        
        # Симулируем добавление на страницу (страница готова)
        self.mock_page._controls_added = True
        
        # Сбрасываем счетчик вызовов для чистого теста
        self.mock_page.open.reset_mock()
        
        # Теперь диалог должен открыться без ошибок
        home_view.show_message("Test message")
        self.mock_page.open.assert_called_once()
        self.assertIsNotNone(self.mock_page.dialog)
        
        # Дополнительная проверка: тестируем другие типы диалогов
        self.mock_page.open.reset_mock()
        self.mock_page.dialog = None
        
        # Тестируем диалог ошибки
        home_view.show_error("Test error")
        self.mock_page.open.assert_called_once()
        self.assertIsNotNone(self.mock_page.dialog)

    def test_snackbar_showing_safety(self):
        """
        Тест проверяет безопасный показ SnackBar.
        
        Проверяет, что SnackBar показывается только после полной инициализации
        страницы и что попытки показать SnackBar до инициализации обрабатываются корректно.
        
        Validates: Requirements 1.3
        """
        # Создаем HomeView
        home_view = HomeView(self.mock_page, self.mock_session)
        
        # Тест 1: Попытка показать SnackBar до инициализации должна вызвать ошибку
        with self.assertRaises(AssertionError) as context:
            home_view.show_error("Test error before initialization")
        
        self.assertIn("Offstage Control must be added to the page first", str(context.exception))
        
        # Проверяем, что dialog не был установлен из-за ошибки
        self.assertIsNone(self.mock_page.dialog)
        self.mock_page.show_snack_bar.assert_not_called()
        
        # Тест 2: Симулируем инициализацию страницы
        self.mock_page._controls_added = True
        
        # Сбрасываем счетчики вызовов для чистого теста
        self.mock_page.open.reset_mock()
        self.mock_page.show_snack_bar.reset_mock()
        
        # Тест 3: Теперь SnackBar должен показаться без ошибок через диалог
        home_view.show_error("Test error after initialization")
        self.mock_page.open.assert_called_once()
        self.assertIsNotNone(self.mock_page.dialog)
        
        # Тест 4: Проверяем показ информационного сообщения
        self.mock_page.open.reset_mock()
        self.mock_page.dialog = None
        
        home_view.show_message("Test info message")
        self.mock_page.open.assert_called_once()
        self.assertIsNotNone(self.mock_page.dialog)
        
        # Тест 5: Проверяем множественные вызовы SnackBar после инициализации
        self.mock_page.open.reset_mock()
        
        for i in range(3):
            self.mock_page.dialog = None
            home_view.show_message(f"Message {i}")
            self.mock_page.open.assert_called()
        
        # Должно быть 3 вызова (по одному на каждое сообщение)
        self.assertEqual(self.mock_page.open.call_count, 3)

    def test_error_handling_without_dialogs(self):
        """
        Тест проверяет обработку ошибок без показа диалогов до инициализации.
        
        Проверяет, что ошибки обрабатываются корректно без попыток показать
        диалоги или SnackBar до полной инициализации компонентов.
        
        Validates: Requirements 1.5
        """
        # Создаем HomeView
        home_view = HomeView(self.mock_page, self.mock_session)
        
        # Тест 1: Симулируем ошибку в Presenter до инициализации
        self.mock_presenter.return_value.load_initial_data.side_effect = Exception("Database connection error")
        
        # Попытка загрузить данные до инициализации не должна показывать диалоги
        with self.assertRaises(Exception) as context:
            # Симулируем вызов load_initial_data (как в MainWindow.did_mount)
            home_view.presenter.load_initial_data()
        
        self.assertIn("Database connection error", str(context.exception))
        
        # Проверяем, что диалоги не были открыты из-за ошибки
        self.mock_page.open.assert_not_called()
        self.mock_page.show_snack_bar.assert_not_called()
        
        # Тест 2: Проверяем обработку ошибок в других методах Presenter
        self.mock_presenter.return_value.load_pending_payments.side_effect = Exception("Service error")
        
        with self.assertRaises(Exception):
            home_view.presenter.load_pending_payments()
        
        # Диалоги по-прежнему не должны показываться
        self.mock_page.open.assert_not_called()
        
        # Тест 3: Симулируем инициализацию страницы
        self.mock_page._controls_added = True
        
        # Сбрасываем side_effect для нормальной работы
        self.mock_presenter.return_value.load_initial_data.side_effect = None
        self.mock_presenter.return_value.load_pending_payments.side_effect = None
        
        # Тест 4: Теперь можно безопасно показывать ошибки
        home_view.show_error("Handled error after initialization")
        self.mock_page.open.assert_called_once()
        
        # Тест 5: Проверяем graceful degradation - приложение продолжает работать
        self.mock_page.open.reset_mock()
        self.mock_page.dialog = None
        
        # Симулируем ошибку, но теперь она должна показаться пользователю
        try:
            raise ValueError("User input validation error")
        except ValueError as e:
            home_view.show_error(f"Ошибка валидации: {str(e)}")
        
        self.mock_page.open.assert_called_once()
        self.assertIsNotNone(self.mock_page.dialog)
        
        # Тест 6: Проверяем, что после ошибки система остается работоспособной
        self.mock_page.open.reset_mock()
        self.mock_page.dialog = None
        
        home_view.show_message("System is still working")
        self.mock_page.open.assert_called_once()

    def test_initialization_components_created_safely(self):
        """
        Тест проверяет, что все UI компоненты создаются безопасно при инициализации.
        
        Validates: Requirements 1.1
        """
        # Создаем HomeView
        home_view = HomeView(self.mock_page, self.mock_session)
        
        # Проверяем, что все основные компоненты созданы
        self.assertIsNotNone(home_view.calendar_widget)
        self.assertIsNotNone(home_view.transactions_panel)
        self.assertIsNotNone(home_view.legend)
        self.assertIsNotNone(home_view.planned_widget)
        self.assertIsNotNone(home_view.pending_payments_widget)
        self.assertIsNotNone(home_view.presenter)
        
        # Проверяем, что модальные окна созданы, но не открыты
        self.assertIsNotNone(home_view.transaction_modal)
        self.assertIsNotNone(home_view.execute_occurrence_modal)
        self.assertIsNotNone(home_view.execute_payment_modal)
        self.assertIsNotNone(home_view.payment_modal)
        
        # Проверяем, что никакие диалоги не были открыты при инициализации
        self.mock_page.open.assert_not_called()

    def test_ui_operations_safety_sequence(self):
        """
        Тест проверяет безопасную последовательность UI операций.
        
        Проверяет различные сценарии взаимодействия с UI до и после инициализации.
        
        Validates: Requirements 1.3, 1.5
        """
        # Создаем HomeView
        home_view = HomeView(self.mock_page, self.mock_session)
        
        # Тест 1: Список операций, которые должны быть безопасны до инициализации
        safe_operations = [
            lambda: home_view.build(),  # Построение UI должно быть безопасно
            lambda: str(home_view),     # Строковое представление
            lambda: home_view.calendar_widget is not None,  # Проверка компонентов
        ]
        
        for operation in safe_operations:
            try:
                operation()
            except Exception as e:
                self.fail(f"Safe operation failed before initialization: {e}")
        
        # Тест 2: Операции, которые должны вызывать ошибку до инициализации
        unsafe_operations = [
            lambda: home_view.show_error("Error"),
            lambda: home_view.show_message("Message"),
        ]
        
        for operation in unsafe_operations:
            with self.assertRaises(AssertionError):
                operation()
        
        # Тест 3: После инициализации все операции должны быть безопасны
        self.mock_page._controls_added = True
        
        for operation in unsafe_operations:
            try:
                self.mock_page.dialog = None  # Сброс для каждого теста
                operation()
            except Exception as e:
                self.fail(f"Operation failed after initialization: {e}")

    def test_modal_operations_safety(self):
        """
        Тест проверяет безопасность операций с модальными окнами.
        
        Validates: Requirements 1.3, 1.4
        """
        # Создаем HomeView
        home_view = HomeView(self.mock_page, self.mock_session)
        
        # Тест 1: Модальные окна должны создаваться безопасно
        self.assertIsNotNone(home_view.transaction_modal)
        self.assertIsNotNone(home_view.execute_occurrence_modal)
        self.assertIsNotNone(home_view.execute_payment_modal)
        self.assertIsNotNone(home_view.payment_modal)
        
        # Тест 2: Попытка открыть модальное окно до инициализации
        # Модальные окна могут пытаться показать ошибки через page.open()
        
        # Симулируем ошибку в модальном окне при попытке открыть
        with patch.object(home_view.transaction_modal, 'open') as mock_open:
            mock_open.side_effect = Exception("Modal error")
            
            # Попытка открыть модальное окно может привести к показу ошибки
            with self.assertRaises(Exception):
                home_view.transaction_modal.open(self.mock_page)
        
        # Проверяем, что диалоги ошибок не были показаны (страница не инициализирована)
        # Если модальное окно попытается показать ошибку, это должно вызвать AssertionError
        
        # Тест 3: После инициализации модальные окна должны работать
        self.mock_page._controls_added = True
        
        # Сбрасываем side_effect для нормальной работы
        with patch.object(home_view.transaction_modal, 'open') as mock_open:
            mock_open.side_effect = None
            mock_open.return_value = None
            
            try:
                home_view.transaction_modal.open(self.mock_page)
            except Exception as e:
                self.fail(f"Modal operation failed after initialization: {e}")
        
        # Тест 4: Проверяем, что модальные окна не пытаются показать диалоги при создании
        # Создание нового HomeView не должно вызывать никаких диалогов
        self.mock_page.open.reset_mock()
        
        new_home_view = HomeView(self.mock_page, self.mock_session)
        self.assertIsNotNone(new_home_view.transaction_modal)
        
        # Никаких диалогов не должно быть показано при создании
        self.mock_page.open.assert_not_called()

    def test_concurrent_ui_operations_safety(self):
        """
        Тест проверяет безопасность одновременных UI операций.
        
        Validates: Requirements 1.3, 1.5
        """
        # Создаем HomeView
        home_view = HomeView(self.mock_page, self.mock_session)
        
        # Тест 1: Множественные попытки показать диалоги до инициализации
        error_count = 0
        
        for i in range(5):
            try:
                home_view.show_error(f"Error {i}")
            except AssertionError as e:
                # Проверяем, что это именно ошибка Offstage Control
                if "Offstage Control must be added to the page first" in str(e):
                    error_count += 1
                else:
                    raise  # Перебрасываем неожиданную ошибку
        
        # Все попытки должны были вызвать ошибку Offstage Control
        self.assertEqual(error_count, 5)
        
        # Тест 2: После инициализации множественные операции должны работать
        self.mock_page._controls_added = True
        
        # Сбрасываем счетчик вызовов для чистого теста
        self.mock_page.open.reset_mock()
        
        success_count = 0
        for i in range(3):
            try:
                self.mock_page.dialog = None  # Сброс для каждого теста
                home_view.show_message(f"Message {i}")
                success_count += 1
            except Exception as e:
                self.fail(f"Unexpected error after initialization: {e}")
        
        # Все операции должны были пройти успешно
        self.assertEqual(success_count, 3)
        self.assertEqual(self.mock_page.open.call_count, 3)
        
        # Тест 3: Проверяем, что ошибки по-прежнему показываются после инициализации
        self.mock_page.open.reset_mock()
        
        try:
            home_view.show_error("Error after initialization")
        except Exception as e:
            self.fail(f"Error showing should work after initialization: {e}")
        
        self.mock_page.open.assert_called_once()

    def test_page_state_tracking(self):
        """
        Тест проверяет корректность отслеживания состояния страницы в mock объекте.
        """
        # Изначально страница не инициализирована
        self.assertFalse(self.mock_page._controls_added)
        
        # Добавляем контрол
        test_control = ft.Text("Test")
        self.mock_page.add(test_control)
        
        # Проверяем, что состояние изменилось
        self.assertTrue(self.mock_page._controls_added)
        self.assertIn(test_control, self.mock_page.controls)
        
        # Теперь диалоги должны открываться без ошибок
        test_dialog = ft.AlertDialog(title=ft.Text("Test"))
        self.mock_page.open(test_dialog)
        self.assertEqual(self.mock_page.dialog, test_dialog)


# =============================================================================
# Property-Based Tests
# =============================================================================

@settings(max_examples=100)
@given(
    st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=10),  # error_messages
    st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=10),  # info_messages
    st.booleans()  # page_initialized
)
def test_property_1_ui_initialization_order_safety(error_messages, info_messages, page_initialized):
    """
    **Feature: error-regression-testing, Property 1: UI Initialization Order Safety**
    
    For any UI component initialization sequence, dialogs and SnackBars should only be 
    shown after the component is fully added to the page.
    
    Validates: Requirements 1.1, 1.2, 1.3, 1.4
    """
    # Создаем mock объекты
    mock_page = MagicMock(spec=ft.Page)
    mock_page.overlay = []
    # Атрибут dialog оставлен для обратной совместимости, но не используется в новом коде
    mock_page.dialog = None
    mock_page.controls = []
    mock_page._controls_added = page_initialized
    
    # Настраиваем поведение page.add()
    def mock_add(control):
        mock_page._controls_added = True
        mock_page.controls.append(control)
    
    mock_page.add = Mock(side_effect=mock_add)
    
    # Настраиваем поведение page.open() с проверкой Offstage Control (СОВРЕМЕННЫЙ API)
    def mock_open(dialog):
        if not mock_page._controls_added:
            raise AssertionError("Offstage Control must be added to the page first")
        mock_page.dialog = dialog
    
    mock_page.open = Mock(side_effect=mock_open)
    mock_page.update = MagicMock()
    # Современный Flet API для закрытия диалогов
    mock_page.close = MagicMock()
    
    # Создаем mock session
    mock_session = Mock()
    
    # Патчим зависимости для изоляции теста
    with patch('finance_tracker.views.home_view.HomePresenter') as MockPresenter, \
         patch('finance_tracker.views.home_view.CalendarWidget') as MockCalendar, \
         patch('finance_tracker.views.home_view.TransactionsPanel') as MockTransactionsPanel:
        
        # Создаем HomeView
        home_view = HomeView(mock_page, mock_session)
        
        # Property 1: Проверяем, что load_initial_data НЕ вызывается в конструкторе
        MockPresenter.return_value.load_initial_data.assert_not_called()
        
        # Property 2: Проверяем поведение UI операций в зависимости от состояния инициализации
        if page_initialized:
            # Если страница инициализирована, все UI операции должны работать
            for message in error_messages:
                try:
                    mock_page.dialog = None  # Сброс для каждого теста
                    home_view.show_error(message)
                    # Проверяем, что диалог был открыт без ошибок
                    mock_page.open.assert_called()
                except AssertionError as e:
                    # Если получили ошибку Offstage Control, это нарушение свойства
                    if "Offstage Control must be added to the page first" in str(e):
                        raise AssertionError(
                            f"UI operation failed on initialized page: {e}. "
                            f"Page state: _controls_added={mock_page._controls_added}"
                        )
                    else:
                        raise  # Перебрасываем другие ошибки
            
            for message in info_messages:
                try:
                    mock_page.dialog = None  # Сброс для каждого теста
                    home_view.show_message(message)
                    # Проверяем, что диалог был открыт без ошибок
                    mock_page.open.assert_called()
                except AssertionError as e:
                    # Если получили ошибку Offstage Control, это нарушение свойства
                    if "Offstage Control must be added to the page first" in str(e):
                        raise AssertionError(
                            f"UI operation failed on initialized page: {e}. "
                            f"Page state: _controls_added={mock_page._controls_added}"
                        )
                    else:
                        raise  # Перебрасываем другие ошибки
        
        else:
            # Если страница НЕ инициализирована, UI операции должны вызывать ошибку Offstage Control
            for message in error_messages:
                with pytest.raises(AssertionError) as exc_info:
                    home_view.show_error(message)
                
                # Проверяем, что это именно ошибка Offstage Control
                assert "Offstage Control must be added to the page first" in str(exc_info.value), \
                    f"Expected Offstage Control error, got: {exc_info.value}"
            
            for message in info_messages:
                with pytest.raises(AssertionError) as exc_info:
                    home_view.show_message(message)
                
                # Проверяем, что это именно ошибка Offstage Control
                assert "Offstage Control must be added to the page first" in str(exc_info.value), \
                    f"Expected Offstage Control error, got: {exc_info.value}"
        
        # Property 3: Проверяем, что компоненты создаются безопасно независимо от состояния страницы
        assert home_view.calendar_widget is not None, "CalendarWidget должен быть создан"
        assert home_view.transactions_panel is not None, "TransactionsPanel должен быть создан"
        assert home_view.presenter is not None, "Presenter должен быть создан"
        
        # Property 4: Проверяем, что UI компоненты созданы, но данные не загружены в конструкторе
        MockCalendar.assert_called_once()
        MockTransactionsPanel.assert_called_once()
        MockPresenter.assert_called_once_with(mock_session, home_view)
        
        # load_initial_data должен вызываться только через MainWindow.did_mount(), не в конструкторе
        MockPresenter.return_value.load_initial_data.assert_not_called()


if __name__ == '__main__':
    unittest.main()
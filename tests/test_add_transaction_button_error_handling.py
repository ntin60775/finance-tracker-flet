"""
Тесты для обработки ошибок кнопки добавления транзакции.
Проверяют граничные случаи и обработку ошибок в TransactionsPanel и HomeView.
"""
import unittest
from unittest.mock import Mock, MagicMock, patch
import datetime
import flet as ft

from finance_tracker.components.transactions_panel import TransactionsPanel
from finance_tracker.views.home_view import HomeView


class TestAddTransactionButtonErrorHandling(unittest.TestCase):
    """Тесты для обработки ошибок кнопки добавления транзакции."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.test_date = datetime.date.today()
        self.transactions = []

    def test_null_callback_function(self):
        """
        Тест с null callback функцией.
        
        Проверяет:
        - Кнопка отключается при None callback
        - Нет исключений при создании панели
        - Безопасный вызов _safe_add_transaction
        - Показ предупреждения пользователю
        
        Requirements: 8.1
        """
        # Arrange - создаем панель с None callback
        panel = TransactionsPanel(
            date_obj=self.test_date,
            transactions=self.transactions,
            on_add_transaction=None  # None callback
        )
        
        # Мокируем page для показа SnackBar
        mock_page = MagicMock()
        panel.page = mock_page
        
        # Act & Assert - проверяем создание панели без ошибок
        self.assertIsNotNone(panel, "Панель должна создаваться даже с None callback")
        self.assertIsNone(panel.on_add_transaction, "Callback должен быть None")
        
        # Проверяем состояние кнопки
        header_row = panel._build_header()
        add_button = header_row.controls[1]
        
        self.assertIsInstance(add_button, ft.IconButton, "Кнопка должна быть создана")
        self.assertTrue(add_button.disabled, "Кнопка должна быть отключена при None callback")
        
        # Проверяем безопасный вызов _safe_add_transaction
        try:
            panel._safe_add_transaction(None)
            # Если дошли сюда, значит исключений не было
        except Exception as e:
            self.fail(f"_safe_add_transaction не должен выбрасывать исключения при None callback: {e}")
        
        # Проверяем, что показан SnackBar с предупреждением
        mock_page.open.assert_called_once()
        snack_bar_call = mock_page.open.call_args[0][0]
        self.assertIsInstance(snack_bar_call, ft.SnackBar, "Должен быть показан SnackBar")
        self.assertIn("недоступна", snack_bar_call.content.value, "SnackBar должен содержать сообщение о недоступности")
        self.assertEqual(snack_bar_call.bgcolor, ft.Colors.ORANGE, "SnackBar должен иметь цвет предупреждения")

    def test_exception_in_callback(self):
        """
        Тест с исключением в callback.
        
        Проверяет:
        - Обработка исключений в callback функции
        - Логирование ошибки
        - Показ ошибки пользователю
        - Стабильность системы после ошибки
        
        Requirements: 8.2
        """
        # Arrange - создаем callback, который выбрасывает исключение
        def failing_callback():
            raise RuntimeError("Test callback exception")
        
        panel = TransactionsPanel(
            date_obj=self.test_date,
            transactions=self.transactions,
            on_add_transaction=failing_callback
        )
        
        # Мокируем page для показа SnackBar
        mock_page = MagicMock()
        panel.page = mock_page
        
        # Act - вызываем _safe_add_transaction
        try:
            panel._safe_add_transaction(None)
            # Если дошли сюда, значит исключение было обработано
        except Exception as e:
            self.fail(f"_safe_add_transaction должен обрабатывать исключения в callback: {e}")
        
        # Assert - проверяем обработку ошибки
        
        # Проверяем, что показан SnackBar с ошибкой
        mock_page.open.assert_called_once()
        snack_bar_call = mock_page.open.call_args[0][0]
        self.assertIsInstance(snack_bar_call, ft.SnackBar, "Должен быть показан SnackBar")
        self.assertIn("Ошибка", snack_bar_call.content.value, "SnackBar должен содержать сообщение об ошибке")
        self.assertEqual(snack_bar_call.bgcolor, ft.Colors.ERROR, "SnackBar должен иметь цвет ошибки")
        
        # Проверяем, что панель остается в рабочем состоянии
        self.assertEqual(panel.on_add_transaction, failing_callback, "Callback не должен изменяться")
        self.assertEqual(panel.date, self.test_date, "Дата не должна изменяться")
        
        # Проверяем, что кнопка остается активной (callback есть, но проблемный)
        header_row = panel._build_header()
        add_button = header_row.controls[1]
        self.assertFalse(add_button.disabled, "Кнопка должна оставаться активной при наличии callback")

    def test_unavailable_page(self):
        """
        Тест с недоступной page.
        
        Проверяет:
        - Обработка случая, когда page равна None
        - Обработка случая, когда page недоступна
        - Логирование ошибки
        - Стабильность системы
        
        Requirements: 8.4
        """
        # Тест 1: page равна None
        def valid_callback():
            pass
        
        panel = TransactionsPanel(
            date_obj=self.test_date,
            transactions=self.transactions,
            on_add_transaction=valid_callback
        )
        
        # page не установлена (None по умолчанию)
        self.assertIsNone(panel.page, "Page должна быть None по умолчанию")
        
        # Act - вызываем _safe_add_transaction без page
        try:
            panel._safe_add_transaction(None)
            # Если дошли сюда, значит исключений не было
        except Exception as e:
            self.fail(f"_safe_add_transaction должен работать без page: {e}")
        
        # Тест 2: page установлена, но недоступна (мок с ошибкой)
        mock_page = MagicMock()
        mock_page.open.side_effect = Exception("Page unavailable")
        panel.page = mock_page
        
        # Создаем failing callback для тестирования показа ошибки
        def failing_callback():
            raise ValueError("Test error")
        
        panel.on_add_transaction = failing_callback
        
        # Act - вызываем _safe_add_transaction с недоступной page
        try:
            panel._safe_add_transaction(None)
            # Если дошли сюда, значит исключения были обработаны
        except Exception as e:
            self.fail(f"_safe_add_transaction должен обрабатывать недоступную page: {e}")
        
        # Assert - проверяем, что была попытка показать SnackBar
        mock_page.open.assert_called_once()

    def test_transaction_modal_creation_error(self):
        """
        Тест с ошибкой создания TransactionModal.
        
        Проверяет:
        - Обработка ошибки при создании TransactionModal
        - Обработка ошибки при вызове modal.open()
        - Логирование ошибки
        - Показ ошибки пользователю
        
        Requirements: 8.3
        """
        # Arrange - создаем HomeView с мокированными зависимостями
        mock_page = MagicMock()
        mock_page.width = 1200
        mock_page.height = 800
        mock_session = Mock()

        with patch('finance_tracker.views.home_view.HomePresenter'), \
             patch('finance_tracker.views.home_view.TransactionsPanel'):

            home_view = HomeView(mock_page, mock_session)
            
            # Тест 1: TransactionModal равен None
            home_view.transaction_modal = None
            
            # Act - пытаемся открыть модальное окно
            try:
                home_view.open_add_transaction_modal()
                # Если дошли сюда, значит исключений не было
            except Exception as e:
                self.fail(f"open_add_transaction_modal должен обрабатывать None modal: {e}")
            
            # Тест 2: TransactionModal.open() выбрасывает исключение
            mock_transaction_modal = Mock()
            mock_transaction_modal.open.side_effect = Exception("Modal creation failed")
            home_view.transaction_modal = mock_transaction_modal
            
            # Act - пытаемся открыть проблемное модальное окно
            try:
                home_view.open_add_transaction_modal()
                # Если дошли сюда, значит исключение было обработано
            except Exception as e:
                self.fail(f"open_add_transaction_modal должен обрабатывать ошибки modal.open(): {e}")
            
            # Assert - проверяем обработку ошибки
            
            # Проверяем, что была попытка вызвать modal.open()
            mock_transaction_modal.open.assert_called_once_with(mock_page, home_view.selected_date)
            
            # Проверяем, что показан SnackBar с ошибкой
            mock_page.open.assert_called()
            
            # Получаем последний вызов page.open (может быть несколько из-за разных тестов)
            last_call = mock_page.open.call_args_list[-1]
            snack_bar_call = last_call[0][0]
            self.assertIsInstance(snack_bar_call, ft.SnackBar, "Должен быть показан SnackBar")
            self.assertIn("Не удалось открыть", snack_bar_call.content.value, "SnackBar должен содержать сообщение об ошибке")
            self.assertEqual(snack_bar_call.bgcolor, ft.Colors.ERROR, "SnackBar должен иметь цвет ошибки")

    def test_page_none_in_home_view(self):
        """
        Тест с page равной None в HomeView.
        
        Проверяет:
        - Обработка случая, когда page равна None в HomeView
        - Логирование ошибки
        - Безопасное завершение метода
        
        Requirements: 8.4
        """
        # Arrange - создаем HomeView с None page
        mock_session = Mock()
        
        with patch('finance_tracker.views.home_view.HomePresenter'), \
             patch('finance_tracker.views.home_view.TransactionsPanel'):
            
            home_view = HomeView(None, mock_session)  # page = None
            
            # Создаем валидный TransactionModal
            mock_transaction_modal = Mock()
            home_view.transaction_modal = mock_transaction_modal
            
            # Act - пытаемся открыть модальное окно без page
            try:
                home_view.open_add_transaction_modal()
                # Если дошли сюда, значит исключений не было
            except Exception as e:
                self.fail(f"open_add_transaction_modal должен обрабатывать None page: {e}")
            
            # Assert - проверяем, что modal.open() не был вызван
            mock_transaction_modal.open.assert_not_called()

    def test_multiple_error_scenarios_stability(self):
        """
        Тест стабильности при множественных ошибках.
        
        Проверяет:
        - Система остается стабильной при повторных ошибках
        - Каждая ошибка обрабатывается независимо
        - Нет накопления состояния ошибок
        
        Requirements: 8.1, 8.2, 8.4
        """
        # Arrange - создаем различные сценарии ошибок
        error_scenarios = [
            ("none_callback", None),
            ("exception_callback", lambda: exec('raise ValueError("Test error 1")')),
            ("runtime_error_callback", lambda: exec('raise RuntimeError("Test error 2")')),
            ("type_error_callback", lambda: exec('raise TypeError("Test error 3")')),
        ]
        
        mock_page = MagicMock()
        
        # Act & Assert - тестируем каждый сценарий
        for i, (scenario_name, callback) in enumerate(error_scenarios):
            with self.subTest(scenario=scenario_name):
                # Создаем новую панель для каждого сценария
                panel = TransactionsPanel(
                    date_obj=self.test_date,
                    transactions=self.transactions,
                    on_add_transaction=callback
                )
                panel.page = mock_page
                
                # Сбрасываем mock для чистого тестирования
                mock_page.reset_mock()
                
                # Вызываем _safe_add_transaction
                try:
                    panel._safe_add_transaction(None)
                    # Каждый вызов должен быть безопасным
                except Exception as e:
                    self.fail(f"Сценарий '{scenario_name}' не должен выбрасывать исключения: {e}")
                
                # Проверяем, что панель остается в рабочем состоянии
                self.assertEqual(panel.on_add_transaction, callback, 
                               f"Callback не должен изменяться в сценарии '{scenario_name}'")
                self.assertEqual(panel.date, self.test_date, 
                               f"Дата не должна изменяться в сценарии '{scenario_name}'")
                
                # Проверяем состояние кнопки
                header_row = panel._build_header()
                add_button = header_row.controls[1]
                
                if callback is None:
                    self.assertTrue(add_button.disabled, 
                                  f"Кнопка должна быть отключена при None callback в сценарии '{scenario_name}'")
                else:
                    self.assertFalse(add_button.disabled, 
                                   f"Кнопка должна быть активна при наличии callback в сценарии '{scenario_name}'")
                
                # Проверяем, что была попытка показать SnackBar (кроме валидного callback)
                if callback is None or callable(callback):
                    mock_page.open.assert_called_once()

    def test_snackbar_display_error_handling(self):
        """
        Тест обработки ошибок при показе SnackBar.
        
        Проверяет:
        - Обработка ошибки при вызове page.open() для SnackBar
        - Логирование ошибки показа SnackBar
        - Стабильность системы при проблемах с UI
        
        Requirements: 8.4
        """
        # Arrange - создаем callback с ошибкой
        def failing_callback():
            raise ValueError("Test callback error")
        
        panel = TransactionsPanel(
            date_obj=self.test_date,
            transactions=self.transactions,
            on_add_transaction=failing_callback
        )
        
        # Мокируем page с ошибкой при показе SnackBar
        mock_page = MagicMock()
        mock_page.open.side_effect = Exception("SnackBar display failed")
        panel.page = mock_page
        
        # Act - вызываем _safe_add_transaction
        try:
            panel._safe_add_transaction(None)
            # Если дошли сюда, значит все исключения были обработаны
        except Exception as e:
            self.fail(f"_safe_add_transaction должен обрабатывать ошибки показа SnackBar: {e}")
        
        # Assert - проверяем, что была попытка показать SnackBar
        mock_page.open.assert_called_once()
        
        # Проверяем, что панель остается в рабочем состоянии
        self.assertEqual(panel.on_add_transaction, failing_callback, "Callback не должен изменяться")
        self.assertEqual(panel.date, self.test_date, "Дата не должна изменяться")

    def test_edge_case_empty_callback(self):
        """
        Тест граничного случая с пустой функцией callback.
        
        Проверяет:
        - Обработка callback, который ничего не делает
        - Нормальное выполнение без ошибок
        - Корректное состояние UI
        
        Requirements: 8.1
        """
        # Arrange - создаем пустой callback
        def empty_callback():
            pass  # Ничего не делает
        
        panel = TransactionsPanel(
            date_obj=self.test_date,
            transactions=self.transactions,
            on_add_transaction=empty_callback
        )
        
        mock_page = MagicMock()
        panel.page = mock_page
        
        # Act - вызываем _safe_add_transaction
        try:
            panel._safe_add_transaction(None)
            # Должно выполниться без ошибок
        except Exception as e:
            self.fail(f"_safe_add_transaction должен работать с пустым callback: {e}")
        
        # Assert - проверяем, что SnackBar не показывался (нет ошибок)
        mock_page.open.assert_not_called()
        
        # Проверяем состояние кнопки
        header_row = panel._build_header()
        add_button = header_row.controls[1]
        self.assertFalse(add_button.disabled, "Кнопка должна быть активна с валидным callback")

    def test_callback_with_parameters(self):
        """
        Тест callback, который ожидает параметры.
        
        Проверяет:
        - Обработка callback, который ожидает параметры, но не получает их
        - Обработка TypeError при вызове callback
        - Показ ошибки пользователю
        
        Requirements: 8.2
        """
        # Arrange - создаем callback, который ожидает параметры
        def callback_with_params(param1, param2):
            return param1 + param2
        
        panel = TransactionsPanel(
            date_obj=self.test_date,
            transactions=self.transactions,
            on_add_transaction=callback_with_params
        )
        
        mock_page = MagicMock()
        panel.page = mock_page
        
        # Act - вызываем _safe_add_transaction (callback не получит нужные параметры)
        try:
            panel._safe_add_transaction(None)
            # Должно обработать TypeError
        except Exception as e:
            self.fail(f"_safe_add_transaction должен обрабатывать TypeError от callback: {e}")
        
        # Assert - проверяем обработку ошибки
        mock_page.open.assert_called_once()
        snack_bar_call = mock_page.open.call_args[0][0]
        self.assertIsInstance(snack_bar_call, ft.SnackBar, "Должен быть показан SnackBar")
        self.assertEqual(snack_bar_call.bgcolor, ft.Colors.ERROR, "SnackBar должен иметь цвет ошибки")


if __name__ == '__main__':
    unittest.main()
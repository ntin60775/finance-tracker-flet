"""
Unit тесты для ModalManager календарной легенды.

Проверяет базовую функциональность создания и управления модальным окном.
"""
import unittest
import unittest.mock
from unittest.mock import MagicMock

import flet as ft

from finance_tracker.components.modal_manager import ModalManager
from finance_tracker.components.calendar_legend_types import (
    IndicatorType,
    INDICATOR_CONFIGS
)


class TestModalManagerUnit(unittest.TestCase):
    """Unit тесты для ModalManager."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_legend_component = MagicMock()
        self.modal_manager = ModalManager(self.mock_legend_component)
        self.mock_page = MagicMock(spec=ft.Page)
        # Явно настраиваем методы для современного Flet Dialog API (>= 0.25.0)
        self.mock_page.open = MagicMock()
        self.mock_page.close = MagicMock()
        self.sample_indicators = [
            INDICATOR_CONFIGS[IndicatorType.INCOME_DOT],
            INDICATOR_CONFIGS[IndicatorType.EXPENSE_DOT],
            INDICATOR_CONFIGS[IndicatorType.PLANNED_SYMBOL]
        ]

    def test_modal_manager_initialization(self):
        """Тест инициализации ModalManager с PageAccessManager."""
        self.assertIsNone(self.modal_manager.dialog)
        self.assertIsNotNone(self.modal_manager.page_manager)
        self.assertEqual(self.modal_manager.page_manager.legend, self.mock_legend_component)

    def test_create_modal_basic(self):
        """Тест создания базового модального окна."""
        dialog = self.modal_manager.create_modal(self.sample_indicators)
        
        self.assertIsNotNone(dialog)
        self.assertIsInstance(dialog, ft.AlertDialog)
        self.assertEqual(dialog.title.value, "Легенда календаря")
        self.assertTrue(dialog.modal)
        self.assertEqual(len(dialog.actions), 1)
        self.assertEqual(dialog.actions[0].text, "Закрыть")

    def test_open_modal_success(self):
        """Тест успешного открытия модального окна через современный Flet API."""
        self.modal_manager.create_modal(self.sample_indicators)
        
        result = self.modal_manager.open_modal(page=self.mock_page)
        
        self.assertTrue(result)
        # Проверяем вызов page.open() (современный Flet API)
        self.mock_page.open.assert_called_once_with(self.modal_manager.dialog)

    def test_open_modal_no_page(self):
        """Тест открытия модального окна без page объекта."""
        self.modal_manager.create_modal(self.sample_indicators)
        
        # Мокируем PageAccessManager, чтобы он возвращал None
        with unittest.mock.patch.object(
            self.modal_manager.page_manager, 
            'get_page', 
            return_value=None
        ):
            result = self.modal_manager.open_modal(page=None)
            
            self.assertFalse(result)

    def test_close_modal_success(self):
        """Тест успешного закрытия модального окна через современный Flet API."""
        self.modal_manager.create_modal(self.sample_indicators)
        self.modal_manager.open_modal(page=self.mock_page)
        
        result = self.modal_manager.close_modal(page=self.mock_page)
        
        self.assertTrue(result)
        # Проверяем вызов page.close() (современный Flet API)
        self.mock_page.close.assert_called_once_with(self.modal_manager.dialog)

    def test_close_modal_no_page(self):
        """Тест закрытия модального окна без page объекта."""
        self.modal_manager.create_modal(self.sample_indicators)
        
        # Мокируем PageAccessManager, чтобы он возвращал None
        with unittest.mock.patch.object(
            self.modal_manager.page_manager, 
            'get_page', 
            return_value=None
        ):
            result = self.modal_manager.close_modal(page=None)
            
            self.assertFalse(result)

    def test_indicator_grouping(self):
        """Тест группировки индикаторов по типам."""
        all_indicators = list(INDICATOR_CONFIGS.values())
        
        groups = self.modal_manager._group_indicators_by_type(all_indicators)
        
        self.assertIn('dots', groups)
        self.assertIn('symbols', groups)
        self.assertIn('backgrounds', groups)
        
        # Проверяем, что все индикаторы распределены
        total_grouped = len(groups['dots']) + len(groups['symbols']) + len(groups['backgrounds'])
        self.assertEqual(total_grouped, len(all_indicators))
        
        # Проверяем корректность группировки
        self.assertEqual(len(groups['dots']), 2)  # INCOME_DOT, EXPENSE_DOT
        self.assertEqual(len(groups['symbols']), 3)  # PLANNED_SYMBOL, PENDING_SYMBOL, LOAN_SYMBOL
        self.assertEqual(len(groups['backgrounds']), 2)  # CASH_GAP_BG, OVERDUE_BG
    
    def test_fallback_notification(self):
        """Тест показа fallback уведомления."""
        # Настраиваем кэшированный page
        mock_page = MagicMock(spec=ft.Page)
        # Явно настраиваем методы для современного Flet Dialog API (>= 0.25.0)
        mock_page.open = MagicMock()
        mock_page.close = MagicMock()
        self.modal_manager.page_manager.cached_page = mock_page
        
        # Вызываем fallback уведомление
        self.modal_manager._show_fallback_notification()
        
        # Проверяем, что была попытка создать snack bar
        # (детальная проверка зависит от реализации, но не должно быть исключений)
    
    def test_alternative_close(self):
        """Тест альтернативного закрытия модального окна через современный Flet API."""
        self.modal_manager.create_modal(self.sample_indicators)
        
        # Настраиваем кэшированный page
        mock_page = MagicMock(spec=ft.Page)
        # Явно настраиваем методы для современного Flet Dialog API (>= 0.25.0)
        mock_page.open = MagicMock()
        mock_page.close = MagicMock()
        self.modal_manager.page_manager.cached_page = mock_page
        
        # Вызываем альтернативное закрытие
        self.modal_manager._try_alternative_close()
        
        # Проверяем вызов page.close() (современный Flet API)
        mock_page.close.assert_called_once_with(self.modal_manager.dialog)
    
    def test_close_modal_handler_with_page_access_manager(self):
        """Тест обработчика закрытия с использованием PageAccessManager."""
        self.modal_manager.create_modal(self.sample_indicators)
        
        # Создаём mock события с page
        mock_event = MagicMock()
        mock_event.control.page = self.mock_page
        
        # Вызываем обработчик
        self.modal_manager._close_modal_handler(mock_event)
        
        # Проверяем, что модальное окно было закрыто
        # (детальная проверка зависит от реализации PageAccessManager)
    
    def test_open_modal_with_event_or_control(self):
        """Тест открытия модального окна через event_or_control параметр с современным Flet API."""
        self.modal_manager.create_modal(self.sample_indicators)
        
        # Создаём mock события с page
        mock_event = MagicMock()
        mock_event.control.page = self.mock_page
        
        # Мокируем PageAccessManager для возврата page
        with unittest.mock.patch.object(
            self.modal_manager.page_manager, 
            'get_page', 
            return_value=self.mock_page
        ):
            result = self.modal_manager.open_modal(event_or_control=mock_event)
            
            self.assertTrue(result)
            # Проверяем вызов page.open() (современный Flet API)
            self.mock_page.open.assert_called_with(self.modal_manager.dialog)


if __name__ == '__main__':
    unittest.main()
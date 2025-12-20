"""
Unit тесты для ModalManager календарной легенды.

Проверяет базовую функциональность создания и управления модальным окном.
"""
import unittest
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
        self.modal_manager = ModalManager()
        self.mock_page = MagicMock(spec=ft.Page)
        self.sample_indicators = [
            INDICATOR_CONFIGS[IndicatorType.INCOME_DOT],
            INDICATOR_CONFIGS[IndicatorType.EXPENSE_DOT],
            INDICATOR_CONFIGS[IndicatorType.PLANNED_SYMBOL]
        ]

    def test_modal_manager_initialization(self):
        """Тест инициализации ModalManager."""
        self.assertIsNone(self.modal_manager.dialog)

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
        """Тест успешного открытия модального окна."""
        self.modal_manager.create_modal(self.sample_indicators)
        
        result = self.modal_manager.open_modal(self.mock_page)
        
        self.assertTrue(result)
        self.assertEqual(self.mock_page.dialog, self.modal_manager.dialog)
        self.assertTrue(self.modal_manager.dialog.open)
        self.mock_page.update.assert_called_once()

    def test_open_modal_no_page(self):
        """Тест открытия модального окна без page объекта."""
        self.modal_manager.create_modal(self.sample_indicators)
        
        result = self.modal_manager.open_modal(None)
        
        self.assertFalse(result)

    def test_close_modal_success(self):
        """Тест успешного закрытия модального окна."""
        self.modal_manager.create_modal(self.sample_indicators)
        self.modal_manager.open_modal(self.mock_page)
        
        result = self.modal_manager.close_modal(self.mock_page)
        
        self.assertTrue(result)
        self.assertFalse(self.modal_manager.dialog.open)
        self.assertEqual(self.mock_page.update.call_count, 2)  # Открытие + закрытие

    def test_close_modal_no_page(self):
        """Тест закрытия модального окна без page объекта."""
        self.modal_manager.create_modal(self.sample_indicators)
        
        result = self.modal_manager.close_modal(None)
        
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


if __name__ == '__main__':
    unittest.main()
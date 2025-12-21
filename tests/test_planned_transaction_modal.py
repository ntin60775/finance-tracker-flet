"""
Тесты для модального окна PlannedTransactionModal.
"""
import unittest
from unittest.mock import Mock, MagicMock, patch
import flet as ft
import datetime
import uuid

from finance_tracker.components.planned_transaction_modal import PlannedTransactionModal
from finance_tracker.models import (
    TransactionType,
    CategoryDB,
    PlannedTransactionCreate,
    RecurrenceType,
    EndConditionType
)


class TestPlannedTransactionModal(unittest.TestCase):
    """Тесты для PlannedTransactionModal."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.patcher = patch('finance_tracker.components.planned_transaction_modal.get_all_categories')
        self.mock_get_all_categories = self.patcher.start()

        self.session = Mock()
        self.on_save = Mock()

        # Generate UUIDs
        self.cat_id_1 = str(uuid.uuid4())
        self.cat_id_2 = str(uuid.uuid4())

        # Мокируем загрузку категорий
        self.expense_categories = [CategoryDB(id=self.cat_id_1, name="Rent", type=TransactionType.EXPENSE, is_system=False, created_at=datetime.datetime.now())]
        self.income_categories = [CategoryDB(id=self.cat_id_2, name="Freelance", type=TransactionType.INCOME, is_system=False, created_at=datetime.datetime.now())]
        self.mock_get_all_categories.side_effect = lambda session, t_type: (
            self.expense_categories if t_type == TransactionType.EXPENSE else self.income_categories
        )

        self.modal = PlannedTransactionModal(
            session=self.session,
            on_save=self.on_save
        )
        self.page = MagicMock()
        self.page.overlay = []
        # Добавляем методы для современного Flet API
        self.page.open = Mock()
        self.page.close = Mock()
        self.modal.page = self.page

    def tearDown(self):
        self.patcher.stop()

    def test_initialization(self):
        """Тест инициализации PlannedTransactionModal."""
        self.assertIsInstance(self.modal.dialog, ft.AlertDialog)
        self.assertEqual(self.modal.dialog.title.value, "Новая плановая транзакция")
        self.assertFalse(self.modal.dialog.open)

    def test_open_modal_defaults(self):
        """Тест открытия модального окна и его значений по умолчанию."""
        self.modal.open(self.page)

        # Проверяем вызов page.open() с диалогом
        self.page.open.assert_called_once_with(self.modal.dialog)
        self.assertEqual(self.modal.type_segment.selected, {TransactionType.EXPENSE.value})
        self.assertEqual(self.modal.recurrence_type_dropdown.value, RecurrenceType.NONE.value)
        self.assertFalse(self.modal.end_condition_dropdown.visible)
        self.mock_get_all_categories.assert_called_with(self.session, TransactionType.EXPENSE)
        self.assertEqual(len(self.modal.category_dropdown.options), 1)

    def test_ui_visibility_for_periodic(self):
        """Тест видимости UI элементов для периодической транзакции."""
        self.modal.open(self.page)
        
        # Переключаемся на еженедельное повторение
        self.modal.recurrence_type_dropdown.value = RecurrenceType.WEEKLY.value
        self.modal._on_recurrence_type_change(None)

        self.assertTrue(self.modal.end_condition_dropdown.visible)
        self.assertFalse(self.modal.interval_field.visible) # Not custom
        self.assertFalse(self.modal.end_date_button.visible) # Default is NEVER
        
        # Переключаемся на "До даты"
        self.modal.end_condition_dropdown.value = EndConditionType.UNTIL_DATE.value
        self.modal._on_end_condition_change(None)
        self.assertTrue(self.modal.end_date_button.visible)
        self.assertFalse(self.modal.occurrences_count_field.visible)

    def test_save_simple_planned_transaction(self):
        """Тест сохранения простой однократной плановой транзакции."""
        self.modal.open(self.page)

        self.modal.amount_field.value = "500"
        self.modal.category_dropdown.value = self.cat_id_1
        self.modal.description_field.value = "One-time payment"

        self.modal._save(None)

        self.on_save.assert_called_once()
        called_arg = self.on_save.call_args[0][0]
        
        self.assertIsInstance(called_arg, PlannedTransactionCreate)
        self.assertEqual(called_arg.amount, 500)
        self.assertEqual(called_arg.category_id, self.cat_id_1)
        self.assertIsNone(called_arg.recurrence_rule)
        # Проверяем вызов page.close() с диалогом
        self.page.close.assert_called_once_with(self.modal.dialog)
        
    def test_save_periodic_transaction(self):
        """Тест сохранения периодической транзакции."""
        self.modal.open(self.page)

        # Заполняем основные поля
        self.modal.amount_field.value = "250"
        self.modal.category_dropdown.value = self.cat_id_1
        
        # Настраиваем повторение
        self.modal.recurrence_type_dropdown.value = RecurrenceType.MONTHLY.value
        self.modal.end_condition_dropdown.value = EndConditionType.AFTER_COUNT.value
        self.modal.occurrences_count_field.value = "12"

        self.modal._save(None)
        
        self.on_save.assert_called_once()
        called_arg = self.on_save.call_args[0][0]

        self.assertIsNotNone(called_arg.recurrence_rule)
        self.assertEqual(called_arg.recurrence_rule.recurrence_type, RecurrenceType.MONTHLY)
        self.assertEqual(called_arg.recurrence_rule.end_condition_type, EndConditionType.AFTER_COUNT)
        self.assertEqual(called_arg.recurrence_rule.occurrences_count, 12)

    def test_validation_fail_bad_interval(self):
        """Тест ошибки валидации при некорректном интервале."""
        self.modal.open(self.page)
        
        # Заполняем основные поля
        self.modal.amount_field.value = "100"
        self.modal.category_dropdown.value = self.cat_id_1
        
        # Некорректный интервал
        self.modal.recurrence_type_dropdown.value = RecurrenceType.CUSTOM.value
        self.modal.interval_field.value = "-5"

        self.modal._save(None)

        self.assertEqual(self.modal.interval_field.error_text, "Интервал должен быть больше 0")
        self.on_save.assert_not_called()
        # При ошибке валидации диалог не закрывается, поэтому page.close не должен быть вызван
        self.page.close.assert_not_called()


if __name__ == '__main__':
    unittest.main()

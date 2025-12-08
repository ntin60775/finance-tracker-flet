"""
Тесты для модального окна TransactionModal.
"""
import unittest
from unittest.mock import Mock, MagicMock, patch
import flet as ft
import datetime
from decimal import Decimal

from finance_tracker.components.transaction_modal import TransactionModal
from finance_tracker.models import TransactionType, CategoryDB, TransactionCreate


class TestTransactionModal(unittest.TestCase):
    """Тесты для TransactionModal."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.patcher = patch('finance_tracker.components.transaction_modal.get_all_categories')
        self.mock_get_all_categories = self.patcher.start()

        self.session = Mock()
        self.on_save = Mock()

        # Мокируем загрузку категорий
        self.expense_categories = [CategoryDB(id=1, name="Food", type=TransactionType.EXPENSE, is_system=False, created_at=datetime.datetime.now())]
        self.income_categories = [CategoryDB(id=2, name="Salary", type=TransactionType.INCOME, is_system=False, created_at=datetime.datetime.now())]
        self.mock_get_all_categories.side_effect = lambda session, t_type: (
            self.expense_categories if t_type == TransactionType.EXPENSE else self.income_categories
        )

        self.modal = TransactionModal(
            session=self.session,
            on_save=self.on_save
        )
        self.page = MagicMock()
        self.page.overlay = []
        self.modal.page = self.page

    def tearDown(self):
        self.patcher.stop()

    def test_initialization(self):
        """Тест инициализации TransactionModal."""
        self.assertIsInstance(self.modal.dialog, ft.AlertDialog)
        self.assertEqual(self.modal.dialog.title.value, "Новая транзакция")
        self.assertFalse(self.modal.dialog.open)

    def test_open_modal(self):
        """Тест открытия модального окна."""
        self.modal.open(self.page)

        self.assertTrue(self.modal.dialog.open)
        self.assertEqual(self.modal.type_segment.selected, {TransactionType.EXPENSE.value})
        self.mock_get_all_categories.assert_called_with(self.session, TransactionType.EXPENSE)
        self.assertEqual(len(self.modal.category_dropdown.options), 1)
        self.assertEqual(self.modal.category_dropdown.options[0].text, "Food")
        self.page.update.assert_called()

    def test_switch_to_income(self):
        """Тест переключения на тип 'Доход'."""
        self.modal.open(self.page)

        # Имитируем нажатие на сегмент "Доход"
        self.modal.type_segment.selected = {TransactionType.INCOME.value}
        self.modal._on_type_change(None)

        self.mock_get_all_categories.assert_called_with(self.session, TransactionType.INCOME)
        self.assertEqual(len(self.modal.category_dropdown.options), 1)
        self.assertEqual(self.modal.category_dropdown.options[0].text, "Salary")

    def test_save_success(self):
        """Тест успешного сохранения транзакции."""
        self.modal.open(self.page)

        self.modal.amount_field.value = "123.45"
        self.modal.category_dropdown.value = "1"
        self.modal.description_field.value = "Test Description"
        
        self.modal._save(None)

        expected_data = TransactionCreate(
            amount=Decimal("123.45"),
            type=TransactionType.EXPENSE,
            category_id=1,
            description="Test Description",
            transaction_date=datetime.date.today()
        )
        
        # Сравниваем поля, так как объекты могут быть разными
        self.on_save.assert_called_once()
        called_arg = self.on_save.call_args[0][0]
        self.assertEqual(called_arg.amount, expected_data.amount)
        self.assertEqual(called_arg.type, expected_data.type)
        self.assertEqual(called_arg.category_id, expected_data.category_id)
        self.assertEqual(called_arg.description, expected_data.description)
        self.assertEqual(called_arg.transaction_date, expected_data.transaction_date)

        self.assertFalse(self.modal.dialog.open)

    def test_save_validation_failure(self):
        """Тест ошибки валидации при сохранении."""
        self.modal.open(self.page)

        self.modal.amount_field.value = "" # Пустая сумма
        self.modal.category_dropdown.value = None # Не выбрана категория

        self.modal._save(None)

        self.assertEqual(self.modal.amount_field.error_text, "Введите корректное число")
        self.assertEqual(self.modal.category_dropdown.error_text, "Выберите категорию")
        self.on_save.assert_not_called()
        self.assertTrue(self.modal.dialog.open)

if __name__ == '__main__':
    unittest.main()

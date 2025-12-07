"""
Тесты для модального окна LoanModal.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import flet as ft
import datetime
from decimal import Decimal

from components.loan_modal import LoanModal
from models.models import LenderDB
from models.enums import LoanType, LenderType


class TestLoanModal(unittest.TestCase):
    """Тесты для LoanModal."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.patcher = patch('finance_tracker_flet.components.loan_modal.get_all_lenders')
        self.mock_get_all_lenders = self.patcher.start()

        self.session = Mock()
        self.on_save = Mock()
        self.on_update = Mock()

        # Мокируем загрузку займодателей
        self.mock_lenders = [
            LenderDB(id=1, name="Bank 1", lender_type=LenderType.BANK),
            LenderDB(id=2, name="Individual", lender_type=LenderType.INDIVIDUAL),
        ]
        self.mock_get_all_lenders.return_value = self.mock_lenders

        self.modal = LoanModal(
            session=self.session,
            on_save=self.on_save,
            on_update=self.on_update
        )
        self.page = MagicMock()
        self.page.overlay = []
        self.modal.page = self.page

    def tearDown(self):
        self.patcher.stop()

    def test_initialization(self):
        """Тест инициализации LoanModal."""
        self.assertIsInstance(self.modal.dialog, ft.AlertDialog)
        self.assertEqual(self.modal.dialog.title.value, "Новый кредит")
        self.assertFalse(self.modal.dialog.open)
        # Call open to trigger _load_lenders
        self.modal.open(self.page)
        self.mock_get_all_lenders.assert_called_once_with(self.session)
        self.assertEqual(len(self.modal.lender_dropdown.options), 2)
        self.assertEqual(self.modal.lender_dropdown.options[0].key, "1")
        self.assertEqual(self.modal.lender_dropdown.options[0].text, "Bank 1")

    def test_open_in_create_mode(self):
        """Тест открытия модального окна в режиме создания."""
        self.modal.open(self.page)

        self.assertIsNone(self.modal.edit_loan_id)
        self.assertEqual(self.modal.dialog.title.value, "Новый кредит")
        self.assertIsNone(self.modal.lender_dropdown.value)
        self.assertEqual(self.modal.name_field.value, "")
        self.assertTrue(self.modal.dialog.open)
        self.assertIn(self.modal.dialog, self.page.overlay)

    def test_save_create_success(self):
        """Тест успешного сохранения нового кредита."""
        self.modal.open(self.page)
        
        # Заполняем поля
        self.modal.lender_dropdown.value = "1"
        self.modal.name_field.value = "New Loan"
        self.modal.type_dropdown.value = LoanType.MORTGAGE.value
        self.modal.amount_field.value = "100000.50"
        self.modal.interest_rate_field.value = "9.9"
        self.modal.issue_date = datetime.date(2024, 1, 1)
        self.modal.end_date = datetime.date(2025, 1, 1)

        self.modal._save(None)

        self.on_save.assert_called_once_with(
            1,
            "New Loan",
            LoanType.MORTGAGE,
            Decimal("100000.50"),
            datetime.date(2024, 1, 1),
            Decimal("9.9"),
            datetime.date(2025, 1, 1),
            None,
            None
        )
        self.on_update.assert_not_called()
        self.assertFalse(self.modal.dialog.open)
        
    def test_save_validation_failure_no_lender(self):
        """Тест ошибки валидации - не выбран займодатель."""
        self.modal.open(self.page)
        self.modal.lender_dropdown.value = None # No lender selected
        
        self.modal._save(None)

        self.assertEqual(self.modal.error_text.value, "Выберите займодателя")
        self.on_save.assert_not_called()
        self.assertTrue(self.modal.dialog.open)

    def test_save_validation_failure_bad_amount(self):
        """Тест ошибки валидации - некорректная сумма."""
        self.modal.open(self.page)
        self.modal.lender_dropdown.value = "1"
        self.modal.name_field.value = "Loan"
        self.modal.amount_field.value = "abc" # Bad amount
        self.modal.issue_date = datetime.date(2024, 1, 1)
        
        self.modal._save(None)

        self.assertEqual(self.modal.error_text.value, "Некорректная сумма кредита")
        self.on_save.assert_not_called()
        self.assertTrue(self.modal.dialog.open)


if __name__ == '__main__':
    unittest.main()

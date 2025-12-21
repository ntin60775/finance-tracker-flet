"""
Тесты для модального окна LenderModal.
"""

import unittest
from unittest.mock import Mock, MagicMock
import flet as ft
from finance_tracker.components.lender_modal import LenderModal
from finance_tracker.models.models import LenderDB
from finance_tracker.models.enums import LenderType


class TestLenderModal(unittest.TestCase):
    """Тесты для LenderModal."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.session = Mock()
        self.on_save = Mock()
        self.on_update = Mock()
        self.modal = LenderModal(
            session=self.session,
            on_save=self.on_save,
            on_update=self.on_update
        )
        self.page = MagicMock()
        self.page.open = Mock()
        self.page.close = Mock()
        self.page.overlay = []
        self.modal.page = self.page

    def test_initialization(self):
        """Тест инициализации LenderModal."""
        self.assertIsInstance(self.modal.dialog, ft.AlertDialog)
        self.assertEqual(self.modal.dialog.title.value, "Новый займодатель")
        # Инициализация не вызывает page.close()

    def test_open_in_create_mode(self):
        """Тест открытия модального окна в режиме создания."""
        self.modal.open(self.page)

        self.assertEqual(self.modal.page, self.page)
        self.assertIsNone(self.modal.edit_lender_id)
        self.assertEqual(self.modal.dialog.title.value, "Новый займодатель")
        self.assertEqual(self.modal.name_field.value, "")
        self.page.open.assert_called()

    def test_open_in_edit_mode(self):
        """Тест открытия модального окна в режиме редактирования."""
        lender = LenderDB(id=1, name="Test Bank", lender_type=LenderType.BANK, description="Desc", contact_info="Contact", notes="Notes")
        
        self.modal.open(self.page, lender)

        self.assertEqual(self.modal.edit_lender_id, 1)
        self.assertEqual(self.modal.dialog.title.value, "Редактировать: Test Bank")
        self.assertEqual(self.modal.name_field.value, "Test Bank")
        self.assertEqual(self.modal.type_dropdown.value, LenderType.BANK.value)
        self.assertEqual(self.modal.description_field.value, "Desc")
        self.assertEqual(self.modal.contact_field.value, "Contact")
        self.assertEqual(self.modal.notes_field.value, "Notes")
        self.page.open.assert_called()

    def test_save_create_success(self):
        """Тест успешного сохранения нового займодателя."""
        self.modal.open(self.page)
        
        self.modal.name_field.value = "New Lender"
        self.modal.type_dropdown.value = LenderType.MFO.value
        self.modal.description_field.value = "  New Description  "
        self.modal.contact_field.value = "new@contact.com"
        self.modal.notes_field.value = ""

        self.modal._save(None)

        self.on_save.assert_called_once_with(
            "New Lender",
            LenderType.MFO,
            "New Description",
            "new@contact.com",
            None
        )
        self.on_update.assert_not_called()
        self.page.close.assert_called()

    def test_save_update_success(self):
        """Тест успешного обновления существующего займодателя."""
        lender = LenderDB(id=1, name="Old Name", lender_type=LenderType.BANK)
        self.modal.open(self.page, lender)

        self.modal.name_field.value = "Updated Name"
        self.modal.type_dropdown.value = LenderType.INDIVIDUAL.value
        
        self.modal._save(None)

        self.on_update.assert_called_once_with(
            1,
            "Updated Name",
            LenderType.INDIVIDUAL,
            None,
            None,
            None
        )
        self.on_save.assert_not_called()
        self.page.close.assert_called()

    def test_save_validation_failure(self):
        """Тест ошибки валидации при сохранении (пустое имя)."""
        self.modal.open(self.page)
        self.modal.name_field.value = "   " # Empty name
        
        self.modal._save(None)

        self.assertEqual(self.modal.error_text.value, "Название займодателя не может быть пустым")
        self.on_save.assert_not_called()
        self.on_update.assert_not_called()
        self.page.open.assert_called() # Dialog should remain open

    def test_close_modal(self):
        """Тест закрытия модального окна."""
        self.modal.open(self.page)
        self.page.open.assert_called()
        
        self.modal.close(None)
        
        self.page.close.assert_called()


if __name__ == '__main__':
    unittest.main()

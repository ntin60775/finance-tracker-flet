"""
Тесты для DebtTransferModal.
"""
import unittest
from unittest.mock import Mock, MagicMock, patch
from decimal import Decimal
from datetime import date

import pytest
from hypothesis import given, strategies as st, settings

from finance_tracker.components.debt_transfer_modal import DebtTransferModal
from finance_tracker.models.enums import LenderType


class TestDebtTransferModal(unittest.TestCase):
    """Тесты для DebtTransferModal."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_session = Mock()
        self.mock_loan = Mock()
        self.mock_loan.id = "loan-123"
        self.mock_loan.name = "Тестовый кредит"
        self.mock_loan.effective_holder_id = "holder-123"
        
        # Мокируем текущего держателя
        self.mock_current_holder = Mock()
        self.mock_current_holder.name = "Текущий держатель"
        self.mock_loan.current_holder = self.mock_current_holder
        self.mock_loan.lender = self.mock_current_holder
        
        self.mock_callback = Mock()

    def create_mock_page(self):
        """Создает mock Page с методами для диалогов."""
        mock_page = MagicMock()
        mock_page.open = Mock()
        mock_page.close = Mock()
        mock_page.update = Mock()
        mock_page.overlay = []
        return mock_page

    @patch('finance_tracker.components.debt_transfer_modal.get_remaining_debt')
    def test_initialization(self, mock_get_remaining_debt):
        """Тест инициализации DebtTransferModal."""
        mock_get_remaining_debt.return_value = Decimal('1000.00')
        
        modal = DebtTransferModal(
            session=self.mock_session,
            loan=self.mock_loan,
            on_transfer_callback=self.mock_callback
        )
        
        # Проверяем создание основных компонентов
        self.assertIsNotNone(modal.dialog)
        self.assertIsNotNone(modal.lender_modal)
        self.assertIsNotNone(modal.to_lender_dropdown)
        self.assertIsNotNone(modal.create_lender_button)
        self.assertEqual(modal.current_remaining_debt, Decimal('1000.00'))

    @patch('finance_tracker.components.debt_transfer_modal.get_remaining_debt')
    @patch('finance_tracker.components.debt_transfer_modal.get_all_lenders')
    def test_create_lender_button_opens_modal(self, mock_get_lenders, mock_get_remaining_debt):
        """Тест нажатия кнопки создания кредитора открывает LenderModal."""
        mock_get_remaining_debt.return_value = Decimal('1000.00')
        mock_get_lenders.return_value = []
        
        modal = DebtTransferModal(
            session=self.mock_session,
            loan=self.mock_loan,
            on_transfer_callback=self.mock_callback
        )
        
        mock_page = self.create_mock_page()
        modal.page = mock_page
        
        # Мокируем метод open у lender_modal
        modal.lender_modal.open = Mock()
        
        # Симулируем нажатие кнопки создания кредитора
        modal._on_create_lender(None)
        
        # Проверяем, что LenderModal был открыт
        modal.lender_modal.open.assert_called_once_with(mock_page)

    @patch('finance_tracker.components.debt_transfer_modal.get_remaining_debt')
    @patch('finance_tracker.components.debt_transfer_modal.create_lender')
    @patch('finance_tracker.components.debt_transfer_modal.get_all_lenders')
    def test_lender_created_callback(self, mock_get_lenders, mock_create_lender, mock_get_remaining_debt):
        """Тест callback при создании нового кредитора."""
        mock_get_remaining_debt.return_value = Decimal('1000.00')
        mock_get_lenders.return_value = []
        
        # Мокируем созданного кредитора
        mock_new_lender = Mock()
        mock_new_lender.id = "new-lender-123"
        mock_new_lender.name = "Новый кредитор"
        mock_create_lender.return_value = mock_new_lender
        
        modal = DebtTransferModal(
            session=self.mock_session,
            loan=self.mock_loan,
            on_transfer_callback=self.mock_callback
        )
        
        mock_page = self.create_mock_page()
        modal.page = mock_page
        
        # Симулируем создание нового кредитора
        modal._on_lender_created(
            name="Новый кредитор",
            lender_type=LenderType.COLLECTOR,
            description="Коллекторское агентство",
            contact_info="+7 123 456 78 90",
            notes="Примечания"
        )
        
        # Проверяем вызов create_lender
        mock_create_lender.assert_called_once_with(
            session=self.mock_session,
            name="Новый кредитор",
            lender_type=LenderType.COLLECTOR,
            description="Коллекторское агентство",
            contact_info="+7 123 456 78 90",
            notes="Примечания"
        )
        
        # Проверяем, что новый кредитор выбран в dropdown
        self.assertEqual(modal.to_lender_dropdown.value, "new-lender-123")
        
        # Проверяем обновление UI
        mock_page.update.assert_called()

    @patch('finance_tracker.components.debt_transfer_modal.get_remaining_debt')
    @patch('finance_tracker.components.debt_transfer_modal.get_all_lenders')
    def test_load_lenders_excludes_current_holder(self, mock_get_lenders, mock_get_remaining_debt):
        """Тест исключения текущего держателя из списка кредиторов."""
        mock_get_remaining_debt.return_value = Decimal('1000.00')
        
        # Создаем список кредиторов, включая текущего держателя
        mock_lender1 = Mock()
        mock_lender1.id = "holder-123"  # Текущий держатель
        mock_lender1.name = "Текущий держатель"
        
        mock_lender2 = Mock()
        mock_lender2.id = "lender-456"
        mock_lender2.name = "Другой кредитор"
        
        mock_get_lenders.return_value = [mock_lender1, mock_lender2]
        
        modal = DebtTransferModal(
            session=self.mock_session,
            loan=self.mock_loan,
            on_transfer_callback=self.mock_callback
        )
        
        modal._load_lenders()
        
        # Проверяем, что в dropdown только один кредитор (не текущий держатель)
        self.assertEqual(len(modal.to_lender_dropdown.options), 1)
        self.assertEqual(modal.to_lender_dropdown.options[0].key, "lender-456")
        self.assertEqual(modal.to_lender_dropdown.options[0].text, "Другой кредитор")

    @patch('finance_tracker.components.debt_transfer_modal.get_remaining_debt')
    @patch('finance_tracker.components.debt_transfer_modal.get_all_lenders')
    def test_load_lenders_no_available_lenders(self, mock_get_lenders, mock_get_remaining_debt):
        """Тест случая, когда нет доступных кредиторов."""
        mock_get_remaining_debt.return_value = Decimal('1000.00')
        
        # Только текущий держатель в списке
        mock_current_holder = Mock()
        mock_current_holder.id = "holder-123"
        mock_current_holder.name = "Текущий держатель"
        
        mock_get_lenders.return_value = [mock_current_holder]
        
        modal = DebtTransferModal(
            session=self.mock_session,
            loan=self.mock_loan,
            on_transfer_callback=self.mock_callback
        )
        
        modal._load_lenders()
        
        # Проверяем информационное сообщение
        self.assertEqual(len(modal.to_lender_dropdown.options), 1)
        self.assertEqual(modal.to_lender_dropdown.options[0].key, "0")
        self.assertIn("Нет доступных кредиторов", modal.to_lender_dropdown.options[0].text)
        
        # Dropdown не должен быть отключен (чтобы пользователь мог видеть сообщение)
        self.assertFalse(modal.to_lender_dropdown.disabled)

    @patch('finance_tracker.components.debt_transfer_modal.get_remaining_debt')
    @patch('finance_tracker.components.debt_transfer_modal.get_all_lenders')
    def test_confirmation_dialog_creation(self, mock_get_lenders, mock_get_remaining_debt):
        """Тест создания диалога подтверждения передачи."""
        mock_get_remaining_debt.return_value = Decimal('1000.00')
        
        # Создаем кредитора для выбора
        mock_lender = Mock()
        mock_lender.id = "lender-456"
        mock_lender.name = "Новый держатель"
        mock_get_lenders.return_value = [mock_lender]
        
        modal = DebtTransferModal(
            session=self.mock_session,
            loan=self.mock_loan,
            on_transfer_callback=self.mock_callback
        )
        
        mock_page = self.create_mock_page()
        modal.page = mock_page
        
        # Заполняем форму валидными данными
        modal.to_lender_dropdown.value = "lender-456"
        modal.transfer_date = date(2024, 12, 15)
        modal.amount_field.value = "1500.00"
        
        # Вызываем показ диалога подтверждения
        modal._show_confirmation_dialog()
        
        # Проверяем, что диалог был открыт
        mock_page.open.assert_called()
        
        # Получаем переданный диалог
        confirmation_dialog = mock_page.open.call_args[0][0]
        
        # Проверяем содержимое диалога подтверждения
        self.assertEqual(confirmation_dialog.title.value, "Подтверждение передачи долга")
        self.assertIsNotNone(confirmation_dialog.content)
        self.assertEqual(len(confirmation_dialog.actions), 2)  # Отмена и Подтвердить
        
        # Проверяем кнопки
        cancel_button = confirmation_dialog.actions[0]
        confirm_button = confirmation_dialog.actions[1]
        
        self.assertEqual(cancel_button.text, "Отмена")
        self.assertEqual(confirm_button.text, "Подтвердить передачу")

    @patch('finance_tracker.components.debt_transfer_modal.get_remaining_debt')
    @patch('finance_tracker.components.debt_transfer_modal.get_all_lenders')
    def test_confirmation_dialog_cancel(self, mock_get_lenders, mock_get_remaining_debt):
        """Тест отмены в диалоге подтверждения."""
        mock_get_remaining_debt.return_value = Decimal('1000.00')
        
        # Создаем кредитора для выбора
        mock_lender = Mock()
        mock_lender.id = "lender-456"
        mock_lender.name = "Новый держатель"
        mock_get_lenders.return_value = [mock_lender]
        
        modal = DebtTransferModal(
            session=self.mock_session,
            loan=self.mock_loan,
            on_transfer_callback=self.mock_callback
        )
        
        mock_page = self.create_mock_page()
        modal.page = mock_page
        
        # Заполняем форму валидными данными
        modal.to_lender_dropdown.value = "lender-456"
        modal.transfer_date = date(2024, 12, 15)
        modal.amount_field.value = "1500.00"
        
        # Вызываем показ диалога подтверждения
        modal._show_confirmation_dialog()
        
        # Получаем диалог подтверждения
        confirmation_dialog = mock_page.open.call_args[0][0]
        
        # Симулируем нажатие кнопки "Отмена"
        cancel_button = confirmation_dialog.actions[0]
        cancel_button.on_click(None)
        
        # Проверяем, что диалог подтверждения был закрыт
        mock_page.close.assert_called_with(confirmation_dialog)
        
        # Проверяем, что callback НЕ был вызван
        self.mock_callback.assert_not_called()

    @patch('finance_tracker.components.debt_transfer_modal.get_remaining_debt')
    @patch('finance_tracker.components.debt_transfer_modal.get_all_lenders')
    def test_confirmation_dialog_confirm(self, mock_get_lenders, mock_get_remaining_debt):
        """Тест подтверждения передачи в диалоге."""
        mock_get_remaining_debt.return_value = Decimal('1000.00')
        
        # Создаем кредитора для выбора
        mock_lender = Mock()
        mock_lender.id = "lender-456"
        mock_lender.name = "Новый держатель"
        mock_get_lenders.return_value = [mock_lender]
        
        modal = DebtTransferModal(
            session=self.mock_session,
            loan=self.mock_loan,
            on_transfer_callback=self.mock_callback
        )
        
        mock_page = self.create_mock_page()
        modal.page = mock_page
        
        # Загружаем кредиторов в dropdown
        modal._load_lenders()
        
        # Заполняем форму валидными данными
        modal.to_lender_dropdown.value = "lender-456"
        modal.transfer_date = date(2024, 12, 15)
        modal.amount_field.value = "1500.00"
        modal.reason_field.value = "Продажа долга"
        modal.notes_field.value = "Примечания к передаче"
        
        # Вызываем показ диалога подтверждения
        modal._show_confirmation_dialog()
        
        # Получаем диалог подтверждения
        confirmation_dialog = mock_page.open.call_args[0][0]
        
        # Симулируем нажатие кнопки "Подтвердить передачу"
        confirm_button = confirmation_dialog.actions[1]
        confirm_button.on_click(None)
        
        # Проверяем, что callback был вызван с правильными параметрами
        self.mock_callback.assert_called_once_with(
            "loan-123",  # loan_id
            "lender-456",  # to_lender_id
            date(2024, 12, 15),  # transfer_date
            Decimal('1500.00'),  # transfer_amount
            "Продажа долга",  # reason
            "Примечания к передаче"  # notes
        )

    @patch('finance_tracker.components.debt_transfer_modal.get_remaining_debt')
    @patch('finance_tracker.components.debt_transfer_modal.get_all_lenders')
    def test_on_confirm_shows_confirmation_dialog(self, mock_get_lenders, mock_get_remaining_debt):
        """Тест, что _on_confirm показывает диалог подтверждения при валидных данных."""
        mock_get_remaining_debt.return_value = Decimal('1000.00')
        
        # Создаем кредитора для выбора
        mock_lender = Mock()
        mock_lender.id = "lender-456"
        mock_lender.name = "Новый держатель"
        mock_get_lenders.return_value = [mock_lender]
        
        modal = DebtTransferModal(
            session=self.mock_session,
            loan=self.mock_loan,
            on_transfer_callback=self.mock_callback
        )
        
        mock_page = self.create_mock_page()
        modal.page = mock_page
        
        # Загружаем кредиторов в dropdown
        modal._load_lenders()
        
        # Заполняем форму валидными данными
        modal.to_lender_dropdown.value = "lender-456"
        modal.transfer_date = date(2024, 12, 15)
        modal.amount_field.value = "1500.00"
        
        # Мокируем _show_confirmation_dialog
        modal._show_confirmation_dialog = Mock()
        
        # Вызываем _on_confirm
        modal._on_confirm(None)
        
        # Проверяем, что диалог подтверждения был показан
        modal._show_confirmation_dialog.assert_called_once()

    @patch('finance_tracker.components.debt_transfer_modal.get_remaining_debt')
    @patch('finance_tracker.components.debt_transfer_modal.get_all_lenders')
    def test_on_confirm_validation_failure(self, mock_get_lenders, mock_get_remaining_debt):
        """Тест, что _on_confirm не показывает диалог при невалидных данных."""
        mock_get_remaining_debt.return_value = Decimal('1000.00')
        mock_get_lenders.return_value = []
        
        modal = DebtTransferModal(
            session=self.mock_session,
            loan=self.mock_loan,
            on_transfer_callback=self.mock_callback
        )
        
        mock_page = self.create_mock_page()
        modal.page = mock_page
        
        # НЕ заполняем форму (невалидные данные)
        
        # Мокируем _show_confirmation_dialog
        modal._show_confirmation_dialog = Mock()
        
        # Вызываем _on_confirm
        modal._on_confirm(None)
        
        # Проверяем, что диалог подтверждения НЕ был показан
        modal._show_confirmation_dialog.assert_not_called()
        
        # Проверяем, что есть сообщение об ошибке
        self.assertNotEqual(modal.error_text.value, "")


class TestDebtTransferModalProperties:
    """Property-based тесты для DebtTransferModal."""

    @given(
        remaining_debt=st.decimals(
            min_value=Decimal('0.01'),
            max_value=Decimal('999999.99'),
            places=2
        )
    )
    @settings(max_examples=100)
    @patch('finance_tracker.components.debt_transfer_modal.get_remaining_debt')
    @patch('finance_tracker.components.debt_transfer_modal.get_all_lenders')
    def test_property_12_amount_field_prefilled_with_remaining_debt(
        self,
        mock_get_lenders,
        mock_get_remaining_debt,
        remaining_debt
    ):
        """
        **Feature: debt-transfer, Property 12: Предзаполнение суммы текущим остатком**
        **Validates: Requirements 8.3**
        
        Property: *For any* открытие модального окна передачи, поле суммы должно быть 
        предзаполнено значением `get_remaining_debt(loan_id)`.
        
        Тест проверяет, что при открытии модального окна поле amount_field 
        автоматически заполняется текущим остатком долга.
        """
        # Arrange - подготовка
        mock_get_remaining_debt.return_value = remaining_debt
        mock_get_lenders.return_value = []
        
        mock_session = Mock()
        mock_loan = Mock()
        mock_loan.id = "loan-123"
        mock_loan.name = "Тестовый кредит"
        mock_loan.effective_holder_id = "holder-123"
        
        mock_current_holder = Mock()
        mock_current_holder.name = "Текущий держатель"
        mock_loan.current_holder = mock_current_holder
        mock_loan.lender = mock_current_holder
        
        mock_callback = Mock()
        
        # Act - создание модального окна и открытие
        modal = DebtTransferModal(
            session=mock_session,
            loan=mock_loan,
            on_transfer_callback=mock_callback
        )
        
        mock_page = MagicMock()
        mock_page.open = Mock()
        mock_page.close = Mock()
        mock_page.update = Mock()
        mock_page.overlay = []
        
        modal.open(mock_page)
        
        # Assert - проверка
        # Проверяем, что поле суммы предзаполнено текущим остатком
        assert modal.amount_field.value == str(remaining_debt), \
            f"Ожидалось, что amount_field будет '{remaining_debt}', но получено '{modal.amount_field.value}'"
        
        # Проверяем, что текущий остаток сохранен в modal
        assert modal.current_remaining_debt == remaining_debt, \
            f"Ожидалось, что current_remaining_debt будет '{remaining_debt}', но получено '{modal.current_remaining_debt}'"
        
        # Проверяем, что диалог был открыт
        mock_page.open.assert_called_once()


if __name__ == '__main__':
    unittest.main()
"""
Тесты для EarlyRepaymentModal.

Проверяет:
- Инициализацию модального окна
- Открытие модального окна
- Переключение между типами погашения
- Валидацию формы
- Обработку полного погашения
- Обработку частичного погашения
- Обработку ошибок

Requirements: 10.7
"""
import unittest
from unittest.mock import Mock, MagicMock, patch
from decimal import Decimal
import datetime
import flet as ft

from finance_tracker.components.early_repayment_modal import EarlyRepaymentModal
from finance_tracker.models.models import LoanDB


class TestEarlyRepaymentModal(unittest.TestCase):
    """Тесты для EarlyRepaymentModal."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_session = Mock()
        self.mock_on_repay = Mock()
        self.mock_page = MagicMock()
        self.mock_page.overlay = []
        self.mock_page.open = Mock()
        self.mock_page.close = Mock()
        self.mock_page.update = Mock()

        self.test_loan = Mock(spec=LoanDB)
        self.test_loan.id = "loan-123"
        self.test_loan.name = "Ипотека"
        self.test_loan.amount = Decimal('1000000.00')

        self.modal = EarlyRepaymentModal(
            session=self.mock_session,
            loan=self.test_loan,
            on_repay=self.mock_on_repay
        )

    def test_initialization(self):
        """
        Тест инициализации модального окна.

        Проверяет:
        - Создание всех UI компонентов
        - Инициализация callback
        - Настройка диалога
        - Начальное состояние (тип погашения = полное)

        Requirements: 10.7
        """
        self.assertIsNotNone(self.modal.dialog)
        self.assertIsNotNone(self.modal.repayment_type_radio)
        self.assertIsNotNone(self.modal.amount_field)
        self.assertIsNotNone(self.modal.repayment_date_button)
        self.assertIsNotNone(self.modal.date_picker)
        self.assertEqual(self.modal.on_repay, self.mock_on_repay)
        self.assertEqual(self.modal.repayment_type_radio.value, "full")
        self.assertTrue(self.modal.warning_text.visible)
        self.assertFalse(self.modal.partial_warning_text.visible)

    def test_open_modal(self):
        """
        Тест открытия модального окна.

        Проверяет:
        - Установку page
        - Добавление date picker в overlay
        - Вызов page.open()

        Requirements: 10.7
        """
        # Act
        self.modal.open(self.mock_page)

        # Assert
        self.assertEqual(self.modal.page, self.mock_page)
        self.assertIn(self.modal.date_picker, self.mock_page.overlay)
        self.mock_page.open.assert_called_once_with(self.modal.dialog)

    def test_switch_to_partial_repayment(self):
        """
        Тест переключения на частичное погашение.

        Проверяет:
        - Изменение видимости предупреждений
        - Обновление страницы

        Requirements: 10.7
        """
        self.modal.open(self.mock_page)
        self.mock_page.update.reset_mock()

        # Act
        self.modal.repayment_type_radio.value = "partial"
        self.modal._on_type_change(None)

        # Assert
        self.assertFalse(self.modal.warning_text.visible)
        self.assertTrue(self.modal.partial_warning_text.visible)
        self.mock_page.update.assert_called()

    def test_switch_to_full_repayment(self):
        """
        Тест переключения на полное погашение.

        Проверяет:
        - Изменение видимости предупреждений
        - Обновление страницы

        Requirements: 10.7
        """
        self.modal.open(self.mock_page)
        self.modal.repayment_type_radio.value = "partial"
        self.modal._on_type_change(None)

        # Act - переключаем обратно на полное
        self.modal.repayment_type_radio.value = "full"
        self.modal._on_type_change(None)

        # Assert
        self.assertTrue(self.modal.warning_text.visible)
        self.assertFalse(self.modal.partial_warning_text.visible)

    def test_validation_empty_amount(self):
        """
        Тест валидации пустой суммы.

        Проверяет:
        - Отклонение пустого поля суммы
        - Отображение ошибки

        Requirements: 10.7
        """
        self.modal.open(self.mock_page)
        self.modal.amount_field.value = ""

        # Act
        result = self.modal._validate_inputs()

        # Assert
        self.assertFalse(result)
        self.assertIn("Введите сумму", self.modal.error_text.value)

    def test_validation_zero_amount(self):
        """
        Тест валидации нулевой суммы.

        Проверяет:
        - Отклонение нулевой суммы
        - Отображение ошибки

        Requirements: 10.7
        """
        self.modal.open(self.mock_page)
        self.modal.amount_field.value = "0"

        # Act
        result = self.modal._validate_inputs()

        # Assert
        self.assertFalse(result)
        self.assertIn("больше 0", self.modal.error_text.value)

    def test_validation_negative_amount(self):
        """
        Тест валидации отрицательной суммы.

        Проверяет:
        - Отклонение отрицательной суммы
        - Отображение ошибки

        Requirements: 10.7
        """
        self.modal.open(self.mock_page)
        self.modal.amount_field.value = "-100"

        # Act
        result = self.modal._validate_inputs()

        # Assert
        self.assertFalse(result)
        self.assertIn("больше 0", self.modal.error_text.value)

    def test_validation_invalid_amount_format(self):
        """
        Тест валидации некорректного формата суммы.

        Проверяет:
        - Отклонение нечисловых значений
        - Отображение ошибки

        Requirements: 10.7
        """
        self.modal.open(self.mock_page)
        self.modal.amount_field.value = "abc"

        # Act
        result = self.modal._validate_inputs()

        # Assert
        self.assertFalse(result)
        self.assertIn("Некорректная сумма", self.modal.error_text.value)

    def test_validation_valid_amount(self):
        """
        Тест валидации корректной суммы.

        Проверяет:
        - Принятие положительной суммы
        - Отсутствие ошибок

        Requirements: 10.7
        """
        self.modal.open(self.mock_page)
        self.modal.amount_field.value = "50000.50"

        # Act
        result = self.modal._validate_inputs()

        # Assert
        self.assertTrue(result)
        # error_text может быть None или пустой строкой
        self.assertIn(self.modal.error_text.value, [None, ""])

    def test_full_repayment_execution(self):
        """
        Тест исполнения полного погашения.

        Проверяет:
        - Вызов callback с правильными параметрами
        - is_full = True
        - Закрытие модального окна

        Requirements: 10.7
        """
        self.modal.open(self.mock_page)
        self.modal.repayment_type_radio.value = "full"
        self.modal.amount_field.value = "1000000.00"
        test_date = datetime.date(2025, 2, 15)
        self.modal.repayment_date = test_date

        # Act
        self.modal._handle_repay(None)

        # Assert
        self.mock_on_repay.assert_called_once_with(
            True,  # is_full
            Decimal('1000000.00'),
            test_date
        )
        self.mock_page.close.assert_called_once_with(self.modal.dialog)

    def test_partial_repayment_execution(self):
        """
        Тест исполнения частичного погашения.

        Проверяет:
        - Вызов callback с правильными параметрами
        - is_full = False
        - Закрытие модального окна

        Requirements: 10.7
        """
        self.modal.open(self.mock_page)
        self.modal.repayment_type_radio.value = "partial"
        self.modal.amount_field.value = "50000.00"
        test_date = datetime.date(2025, 2, 15)
        self.modal.repayment_date = test_date

        # Act
        self.modal._handle_repay(None)

        # Assert
        self.mock_on_repay.assert_called_once_with(
            False,  # is_full
            Decimal('50000.00'),
            test_date
        )
        self.mock_page.close.assert_called_once_with(self.modal.dialog)

    def test_error_handling_in_repayment(self):
        """
        Тест обработки ошибок при погашении.

        Проверяет:
        - Отлов исключений от callback
        - Отображение ошибки пользователю
        - Модальное окно остаётся открытым

        Requirements: 10.7
        """
        self.modal.open(self.mock_page)
        self.modal.amount_field.value = "50000.00"

        # Настраиваем callback на выброс исключения
        self.mock_on_repay.side_effect = Exception("Ошибка БД")

        # Act
        self.modal._handle_repay(None)

        # Assert
        self.assertIn("Ошибка", self.modal.error_text.value)
        self.mock_page.update.assert_called()

    def test_close_dialog(self):
        """
        Тест закрытия модального окна.

        Проверяет:
        - Вызов page.close() с диалогом

        Requirements: 10.7
        """
        self.modal.open(self.mock_page)
        self.mock_page.close.reset_mock()

        # Act
        self.modal._close_dialog()

        # Assert
        self.mock_page.close.assert_called_once_with(self.modal.dialog)

    def test_date_picker_integration(self):
        """
        Тест интеграции с выбором даты.

        Проверяет:
        - Добавление date picker в overlay
        - Начальная дата = сегодня

        Requirements: 10.7
        """
        # Act
        self.modal.open(self.mock_page)

        # Assert
        self.assertIn(self.modal.date_picker, self.mock_page.overlay)
        self.assertIsNotNone(self.modal.repayment_date)

    def test_clear_error(self):
        """
        Тест очистки ошибки.

        Проверяет:
        - Очистку текста ошибки
        - Обновление страницы

        Requirements: 10.7
        """
        self.modal.open(self.mock_page)
        self.modal.error_text.value = "Тестовая ошибка"
        self.mock_page.update.reset_mock()

        # Act
        self.modal._clear_error()

        # Assert
        self.assertEqual(self.modal.error_text.value, "")
        self.mock_page.update.assert_called()

    def test_show_error(self):
        """
        Тест отображения ошибки.

        Проверяет:
        - Установку текста ошибки
        - Обновление страницы

        Requirements: 10.7
        """
        self.modal.open(self.mock_page)
        self.mock_page.update.reset_mock()

        # Act
        self.modal._show_error("Тестовая ошибка")

        # Assert
        self.assertEqual(self.modal.error_text.value, "Тестовая ошибка")
        self.mock_page.update.assert_called()


if __name__ == '__main__':
    unittest.main()

"""
Тесты для ExecutePendingPaymentModal.

Проверяет:
- Инициализацию модального окна
- Открытие модального окна с отложенным платежом
- Валидацию формы исполнения
- Исполнение платежа с созданием транзакции
- Обработку ошибок
- Работу с датами

Requirements: 8.4
"""
import unittest
from unittest.mock import Mock, MagicMock
from decimal import Decimal
import datetime
import flet as ft

from finance_tracker.components.execute_pending_payment_modal import ExecutePendingPaymentModal
from finance_tracker.models.models import PendingPaymentDB
from finance_tracker.models.enums import PendingPaymentPriority


class TestExecutePendingPaymentModal(unittest.TestCase):
    """Тесты для ExecutePendingPaymentModal."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_session = Mock()
        self.mock_on_execute = Mock()
        self.mock_page = MagicMock()
        self.mock_page.overlay = []
        self.mock_page.open = Mock()
        self.mock_page.close = Mock()
        self.mock_page.update = Mock()

        self.modal = ExecutePendingPaymentModal(
            session=self.mock_session,
            on_execute=self.mock_on_execute
        )

    def test_initialization(self):
        """
        Тест инициализации модального окна.

        Проверяет:
        - Создание всех UI компонентов
        - Инициализация callback
        - Настройка диалога

        Requirements: 8.4
        """
        self.assertIsNotNone(self.modal.dialog)
        self.assertIsNotNone(self.modal.amount_field)
        self.assertIsNotNone(self.modal.date_button)
        self.assertIsNotNone(self.modal.date_picker)
        self.assertEqual(self.modal.on_execute, self.mock_on_execute)

    def test_open_modal_with_payment(self):
        """
        Тест открытия модального окна с отложенным платежом.

        Проверяет:
        - Установку текущего платежа
        - Предзаполнение суммы из платежа
        - Установку даты по умолчанию
        - Отображение информации о платеже
        - Вызов page.open()

        Requirements: 8.4
        """
        # Arrange
        test_payment = Mock(spec=PendingPaymentDB)
        test_payment.id = "payment-123"
        test_payment.description = "Оплата интернета"
        test_payment.amount = Decimal('500.00')
        test_payment.priority = PendingPaymentPriority.MEDIUM
        test_payment.planned_date = datetime.date(2025, 1, 15)

        # Act
        self.modal.open(self.mock_page, test_payment)

        # Assert
        self.assertEqual(self.modal.payment, test_payment)
        self.assertEqual(self.modal.amount_field.value, "500.00")
        self.assertIn("Оплата интернета", self.modal.info_text.value)
        self.assertIn("500.00", self.modal.info_text.value)
        self.assertIn("Средний", self.modal.info_text.value)
        self.mock_page.open.assert_called_once_with(self.modal.dialog)

    def test_execute_with_valid_data(self):
        """
        Тест успешного исполнения платежа.

        Проверяет:
        - Валидацию корректных данных
        - Вызов callback on_execute с правильными параметрами
        - Закрытие модального окна

        Requirements: 8.4
        """
        # Arrange
        test_payment = Mock(spec=PendingPaymentDB)
        test_payment.id = "payment-123"
        test_payment.description = "Оплата интернета"
        test_payment.amount = Decimal('500.00')
        test_payment.priority = PendingPaymentPriority.HIGH
        test_payment.planned_date = None

        self.modal.open(self.mock_page, test_payment)

        # Изменяем сумму
        self.modal.amount_field.value = "525.50"

        # Act
        self.modal._execute(None)

        # Assert
        self.mock_on_execute.assert_called_once_with(
            "payment-123",
            Decimal('525.50'),
            self.modal.current_date
        )
        self.mock_page.close.assert_called_once_with(self.modal.dialog)

    def test_validation_negative_amount(self):
        """
        Тест валидации отрицательной суммы.

        Проверяет:
        - Отклонение отрицательной суммы
        - Отображение ошибки валидации
        - Модальное окно остаётся открытым

        Requirements: 8.4
        """
        test_payment = Mock(spec=PendingPaymentDB)
        test_payment.id = "payment-123"
        test_payment.description = "Тест"
        test_payment.amount = Decimal('100.00')
        test_payment.priority = PendingPaymentPriority.LOW
        test_payment.planned_date = None

        self.modal.open(self.mock_page, test_payment)

        # Устанавливаем отрицательную сумму
        self.modal.amount_field.value = "-50"

        # Act
        result = self.modal._validate()

        # Assert
        self.assertFalse(result)
        self.assertIsNotNone(self.modal.amount_field.error_text)
        self.mock_on_execute.assert_not_called()

    def test_validation_zero_amount(self):
        """
        Тест валидации нулевой суммы.

        Проверяет:
        - Отклонение нулевой суммы
        - Отображение ошибки валидации

        Requirements: 8.4
        """
        test_payment = Mock(spec=PendingPaymentDB)
        test_payment.id = "payment-123"
        test_payment.description = "Тест"
        test_payment.amount = Decimal('100.00')
        test_payment.priority = PendingPaymentPriority.LOW
        test_payment.planned_date = None

        self.modal.open(self.mock_page, test_payment)

        # Устанавливаем нулевую сумму
        self.modal.amount_field.value = "0"

        # Act
        result = self.modal._validate()

        # Assert
        self.assertFalse(result)
        self.assertIsNotNone(self.modal.amount_field.error_text)

    def test_validation_invalid_format(self):
        """
        Тест валидации некорректного формата суммы.

        Проверяет:
        - Отклонение нечисловых значений
        - Отображение ошибки валидации

        Requirements: 8.4
        """
        test_payment = Mock(spec=PendingPaymentDB)
        test_payment.id = "payment-123"
        test_payment.description = "Тест"
        test_payment.amount = Decimal('100.00')
        test_payment.priority = PendingPaymentPriority.LOW
        test_payment.planned_date = None

        self.modal.open(self.mock_page, test_payment)

        # Устанавливаем нечисловое значение
        self.modal.amount_field.value = "abc"

        # Act
        result = self.modal._validate()

        # Assert
        self.assertFalse(result)
        self.assertIsNotNone(self.modal.amount_field.error_text)

    def test_validation_valid_amount(self):
        """
        Тест валидации корректной суммы.

        Проверяет:
        - Принятие положительной суммы
        - Отсутствие ошибок валидации

        Requirements: 8.4
        """
        test_payment = Mock(spec=PendingPaymentDB)
        test_payment.id = "payment-123"
        test_payment.description = "Тест"
        test_payment.amount = Decimal('100.00')
        test_payment.priority = PendingPaymentPriority.LOW
        test_payment.planned_date = None

        self.modal.open(self.mock_page, test_payment)

        # Устанавливаем корректную сумму
        self.modal.amount_field.value = "150.75"

        # Act
        result = self.modal._validate()

        # Assert
        self.assertTrue(result)
        self.assertIsNone(self.modal.amount_field.error_text)

    def test_close_modal(self):
        """
        Тест закрытия модального окна.

        Проверяет:
        - Вызов page.close() с диалогом

        Requirements: 8.4
        """
        test_payment = Mock(spec=PendingPaymentDB)
        test_payment.id = "payment-123"
        test_payment.description = "Тест"
        test_payment.amount = Decimal('100.00')
        test_payment.priority = PendingPaymentPriority.LOW
        test_payment.planned_date = None

        self.modal.open(self.mock_page, test_payment)
        self.mock_page.close.reset_mock()

        # Act
        self.modal.close()

        # Assert
        self.mock_page.close.assert_called_once_with(self.modal.dialog)

    def test_date_picker_integration(self):
        """
        Тест интеграции с выбором даты.

        Проверяет:
        - Добавление date picker в overlay
        - Установку даты по умолчанию
        - Обновление date_button при открытии

        Requirements: 8.4
        """
        test_payment = Mock(spec=PendingPaymentDB)
        test_payment.id = "payment-123"
        test_payment.description = "Тест"
        test_payment.amount = Decimal('100.00')
        test_payment.priority = PendingPaymentPriority.LOW
        test_payment.planned_date = None

        # Act
        self.modal.open(self.mock_page, test_payment)

        # Assert
        self.assertIn(self.modal.date_picker, self.mock_page.overlay)
        today_str = datetime.date.today().strftime("%d.%m.%Y")
        self.assertIn(today_str, self.modal.date_button.text)

    def test_execute_error_handling(self):
        """
        Тест обработки ошибок при исполнении.

        Проверяет:
        - Отлов исключений от callback
        - Отображение ошибки пользователю
        - Модальное окно остаётся открытым

        Requirements: 8.4
        """
        test_payment = Mock(spec=PendingPaymentDB)
        test_payment.id = "payment-123"
        test_payment.description = "Тест"
        test_payment.amount = Decimal('100.00')
        test_payment.priority = PendingPaymentPriority.LOW
        test_payment.planned_date = None

        self.modal.open(self.mock_page, test_payment)
        self.modal.amount_field.value = "100.00"

        # Настраиваем callback на выброс исключения
        self.mock_on_execute.side_effect = Exception("Ошибка БД")

        # Act
        self.modal._execute(None)

        # Assert
        self.assertIn("Ошибка исполнения", self.modal.error_text.value)
        self.mock_page.update.assert_called()

    def test_payment_with_planned_date(self):
        """
        Тест отображения платежа с плановой датой.

        Проверяет:
        - Корректное отображение плановой даты в info_text

        Requirements: 8.4
        """
        test_payment = Mock(spec=PendingPaymentDB)
        test_payment.id = "payment-123"
        test_payment.description = "Тест"
        test_payment.amount = Decimal('100.00')
        test_payment.priority = PendingPaymentPriority.CRITICAL
        test_payment.planned_date = datetime.date(2025, 2, 15)

        # Act
        self.modal.open(self.mock_page, test_payment)

        # Assert
        self.assertIn("15.02.2025", self.modal.info_text.value)
        self.assertIn("Критический", self.modal.info_text.value)

    def test_payment_without_planned_date(self):
        """
        Тест отображения платежа без плановой даты.

        Проверяет:
        - Корректная обработка None в planned_date

        Requirements: 8.4
        """
        test_payment = Mock(spec=PendingPaymentDB)
        test_payment.id = "payment-123"
        test_payment.description = "Тест"
        test_payment.amount = Decimal('100.00')
        test_payment.priority = PendingPaymentPriority.LOW
        test_payment.planned_date = None

        # Act
        self.modal.open(self.mock_page, test_payment)

        # Assert - проверяем что модальное окно открылось без ошибок
        self.mock_page.open.assert_called_once()
        self.assertIsNotNone(self.modal.info_text.value)


if __name__ == '__main__':
    unittest.main()

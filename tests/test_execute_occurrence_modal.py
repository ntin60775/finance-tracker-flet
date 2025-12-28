"""
Тесты для ExecuteOccurrenceModal.

Проверяет:
- Инициализацию модального окна
- Открытие модального окна с плановым вхождением
- Валидацию формы исполнения
- Исполнение вхождения с созданием транзакции
- Пропуск вхождения с указанием причины
- Переключение между формами исполнения и пропуска
- Обработку ошибок

Requirements: 5.4, 5.5
"""
import unittest
from unittest.mock import Mock, MagicMock, patch
from decimal import Decimal
import datetime
import flet as ft

from finance_tracker.components.execute_occurrence_modal import ExecuteOccurrenceModal
from finance_tracker.models import PlannedOccurrence, OccurrenceStatus, TransactionType


class TestExecuteOccurrenceModal(unittest.TestCase):
    """Тесты для ExecuteOccurrenceModal."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_session = Mock()
        self.mock_on_execute = Mock()
        self.mock_on_skip = Mock()
        self.mock_page = MagicMock()
        self.mock_page.overlay = []
        self.mock_page.open = Mock()
        self.mock_page.close = Mock()
        self.mock_page.update = Mock()

        self.modal = ExecuteOccurrenceModal(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_skip=self.mock_on_skip
        )

    def test_initialization(self):
        """
        Тест инициализации модального окна.

        Проверяет:
        - Создание всех UI компонентов
        - Инициализация callbacks
        - Настройка диалога

        Requirements: 5.4, 5.5
        """
        self.assertIsNotNone(self.modal.dialog)
        self.assertIsNotNone(self.modal.amount_field)
        self.assertIsNotNone(self.modal.date_button)
        self.assertIsNotNone(self.modal.skip_reason_field)
        self.assertIsNotNone(self.modal.execute_button)
        self.assertIsNotNone(self.modal.skip_button)
        self.assertEqual(self.modal.on_execute, self.mock_on_execute)
        self.assertEqual(self.modal.on_skip, self.mock_on_skip)

    def test_open_modal_with_occurrence(self):
        """
        Тест открытия модального окна с плановым вхождением.

        Проверяет:
        - Установку текущего вхождения
        - Предзаполнение суммы из вхождения
        - Установку даты по умолчанию
        - Отображение информации о вхождении
        - Вызов page.open()

        Requirements: 5.4
        """
        # Arrange
        test_occurrence = Mock(spec=PlannedOccurrence)
        test_occurrence.id = "occ-123"
        test_occurrence.amount = Decimal('150.50')
        test_occurrence.occurrence_date = datetime.date(2025, 1, 15)
        test_date = datetime.date(2025, 1, 20)

        # Act
        self.modal.open(self.mock_page, test_occurrence, test_date)

        # Assert
        self.assertEqual(self.modal.occurrence, test_occurrence)
        self.assertEqual(self.modal.amount_field.value, "150.50")
        self.assertEqual(self.modal.current_date, test_date)
        self.assertIn("15.01.2025", self.modal.info_text.value)
        self.assertIn("150.50", self.modal.info_text.value)
        self.mock_page.open.assert_called_once_with(self.modal.dialog)

    def test_execute_with_valid_data(self):
        """
        Тест успешного исполнения вхождения.

        Проверяет:
        - Валидацию корректных данных
        - Вызов callback on_execute с правильными параметрами
        - Закрытие модального окна

        Requirements: 5.4
        """
        # Arrange
        test_occurrence = Mock(spec=PlannedOccurrence)
        test_occurrence.id = "occ-123"
        test_occurrence.amount = Decimal('100.00')
        test_occurrence.occurrence_date = datetime.date(2025, 1, 15)

        self.modal.open(self.mock_page, test_occurrence)

        # Изменяем сумму
        self.modal.amount_field.value = "125.75"

        # Act
        self.modal._execute(None)

        # Assert
        self.mock_on_execute.assert_called_once_with(
            "occ-123",
            Decimal('125.75'),
            self.modal.current_date
        )
        self.mock_page.close.assert_called_once_with(self.modal.dialog)

    def test_execute_with_invalid_amount(self):
        """
        Тест валидации невалидной суммы при исполнении.

        Проверяет:
        - Отклонение отрицательной суммы
        - Отклонение нулевой суммы
        - Отклонение нечислового значения
        - Отображение ошибки валидации
        - Модальное окно остаётся открытым

        Requirements: 5.4
        """
        test_occurrence = Mock(spec=PlannedOccurrence)
        test_occurrence.id = "occ-123"
        test_occurrence.amount = Decimal('100.00')
        test_occurrence.occurrence_date = datetime.date(2025, 1, 15)

        self.modal.open(self.mock_page, test_occurrence)

        # Test negative amount
        self.modal.amount_field.value = "-50"
        self.modal._execute(None)
        self.assertIsNotNone(self.modal.amount_field.error_text)
        self.mock_on_execute.assert_not_called()

        # Reset
        self.mock_on_execute.reset_mock()
        self.modal.amount_field.error_text = None

        # Test zero amount
        self.modal.amount_field.value = "0"
        self.modal._execute(None)
        self.assertIsNotNone(self.modal.amount_field.error_text)
        self.mock_on_execute.assert_not_called()

        # Reset
        self.mock_on_execute.reset_mock()
        self.modal.amount_field.error_text = None

        # Test invalid format
        self.modal.amount_field.value = "abc"
        self.modal._execute(None)
        self.assertIsNotNone(self.modal.amount_field.error_text)
        self.mock_on_execute.assert_not_called()

    def test_show_skip_form(self):
        """
        Тест переключения на форму пропуска.

        Проверяет:
        - Скрытие полей исполнения (дата, сумма)
        - Отображение поля причины пропуска
        - Изменение видимости кнопок
        - Вызов page.update()

        Requirements: 5.5
        """
        test_occurrence = Mock(spec=PlannedOccurrence)
        test_occurrence.id = "occ-123"
        test_occurrence.amount = Decimal('100.00')
        test_occurrence.occurrence_date = datetime.date(2025, 1, 15)

        self.modal.open(self.mock_page, test_occurrence)
        self.mock_page.update.reset_mock()

        # Act
        self.modal._show_skip_form()

        # Assert
        self.assertFalse(self.modal.date_button.visible)
        self.assertFalse(self.modal.amount_field.visible)
        self.assertTrue(self.modal.skip_reason_field.visible)
        self.assertFalse(self.modal.execute_button.visible)
        self.assertFalse(self.modal.skip_button.visible)
        self.assertTrue(self.modal.confirm_skip_button.visible)
        self.assertTrue(self.modal.cancel_skip_button.visible)
        self.mock_page.update.assert_called()

    def test_hide_skip_form(self):
        """
        Тест возврата к форме исполнения из формы пропуска.

        Проверяет:
        - Отображение полей исполнения
        - Скрытие поля причины пропуска
        - Восстановление кнопок исполнения

        Requirements: 5.5
        """
        test_occurrence = Mock(spec=PlannedOccurrence)
        test_occurrence.id = "occ-123"
        test_occurrence.amount = Decimal('100.00')
        test_occurrence.occurrence_date = datetime.date(2025, 1, 15)

        self.modal.open(self.mock_page, test_occurrence)
        self.modal._show_skip_form()

        # Act
        self.modal._hide_skip_form()

        # Assert
        self.assertTrue(self.modal.date_button.visible)
        self.assertTrue(self.modal.amount_field.visible)
        self.assertFalse(self.modal.skip_reason_field.visible)
        self.assertTrue(self.modal.execute_button.visible)
        self.assertTrue(self.modal.skip_button.visible)
        self.assertFalse(self.modal.confirm_skip_button.visible)
        self.assertFalse(self.modal.cancel_skip_button.visible)

    def test_confirm_skip_with_reason(self):
        """
        Тест пропуска вхождения с указанием причины.

        Проверяет:
        - Вызов callback on_skip с ID и причиной
        - Закрытие модального окна

        Requirements: 5.5
        """
        test_occurrence = Mock(spec=PlannedOccurrence)
        test_occurrence.id = "occ-123"
        test_occurrence.amount = Decimal('100.00')
        test_occurrence.occurrence_date = datetime.date(2025, 1, 15)

        self.modal.open(self.mock_page, test_occurrence)
        self.modal._show_skip_form()

        # Вводим причину
        self.modal.skip_reason_field.value = "Забыл внести платёж"

        # Act
        self.modal._confirm_skip(None)

        # Assert
        self.mock_on_skip.assert_called_once_with("occ-123", "Забыл внести платёж")
        self.mock_page.close.assert_called_with(self.modal.dialog)

    def test_confirm_skip_without_reason(self):
        """
        Тест пропуска вхождения без указания причины.

        Проверяет:
        - Вызов callback on_skip с ID и None
        - Обработка пустого поля причины

        Requirements: 5.5
        """
        test_occurrence = Mock(spec=PlannedOccurrence)
        test_occurrence.id = "occ-123"
        test_occurrence.amount = Decimal('100.00')
        test_occurrence.occurrence_date = datetime.date(2025, 1, 15)

        self.modal.open(self.mock_page, test_occurrence)
        self.modal._show_skip_form()

        # Оставляем пустым
        self.modal.skip_reason_field.value = ""

        # Act
        self.modal._confirm_skip(None)

        # Assert
        self.mock_on_skip.assert_called_once_with("occ-123", None)

    def test_close_modal(self):
        """
        Тест закрытия модального окна.

        Проверяет:
        - Вызов page.close() с диалогом

        Requirements: 5.4, 5.5
        """
        test_occurrence = Mock(spec=PlannedOccurrence)
        test_occurrence.id = "occ-123"
        test_occurrence.amount = Decimal('100.00')
        test_occurrence.occurrence_date = datetime.date(2025, 1, 15)

        self.modal.open(self.mock_page, test_occurrence)
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

        Requirements: 5.4
        """
        test_occurrence = Mock(spec=PlannedOccurrence)
        test_occurrence.id = "occ-123"
        test_occurrence.amount = Decimal('100.00')
        test_occurrence.occurrence_date = datetime.date(2025, 1, 15)
        test_date = datetime.date(2025, 1, 20)

        # Act
        self.modal.open(self.mock_page, test_occurrence, test_date)

        # Assert
        self.assertIn(self.modal.date_picker, self.mock_page.overlay)
        # date_picker.value может быть datetime, проверяем дату
        if hasattr(self.modal.date_picker.value, 'date'):
            self.assertEqual(self.modal.date_picker.value.date(), test_date)
        else:
            self.assertEqual(self.modal.date_picker.value, test_date)
        self.assertIn("20.01.2025", self.modal.date_button.text)

    def test_execute_error_handling(self):
        """
        Тест обработки ошибок при исполнении.

        Проверяет:
        - Отлов исключений от callback
        - Отображение ошибки пользователю
        - Модальное окно остаётся открытым

        Requirements: 5.4
        """
        test_occurrence = Mock(spec=PlannedOccurrence)
        test_occurrence.id = "occ-123"
        test_occurrence.amount = Decimal('100.00')
        test_occurrence.occurrence_date = datetime.date(2025, 1, 15)

        self.modal.open(self.mock_page, test_occurrence)
        self.modal.amount_field.value = "100.00"

        # Настраиваем callback на выброс исключения
        self.mock_on_execute.side_effect = Exception("Ошибка БД")

        # Act
        self.modal._execute(None)

        # Assert
        self.assertIn("Ошибка исполнения", self.modal.error_text.value)
        self.mock_page.update.assert_called()

    def test_skip_error_handling(self):
        """
        Тест обработки ошибок при пропуске.

        Проверяет:
        - Отлов исключений от callback
        - Отображение ошибки пользователю
        - Модальное окно остаётся открытым

        Requirements: 5.5
        """
        test_occurrence = Mock(spec=PlannedOccurrence)
        test_occurrence.id = "occ-123"
        test_occurrence.amount = Decimal('100.00')
        test_occurrence.occurrence_date = datetime.date(2025, 1, 15)

        self.modal.open(self.mock_page, test_occurrence)
        self.modal._show_skip_form()

        # Настраиваем callback на выброс исключения
        self.mock_on_skip.side_effect = Exception("Ошибка БД")

        # Act
        self.modal._confirm_skip(None)

        # Assert
        self.assertIn("Ошибка пропуска", self.modal.error_text.value)
        self.mock_page.update.assert_called()


if __name__ == '__main__':
    unittest.main()

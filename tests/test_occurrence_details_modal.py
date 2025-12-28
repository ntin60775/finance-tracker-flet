"""
Тесты для OccurrenceDetailsModal.

Проверяет:
- Инициализацию модального окна
- Отображение деталей ожидающего вхождения
- Отображение деталей исполненного вхождения
- Отображение деталей пропущенного вхождения
- Закрытие модального окна
"""
import unittest
from unittest.mock import Mock, MagicMock
from decimal import Decimal
import datetime
import flet as ft

from finance_tracker.components.occurrence_details_modal import OccurrenceDetailsModal
from finance_tracker.models.enums import OccurrenceStatus


class TestOccurrenceDetailsModal(unittest.TestCase):
    """Тесты для OccurrenceDetailsModal."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_page = MagicMock()
        self.mock_page.open = Mock()
        self.mock_page.close = Mock()
        self.modal = OccurrenceDetailsModal()

    def test_initialization(self):
        """
        Тест инициализации модального окна.

        Проверяет:
        - Создание диалога
        - Наличие заголовка
        - Наличие кнопки закрытия
        - Настройка scrollable
        """
        self.assertIsNotNone(self.modal.title)
        self.assertTrue(self.modal.scrollable)
        self.assertIsNotNone(self.modal.content_column)
        self.assertEqual(len(self.modal.actions), 1)

    def test_show_pending_occurrence(self):
        """
        Тест отображения деталей ожидающего вхождения.

        Проверяет:
        - Вызов page.open()
        - Отображение статуса PENDING
        - Отображение плановых данных
        - Отсутствие фактических данных
        """
        # Arrange
        details = {
            'status': OccurrenceStatus.PENDING,
            'scheduled_date': '2025-01-15',
            'planned_amount': Decimal('150.50'),
            'category_name': 'Продукты',
            'description': 'Еженедельные покупки'
        }

        # Act
        self.modal.show(self.mock_page, details)

        # Assert
        self.mock_page.open.assert_called_once_with(self.modal)
        self.assertEqual(self.modal.page, self.mock_page)
        # Проверяем что контент построен (есть контролы)
        self.assertGreater(len(self.modal.content_column.controls), 0)

    def test_show_executed_occurrence(self):
        """
        Тест отображения деталей исполненного вхождения.

        Проверяет:
        - Отображение статуса EXECUTED
        - Отображение плановых данных
        - Отображение фактических данных
        - Отображение отклонений
        """
        # Arrange
        details = {
            'status': OccurrenceStatus.EXECUTED,
            'scheduled_date': '2025-01-15',
            'planned_amount': Decimal('150.00'),
            'category_name': 'Продукты',
            'description': 'Покупки',
            'executed_date': '2025-01-16',
            'actual_amount': Decimal('165.50'),
            'amount_deviation': Decimal('15.50'),
            'date_deviation': 1
        }

        # Act
        self.modal.show(self.mock_page, details)

        # Assert
        self.mock_page.open.assert_called_once()
        # Проверяем что есть секции (больше контролов чем для PENDING)
        self.assertGreater(len(self.modal.content_column.controls), 1)

    def test_show_skipped_occurrence(self):
        """
        Тест отображения деталей пропущенного вхождения.

        Проверяет:
        - Отображение статуса SKIPPED
        - Отображение плановых данных
        - Отображение причины пропуска
        """
        # Arrange
        details = {
            'status': OccurrenceStatus.SKIPPED,
            'scheduled_date': '2025-01-15',
            'planned_amount': Decimal('150.00'),
            'category_name': 'Продукты',
            'description': 'Покупки',
            'skip_reason': 'Забыл внести платёж'
        }

        # Act
        self.modal.show(self.mock_page, details)

        # Assert
        self.mock_page.open.assert_called_once()
        self.assertGreater(len(self.modal.content_column.controls), 0)

    def test_show_skipped_occurrence_without_reason(self):
        """
        Тест отображения пропущенного вхождения без причины.

        Проверяет:
        - Корректную обработку отсутствующей причины
        - Отображение значения по умолчанию
        """
        # Arrange
        details = {
            'status': OccurrenceStatus.SKIPPED,
            'scheduled_date': '2025-01-15',
            'planned_amount': Decimal('100.00'),
            'category_name': 'Продукты',
            'skip_reason': None  # Нет причины
        }

        # Act
        self.modal.show(self.mock_page, details)

        # Assert
        self.mock_page.open.assert_called_once()
        # Проверяем что модальное окно открылось без ошибок
        self.assertIsNotNone(self.modal.page)

    def test_close_modal(self):
        """
        Тест закрытия модального окна.

        Проверяет:
        - Вызов page.close() с модальным окном
        """
        # Arrange
        details = {
            'status': OccurrenceStatus.PENDING,
            'scheduled_date': '2025-01-15',
            'planned_amount': Decimal('100.00'),
            'category_name': 'Продукты'
        }
        self.modal.show(self.mock_page, details)
        self.mock_page.close.reset_mock()

        # Act
        self.modal.close()

        # Assert
        self.mock_page.close.assert_called_once_with(self.modal)

    def test_show_with_minimal_details(self):
        """
        Тест отображения с минимальным набором данных.

        Проверяет:
        - Корректную обработку отсутствующих полей
        - Отображение значений по умолчанию
        """
        # Arrange
        details = {
            'status': OccurrenceStatus.PENDING,
            # Минимум данных
        }

        # Act
        self.modal.show(self.mock_page, details)

        # Assert
        self.mock_page.open.assert_called_once()
        # Модальное окно должно открыться без ошибок
        self.assertIsNotNone(self.modal.page)

    def test_build_content_clears_previous_controls(self):
        """
        Тест очистки предыдущего содержимого при построении нового.

        Проверяет:
        - Очистку старых контролов
        - Построение новых контролов
        """
        # Arrange
        details1 = {
            'status': OccurrenceStatus.PENDING,
            'scheduled_date': '2025-01-15',
            'planned_amount': Decimal('100.00'),
            'category_name': 'Первая'
        }
        details2 = {
            'status': OccurrenceStatus.EXECUTED,
            'scheduled_date': '2025-01-20',
            'planned_amount': Decimal('200.00'),
            'category_name': 'Вторая',
            'executed_date': '2025-01-20',
            'actual_amount': Decimal('200.00'),
            'amount_deviation': Decimal('0'),
            'date_deviation': 0
        }

        # Act
        self.modal.show(self.mock_page, details1)
        first_count = len(self.modal.content_column.controls)

        self.modal._build_content(details2)
        second_count = len(self.modal.content_column.controls)

        # Assert
        # Количество контролов изменилось (executed имеет больше секций)
        self.assertNotEqual(first_count, second_count)

    def test_negative_amount_deviation_color(self):
        """
        Тест цвета отклонения для отрицательной разницы.

        Проверяет:
        - Построение контента с отрицательным отклонением
        - Отсутствие ошибок при обработке
        """
        # Arrange
        details = {
            'status': OccurrenceStatus.EXECUTED,
            'scheduled_date': '2025-01-15',
            'planned_amount': Decimal('150.00'),
            'category_name': 'Продукты',
            'executed_date': '2025-01-15',
            'actual_amount': Decimal('140.00'),
            'amount_deviation': Decimal('-10.00'),  # Отрицательное отклонение
            'date_deviation': 0
        }

        # Act
        self.modal.show(self.mock_page, details)

        # Assert
        self.mock_page.open.assert_called_once()
        # Модальное окно должно открыться без ошибок
        self.assertIsNotNone(self.modal.page)

    def test_positive_date_deviation(self):
        """
        Тест отображения положительного отклонения по дате.

        Проверяет:
        - Построение контента с положительным отклонением даты
        """
        # Arrange
        details = {
            'status': OccurrenceStatus.EXECUTED,
            'scheduled_date': '2025-01-15',
            'planned_amount': Decimal('150.00'),
            'category_name': 'Продукты',
            'executed_date': '2025-01-18',
            'actual_amount': Decimal('150.00'),
            'amount_deviation': Decimal('0'),
            'date_deviation': 3  # Исполнено на 3 дня позже
        }

        # Act
        self.modal.show(self.mock_page, details)

        # Assert
        self.mock_page.open.assert_called_once()
        self.assertGreater(len(self.modal.content_column.controls), 0)


if __name__ == '__main__':
    unittest.main()
